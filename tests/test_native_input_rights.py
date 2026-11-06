import asyncio
import json
import unittest
from financial_evidence.trading.client import ProductClient
from financial_evidence.trading.input_rights import project_native_payload


class NativeRightsTests(unittest.TestCase):
    def test_nested_restriction_removes_all_dependent_representations(self):
        for source in ("fred", "coinbase", "https://data.binance.vision/file.zip", "OONI", "https://t.me/public/12", "yahoo finance chart", "https://archive-api.open-meteo.com/v1/archive"):
            document = {"rows": [{"source": source, "value": 12345}], "derived_total": 24690}
            original = {"server": {"name": "fixture"}, "result": {"structuredContent": document,
                "content": [{"type": "text", "text": json.dumps(document)}, {"type": "text", "text": "dependent 24690"}], "_meta": {"raw": 12345}}}
            out, receipt = project_native_payload(original)
            self.assertNotIn("12345", json.dumps(out))
            self.assertNotIn("24690", json.dumps(out))
            self.assertEqual(original["result"]["structuredContent"]["derived_total"], 24690)
            self.assertFalse(receipt["ai_inference_eligible"])

    def test_safe_sources_and_source_names_in_ordinary_prose_do_not_grant_or_deny(self):
        payload = {"result": {"structuredContent": {"source": "US Treasury", "value": 4,
                   "note": "Coinbase requires separate review"}}}
        self.assertEqual(project_native_payload(payload), (payload, None))

    def test_json_text_cannot_bypass_structured_gate(self):
        payload = {"result": {"content": [{"type": "text", "text": '{"source_id":"coinbase_exchange_public_market_data","value":9137}'}]}}
        out, receipt = project_native_payload(payload)
        self.assertNotIn("9137", json.dumps(out))
        self.assertEqual(receipt["sources"], ["coinbase"])

    def test_embedded_json_resource_has_the_same_gate(self):
        payload = {"result": {"content": [{"type": "resource", "resource": {
            "uri": "fixture:input", "text": '{"source":"Coinbase","value":9137}'}}]}}
        out, receipt = project_native_payload(payload)
        self.assertNotIn("9137", json.dumps(out))
        self.assertEqual(receipt["sources"], ["coinbase"])

    def test_explicit_plaintext_provenance_withholds_dependent_text(self):
        for text in ("Source: Coinbase\nprice: 9137", "**Source:** Coinbase\nDerived value: 9137", "Provider = OONI\n93521 observations"):
            payload = {"result": {"content": [{"type": "text", "text": text}, {"type": "text", "text": "dependent 18274"}]}}
            out, receipt = project_native_payload(payload)
            self.assertIsNotNone(receipt)
            self.assertNotIn("9137", json.dumps(out))
            self.assertNotIn("93521", json.dumps(out))
            self.assertNotIn("18274", json.dumps(out))

    def test_plain_embedded_resource_uses_explicit_source_uri(self):
        payload = {"result": {"content": [{"type": "resource", "resource": {
            "uri": "https://api.exchange.coinbase.com/products/BTC-USD/book", "text": "price 9137"}}]}}
        out, receipt = project_native_payload(payload)
        self.assertEqual(receipt["sources"], ["coinbase"])
        self.assertNotIn("9137", json.dumps(out))

    def test_incidental_opaque_text_is_not_a_positive_qualification(self):
        payload = {"result": {"content": [{"type": "text", "text": "Review Coinbase licensing before use."}]}}
        self.assertEqual(project_native_payload(payload), (payload, None))
        async def transport(*args):
            return payload
        result = asyncio.run(ProductClient(transport=transport).call("undertow", "liquidity_tiers"))
        self.assertEqual(result["ai_input_eligibility"], "requires_source_qualification")

    def test_client_hashes_and_caches_only_projected_payload(self):
        calls = []
        async def transport(*args):
            calls.append(args)
            return {"result": {"structuredContent": {"venue": "coinbase", "value": 9911}}}
        async def exercise():
            client = ProductClient(transport=transport, cache_seconds=30)
            first = await client.call("undertow", "liquidity_tiers")
            second = await client.call("undertow", "liquidity_tiers")
            self.assertEqual(first["ai_input_eligibility"], "restricted")
            self.assertNotEqual(first["payload_sha256"], first["upstream_payload_sha256"])
            self.assertTrue(second["cache_hit"])
            self.assertNotIn("9911", json.dumps(client.cache, default=lambda o: o.__dict__))
            self.assertEqual(len(calls), 1)
        asyncio.run(exercise())
