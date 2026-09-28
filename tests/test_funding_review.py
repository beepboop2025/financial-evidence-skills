"""Deterministic acceptance failures for a captured USD funding review."""

import copy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_funding_review import REQUIRED, TGA_SCHEDULE_SOURCE, evaluate, main

NOW = "2026-09-28T19:17:00Z"
CLOCK = "2026-09-28T19:15:00Z"


def captures():
    metrics = [
        {
            "id": name,
            "value": 0,
            "unit": unit,
            "cadence": cadence,
            "asof": "2026-09-23" if cadence == "weekly" else "2026-09-25",
            "source": "Synthetic test source",
            "status": "available",
            "freshness": "fresh",
        }
        for name, (unit, cadence) in REQUIRED.items()
    ]
    metrics.append({**metrics[0], "id": "distribution.sofr.rate"})
    desk = {
        "ok": True,
        "schema": "seiche.money-market-desk.v1",
        "selection": "all",
        "snapshot_generated_at": CLOCK,
        "sections": [{"id": "test", "metrics": metrics}],
    }
    atlas = {
        "schema": "seiche.global-money-markets.v1",
        "generated_at": CLOCK,
        "markets": [
            {
                "market_id": "US-USD",
                "benchmark": {
                    "mnemonic": "SOFR",
                    "value": 0,
                    "unit": "%",
                    "asof": "2026-09-25",
                    "availability": "AVAILABLE",
                    "status": "FRESH",
                    "redistribution_status": "allowed",
                    "missed_publication_opportunities": 0,
                },
            }
        ],
    }
    health = {
        "generated_at": CLOCK,
        "provenance": [{"mnemonic": "SOFR", "asof": "2026-09-25"}],
    }
    return desk, atlas, health


