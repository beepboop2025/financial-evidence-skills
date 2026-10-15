"""Bounded MCP sessions whose context managers always belong to one task."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import dataclass
import time

MAX_RESPONSE_BYTES = 2_097_152
CLEANUP_TIMEOUT_SECONDS = 5


class MCPTransportError(RuntimeError):
    """A session failed; the request was not replayed."""


class MCPCapacityError(RuntimeError):
    """A local session or pending-request budget has been reached."""


@asynccontextmanager
async def open_session(url, timeout, *, traffic_class, credential):
    # Import optional SDK dependencies only when the default transport is used.
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    import httpx

    class BoundedStream(httpx.AsyncByteStream):
        def __init__(self, stream):
            self.stream = stream

        async def __aiter__(self):
            size = 0
            async for chunk in self.stream:
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    raise MCPTransportError("MCP response exceeds bounded contract")
                yield chunk

        async def aclose(self):
            await self.stream.aclose()

    async def response_policy(response):
        # MCP 1.30 handles same-origin redirects itself, independently of
        # httpx.follow_redirects. Reject them before that SDK handler runs.
        if 300 <= response.status_code < 400:
            await response.aclose()
            raise MCPTransportError("MCP redirects are not permitted")
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            await response.aclose()
            raise MCPTransportError("Compressed MCP responses are outside the bounded contract")
        response.stream = BoundedStream(response.stream)

    headers = {"X-Financial-Evidence-Traffic-Class": traffic_class, "Accept-Encoding": "identity"}
    if credential:
        headers["Authorization"] = "Bearer " + credential
    owner, loop, cleanup_timer = asyncio.current_task(), asyncio.get_running_loop(), None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers=headers,
                                     event_hooks={"response": [response_policy]}) as http:
            async with streamable_http_client(url, http_client=http) as (read, write, _):
                async with ClientSession(read, write) as session:
                    try:
                        started = time.monotonic()
                        server = await session.initialize()
                        yield session, server.serverInfo.model_dump(mode="json"), (time.monotonic() - started) * 1000
                    finally:
                        # wait_for(__aexit__) would move AnyIO cleanup into a
                        # different task. A timer cancels this same owner if
                        # termination stalls, including a slow-drip DELETE.
                        cleanup_timer = loop.call_later(CLEANUP_TIMEOUT_SECONDS, owner.cancel)
    finally:
        if cleanup_timer is not None:
            cleanup_timer.cancel()


@dataclass
class _Request:
    tool: str
    arguments: dict
    future: asyncio.Future
    queued_at: float


class _Session:
    def __init__(self, url, timeout, traffic_class, credential, max_pending):
        self.url, self.timeout = url, timeout
        self.traffic_class, self.credential = traffic_class, credential
        self.queue = asyncio.Queue(maxsize=max_pending)
        self.current = None
        self.task = None
        self.stopping = False

    def stop(self):
        if not self.stopping:
            self.stopping = True
            self.fail_pending()
            if self.task is not None:
                self.task.cancel()

    def fail_pending(self):
        pending = [self.current] if self.current else []
        while not self.queue.empty():
            pending.append(self.queue.get_nowait())
        for request in pending:
            if not request.future.done():
                request.future.set_exception(MCPTransportError("MCP session closed; request was not replayed"))

    async def run(self):
        # AnyIO's cancel scopes must be entered and exited by this same task.
        # Never hand an entered SDK context manager back to a caller task.
        try:
            self.current = await self.queue.get()
            dispatched_at = time.monotonic()
            async with open_session(self.url, self.timeout, traffic_class=self.traffic_class,
                                    credential=self.credential) as (session, server, initialization_ms):
                reused = False
                while True:
                    request = self.current
                    if not request.future.cancelled():
                        started = time.monotonic()
                        result = await session.call_tool(request.tool, request.arguments)
                        payload = {"server": deepcopy(server), "result": result.model_dump(mode="json", exclude_none=True),
                                   "_transport_timing": {"session_reused": reused,
                                       "initialization_ms": round(initialization_ms if not reused else 0, 3),
                                       "tool_ms": round((time.monotonic() - started) * 1000, 3),
                                       "queue_ms": round(max(0, (dispatched_at - request.queued_at) * 1000), 3)}}
                        if not request.future.done():
                            request.future.set_result(payload)
                        reused = True
                    self.current = None
                    self.current = await self.queue.get()
                    dispatched_at = time.monotonic()
        except (Exception, asyncio.CancelledError):
            # Do not retain SDK error text, credentials, arguments, or URLs in
            # errors. A failed request is never retried, even when read-only.
            pass
        finally:
            self.stopping = True
            self.fail_pending()
            self.current = None


class PersistentMCPTransport:
    """A client-owned pool, never shared between credentials or event loops.

    One session belongs to each exact endpoint. Calls on it are serialized;
    different endpoints proceed concurrently. Exhaustion fails locally rather
    than opening unbounded sessions or retaining an unbounded request queue.
    """

    def __init__(self, *, traffic_class="unverified", credential=None, max_sessions=14, max_pending=16):
        if type(max_sessions) is not int or not 1 <= max_sessions <= 14:
            raise ValueError("max_sessions must be between one and fourteen")
        if type(max_pending) is not int or not 1 <= max_pending <= 128:
            raise ValueError("max_pending must be between one and 128")
        self._traffic_class, self._credential = traffic_class, credential
        self._max_sessions, self._max_pending = max_sessions, max_pending
        self._sessions = {}
        self._loop = None
        self._closed = False
        self._close_task = None

    def _bind_loop(self):
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError("Persistent MCP transport belongs to another event loop")
        self._loop = loop
        return loop

    async def __call__(self, url, tool, arguments, timeout):
        loop = self._bind_loop()
        if self._closed:
            raise RuntimeError("Persistent MCP transport is closed")
        session = self._sessions.get(url)
        if session is not None and session.stopping:
            # Cleanup completes before replacement, keeping the session bound
            # true even during reconnect. This is a new explicit request.
            await asyncio.shield(session.task)
            if self._closed:
                raise RuntimeError("Persistent MCP transport is closed")
            session = self._sessions.get(url)
        # No await between selection and enqueue: callers cannot race to create
        # two sessions for the same endpoint within the owning event loop.
        for key, candidate in list(self._sessions.items()):
            if candidate.task.done():
                del self._sessions[key]
        session = self._sessions.get(url)
        if session is None:
            if len(self._sessions) >= self._max_sessions:
                raise MCPCapacityError("MCP session limit reached")
            session = _Session(url, timeout, self._traffic_class, self._credential, self._max_pending)
            self._sessions[url] = session
            session.task = asyncio.create_task(session.run(), name="financial-evidence-mcp-session")
        future = loop.create_future()
        request = _Request(tool, arguments, future, time.monotonic())
        try:
            session.queue.put_nowait(request)
        except asyncio.QueueFull:
            raise MCPCapacityError("MCP pending-request limit reached") from None
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            future.cancel()
            if session.current is request:
                # An in-flight request may have reached the server. Discard its
                # session; never infer it is safe to replay from a timeout.
                session.stop()
            raise

    async def aclose(self):
        self._bind_loop()
        self._closed = True
        if self._close_task is None:
            sessions = list(self._sessions.values())
            for session in sessions:
                session.stop()

            async def finish():
                await asyncio.gather(*(session.task for session in sessions), return_exceptions=True)
                self._sessions.clear()

            self._close_task = asyncio.create_task(finish(), name="financial-evidence-mcp-close")
        # Cancellation of one closer must not cancel the owner during AnyIO
        # cleanup. Another caller may await aclose again to join that cleanup.
        await asyncio.shield(self._close_task)
