"""Actionable feedback without counting tests, retries, or ratings as adoption."""
import json
from pathlib import Path
import tempfile
import unittest

from financial_evidence.learning import LearningStore, PermissionDenied
from financial_evidence.learning import contracts as c
from financial_evidence.learning.insights import summarize

NOW = 1_800_000_000
DAY = 86400


def event(**changes):
    value = {
        "id": "run:read", "logical_workflow_id": "run", "product": "seiche",
        "tool": "financial_evidence_workflow", "task": "funding_review",
        "occurred_at": NOW, "duration_ms": 150, "status": "success", "mode": "paper",
        "event_kind": "attempt",
    }
    return {**value, **changes}


def feedback(**changes):
    return event(**{"id": "run:feedback", "event_kind": "feedback", "duration_ms": 0,
                    "useful": False, "feedback_reason": "missing_data",
                    "data_gaps": ["historical_depth"], **changes})


class ProductLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = NOW
        self.store = LearningStore(Path(self.temp.name) / "learning", clock=lambda: self.now)
        self.token = self.enroll()

    def enroll(self):
        return self.store.enroll(
            purposes=["measurement"], policy_version="measurement-v1",
            expires_at=self.now + 90 * DAY, retention_days=30,
        )["credential"]

    def test_schema_rejects_private_text_bad_categories_and_fake_request_metrics(self):
        for changes in (
            {"feedback_reason": "private account text"},
            {"data_gaps": ["https://private.example/portfolio"]},
            {"data_gaps": [{"private": "text"}]},
            {"data_gaps": []},
            {"data_gaps": ["historical_depth"] * 2},
            {"data_gaps": sorted(c.DATA_GAPS)},
            {"event_kind": "rating"},
            {"duration_ms": 10},
            {"cost_usd": 0},
            {"cached": False},
            {"failure_reason": "access_denied"},
            {"raw_arguments": "private"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.store.record_tool(self.token, feedback(**changes))
        for field in ("logical_workflow_id", "useful"):
            value = feedback()
            value.pop(field)
            with self.assertRaises(ValueError):
                self.store.record_tool(self.token, value)
        with self.assertRaises(ValueError):
            self.store.record_tool(self.token, event(failure_reason="access_denied"))
        self.assertEqual(self.store.report(self.token)["measurement_records"], 0)

    def test_feedback_is_not_an_attempt_latency_failure_or_missing_cost(self):
        self.store.record_tool(self.token, event(cost_usd=.02))
        value = feedback(useful=True)
        self.store.record_tool(self.token, value)
        self.store.record_tool(self.token, value)
        report = self.store.report(self.token)
        self.assertEqual(report["requests"], 1)
        self.assertEqual(report["feedback_records"], 1)
        self.assertEqual(report["measurement_records"], 2)
        self.assertEqual(report["p50_duration_ms"], 150)
        self.assertEqual(report["cost_per_useful_workflow_usd"], .02)
        self.assertEqual(report["cost_eligible_requests"], 1)
        self.assertEqual(report["product_learning"]["confirmed_useful_workflows"], 1)
        self.assertEqual(report["product_learning"]["feedback_coverage"], 1)
        self.assertEqual(report["product_learning"]["requested_data"][0]["affected_workflows"], 1)

    def test_legacy_workflow_feedback_is_recognized_without_changing_receipts(self):
        legacy = feedback()
        legacy.pop("event_kind")
        self.store.record_tool(self.token, event())
        receipt = self.store.record_tool(self.token, legacy)
        self.assertEqual(receipt["sha256"], c.digest(legacy))
        report = self.store.report(self.token)
        self.assertEqual(report["requests"], 1)
        self.assertEqual(report["feedback_records"], 1)
        self.assertFalse(c.is_feedback(event(id="run:feedback", useful=True)))

    def test_missing_feedback_is_unknown_and_feedback_only_is_not_an_attempt(self):
        report = summarize([("one", event()), ("two", feedback(useful=True))])
        self.assertEqual(report["observed_workflows"], 1)
        self.assertEqual(report["workflows_without_feedback"], 1)
        self.assertEqual(report["not_useful_workflows"], 0)
        self.assertEqual(report["confirmed_useful_workflows"], 0)
        self.assertEqual(report["feedback_only_workflows"], 1)
        self.assertEqual(report["feedback_only_reported_useful"], 1)
        self.assertIsNone(summarize([])["feedback_coverage"])

    def test_repeated_reports_do_not_outvote_more_affected_workspaces(self):
        events = []
        for index in range(5):
            events.append(("one", feedback(id=f"rating-{index}")))
        for owner in ("two", "three"):
            events.append((owner, feedback(data_gaps=["series_coverage"])))
        # Synthetic and unclassified traffic never enters improvement priorities.
        for mode in ("unknown", "test", "backtest"):
            events.append(("excluded", feedback(mode=mode, data_gaps=["venue_coverage"])))
        report = summarize(events)
        self.assertEqual(report["requested_data"][0]["category"], "series_coverage")
        self.assertEqual(report["requested_data"][0]["affected_workspaces"], 2)
        self.assertEqual(report["requested_data"][1]["affected_workflows"], 1)
        self.assertEqual(report["excluded_events_by_mode"], {"backtest": 1, "test": 1, "unknown": 1})
        self.assertNotIn("venue_coverage", json.dumps(report["requested_data"]))
        self.assertNotIn('"one"', json.dumps(report))
        self.assertFalse(report["data_requests_grant_source_access"])

    def test_conflicting_feedback_stays_unknown_and_product_workflows_do_not_collide(self):
        rows = [("one", event()), ("one", feedback(useful=True)),
                ("one", feedback(id="different-rating", useful=False)),
                ("one", event(product="undertow", task="liquidity"))]
        report = summarize(rows)
        self.assertEqual(report["observed_workflows"], 2)
        self.assertEqual(report["confirmed_useful_workflows"], 0)
        self.assertEqual(report["not_useful_workflows"], 0)
        self.assertEqual(report["conflicting_feedback_workflows"], 1)
        self.assertEqual(report["workflows_without_feedback"], 1)

    def test_refusals_and_reported_problems_keep_their_separate_basis(self):
        report = summarize([
            ("one", event(status="refused", failure_reason="rate_limited")),
            ("one", feedback(status="refused", feedback_reason="access_blocked")),
        ])
        self.assertEqual(
            {(row["signal"], row["category"]) for row in report["recurring_problems"]},
            {("attempt", "rate_limited"), ("feedback", "access_blocked")},
        )
        self.assertEqual(report["observed_attempts"], 1)

    def test_delayed_feedback_does_not_manufacture_a_return_visit(self):
        self.store.record_tool(self.token, event(useful=True))
        self.now += 8 * DAY
        self.store.record_tool(self.token, feedback(useful=True, occurred_at=self.now))
        self.now += 7 * DAY
        report = self.store.report(self.token)
        self.assertEqual(report["retention"]["d7"]["eligible"], 1)
        self.assertEqual(report["retention"]["d7"]["returned"], 0)
        self.assertEqual(report["confirmed_useful_workflows"], 1)

    def test_private_reports_withdrawal_expiry_and_permissions(self):
        other = self.enroll()
        self.store.record_tool(self.token, event())
        self.store.record_tool(self.token, feedback())
        self.assertEqual(self.store.report(other)["product_learning"]["requested_data"], [])
        self.assertEqual(self.store.report()["product_learning"]["requested_data"][0]["affected_workspaces"], 1)
        self.store.withdraw(self.token, purposes=["measurement"], delete=True)
        with self.assertRaises(PermissionDenied):
            self.store.record_tool(self.token, feedback(id="retry"))
        self.assertEqual(self.store.report()["product_learning"]["requested_data"], [])
        self.store.record_tool(other, event())
        self.store.record_tool(other, feedback())
        self.now += 31 * DAY
        self.assertEqual(self.store.report()["product_learning"]["requested_data"], [])


if __name__ == "__main__":
    unittest.main()