class FundingReviewTests(unittest.TestCase):
    def result(self, docs):
        return evaluate(*docs, evaluated_at=NOW)

    def codes(self, docs):
        result = self.result(docs)
        self.assertEqual(result["status"], "attention_required")
        return {issue["code"] for issue in result["issues"]}

    def test_complete_zero_values_and_distinct_weekly_dates_are_valid(self):
        docs = captures()
        original = copy.deepcopy(docs)
        self.assertEqual(self.result(docs)["status"], "checks_passed")
        self.assertEqual(docs, original)

    def test_missing_metric_cannot_be_replaced_by_high_coverage(self):
        docs = captures()
        docs[0]["sections"][0]["metrics"].pop(0)
        docs[0]["coverage"] = {"coverage_pct": 100}
        self.assertIn("missing_required_metric", self.codes(docs))

    def test_duplicate_metric_is_not_silently_overwritten(self):
        docs = captures()
        docs[0]["sections"][0]["metrics"].append(
            {**docs[0]["sections"][0]["metrics"][0], "value": 99}
        )
        self.assertIn("duplicate_metric", self.codes(docs))

    def test_source_claim_of_freshness_does_not_override_age(self):
        docs = captures()
        docs[0]["sections"][0]["metrics"][1]["asof"] = "2026-01-01"
        self.assertIn("observation_exceeds_age_backstop", self.codes(docs))

    def test_aging_unknown_and_unavailable_states_require_attention(self):
        for state in ("aging", "stale", "unknown", None):
            with self.subTest(state=state):
                docs = captures()
                docs[0]["sections"][0]["metrics"][1]["freshness"] = state
                self.assertIn("required_metric_not_reported_fresh", self.codes(docs))

    def test_complete_tga_schedule_can_explain_holiday_age_but_not_a_missed_release(
        self,
    ):
        docs = captures()
        holiday_now = "2026-09-08T19:00:00Z"
        for key, document in zip(
            ("snapshot_generated_at", "generated_at", "generated_at"), docs
        ):
            document[key] = "2026-09-08T18:58:00Z"
        for metric in docs[0]["sections"][0]["metrics"]:
            metric["asof"] = (
                "2026-09-02" if metric["cadence"] == "weekly" else "2026-09-04"
            )
        docs[1]["markets"][0]["benchmark"]["asof"] = "2026-09-04"
        docs[2]["provenance"][0]["asof"] = "2026-09-04"
        tga = next(
            row
            for row in docs[0]["sections"][0]["metrics"]
            if row["id"] == "liquidity.tga"
        )
        tga.update(
            asof="2026-09-03",
            freshness_policy="treasury-dts-next-business-day-v1",
            publication_schedule={
                "source_url": TGA_SCHEDULE_SOURCE,
                "timezone": "America/New_York",
                "clock_precision": "scheduled",
                "expected_observation_date": "2026-09-03",
                "latest_due_at": "2026-09-04T16:00:00-04:00",
                "missed_publication_opportunities": 0,
            },
        )
        # Tuesday before the new release after Labor Day: Thursday's TGA
        # observation is five calendar days old but the Friday due time is
        # still within the bounded publisher-schedule acceptance interval.
        self.assertEqual(
            evaluate(*docs, evaluated_at=holiday_now)["status"], "checks_passed"
        )
        for field, value in (
            ("missed_publication_opportunities", 1),
            ("expected_observation_date", "2026-09-04"),
        ):
            broken = copy.deepcopy(docs)
            row = next(
                row
                for row in broken[0]["sections"][0]["metrics"]
                if row["id"] == "liquidity.tga"
            )
            row["publication_schedule"][field] = value
            result = evaluate(*broken, evaluated_at=holiday_now)
            self.assertEqual(result["status"], "attention_required")
            self.assertTrue(
                {issue["code"] for issue in result["issues"]}
                & {"publication_opportunity_missed", "publication_schedule_invalid"}
            )
        tga["publication_schedule"]["latest_due_at"] = "2099-01-01T00:00:00Z"
        self.assertIn(
            "publication_schedule_invalid",
            {
                issue["code"]
                for issue in evaluate(*docs, evaluated_at=holiday_now)["issues"]
            },
        )

    def test_expired_tga_schedule_cannot_hide_old_observations(self):
        for day, due in (
            ("2020-01-01", "2020-01-02T16:00:00-05:00"),
            ("2026-09-22", "2026-09-23T16:00:00-04:00"),
        ):
            docs = captures()
            tga = next(
                row
                for row in docs[0]["sections"][0]["metrics"]
                if row["id"] == "liquidity.tga"
            )
            tga.update(
                asof=day,
                freshness_policy="treasury-dts-next-business-day-v1",
                publication_schedule={
                    "source_url": TGA_SCHEDULE_SOURCE,
                    "timezone": "America/New_York",
                    "clock_precision": "scheduled",
                    "expected_observation_date": day,
                    "latest_due_at": due,
                    "missed_publication_opportunities": 0,
                },
            )
            codes = self.codes(docs)
            self.assertIn("publication_schedule_invalid", codes)
            self.assertIn("observation_exceeds_age_backstop", codes)

    def test_tga_schedule_requires_recognized_source_and_local_release_time(self):
        for source, due, expected in (
            (
                "https://home.treasury.gov/anything",
                "2026-09-25T16:00:00-04:00",
                "2026-09-24",
            ),
            (TGA_SCHEDULE_SOURCE, "2026-09-25T15:00:00-04:00", "2026-09-24"),
            (TGA_SCHEDULE_SOURCE, "2026-09-25T16:00:00-04:00", "2026-09-25"),
            (TGA_SCHEDULE_SOURCE, "2026-09-25T16:00:00-04:00", "2026-09-20"),
        ):
            docs = captures()
            tga = next(
                row
                for row in docs[0]["sections"][0]["metrics"]
                if row["id"] == "liquidity.tga"
            )
            tga.update(
                freshness_policy="treasury-dts-next-business-day-v1",
                publication_schedule={
                    "source_url": source,
                    "timezone": "America/New_York",
                    "clock_precision": "scheduled",
                    "expected_observation_date": expected,
                    "latest_due_at": due,
                    "missed_publication_opportunities": 0,
                },
            )
            self.assertIn("publication_schedule_invalid", self.codes(docs))

    def test_missing_nonfinite_boolean_values_and_unit_changes_fail(self):
        for value in (None, True, float("nan"), float("inf"), 10**400):
            with self.subTest(value_type=type(value).__name__):
                docs = captures()
                docs[0]["sections"][0]["metrics"][1]["value"] = value
                self.assertIn("required_value_unavailable", self.codes(docs))
        docs = captures()
        docs[0]["sections"][0]["metrics"][1]["unit"] = "basis_points"
        self.assertIn("unit_or_cadence_changed", self.codes(docs))

    def test_future_and_undated_observations_fail(self):
        for value, code in (
            ("2099-01-01", "future_observation_date"),
            (None, "missing_or_invalid_observation_date"),
        ):
            docs = captures()
            docs[0]["sections"][0]["metrics"][1]["asof"] = value
            self.assertIn(code, self.codes(docs))

    def test_stale_future_and_naive_snapshot_clocks_fail(self):
        for value, code in (
            ("2026-09-28T18:00:00Z", "snapshot_too_old"),
            ("2026-09-28T20:00:00Z", "future_snapshot_clock"),
            ("2026-09-28T19:15:00", "missing_or_invalid_snapshot_clock"),
        ):
            docs = captures()
            docs[0]["snapshot_generated_at"] = value
            self.assertIn(code, self.codes(docs))

    def test_new_capture_time_cannot_hide_cross_surface_observation_lag(self):
        docs = captures()
        docs[1]["markets"][0]["benchmark"]["asof"] = "2026-09-24"
        self.assertIn("sofr_observation_dates_disagree", self.codes(docs))

    def test_same_date_conflicting_values_require_attention(self):
        docs = captures()
        docs[1]["markets"][0]["benchmark"]["value"] = 3.9
        self.assertIn("sofr_same_date_values_disagree", self.codes(docs))

    def test_missed_publication_cannot_be_overridden_by_fresh_label(self):
        docs = captures()
        docs[1]["markets"][0]["benchmark"]["missed_publication_opportunities"] = 2
        self.assertIn("publication_opportunity_missed", self.codes(docs))

    def test_missing_health_data_or_schema_drift_requires_attention(self):
        docs = captures()
        docs[2]["provenance"] = []
        self.assertIn("health_sofr_date_missing_or_disagrees", self.codes(docs))
        docs = captures()
        docs[0]["schema"] = "new-format"
        self.assertIn("desk_unavailable_or_schema_changed", self.codes(docs))

    def test_ambiguous_usd_benchmarks_fail(self):
        docs = captures()
        docs[1]["markets"] *= 2
        self.assertIn("missing_or_duplicate_usd_benchmark", self.codes(docs))

    def test_parent_publication_restrictions_override_child_availability(self):
        for document in (0, 1):
            docs = captures()
            docs[document]["publication_allowed"] = False
            self.assertIn("publication_restricted", self.codes(docs))
        docs = captures()
        docs[1]["markets"][0]["rights_status"] = "metadata_only"
        self.assertIn("publication_restricted", self.codes(docs))
        docs = captures()
        docs[0]["sections"][0]["rights_status"] = "metadata_only"
        self.assertIn("publication_restricted", self.codes(docs))

    def test_invalid_evaluation_time_and_unbounded_policy_fail(self):
        for value in ("2026-09-28", "not-a-date"):
            with self.assertRaises(ValueError):
                evaluate(*captures(), evaluated_at=value)
        for value in (0, 86401, float("nan"), True):
            with self.assertRaises(ValueError):
                evaluate(*captures(), evaluated_at=NOW, max_snapshot_age_seconds=value)

    def test_cli_hashes_exact_inputs_and_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as folder:
            args = []
            for name, doc in zip(("desk", "atlas", "health"), captures()):
                path = Path(folder) / (name + ".json")
                path.write_text(json.dumps(doc))
                args += ["--" + name, str(path)]
            args += ["--evaluated-at", NOW]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(args), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(set(report["input_sha256"]), {"desk", "atlas", "health"})
            self.assertTrue(all(len(x) == 64 for x in report["input_sha256"].values()))
            for token in ("NaN", "1e999", "-1e999"):
                (Path(folder) / "desk.json").write_text('{"bad":' + token + "}")
                with (
                    self.subTest(token=token),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(main(args), 2)


if __name__ == "__main__":
    unittest.main()
