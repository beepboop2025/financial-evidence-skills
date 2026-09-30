"""Agent output semantics and real optional-framework registration."""

import copy
import importlib.util
import unittest

from test_openbb_tables import MONEY, source_result
from financial_evidence.agents import EvidenceAgentClient, framework_tools, tool_functions
from financial_evidence.service import EvidenceService


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.document = copy.deepcopy(MONEY)
        self.ok = True
        self.calls = []

        def fetcher(source, **_):
            self.calls.append(source.url)
            value = source_result(source, self.document, ok=self.ok)
            value["retrieved_at"] = str(len(self.calls))
            return value

        self.service = EvidenceService(ttl=0, error_ttl=0, fetcher=fetcher)
        self.addCleanup(self.service.close)
        self.client = EvidenceAgentClient(self.service)

    def test_repeat_query_keeps_clocks_and_gaps_without_repeating_rows(self):
        first = self.client.query("money_markets")
        self.assertEqual(first["results"][0]["value"], 0)
        self.assertIsNone(first["results"][1]["value"])
        second = self.client.query("money_markets", previous_revision=first["revision"])
        self.assertEqual(second["change_status"], "unchanged")
        self.assertEqual(second["results"], [])
        self.assertEqual(second["suppressed_rows"], 2)
        self.assertEqual(second["freshness_status"], "not_evaluated")
        self.assertNotEqual(first["sources"][0]["retrieved_at"], second["sources"][0]["retrieved_at"])
        self.assertIn("source_reported", second["sources"][0])

    def test_observation_clock_rights_and_filter_changes_invalidate_revision(self):
        first = self.client.query("money_markets")
        for key, value in [("asof", "2026-09-25"), ("redistribution_status", "restricted")]:
            self.document["markets"][0]["benchmark"][key] = value
            result = self.client.query("money_markets", previous_revision=first["revision"])
            self.assertEqual(result["change_status"], "changed")
            self.assertNotEqual(result["revision"], first["revision"])
        other = self.client.query("money_markets", entity="USD", previous_revision=first["revision"])
        self.assertEqual(other["change_status"], "changed")
        self.assertIsNone(other["results"][0]["value"])

    def test_failure_never_suppresses_diagnostics(self):
        first = self.client.query("money_markets")
        self.ok = False
        failed = self.client.query("money_markets", previous_revision=first["revision"])
        repeated = self.client.query("money_markets", previous_revision=failed["revision"])
        self.assertEqual(repeated["transport_status"], "unavailable")
        self.assertEqual(repeated["change_status"], "changed")
        self.assertTrue(repeated["diagnostics"])
        self.assertNotIn("suppressed_rows", repeated)

    def test_review_fetches_each_product_once_and_preserves_schema_gaps(self):
        result = self.client.review(bank="missing bank", limit=2)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(len(set(self.calls)), 3)
        self.assertEqual([x["dataset"] for x in result["sections"]], ["money_markets", "bank_risk", "market_liquidity"])
        self.assertEqual(result["sections"][1]["results"], [])
        self.assertTrue(result["sections"][1]["diagnostics"])
        self.assertEqual(result["financial_authority"], "none")
        self.assertNotIn("document", result["sources"][0])
        self.assertEqual(result["sections"][0]["results"][0]["source_field"], "/markets/0/benchmark/value")

    def test_invalid_parameters_do_not_fetch(self):
        for kwargs in [{"limit": 101}, {"limit": True}, {"offset": -1}, {"previous_revision": "bad"}, {"start_date": "yesterday"}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.client.query("money_markets", **kwargs)
        with self.assertRaises(ValueError):
            self.client.review(limit=26)
        self.assertFalse(self.calls)

    def test_plain_tools_are_offline_until_called_and_shared_service_is_not_closed(self):
        tools = tool_functions(self.client)
        self.assertEqual(len(tools), 3)
        self.assertEqual(len(tools[0]()["datasets"]), 7)
        self.assertFalse(self.calls)
        self.client.close()
        self.assertTrue(self.client.query("money_markets")["results"])
        with self.assertRaises(ValueError):
            framework_tools("unknown", self.client)

    def test_optional_native_tool_schemas_with_installed_frameworks(self):
        checked = 0
        for name, module in [("langchain", "langchain_core"), ("crewai", "crewai"), ("openai", "agents"), ("pydantic-ai", "pydantic_ai")]:
            if importlib.util.find_spec(module) is None:
                continue
            with self.subTest(framework=name):
                tools = framework_tools(name, self.client)
                self.assertEqual(len(tools), 3)
                checked += 1
                if name == "langchain":
                    self.assertIn("money_markets", tools[1].args_schema.model_json_schema()["properties"]["dataset"]["enum"])
                    self.assertEqual(len(tools[0].invoke({})["datasets"]), 7)
                if name == "openai":
                    self.assertIn("dataset", tools[1].params_json_schema["properties"])
        if not checked:
            self.skipTest("Optional agent SDKs are not installed")


if __name__ == "__main__":
    unittest.main()
