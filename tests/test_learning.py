"""Permission, isolation, timing and withdrawal tests for opt-in learning."""

import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import tempfile
import unittest

from financial_evidence.learning import LearningStore, PermissionDenied
from financial_evidence.learning.contracts import digest
from financial_evidence.learning.evaluation import evaluate

DAY = 86400
START = 1_800_000_000


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = START
        self.store = LearningStore(Path(self.temp.name) / "learning", clock=lambda: self.now)
        self.enrollment = self.enroll()
        self.token = self.enrollment["credential"]
        self.tenant = self.enrollment["tenant_id"]

    def enroll(self, purposes=None, **kwargs):
        return self.store.enroll(purposes=purposes or ["measurement", "private_evidence", "research_training"],
                                 policy_version="learning-v1", expires_at=self.now + 100 * DAY, **kwargs)

    def event(self, **changes):
        value = {"id": "attempt-1", "product": "seiche", "tool": "funding", "task": "funding_review",
                 "occurred_at": self.now, "duration_ms": 17, "status": "success", "mode": "shadow"}
        value.update(changes)
        return value

    def decision(self, **changes):
        feature = {"value": 2.5, "observed_at": self.now - 30, "available_at": self.now - 10, "source": "public-rate", "revision": "r1"}
        value = {"id": "decision-1", "decided_at": self.now, "target": "funding_next_release_change", "entity": "US-USD",
                 "horizon_seconds": 60, "mode": "shadow",
                 "evidence_refs": [{"kind": "product", "product": "seiche", "receipt_id": "receipt-1", "sha256": "a" * 64}],
                 "data_features": {"current_rate": feature}, "usage_features": {"request_count": {**feature, "value": 3, "source": "permitted-usage"}}}
        value.update(changes)
        return value

    def pair(self):
        self.store.record_decision(self.token, self.decision())
        self.now += 120
        result = self.store.record_outcome(self.token, {"id": "outcome-1", "decision_id": "decision-1", "value": .03,
                               "unit": "percentage_points", "observed_at": self.now - 30, "available_at": self.now - 10,
                               "source": "public-rate", "revision": "r2"})
        self.assertEqual(result["verification"], "operator_reported")

    def admit(self, **changes):
        value = {"purpose": "research_training", "reviewer": "reviewer-1", "rights_reference": "rights-sha-1",
                 "source_scopes": {"public-rate": "research_training", "permitted-usage": "research_training"},
                 "expires_at": self.now + DAY}
        value.update(changes)
        return self.store.review_contribution(self.tenant, "decision-1", **value)

    def reviewed(self):
        self.pair()
        self.store.review_outcome(self.tenant, "outcome-1", reviewer="reviewer-1", verification_reference="publisher-vintage-r2")
        self.admit()

    def test_credentials_hashed_and_no_verified_institution_by_default(self):
        self.assertNotIn(self.token.encode(), self.store.path.read_bytes())
        self.assertFalse(self.store.describe(self.token)["organisation_verified"])
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.root.stat().st_mode & 0o777, 0o700)

    def test_allowlist_and_no_backfilled_measurement(self):
        for extra in ({"prompt": "secret"}, {"raw_arguments": {}}, {"ip": "127.0.0.1"}, {"portfolio": {}}, {"training_eligible": True}):
            with self.assertRaises(ValueError):
                self.store.record_tool(self.token, self.event(**extra))
        with self.assertRaises(ValueError):
            self.store.record_tool(self.token, self.event(occurred_at=START - 1))
        with self.assertRaises(ValueError):
            self.store.record_tool(self.token, self.event(duration_ms=float("nan")))
        self.assertEqual(self.store.report(self.token)["requests"], 0)

    def test_atomic_idempotency_and_conflict(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.store.record_tool(self.token, self.event()), range(8)))
        self.assertEqual(sum(result["created"] for result in results), 1)
        with self.assertRaises(ValueError):
            self.store.record_tool(self.token, self.event(duration_ms=99))
        self.assertEqual(self.store.report(self.token)["requests"], 1)

    def test_tenant_isolation_and_unknown_is_not_production(self):
        other = self.enroll()
        self.store.record_tool(self.token, self.event(mode="unknown", useful=True))
        self.assertEqual(self.store.report(other["credential"])["requests"], 0)
        self.assertEqual(self.store.report(self.token)["confirmed_useful_workflows"], 0)
        self.store.record_decision(self.token, self.decision())
        with self.assertRaises(ValueError):
            self.store.get_record(other["credential"], "decision", "decision-1")
        with self.assertRaises(PermissionDenied):
            self.store.report("x" * 43)

    def test_separate_purposes_and_no_automatic_shared_training(self):
        isolated = self.enroll(["measurement"])
        with self.assertRaises(PermissionDenied):
            self.store.record_decision(isolated["credential"], self.decision())
        self.pair()
        with self.assertRaises(ValueError):
            self.admit()
        self.assertEqual(self.store.export_dataset(purpose="research_training", target="funding_next_release_change")["status"], "insufficient_data")
        self.store.review_outcome(self.tenant, "outcome-1", reviewer="operator", verification_reference="public-release-r2")
        with self.assertRaises(PermissionDenied):
            self.admit(purpose="commercial_training")
        with self.assertRaises(ValueError):
            self.admit(source_scopes={"public-rate": "context_only", "permitted-usage": "research_training"})

    def test_feature_asof_outcome_timing_and_restricted_schema(self):
        value = self.decision()
        value["data_features"]["current_rate"]["available_at"] = self.now + 1
        with self.assertRaises(ValueError):
            self.store.record_decision(self.token, value)
        self.store.record_decision(self.token, self.decision())
        with self.assertRaises(ValueError):
            self.store.record_outcome(self.token, {"id": "bad", "decision_id": "decision-1", "value": 1, "unit": "percentage_points",
                     "observed_at": self.now, "available_at": self.now, "source": "public-rate", "revision": "r2"})
        self.now += 120
        outcome = {"id": "bad", "decision_id": "decision-1", "value": 1, "unit": "percentage_points",
                   "observed_at": self.now, "available_at": self.now, "source": "public-rate", "revision": "r2", "verification": "reviewer_verified"}
        with self.assertRaises(ValueError):
            self.store.record_outcome(self.token, outcome)

    def test_export_uses_received_time_and_source_reviews(self):
        self.reviewed()
        earlier = self.store.export_dataset(purpose="research_training", target="funding_next_release_change", as_of=START + 119)
        self.assertEqual(earlier["rows"], [])
        dataset = self.store.export_dataset(purpose="research_training", target="funding_next_release_change")
        self.assertEqual(len(dataset["rows"]), 1)
        self.assertEqual(dataset["manifest"]["data_sha256"], digest(dataset["rows"]))
        self.assertNotIn("lineage", dataset["manifest"])
        self.assertNotIn("decision_id", dataset["rows"][0]["outcome"])
        self.assertNotIn(self.token, json.dumps(dataset))
        self.assertEqual(self.store.report(self.token)["outcome_coverage"]["verified_rate"], 1)

    def test_withdrawal_invalidates_snapshots_and_models_preserves_other_purposes(self):
        self.reviewed()
        snapshot = self.store.export_dataset(purpose="research_training", target="funding_next_release_change")
        self.assertTrue(self.store.validate_snapshot(snapshot)["currently_valid"])
        self.store.record_model(model_id="experiment-1", snapshot_id=snapshot["manifest"]["id"], artifact_sha256="b" * 64)
        result = self.store.withdraw(self.token, purposes=["research_training"])
        self.assertTrue(result["model_review_required"])
        self.assertTrue(self.store.model_lineage()[0]["needs_review"])
        with self.assertRaises(ValueError):
            self.store.validate_snapshot(snapshot)
        self.store.record_tool(self.token, self.event())
        self.assertEqual(self.store.export_dataset(purpose="research_training", target="funding_next_release_change")["rows"], [])
        with self.assertRaises(ValueError):
            self.store.record_model(model_id="experiment-2", snapshot_id=snapshot["manifest"]["id"], artifact_sha256="c" * 64)

    def test_expiry_deletes_records_without_new_events_and_blocks_old_exports(self):
        self.reviewed()
        dataset = self.store.export_dataset(purpose="research_training", target="funding_next_release_change")
        self.now += DAY + 1
        self.store.expire()
        with self.assertRaises(ValueError):
            self.store.record_model(model_id="expired", snapshot_id=dataset["manifest"]["id"], artifact_sha256="a" * 64)
        self.now += 100 * DAY
        self.store.expire()
        self.assertEqual(self.store.report(self.token)["outcome_coverage"]["decisions"], 0)
        with self.assertRaises(PermissionDenied):
            self.store.record_tool(self.token, self.event())

    def test_delete_removes_credential_and_private_records(self):
        self.pair()
        self.store.delete_tenant(self.token)
        with self.assertRaises(PermissionDenied):
            self.store.describe(self.token)
        with self.store.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM records").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM tenants").fetchone()[0], 0)

    def test_return_denominators_and_cost_coverage(self):
        self.store.record_tool(self.token, self.event(id="day0", useful=True, cost_usd=.02))
        self.now += 8 * DAY
        self.store.record_tool(self.token, self.event(id="day8", useful=True))
        early = self.store.report(self.token)
        self.assertEqual(early["retention"]["d7"]["eligible"], 0)
        self.assertIsNone(early["cost_per_useful_workflow_usd"])
        self.now = START + 15 * DAY
        report = self.store.report(self.token)
        self.assertEqual(report["retention"]["d7"]["eligible"], 1)
        self.assertEqual(report["retention"]["d7"]["returned"], 1)
        self.assertEqual(report["retention"]["d30"]["eligible"], 0)
        self.assertEqual(report["cost_observed_requests"], 1)
        self.assertEqual(report["cost_eligible_requests"], 2)
        self.assertEqual(report["p95_duration_ms"], 17)

    def test_private_directory_and_symlinks_rejected(self):
        public = Path(self.temp.name) / "public"
        public.mkdir(mode=0o755)
        with self.assertRaises(ValueError):
            LearningStore(public)
        linked = Path(self.temp.name) / "linked"
        linked.symlink_to(self.store.root)
        with self.assertRaises(ValueError):
            LearningStore(linked)


