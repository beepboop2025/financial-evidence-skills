import asyncio
from datetime import datetime, timezone
import importlib.util
import json
import unittest

from financial_evidence.trading.context import ContextClient, validate_snapshot

NOW = 1_800_000_000


def stamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def fresh_snapshot():
    return {**snapshot(), "source_monitor": {"current": True, "status": "current", "evaluated_at": stamp(NOW),
            "valid_until": stamp(NOW + 900), "max_age_seconds": 900}, "input_eligibility": "not_evaluated"}


def snapshot(sequence=1):
    return {"schema": "seiche-agent-network.context.v1", "stream_id": "a" * 32,
            "sequence": sequence, "revision": "b" * 64, "scope": "source_status_metadata",
            "source_monitor": {"current": False, "status": "stale"}, "products": [],
            "execution_authority": "none", "coverage_complete": False,
            "input_eligibility": "blocked_monitor", "delivery": {"replay_complete": False}}


def frame(event="reset", value=None, event_id=None):
    value = snapshot() if value is None else value
    event_id = event_id or f'{value["stream_id"]}:{value["sequence"]}'
    return f"event: {event}\nid: {event_id}\ndata: {json.dumps(value)}\n\n".encode()


class ContractTests(unittest.TestCase):
    def test_wrong_scope_and_execution_authority_are_refused(self):
        for changes in ({"execution_authority": "trade"}, {"scope": "live_prices"},
                       {"sequence": True}, {"coverage_complete": True}):
            with self.assertRaises(ValueError):
                validate_snapshot({**snapshot(), **changes})

    def test_local_expiry_future_and_invalid_bounds_fail_closed_without_mutating_source(self):
        source = fresh_snapshot()
        original = json.loads(json.dumps(source))
        for now, expected in ((NOW, "current"), (NOW + 899.999, "current"),
                              (NOW + 900, "stale"), (NOW - .001, "future_clock")):
            result = validate_snapshot(source, now=now)
            self.assertEqual(result["client_monitor_status"], expected)
            self.assertEqual(result["client_monitor_current"], expected == "current")
            self.assertEqual(result["input_eligibility"], "not_evaluated" if expected == "current" else "blocked_monitor")
            self.assertEqual(result["source_monitor"], original["source_monitor"])
        self.assertEqual(source, original)
        for changes in ({"valid_until": stamp(NOW + 901)}, {"max_age_seconds": True},
                        {"max_age_seconds": 901}, {"evaluated_at": "2026-02-30T00:00:00Z"},
                        {"evaluated_at": "2026-01-01T00:00:00"}, {"valid_until": None}):
            result = validate_snapshot({**source, "source_monitor": {**source["source_monitor"], **changes}}, now=NOW)
            self.assertEqual(result["client_monitor_status"], "invalid_monitor")
            self.assertEqual(result["input_eligibility"], "blocked_monitor")

    def test_source_block_cannot_be_upgraded_by_client_clock(self):
        source = fresh_snapshot()
        blocked = validate_snapshot({**source, "input_eligibility": "blocked_monitor"}, now=NOW)
        self.assertTrue(blocked["client_monitor_current"])
        self.assertEqual(blocked["input_eligibility"], "blocked_monitor")
        blocked = validate_snapshot({**source, "source_monitor": {**source["source_monitor"], "current": False}}, now=NOW)
        self.assertEqual(blocked["client_monitor_status"], "source_blocked")
        self.assertEqual(blocked["input_eligibility"], "blocked_monitor")


