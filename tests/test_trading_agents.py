import asyncio
from dataclasses import replace
import json
import os
import tempfile
import threading
import time
import subprocess
import sys
import unittest
from pathlib import Path

from financial_evidence.trading import ProductClient, Observation, InputPolicy, assess, select_as_of
from financial_evidence.trading.journal import save_receipt, read_receipt


def observation(**changes):
    return replace(Observation(product="seiche", series="funding", period="2026-10-10", value=1.2,
        unit="percent", source_url="https://example.org/source", observed_at="2026-10-10T00:00:00Z",
        published_at="2026-10-10T12:00:00Z", available_at="2026-10-10T12:01:00Z",
        captured_at="2026-10-10T12:02:00Z", revision="1", rights="permitted", quality="observed"), **changes)


class ObservationTests(unittest.TestCase):
    def test_later_revision_and_late_capture_do_not_leak(self):
        first = observation()
        revision = observation(value=2, revision="2", available_at="2026-10-11T12:01:00Z", captured_at="2026-10-11T12:02:00Z")
        self.assertEqual(select_as_of([first, revision], "2026-10-10T13:00:00Z"), [first])
        self.assertEqual(select_as_of([revision], "2026-10-10T13:00:00Z"), [])

    def test_missing_stale_rights_and_context_block_consumption(self):
        policy = InputPolicy(("seiche:funding",), 86400)
        for item in [observation(value=None), observation(rights="restricted"), observation(context_only=True), observation(quality="forecast")]:
            self.assertEqual(assess([item], policy, "2026-10-10T13:00:00Z")["status"], "hold")
        self.assertEqual(assess([observation()], policy, "2026-10-12T13:00:00Z")["status"], "hold")
        self.assertEqual(assess([observation()], policy, "2026-10-10T13:00:00Z")["status"], "input_eligible")

    def test_product_identity_cannot_be_substituted(self):
        self.assertEqual(assess([observation(product="palimpsest")], InputPolicy(("seiche:funding",), 86400), "2026-10-10T13:00:00Z")["reasons"][0]["reason"], "missing_at_decision")

    def test_reject_invalid_clocks_values_and_sources(self):
        for changes in [{"captured_at":"2026-10-09T00:00:00Z"}, {"value":float("nan")}, {"value":True}, {"source_url":"file:///etc/passwd"}]:
            with self.assertRaises(ValueError): observation(**changes)


class DirectClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_no_measurement_and_direct_endpoint(self):
        calls, events = [], []
        async def transport(url, tool, args, timeout):
            calls.append((url, tool, args)); return {"result":{"content":[]}}
        client=ProductClient(transport=transport,event_sink=events.append)
        await client.call("seiche","funding_stress_now")
        self.assertEqual(events,[])
        self.assertEqual(calls[0][0],"https://api.seiche.info/mcp")

    async def test_cache_has_original_capture_and_optional_safe_event(self):
        calls, events, now = [], [], [1000.0]
        async def transport(*args): calls.append(args); return {"result":{"content":[{"text":"private-result"}]}}
        client=ProductClient(transport=transport,event_sink=events.append,measurement=True,cache_seconds=60,clock=lambda:now[0])
        a=await client.call("seiche","funding_stress_now",{"secret":"do not capture"})
        now[0]+=10
        b=await client.call("seiche","funding_stress_now",{"secret":"do not capture"})
        self.assertEqual(len(calls),1); self.assertTrue(b["cache_hit"])
        self.assertEqual(a["captured_at"],b["captured_at"])
        self.assertNotIn("private-result",json.dumps(events)); self.assertNotIn("secret",json.dumps(events))
        self.assertNotEqual(events[0]["id"],events[1]["id"])

    async def test_telemetry_failure_does_not_fail_data(self):
        async def transport(*args): return {"result":{}}
        def broken(event): raise OSError("collector offline")
        client=ProductClient(transport=transport,event_sink=broken,measurement=True)
        self.assertIn("payload",await client.call("seiche","funding_stress_now"))
        self.assertEqual(client.measurement_failures,1)

    async def test_blocking_measurement_is_bounded_and_cannot_accumulate_workers(self):
        release, entered = threading.Event(), threading.Event()
        calls = []
        async def transport(*args): return {"result":{}}
        def blocked(event):
            calls.append(event)
            entered.set()
            release.wait(2)
        client = ProductClient(transport=transport, event_sink=blocked, measurement=True,
                               measurement_timeout=0.02)
        try:
            first = await asyncio.wait_for(client.call("seiche", "funding_stress_now"), 0.5)
            self.assertIn("payload", first)
            self.assertTrue(entered.is_set())
            self.assertTrue(client._measurement_thread.daemon)
            for _ in range(3):
                self.assertIn("payload", await client.call("seiche", "funding_stress_now"))
            self.assertEqual(len(calls), 1)
            self.assertEqual(client.measurement_failures, 4)
        finally:
            release.set()
            await asyncio.wait_for(client._measurement_task, 0.5)

    async def test_sync_and_async_measurement_share_one_deadline(self):
        stopped = asyncio.Event()
        async def transport(*args): return {"result":{}}
        async def asynchronous_delivery():
            try:
                await asyncio.sleep(2)
            finally:
                stopped.set()
        def sink(event):
            time.sleep(0.03)
            return asynchronous_delivery()
        client = ProductClient(transport=transport, event_sink=sink, measurement=True,
                               measurement_timeout=0.08)
        started = time.monotonic()
        self.assertIn("payload", await client.call("seiche", "funding_stress_now"))
        self.assertLess(time.monotonic() - started, 0.3)
        await asyncio.wait_for(stopped.wait(), 0.5)
        self.assertEqual(client.measurement_failures, 1)

    async def test_invalid_measurement_deadlines_are_rejected(self):
        for deadline in [0, -1, 6, True, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                ProductClient(measurement_timeout=deadline)

    def test_blocked_optional_sink_does_not_hold_process_shutdown(self):
        script = """
import asyncio, threading
from financial_evidence.trading import ProductClient
async def transport(*args): return {"result": {}}
def blocked(event): threading.Event().wait()
async def main():
    client = ProductClient(transport=transport, event_sink=blocked,
                           measurement=True, measurement_timeout=0.02)
    assert "payload" in await client.call("seiche", "funding_stress_now")
    assert client.measurement_failures == 1
asyncio.run(main())
print("returned-and-exited")
"""
        # The stdlib-only CI job runs before package installation. Parent test
        # imports may amend sys.path, which a fresh interpreter does not inherit.
        source = str(Path(__file__).resolve().parents[1] / "src")
        child_env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None,
                     [source, os.environ.get("PYTHONPATH")]))}
        result = subprocess.run([sys.executable, "-c", script], capture_output=True,
                                text=True, timeout=3, env=child_env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "returned-and-exited")

    async def test_bounds_reject_unreviewed_tools_and_task_payload(self):
        client=ProductClient()
        for tool, task in [("agent_room_create","workflow"),("funding_stress_now","secret strategy text")]:
            with self.assertRaises(ValueError): await client.call("seiche",tool,task=task)

    async def test_partial_workflow_preserves_failed_product(self):
        async def transport(url,tool,*_):
            if "palimpsest" in url: raise TimeoutError()
            return {"result":{}}
        result=await ProductClient(transport=transport).funding_china_review()
        self.assertEqual(len(result["inputs"]),4)
        self.assertEqual(sum(x.get("status")=="unavailable" for x in result["inputs"]),2)
        self.assertEqual(result["input_eligibility"],"not_evaluated")


class JournalTests(unittest.TestCase):
    def test_immutable_capture_rejects_corruption_and_public_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/"private"
            receipt={"product":"seiche","payload":{"value":1}}
            ref=save_receipt(folder,receipt)
            self.assertEqual(read_receipt(ref["path"]),receipt)
            self.assertEqual(save_receipt(folder,receipt)["sha256"],ref["sha256"])
            Path(ref["path"]).write_text('{}')
            with self.assertRaises(ValueError): read_receipt(ref["path"])
            folder.chmod(0o755)
            with self.assertRaises(ValueError): save_receipt(folder,receipt)


class TrafficClassificationTests(unittest.TestCase):
    def test_explicit_modes_remain_reported_classes_not_verified_trades(self):
        for mode,expected in [('test','synthetic'),('unknown','unknown'),('paper','paper'),('shadow','shadow'),('operator_reported_production','operator_reported_production')]:
            client=ProductClient(mode=mode)
            self.assertEqual(client.transport.keywords['traffic_class'],expected)
