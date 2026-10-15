"""Session ownership, bounded work, and no replay after ambiguous failures."""
import asyncio
from contextlib import asynccontextmanager, nullcontext
import importlib.util
import json
import unittest
from unittest.mock import patch

from financial_evidence.trading.client import ProductClient
from financial_evidence.trading.transport import PersistentMCPTransport, MCPCapacityError, MCPTransportError


class Result:
    def __init__(self, value=None):
        self.value = value or {"content": [], "structuredContent": {"observed_at": "2000-01-01T00:00:00Z"}}

    def model_dump(self, **_):
        return self.value


class Sessions:
    def __init__(self):
        self.opened, self.closed, self.calls = [], [], []
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.fail_initialize = False

    @asynccontextmanager
    async def open(self, url, timeout, **identity):
        owner = asyncio.current_task()
        self.opened.append((url, identity, owner))
        try:
            if self.fail_initialize:
                raise OSError("PRIVATE initialization detail")

            async def call_tool(tool, arguments):
                assert asyncio.current_task() is owner
                self.calls.append((url, tool, arguments))
                self.started.set()
                if arguments.get("block"):
                    await self.release.wait()
                if arguments.get("fail"):
                    raise OSError("PRIVATE upstream credential")
                return Result({"isError": bool(arguments.get("isError")), "content": []})

            class Session:
                pass

            session = Session()
            session.call_tool = call_tool
            yield session, {"name": "fixture", "version": "1"}, 2.0
        finally:
            assert asyncio.current_task() is owner
            self.closed.append(url)


class PersistentTransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sessions = Sessions()
        self.patcher = patch("financial_evidence.trading.transport.open_session", self.sessions.open)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.pool = PersistentMCPTransport(traffic_class="synthetic")
        self.addAsyncCleanup(self.pool.aclose)

    async def call(self, url="https://example.test/products/seiche/mcp", **args):
        return await self.pool(url, "data_health", args, 1)

    async def test_reuse_same_owner_and_exact_endpoint_isolation(self):
        first, second = await self.call(), await self.call()
        await self.call("https://example.test/products/undertow/mcp")
        await self.call("https://other.test/products/seiche/mcp")
        self.assertEqual(len(self.sessions.opened), 3)
        self.assertFalse(first["_transport_timing"]["session_reused"])
        self.assertTrue(second["_transport_timing"]["session_reused"])
        self.assertEqual(second["_transport_timing"]["initialization_ms"], 0)
        await self.pool.aclose()
        self.assertEqual(len(self.sessions.closed), 3)

    async def test_concurrent_same_endpoint_shares_session_and_other_endpoint_progresses(self):
        first = asyncio.create_task(self.call(block=True))
        await self.sessions.started.wait()
        second = asyncio.create_task(self.call())
        other = await asyncio.wait_for(self.call("https://example.test/other"), 0.5)
        self.assertEqual(other["server"]["name"], "fixture")
        self.assertFalse(second.done())
        self.sessions.release.set()
        a, b = await asyncio.gather(first, second)
        self.assertFalse(a["_transport_timing"]["session_reused"])
        self.assertTrue(b["_transport_timing"]["session_reused"])
        self.assertEqual(len(self.sessions.opened), 2)

    async def test_failed_tool_is_not_replayed_and_next_request_reconnects(self):
        with self.assertRaisesRegex(MCPTransportError, "not replayed") as caught:
            await self.call(fail=True)
        self.assertNotIn("PRIVATE", str(caught.exception))
        self.assertEqual(len(self.sessions.calls), 1)
        await self.call()
        self.assertEqual(len(self.sessions.opened), 2)
        self.assertEqual(len(self.sessions.calls), 2)

    async def test_failed_initialization_is_not_replayed(self):
        self.sessions.fail_initialize = True
        with self.assertRaises(MCPTransportError):
            await self.call()
        self.assertEqual(len(self.sessions.opened), 1)
        self.assertEqual(self.sessions.calls, [])
        self.sessions.fail_initialize = False
        await self.call()
        self.assertEqual(len(self.sessions.opened), 2)

    async def test_transport_cannot_cross_event_loops(self):
        await self.call()
        def other_loop():
            return asyncio.run(self.call())
        with self.assertRaisesRegex(RuntimeError, "another event loop"):
            await asyncio.to_thread(other_loop)
        self.assertEqual(len(self.sessions.opened), 1)

    async def test_initialization_timeout_cleans_up_same_owner(self):
        initializing, closed = asyncio.Event(), asyncio.Event()
        @asynccontextmanager
        async def blocked_initialize(*args, **kwargs):
            owner = asyncio.current_task()
            try:
                initializing.set()
                await asyncio.Event().wait()
                yield
            finally:
                self.assertIs(asyncio.current_task(), owner)
                closed.set()
        with patch("financial_evidence.trading.transport.open_session", blocked_initialize):
            async with ProductClient(timeout=0.02) as client:
                with self.assertRaises(asyncio.TimeoutError):
                    await client.call("seiche", "data_health")
            self.assertTrue(initializing.is_set())
            self.assertTrue(closed.is_set())

    async def test_failed_active_call_fails_queued_work_without_sending_it(self):
        active = asyncio.create_task(self.call(block=True, fail=True))
        await self.sessions.started.wait()
        queued = asyncio.create_task(self.call())
        await asyncio.sleep(0)
        self.sessions.release.set()
        results = await asyncio.gather(active, queued, return_exceptions=True)
        self.assertTrue(all(isinstance(result, MCPTransportError) for result in results))
        self.assertEqual(len(self.sessions.calls), 1)

    async def test_tool_error_response_does_not_discard_a_healthy_session(self):
        self.assertTrue((await self.call(isError=True))["result"]["isError"])
        await self.call()
        self.assertEqual(len(self.sessions.opened), 1)

    async def test_mutating_a_receipt_does_not_change_session_identity(self):
        first = await self.call()
        first["server"]["name"] = "caller-mutated"
        self.assertEqual((await self.call())["server"]["name"], "fixture")

    async def test_active_cancellation_fails_queue_and_next_call_reconnects(self):
        active = asyncio.create_task(self.call(block=True))
        await self.sessions.started.wait()
        queued = asyncio.create_task(self.call())
        await asyncio.sleep(0)
        active.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await active
        with self.assertRaises(MCPTransportError):
            await asyncio.wait_for(queued, 0.5)
        self.assertEqual(len(self.sessions.calls), 1)
        await self.call()
        self.assertEqual(len(self.sessions.opened), 2)

    async def test_queued_cancellation_does_not_interrupt_active_request(self):
        active = asyncio.create_task(self.call(block=True))
        await self.sessions.started.wait()
        queued = asyncio.create_task(self.call())
        await asyncio.sleep(0)
        queued.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await queued
        self.sessions.release.set()
        await active
        await self.call()
        self.assertEqual(len(self.sessions.calls), 2)
        self.assertEqual(len(self.sessions.opened), 1)

    async def test_queue_capacity_rejects_without_sending(self):
        pool = PersistentMCPTransport(max_pending=1)
        self.addAsyncCleanup(pool.aclose)
        active = asyncio.create_task(pool("https://a.test", "data_health", {"block": True}, 1))
        await self.sessions.started.wait()
        queued = asyncio.create_task(pool("https://a.test", "data_health", {}, 1))
        await asyncio.sleep(0)
        with self.assertRaises(MCPCapacityError):
            await pool("https://a.test", "data_health", {}, 1)
        self.sessions.release.set()
        await asyncio.gather(active, queued)
        self.assertEqual(len(self.sessions.calls), 2)

    async def test_session_capacity_rejects_without_opening(self):
        pool = PersistentMCPTransport(max_sessions=1)
        self.addAsyncCleanup(pool.aclose)
        await pool("https://a.test", "data_health", {}, 1)
        with self.assertRaises(MCPCapacityError):
            await pool("https://b.test", "data_health", {}, 1)
        self.assertEqual(len(self.sessions.opened), 1)

    async def test_close_interrupts_active_and_queued_calls_and_is_idempotent(self):
        active = asyncio.create_task(self.call(block=True))
        await self.sessions.started.wait()
        queued = asyncio.create_task(self.call())
        await asyncio.sleep(0)
        await asyncio.wait_for(self.pool.aclose(), 0.5)
        values = await asyncio.gather(active, queued, return_exceptions=True)
        self.assertTrue(all(isinstance(value, MCPTransportError) for value in values))
        await self.pool.aclose()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            await self.call()
        self.assertEqual(len(self.sessions.closed), 1)

    async def test_close_before_owner_starts_completes_waiter(self):
        call = asyncio.create_task(self.call())
        # The submitter runs and schedules its owner behind this test task.
        await asyncio.sleep(0)
        await self.pool.aclose()
        with self.assertRaises(MCPTransportError):
            await asyncio.wait_for(call, 0.5)
        self.assertEqual(self.sessions.calls, [])

    async def test_cancelling_close_does_not_cancel_session_cleanup(self):
        cleanup_started, cleanup_release = asyncio.Event(), asyncio.Event()
        original = self.sessions.open
        @asynccontextmanager
        async def slow_close(*args, **kwargs):
            async with original(*args, **kwargs) as value:
                try:
                    yield value
                finally:
                    cleanup_started.set()
                    await cleanup_release.wait()
        with patch("financial_evidence.trading.transport.open_session", slow_close):
            await self.call()
            closing = asyncio.create_task(self.pool.aclose())
            await cleanup_started.wait()
            closing.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await closing
            cleanup_release.set()
            await asyncio.wait_for(self.pool.aclose(), 0.5)
        self.assertEqual(len(self.sessions.closed), 1)

    async def test_credentials_and_classification_are_never_shared_between_clients(self):
        async with ProductClient(credential="private-principal-token-aaa", mode="test") as first:
            async with ProductClient(credential="private-principal-token-bbb", mode="shadow") as second:
                receipts = await asyncio.gather(first.call("seiche", "data_health"), second.call("seiche", "data_health"))
        self.assertEqual(len(self.sessions.opened), 2)
        self.assertEqual({entry[1]["traffic_class"] for entry in self.sessions.opened}, {"synthetic", "shadow"})
        self.assertEqual(len({entry[1]["credential"] for entry in self.sessions.opened}), 2)
        self.assertNotIn("private-principal", json.dumps(receipts))

    async def test_product_client_timeout_cleans_owner_without_replay(self):
        async with ProductClient(timeout=0.02) as client:
            with self.assertRaises(asyncio.TimeoutError):
                await client.call("seiche", "data_health", {"block": True})
            await client.call("seiche", "data_health")
        self.assertEqual(len(self.sessions.calls), 2)
        self.assertEqual(len(self.sessions.opened), 2)
        self.assertEqual(len(self.sessions.closed), 2)

    async def test_one_shot_remains_one_shot_and_cache_does_not_retimestamp_source(self):
        client = ProductClient()
        for _ in range(2):
            receipt = await client.call("seiche", "data_health")
            self.assertFalse(receipt["timing"]["session_reused"])
        self.assertEqual(len(self.sessions.closed), 2)
        now = [1000.0]
        async with ProductClient(cache_seconds=60, clock=lambda: now[0]) as client:
            first = await client.call("seiche", "data_health")
            now[0] += 10
            second = await client.call("seiche", "data_health")
        self.assertTrue(second["cache_hit"])
        self.assertEqual(first["captured_at"], second["captured_at"])
        self.assertEqual(first["payload_sha256"], second["payload_sha256"])
        self.assertNotIn("session_reused", second["timing"])
        self.assertEqual(second["timing"]["clock"], "monotonic")

    async def test_injected_transport_ownership_and_read_allowlist_unchanged(self):
        calls = []
        async def transport(*args):
            calls.append(args)
            return {"result": {}}
        async with ProductClient(transport=transport) as client:
            await client.call("seiche", "data_health")
            with self.assertRaises(ValueError):
                await client.call("seiche", "submit_order")
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.sessions.opened, [])
        with self.assertRaises(RuntimeError):
            await client.call("seiche", "data_health")
        with self.assertRaises(RuntimeError):
            await client.__aenter__()

    async def test_monotonic_duration_survives_wall_clock_rollback(self):
        now = [1000.0]
        async def transport(*_):
            now[0] -= 100
            return {"result": {}}
        events = []
        client = ProductClient(transport=transport, clock=lambda: now[0], measurement=True, event_sink=events.append)
        result = await client.call("seiche", "data_health")
        self.assertGreaterEqual(result["timing"]["duration_ms"], 0)
        self.assertGreaterEqual(events[0]["duration_ms"], 0)

    def test_invalid_capacity_is_rejected(self):
        for kwargs in ({"max_sessions": 0}, {"max_sessions": 15}, {"max_sessions": True},
                       {"max_pending": 0}, {"max_pending": 129}, {"max_pending": float("nan")}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ProductClient(**kwargs)


@unittest.skipUnless(importlib.util.find_spec("mcp") and importlib.util.find_spec("httpx"), "optional MCP SDK required")
class ActualSDKTests(unittest.IsolatedAsyncioTestCase):
    async def test_wire_size_and_compression_fail_before_unbounded_parsing(self):
        import httpx
        import mcp.client.streamable_http
        real_client = httpx.AsyncClient
        for compressed in (False, True):
            reads = []
            class Bytes(httpx.AsyncByteStream):
                async def __aiter__(self):
                    reads.append(True)
                    for _ in range(3):
                        yield b"x" * 1_048_576
            def upstream(request):
                return httpx.Response(200, headers={"content-type": "application/json",
                    "content-encoding": "gzip" if compressed else "identity"}, stream=Bytes())
            def http(**kwargs):
                return real_client(transport=httpx.MockTransport(upstream), **kwargs)
            logs = nullcontext() if compressed else self.assertLogs("mcp.client.streamable_http", level="ERROR")
            with self.subTest(compressed=compressed), patch("httpx.AsyncClient", http), logs:
                async with ProductClient(mode="test", timeout=.2) as client:
                    with self.assertRaises((MCPTransportError, asyncio.TimeoutError)):
                        await client.call("seiche", "data_health")
            self.assertEqual(reads, [] if compressed else [True])

    async def test_sdk_owned_redirect_cannot_bypass_no_redirect_policy(self):
        import httpx
        import mcp.client.streamable_http
        real_client, requests = httpx.AsyncClient, []
        def upstream(request):
            requests.append(request)
            return httpx.Response(307, headers={"Location": str(request.url) + "/unreviewed"})
        def http(**kwargs):
            return real_client(transport=httpx.MockTransport(upstream), **kwargs)
        with patch("httpx.AsyncClient", http):
            async with ProductClient(mode="test", timeout=.2) as client:
                with self.assertRaises(MCPTransportError):
                    await client.call("seiche", "data_health")
        self.assertEqual(len(requests), 1)

    async def test_hung_delete_cleanup_is_bounded_in_its_owning_task(self):
        import httpx
        import mcp.client.streamable_http
        real_client, deletes = httpx.AsyncClient, []
        async def upstream(request):
            if request.method == "DELETE":
                deletes.append(True)
                await asyncio.Event().wait()
            if request.method != "POST":
                return httpx.Response(405)
            payload = json.loads(request.content)
            if "id" not in payload:
                return httpx.Response(202)
            if payload["method"] == "initialize":
                result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "fixture", "version": "1"}}
            elif payload["method"] == "tools/list":
                result = {"tools": [{"name": "data_health", "inputSchema": {"type": "object"}}]}
            else:
                result = {"content": []}
            return httpx.Response(200, headers={"mcp-session-id": "synthetic-session"},
                                  json={"jsonrpc": "2.0", "id": payload["id"], "result": result})
        def http(**kwargs):
            return real_client(transport=httpx.MockTransport(upstream), **kwargs)
        with patch("httpx.AsyncClient", http), patch("financial_evidence.trading.transport.CLEANUP_TIMEOUT_SECONDS", .02):
            client = await ProductClient(mode="test").__aenter__()
            await client.call("seiche", "data_health")
            await asyncio.wait_for(client.aclose(), .5)
        self.assertEqual(deletes, [True])

    async def test_actual_sdk_reuses_initialize_and_closes_without_scope_errors(self):
        import httpx
        import mcp.client.streamable_http  # Load annotations before patching httpx's constructor.
        real_client, requests = httpx.AsyncClient, []
        def upstream(request):
            requests.append(request)
            if request.method != "POST":
                return httpx.Response(405)
            payload = json.loads(request.content)
            if "id" not in payload:
                return httpx.Response(202)
            if payload["method"] == "initialize":
                result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "fixture", "version": "1"}}
            elif payload["method"] == "tools/list":
                result = {"tools": [{"name": "data_health", "inputSchema": {"type": "object"}}]}
            else:
                result = {"content": [{"type": "text", "text": "source observation remains unchanged"}]}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})
        def http(**kwargs):
            self.assertFalse(kwargs["follow_redirects"])
            return real_client(transport=httpx.MockTransport(upstream), **kwargs)
        with patch("httpx.AsyncClient", http):
            async with ProductClient(mode="test") as client:
                first = await client.call("seiche", "data_health")
                second = await client.call("seiche", "data_health")
        methods = [json.loads(request.content)["method"] for request in requests if request.method == "POST"]
        self.assertEqual(methods.count("initialize"), 1)
        self.assertEqual(methods.count("tools/call"), 2)
        self.assertFalse(first["timing"]["session_reused"])
        self.assertTrue(second["timing"]["session_reused"])
        self.assertTrue(all("authorization" not in request.headers for request in requests))
        self.assertTrue(all(request.headers["X-Financial-Evidence-Traffic-Class"] == "synthetic" for request in requests))

    async def test_actual_sdk_timeout_closes_and_next_explicit_request_reinitializes(self):
        import httpx
        import mcp.client.streamable_http
        real_client, methods, deleted = httpx.AsyncClient, [], []
        async def upstream(request):
            if request.method == "DELETE":
                deleted.append(request.headers.get("mcp-session-id"))
                return httpx.Response(200)
            if request.method != "POST":
                return httpx.Response(405)
            payload = json.loads(request.content)
            methods.append(payload["method"])
            if "id" not in payload:
                return httpx.Response(202)
            if payload["method"] == "initialize":
                result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "fixture", "version": "1"}}
            elif payload["method"] == "tools/list":
                result = {"tools": [{"name": "data_health", "inputSchema": {"type": "object"}}]}
            else:
                if payload["params"]["arguments"].get("block"):
                    await asyncio.Event().wait()
                result = {"content": []}
            return httpx.Response(200, headers={"mcp-session-id": "synthetic-session"},
                                  json={"jsonrpc": "2.0", "id": payload["id"], "result": result})
        def http(**kwargs):
            return real_client(transport=httpx.MockTransport(upstream), **kwargs)
        with patch("httpx.AsyncClient", http):
            async with ProductClient(timeout=0.08, mode="test") as client:
                with self.assertRaises(asyncio.TimeoutError):
                    await client.call("seiche", "data_health", {"block": True})
                receipt = await client.call("seiche", "data_health")
                self.assertFalse(receipt["timing"]["session_reused"])
        self.assertEqual(methods.count("initialize"), 2)
        self.assertEqual(methods.count("tools/call"), 2)
        self.assertEqual(deleted, ["synthetic-session", "synthetic-session"])


if __name__ == "__main__":
    unittest.main()