def experiment_fixture(count=70):
    rows = []
    for index in range(count):
        decided = START + index * DAY
        def feature(value):
            return {"value": value, "observed_at": decided - 10, "available_at": decided - 1, "source": "reviewed-source", "revision": "v1"}
        x = (index % 7) - 3
        rows.append({"id": str(index), "entity": "US-USD", "target": "funding_next_release_change", "decided_at": decided,
                     "horizon_end": decided + 100, "decision_received_at": decided + 1,
                     "data_features": {"rate": feature(2.5)}, "usage_features": {"count": feature(x)},
                     "outcome": {"value": 2 * x + .1, "observed_at": decided + 100, "available_at": decided + 200,
                                 "received_at": decided + 201, "verification": "reviewer_verified"}})
    manifest = {"schema": "financial-evidence.learning-snapshot.v1", "id": "fixture-not-real-evidence", "purpose": "research_training",
                "target": "funding_next_release_change", "as_of": START + count * DAY, "data_sha256": digest(rows)}
    return {"manifest": manifest, "rows": rows}


class EvaluationTests(unittest.TestCase):
    def test_empty_dataset_reports_insufficient_not_skill(self):
        self.assertEqual(evaluate(experiment_fixture(0))["status"], "insufficient_data")

    def test_chronological_comparison_reports_actual_metrics(self):
        result = evaluate(experiment_fixture())
        self.assertEqual(result["status"], "evaluated")
        self.assertTrue(result["usage_improved_mae_on_this_holdout"])
        self.assertFalse(result["commercial_release_authorized"])
        self.assertLess(result["metrics"]["data_plus_usage"]["mae"], .1)
        self.assertGreater(result["metrics"]["data_only"]["mae"], 1)
        self.assertEqual(result, evaluate(experiment_fixture()))

    def test_data_only_baseline_runs_without_usage(self):
        data = experiment_fixture()
        for row in data["rows"]:
            row["usage_features"] = {}
        data["manifest"]["data_sha256"] = digest(data["rows"])
        result = evaluate(data)
        self.assertEqual(result["status"], "evaluated_baseline_only")
        self.assertEqual(result["usage_uplift"], "not_evaluable")
        self.assertIn("data_only", result["metrics"])
        self.assertNotIn("data_plus_usage", result["metrics"])
        self.assertIsNone(result["usage_improved_mae_on_this_holdout"])

    def test_late_training_labels_are_purged(self):
        data = experiment_fixture()
        for row in data["rows"][:25]:
            row["outcome"]["received_at"] = START + 65 * DAY
        data["manifest"]["data_sha256"] = digest(data["rows"])
        result = evaluate(data)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["excluded"]["overlapping_or_late_training_labels"], 25)

    def test_backfilled_decisions_and_future_features_excluded(self):
        data = experiment_fixture()
        data["rows"][0]["decision_received_at"] = data["rows"][0]["outcome"]["available_at"]
        data["rows"][1]["data_features"]["rate"]["available_at"] = START + 2 * DAY
        data["manifest"]["data_sha256"] = digest(data["rows"])
        result = evaluate(data)
        self.assertEqual(result["excluded"]["backfilled_after_outcome"], 1)
        self.assertEqual(result["excluded"]["invalid_time_or_verification"], 1)

    def test_tampering_and_mixed_entities(self):
        data = experiment_fixture()
        data["rows"][0]["outcome"]["value"] = 999
        with self.assertRaises(ValueError):
            evaluate(data)
        data["rows"][0]["entity"] = "EU-EUR"
        data["manifest"]["data_sha256"] = digest(data["rows"])
        self.assertEqual(evaluate(data)["reason"], "select_one_entity_before_evaluation")

    def test_cloned_queries_do_not_inflate_independent_labels(self):
        data = experiment_fixture(20)
        original = copy.deepcopy(data["rows"])
        for clone in range(5):
            for row in original:
                data["rows"].append({**copy.deepcopy(row), "id": f"clone-{clone}-{row['id']}"})
        data["manifest"]["data_sha256"] = digest(data["rows"])
        result = evaluate(data)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["eligible_rows"], 20)
        self.assertEqual(result["excluded"]["duplicate_outcome_observations"], 100)


if __name__ == "__main__":
    unittest.main()
