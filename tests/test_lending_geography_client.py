"""Public geography requests remain read-only, bounded and source preserving."""
import copy
import json
import unittest

from financial_evidence.trading import ProductClient
from financial_evidence.trading.client import READ_TOOLS, validate_read_arguments


class LendingGeographyTests(unittest.IsolatedAsyncioTestCase):
    async def test_routes_only_to_the_configured_hosted_product_and_preserves_evidence(self):
        calls = []
        evidence = {"schema": "liquilens.lending-geography.v1", "scope": "research",
                    "score_authority": False, "scoring_eligible": False,
                    "as_of": "2026-11-05", "offset": 5, "next_offset": 10,
                    "districts_total": 33, "sources": {"soil_moisture": {"as_of": "2024-10-15"}},
                    "districts": [{"recent_months": {"mm": [0, None, 10]}}]}
        result = {"content": [{"type": "text", "text": json.dumps(evidence)}]}

        async def transport(url, tool, arguments, timeout):
            calls.append((url, tool, copy.deepcopy(arguments)))
            return {"result": copy.deepcopy(result)}

        client = ProductClient(transport=transport)
        receipt = await client.call("liquilens", "lending_geography",
                                    {"id": "in-state-rajasthan", "offset": 5}, task="geography_research")
        self.assertEqual(calls, [("https://agents.seiche.info/products/liquilens/mcp", "lending_geography",
                                 {"id": "in-state-rajasthan", "offset": 5})])
        self.assertEqual(receipt["payload"]["result"], result)
        recovered = json.loads(receipt["payload"]["result"]["content"][0]["text"])
        self.assertEqual(recovered["districts"][0]["recent_months"]["mm"], [0, None, 10])
        self.assertEqual(recovered["sources"]["soil_moisture"]["as_of"], "2024-10-15")
        self.assertEqual(recovered["next_offset"], 10)
        self.assertFalse(recovered["score_authority"])

    async def test_invalid_geography_arguments_never_reach_transport(self):
        calls = []
        async def transport(*args):
            calls.append(args)
            return {"result": {}}
        client = ProductClient(transport=transport)
        cases = [{}, {"id": "../../secret"}, {"id": "https://example.org"},
                 {"id": "in-dist-rajasthan-jaipur", "offset": True},
                 {"id": "in-dist-rajasthan-jaipur", "offset": -1},
                 {"id": "in-dist-rajasthan-jaipur", "offset": 1001},
                 {"id": "in-dist-rajasthan-jaipur", "offset": 0.5},
                 {"id": "in-dist-rajasthan-jaipur", "score_authority": True},
                 {"id": "in-dist-" + "a" * 120}]
        for arguments in cases:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                await client.call("liquilens", "lending_geography", arguments)
        self.assertEqual(calls, [])

    def test_all_four_public_identity_types_are_supported_without_new_write_tools(self):
        for place in ("in-dist-rajasthan-jaipur", "in-state-rajasthan", "in-dccb-rajasthan-jaipur", "in-stcb-rajasthan"):
            validate_read_arguments("liquilens", "lending_geography", {"id": place})
        self.assertIn("lending_geography", READ_TOOLS["liquilens"])
        self.assertNotIn("lending_geography", READ_TOOLS["undertow"])
        self.assertNotIn("approve_credit", READ_TOOLS["liquilens"])


if __name__ == "__main__":
    unittest.main()
