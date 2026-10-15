import asyncio
import json
import unittest

from financial_evidence.trading.latency import measure_latency, summarize


class Client:
    def __init__(self, **kwargs):
        assert kwargs["mode"] == "test" and kwargs["credential"] is None
        assert kwargs["cache_seconds"] == 0
        self.closed = False
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self.closed = True

    async def call(self, product, tool, arguments):
        self.calls.append(product)
        if product == "seiche":
            raise OSError("secret payload should never appear")
        return {"payload": {"result": {}}, "payload_sha256": "a" * 64}


class LatencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_failure_stops_only_affected_probe_and_closes_client(self):
        instances = []
        def factory(**kwargs):
            client = Client(**kwargs)
            instances.append(client)
            return client
        result = await measure_latency(products=["seiche", "undertow"], samples=3, client_factory=factory)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(instances[0].calls.count("seiche"), 1)
        self.assertEqual(instances[0].calls.count("undertow"), 3)
        self.assertTrue(instances[0].closed)
        self.assertNotIn("secret", json.dumps(result))
        self.assertIsNone(result["products"][1]["repeat_calls"]["p95_ms"])

    async def test_bad_input_never_constructs_client(self):
        for kwargs in ({"samples": 1000}, {"samples": True}, {"timeout": float("nan")},
                       {"products": []}, {"products": ["other"]}):
            with self.assertRaises(ValueError):
                await measure_latency(client_factory=lambda **_: self.fail("must not connect"), **kwargs)

    async def test_hung_call_deadline_is_reported_without_retry(self):
        class Hung(Client):
            async def call(self, *_):
                await asyncio.sleep(30)
        result = await measure_latency(products=["undertow"], timeout=.01, client_factory=Hung)
        self.assertEqual(result["products"][0]["calls"][0]["reason"], "timeout")
        self.assertEqual(len(result["products"][0]["calls"]), 1)

    def test_small_samples_do_not_claim_tail_percentiles(self):
        self.assertIsNone(summarize([1, 2, 3])["p95_ms"])
        self.assertEqual(summarize(list(range(1, 101)))["p95_ms"], 95)
        self.assertIsNone(summarize(list(range(1, 101)))["p99_ms"])
        self.assertEqual(summarize(list(range(1, 1001)))["p99_ms"], 990)
