"""Anonymous bounded client for source-status metadata snapshots and SSE updates."""
import asyncio
from datetime import datetime, timezone
import json
import math
import re
import time

from ..hosted import platform_base

MAX_SNAPSHOT = 16384
MAX_FRAME = 17408


def _timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)", value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def validate_snapshot(value, *, now=None):
    """Annotate receipt-time validity; call again before using a retained snapshot."""
    if (not isinstance(value, dict) or value.get("schema") != "seiche-agent-network.context.v1"
            or not isinstance(value.get("stream_id"), str)
            or not re.fullmatch(r"[a-f0-9]{32}", value["stream_id"])
            or type(value.get("sequence")) is not int or value["sequence"] < 1
            or not isinstance(value.get("revision"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", value["revision"])
            or value.get("scope") != "source_status_metadata"
            or value.get("execution_authority") != "none"
            or value.get("coverage_complete") is not False
            or not isinstance(value.get("source_monitor"), dict)
            or not isinstance(value.get("products"), list)):
        raise ValueError("invalid source-status snapshot contract")
    now = time.time() if now is None else now
    if type(now) not in {int, float} or not math.isfinite(now):
        raise ValueError("invalid client clock")
    monitor = value["source_monitor"]
    evaluated, expires = _timestamp(monitor.get("evaluated_at")), _timestamp(monitor.get("valid_until"))
    if (evaluated is None or expires is None or type(monitor.get("max_age_seconds")) not in {int, float}
            or monitor["max_age_seconds"] != 900 or expires != evaluated + 900):
        status = "invalid_monitor"
    elif evaluated > now:
        status = "future_clock"
    elif now >= expires:
        status = "stale"
    elif monitor.get("status") != "current" or monitor.get("current") is not True:
        status = "source_blocked"
    else:
        status = "current"
    # Preserve the source report and its revision. This is a local admission
    # annotation at receipt time; revalidate a retained snapshot before use.
    result = {**value, "client_monitor_current": status == "current", "client_monitor_status": status,
              "client_monitor_checked_at": datetime.fromtimestamp(now, timezone.utc).isoformat()}
    if status != "current" or value.get("input_eligibility") != "not_evaluated":
        result["input_eligibility"] = "blocked_monitor"
    return result


class ContextClient:
    """Use async with. Reconnect is explicit and always receives a latest-state reset.

    This client reports source metadata, not live prices or trading admission.
    It never reads ambient credentials or forwards caller secrets.
    """
    def __init__(self, *, platform_url=None, timeout=30, synthetic=False, transport=None):
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError("invalid timeout")
        if type(synthetic) is not bool:
            raise ValueError("synthetic must be an explicit boolean")
        self.base = platform_base(platform_url)
        self.timeout, self.synthetic, self.transport = timeout, synthetic, transport
        self.http = None

    async def __aenter__(self):
        import httpx
        if self.http is not None:
            raise RuntimeError("client already entered")
        self.http = httpx.AsyncClient(timeout=self.timeout, follow_redirects=False,
            transport=self.transport, headers={
                "X-Financial-Evidence-Traffic-Class": "synthetic" if self.synthetic else "unknown",
                "Accept-Encoding": "identity",
                "User-Agent": "Financial-Evidence-context/1"})
        return self

    async def __aexit__(self, *_):
        if self.http is not None:
            await self.http.aclose()
            self.http = None

    def _client(self):
        if self.http is None:
            raise RuntimeError("use async with ContextClient()")
        return self.http

    async def snapshot(self):
        return await asyncio.wait_for(self._snapshot(), self.timeout)

    async def _snapshot(self):
        async with self._client().stream("GET", self.base + "/v1/context/snapshot") as response:
            response.raise_for_status()
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise ValueError("compressed snapshots are outside the bounded contract")
            body = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=4096):
                body.extend(chunk)
                if len(body) > MAX_SNAPSHOT:
                    raise ValueError("snapshot exceeds bounded contract")
        return validate_snapshot(json.loads(body))

    async def events(self, *, last_event_id=None):
        if last_event_id is not None and (not isinstance(last_event_id, str)
                or not re.fullmatch(r"[a-f0-9]{32}:[1-9][0-9]{0,19}", last_event_id)):
            raise ValueError("invalid event cursor")
        headers = {"Accept": "text/event-stream"}
        if last_event_id is not None:
            headers["Last-Event-ID"] = last_event_id
        async with self._client().stream("GET", self.base + "/v1/context/events", headers=headers) as response:
            response.raise_for_status()
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise ValueError("compressed streams are outside the bounded contract")
            if response.headers.get("content-type", "").split(";")[0] != "text/event-stream":
                raise ValueError("expected event stream")
            pending, frame = bytearray(), []
            frame_bytes, previous, initialized = 0, None, False
            async for chunk in response.aiter_bytes():
                pending.extend(chunk)
                while b"\n" in pending:
                    raw, _, tail = pending.partition(b"\n")
                    pending = bytearray(tail)
                    frame_bytes += len(raw) + 1
                    if frame_bytes > MAX_FRAME:
                        raise ValueError("event exceeds bounded contract")
                    line = raw.rstrip(b"\r").decode("utf-8")
                    if line:
                        frame.append(line)
                        continue
                    event, frame, frame_bytes = _decode_frame(frame), [], 0
                    if event is None:
                        continue
                    if event["event"] == "keepalive":
                        if event["data"] != {"transport_only": True, "source_freshness_proof": False}:
                            raise ValueError("invalid keepalive")
                        yield event
                        continue
                    snapshot = validate_snapshot(event["data"])
                    cursor = (snapshot["stream_id"], snapshot["sequence"])
                    if event.get("id") != f"{cursor[0]}:{cursor[1]}":
                        raise ValueError("event cursor mismatch")
                    if not initialized and event["event"] != "reset":
                        raise ValueError("stream must begin with latest-state reset")
                    if previous and event["event"] != "reset" and (
                            cursor[0] != previous[0] or cursor[1] <= previous[1]):
                        raise ValueError("nonmonotonic event cursor")
                    if snapshot.get("delivery", {}).get("replay_complete") is not False:
                        raise ValueError("stream must disclose incomplete replay")
                    previous, initialized = cursor, True
                    yield {**event, "data": snapshot}
                if len(pending) + frame_bytes > MAX_FRAME:
                    raise ValueError("event exceeds bounded contract")
            if pending or frame:
                raise ValueError("truncated event stream")


def _decode_frame(lines):
    fields, data = {}, []
    for line in lines:
        if line.startswith(":"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        value = value[1:] if value.startswith(" ") else value
        if key == "data":
            data.append(value)
        elif key in {"event", "id"}:
            if key in fields:
                raise ValueError("duplicate event field")
            fields[key] = value
    if not data:
        return None
    if fields.get("event") not in {"reset", "snapshot", "keepalive"}:
        raise ValueError("unknown event type")
    return {**fields, "data": json.loads("\n".join(data))}