@unittest.skipUnless(importlib.util.find_spec("httpx"), "workspace extra required")
class ContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_preserves_stale_and_no_credentials_or_redirect(self):
        import httpx
        def transport(request):
            self.assertNotIn("authorization", request.headers)
            self.assertEqual(request.headers["X-Financial-Evidence-Traffic-Class"], "synthetic")
            return httpx.Response(200, json=snapshot())
        async with ContextClient(synthetic=True, transport=httpx.MockTransport(transport)) as reader:
            result = await reader.snapshot()
            self.assertEqual(result["input_eligibility"], "blocked_monitor")
            self.assertFalse(result["source_monitor"]["current"])
        self.assertIsNone(reader.http)

    async def collect(self, body):
        import httpx
        class Bytes(httpx.AsyncByteStream):
            async def __aiter__(self):
                for start in range(0, len(body), 7):
                    yield body[start:start + 7]
        async with ContextClient(transport=httpx.MockTransport(lambda _: httpx.Response(
            200, headers={"content-type": "text/event-stream"}, stream=Bytes()))) as reader:
            return [event async for event in reader.events()]

    async def test_fragmented_reset_update_and_transport_heartbeat(self):
        body = frame() + b'event: keepalive\ndata: {"transport_only":true,"source_freshness_proof":false}\n\n'
        body += frame("snapshot", snapshot(3))  # latest-state coalescing can skip sequence 2.
        events = await self.collect(body)
        self.assertEqual([event["event"] for event in events], ["reset", "keepalive", "snapshot"])
        self.assertFalse(events[-1]["data"]["delivery"]["replay_complete"])
        self.assertFalse(events[-1]["data"]["client_monitor_current"])

    async def test_initial_frame_is_yielded_before_stream_finishes(self):
        import httpx
        closed = asyncio.Event()
        class Bytes(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield frame()
                await asyncio.Event().wait()
            async def aclose(self):
                closed.set()
        async with ContextClient(transport=httpx.MockTransport(lambda _: httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=Bytes()))) as reader:
            events = reader.events()
            first = await asyncio.wait_for(events.__anext__(), .2)
            self.assertEqual(first["event"], "reset")
            await events.aclose()
        self.assertTrue(closed.is_set())

    async def test_snapshot_deadline_bounds_a_slow_drip_body(self):
        import httpx
        closed = asyncio.Event()
        class Bytes(httpx.AsyncByteStream):
            async def __aiter__(self):
                for byte in json.dumps(snapshot()).encode():
                    await asyncio.sleep(.005)
                    yield bytes([byte])
            async def aclose(self):
                closed.set()
        async with ContextClient(timeout=.02, transport=httpx.MockTransport(
                lambda _: httpx.Response(200, stream=Bytes()))) as reader:
            with self.assertRaises(asyncio.TimeoutError):
                await reader.snapshot()
        self.assertTrue(closed.is_set())

    async def test_compressed_responses_are_rejected_before_reading_body(self):
        import httpx
        class Unread(httpx.AsyncByteStream):
            async def __aiter__(self):
                raise AssertionError("must reject before decoding")
                yield b""
        async with ContextClient(transport=httpx.MockTransport(lambda _: httpx.Response(
                200, headers={"content-type": "text/event-stream", "content-encoding": "gzip"}, stream=Unread()))) as reader:
            with self.assertRaisesRegex(ValueError, "compressed"):
                await reader.snapshot()
            with self.assertRaisesRegex(ValueError, "compressed"):
                await reader.events().__anext__()

    async def test_invalid_reset_order_reversal_epoch_and_cursor_refused(self):
        for body in (frame("snapshot"), frame() + frame("snapshot"),
                     frame() + frame("snapshot", {**snapshot(2), "stream_id": "c" * 32}),
                     frame(event_id="invalid"), frame()[:-1], b"data: " + b"x" * 18000):
            with self.subTest(body=body[:50]), self.assertRaises(ValueError):
                await self.collect(body)

    async def test_http_redirect_is_not_followed(self):
        import httpx
        calls = []
        def transport(request):
            calls.append(request.url)
            return httpx.Response(302, headers={"Location": "https://other.invalid/private"})
        async with ContextClient(transport=httpx.MockTransport(transport)) as reader:
            with self.assertRaises(httpx.HTTPStatusError):
                await reader.snapshot()
        self.assertEqual(len(calls), 1)
