"""Forward clocks, missingness, archive integrity and genuine optional native tools."""
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "integrations" / "finance-research"))
from forward_evidence import capture, for_decision, load, numeric_record, save
from framework_workflows import crewai_review, langgraph_review, tradingagents_funding_tool

CAPTURED = "2026-10-10T19:00:00+00:00"
ROW = {
    "dataset": "money_markets", "product": "Seiche", "entity_id": "US-USD",
    "entity_name": "United States dollar", "metric": "SOFR", "value": 0,
    "unit": "%", "as_of": "2026-10-08", "source_status": "FRESH",
    "availability": "AVAILABLE", "rights_status": "allowed",
    "source_url": "https://example.invalid/observations", "source_field": "/rates/0/value",
    "knowledge_time": "2026-10-09T12:00:00+00:00", "published_at": "2026-10-09T08:00:00Z",
}


def packet():
    return {
        "schema": "financial-evidence.agent-result.v1", "dataset": "money_markets",
        "results": [copy.deepcopy(ROW), {**ROW, "metric": "WITHHELD", "value": None,
                                        "availability": "withheld", "rights_status": "restricted"}],
        "sources": [{"source_url": ROW["source_url"], "ok": True}],
        "diagnostics": [], "transport_status": "complete", "next_offset": None,
    }


class FixtureClient:
    def __init__(self):
        self.calls = []

    def query(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return packet()


class ForwardResearchTests(unittest.TestCase):
    def test_observation_and_capture_clocks_remain_distinct_without_invented_publication(self):
        original = packet()
        result = capture(original, captured_at=CAPTURED)
        row = result["rows"][0]
        self.assertEqual(row["event_time"], "2026-10-08")
        self.assertEqual(row["event_time_precision"], "date")
        self.assertEqual(row["available_at"], CAPTURED)
        self.assertEqual(row["row"]["knowledge_time"], ROW["knowledge_time"])
        self.assertEqual(row["row"]["published_at"], ROW["published_at"])
        original["results"][0]["value"] = 999
        self.assertEqual(row["row"]["value"], 0)

    def test_current_amended_history_refuses_backtest_and_use_before_capture(self):
        result = capture(packet(), captured_at=CAPTURED)
        for kwargs in [{"decision_at": "2026-10-09T19:00:00Z"},
                       {"decision_at": CAPTURED, "mode": "historical_backtest"}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                for_decision(result, **kwargs)
        self.assertIs(for_decision(result, decision_at=CAPTURED), result)

    def test_dates_and_timezone_naive_timestamps_are_rejected(self):
        for stamp in ["2026-10-10", "2026-10-10T19:00:00", "yesterday"]:
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                capture(packet(), captured_at=stamp)

    def test_partial_pages_and_failed_transport_never_become_full_coverage(self):
        for changes in [{"next_offset": 2}, {"transport_status": "partial"},
                        {"transport_status": "unavailable", "results": []}]:
            result = capture({**packet(), **changes}, captured_at=CAPTURED)
            self.assertFalse(result["coverage_complete"])
            self.assertEqual(result["packet"]["transport_status"], changes.get("transport_status", "complete"))

    def test_archive_preserves_all_rows_but_excludes_missing_values_from_numeric_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "capture"
            receipt = save(capture(packet(), captured_at=CAPTURED), destination)
            self.assertEqual(receipt["retained_rows"], 2)
            self.assertEqual(receipt["numeric_funding_rows"], 1)
            self.assertEqual(len(receipt["excluded_from_numeric_export"]), 1)
            record = json.loads((destination / "funding.jsonl").read_text())
            self.assertEqual(record["row"]["value"], 0)
            self.assertIsNone(load(destination / "capture.json")["rows"][1]["row"]["value"])
            with self.assertRaises(FileExistsError):
                save(capture(packet(), captured_at=CAPTURED), destination)

    def test_mutating_packet_or_capture_clock_fails_integrity_check(self):
        for mutation in [lambda value: value["packet"]["results"][0].update(value=9),
                         lambda value: value["rows"][0].update(available_at="2020-01-01T00:00:00Z")]:
            result = capture(packet(), captured_at=CAPTURED)
            mutation(result)
            with self.assertRaises(ValueError):
                for_decision(result, decision_at=CAPTURED)

    def test_numeric_import_rejects_unknown_rights_nonfinite_values_and_future_observation(self):
        for change in [{"rights_status": "unknown"}, {"value": None}, {"value": True},
                       {"value": float("nan")}, {"value": float("inf")},
                       {"availability": "withheld"}, {"dataset": "bank_risk"}, {"source_field": ""}]:
            record = capture(packet(), captured_at=CAPTURED)["rows"][0]
            record["row"].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                numeric_record(record)
        record = capture(packet(), captured_at=CAPTURED)["rows"][0]
        record["event_time"] = record["row"]["as_of"] = "2026-10-11"
        with self.assertRaises(ValueError):
            numeric_record(record)

    def test_unbounded_or_invalid_envelopes_fail(self):
        for changes in [{"schema": "wrong"}, {"results": [ROW] * 101}, {"sources": None},
                        {"transport_status": "ok"}, {"results": ["not a row"]}]:
            with self.subTest(changes=list(changes)), self.assertRaises(ValueError):
                capture({**packet(), **changes}, captured_at=CAPTURED)


class NativeFrameworkTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("langgraph"), "Native LangGraph is not installed")
    def test_langgraph_executes_real_tool_node_once_and_retains_missingness(self):
        client = FixtureClient()
        result = langgraph_review(client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result["packet"]["results"][0]["value"], 0)
        self.assertIsNone(result["packet"]["results"][1]["value"])

    @unittest.skipUnless(importlib.util.find_spec("crewai"), "Native CrewAI is not installed")
    def test_crewai_executes_native_tool_without_model_or_account(self):
        client = FixtureClient()
        result = crewai_review(client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result["packet"]["results"][1]["availability"], "withheld")

    @unittest.skipUnless(importlib.util.find_spec("langchain_core"), "Native LangChain is not installed")
    def test_tradingagents_extension_rejects_past_and_future_before_fetching(self):
        client = FixtureClient()
        tool = tradingagents_funding_tool(client)
        for day in ["2020-01-01", "2099-01-01"]:
            with self.subTest(day=day), self.assertRaises(ValueError):
                tool.invoke({"trade_date": day})
        self.assertEqual(client.calls, [])
        result = tool.invoke({"trade_date": datetime.now(timezone.utc).date().isoformat()})
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result["financial_authority"], "none")


if __name__ == "__main__":
    unittest.main()
