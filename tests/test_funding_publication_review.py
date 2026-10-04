"""Publication deadlines must explain, never conceal, aging observations."""

import copy
import unittest

from scripts.check_funding_review import (
    ATLAS_CLOCK_BASIS,
    ATLAS_DECLARED_CLOCK_BASIS,
    evaluate,
)
from test_funding_review import captures


def overnight(asof="2026-09-25", now="2026-09-29T00:01:00Z", due="2026-09-29"):
    docs = captures()
    for key, doc in zip(
        ("snapshot_generated_at", "generated_at", "generated_at"), docs
    ):
        doc[key] = now
    rows = {row["id"]: row for row in docs[0]["sections"][0]["metrics"]}
    cases = [
        ("policy.sofr", "US.NYFED.SOFR", 3.9, "%", 3.9, "fred", 12),
        ("policy.effr", "US.NYFED.EFFR", 3.88, "%", 3.88, "fred", 13),
        (
            "distribution.sofr.p99",
            "US.NYFED.SOFR_P99",
            3.96,
            "%",
            3.96,
            "nyfed_rates",
            12,
        ),
        (
            "distribution.sofr.volume",
            "US.NYFED.SOFR_VOLUME",
            2990,
            "local_currency_millions",
            2990000,
            "nyfed_rates",
            12,
        ),
    ]
    market = docs[1]["markets"][0]
    market.update(
        timezone="America/New_York", settlement_calendar="US-FEDWIRE", metrics=[]
    )
    for name, instrument, value, unit, atlas_value, source, hour in cases:
        rows[name].update(value=value, asof=asof, freshness="aging")
        market["metrics"].append(
            {
                "id": instrument,
                "value": atlas_value,
                "unit": unit,
                "asof": asof,
                "event_time": asof + "T00:00:00Z",
                "expected_next_update": f"{due}T{hour}:00:00Z",
                "availability": "AVAILABLE",
                "status": "FRESH",
                "cadence": "P1D",
                "source": source,
                "source_tier": "official_open",
                "redistribution_status": "allowed",
                "freshness_basis": ATLAS_CLOCK_BASIS,
                "missed_publication_opportunities": 0,
            }
        )
    rows["distribution.sofr.rate"].update(value=3.9, asof=asof)
    market["benchmark"].update(value=3.9, asof=asof)
    docs[2]["provenance"][0]["asof"] = asof
    for name in ("policy.iorb", "liquidity.on_rrp", "liquidity.srf", "liquidity.tga"):
        rows[name]["asof"] = now[:10]
    rows["liquidity.reserves"]["asof"] = asof
    return docs


class PublicationReviewTests(unittest.TestCase):
    def test_declared_schedule_description_preserves_observations_and_deadlines(self):
        now = "2026-10-04T06:00:00Z"
        docs = overnight("2026-10-01", now, "2026-10-05")
        for row in docs[1]["markets"][0]["metrics"]:
            row["freshness_basis"] = ATLAS_DECLARED_CLOCK_BASIS
        before = copy.deepcopy(docs)
        result = evaluate(*docs, evaluated_at=now)
        self.assertEqual(result["issues"], [])
        self.assertEqual(docs, before)
        for clock, count in (("12:00:00", 3), ("13:00:00", 4)):
            expired = evaluate(*docs, evaluated_at=f"2026-10-05T{clock}Z")
            self.assertEqual(
                sum(x["code"] == "nyfed_publication_clock_not_usable"
                    for x in expired["issues"]),
                count,
            )

    def test_new_description_does_not_admit_inferred_or_inconsistent_clocks(self):
        inferred = (
            "pack business calendar + adapter publication lag/cadence; "
            "native publication clock inferred from retained row; "
            "schedule is estimated, not a publication receipt; "
            "stored state is a lower bound"
        )
        for field, value in (
            ("freshness_basis", inferred),
            ("freshness_basis", ATLAS_DECLARED_CLOCK_BASIS + "; unreviewed"),
            ("freshness_basis", None),
            ("freshness_basis", [ATLAS_DECLARED_CLOCK_BASIS]),
            ("value", 3.91),
            ("redistribution_status", "prohibited"),
            ("expected_next_update", "2026-09-30T12:00:00Z"),
            ("missed_publication_opportunities", 1),
        ):
            with self.subTest(field=field, value=value):
                docs = overnight()
                rows = docs[1]["markets"][0]["metrics"]
                for row in rows:
                    row["freshness_basis"] = ATLAS_DECLARED_CLOCK_BASIS
                rows[0][field] = value
                result = evaluate(*docs, evaluated_at="2026-09-29T00:01:00Z")
                self.assertIn(
                    {"code": "nyfed_publication_clock_not_usable", "subject": "policy.sofr"},
                    result["issues"],
                )

    def test_midnight_accepts_matching_four_instruments_without_rewriting_labels(self):
        docs = overnight()
        before = copy.deepcopy(docs)
        result = evaluate(*docs, evaluated_at="2026-09-29T00:01:00Z")
        self.assertEqual(result["issues"], [])
        self.assertEqual(docs, before)
        for name in (
            "policy.sofr",
            "policy.effr",
            "distribution.sofr.p99",
            "distribution.sofr.volume",
        ):
            self.assertEqual(
                result["freshness_assessments"][name]["publisher_freshness"], "aging"
            )
            self.assertEqual(
                result["freshness_assessments"][name]["basis"],
                "matched_nyfed_publication_clock",
            )

    def test_holiday_five_day_age_requires_matching_publication_evidence(self):
        now = "2026-09-09T00:01:00Z"
        docs = overnight("2026-09-04", now, "2026-09-09")
        result = evaluate(*docs, evaluated_at=now)
        self.assertEqual(result["issues"], [])
        del docs[1]["markets"][0]["metrics"]
        result = evaluate(*docs, evaluated_at=now)
        self.assertIn(
            "observation_exceeds_age_backstop", {x["code"] for x in result["issues"]}
        )

    def test_exact_due_time_expires_sofr_before_effr(self):
        for clock, expected in (
            (
                "12:00:00",
                {"policy.sofr", "distribution.sofr.p99", "distribution.sofr.volume"},
            ),
            (
                "13:00:00",
                {
                    "policy.sofr",
                    "distribution.sofr.p99",
                    "distribution.sofr.volume",
                    "policy.effr",
                },
            ),
        ):
            now = "2026-09-29T" + clock + "Z"
            with self.subTest(now=now):
                result = evaluate(*overnight(now=now), evaluated_at=now)
                self.assertEqual(
                    {
                        x["subject"]
                        for x in result["issues"]
                        if x["code"] == "nyfed_publication_clock_not_usable"
                    },
                    expected,
                )

    def test_bad_atlas_claims_cannot_override_aging_or_fresh_labels(self):
        mutations = [
            ("asof", "2026-09-24"),
            ("event_time", "2026-09-25T04:00:00Z"),
            ("value", 3.91),
            ("unit", "bp"),
            ("cadence", "PT1H"),
            ("source", "unknown"),
            ("source_tier", "estimated"),
            ("redistribution_status", "derived_only"),
            ("availability", "MISSING"),
            ("status", "AGING"),
            ("freshness_basis", "inferred"),
            ("missed_publication_opportunities", 1),
            ("missed_publication_opportunities", True),
            ("expected_next_update", "2026-09-30T12:00:00Z"),
            ("expected_next_update", "2026-09-29T08:00:00"),
        ]
        for field, value in mutations:
            for label in ("fresh", "aging"):
                with self.subTest(field=field, label=label):
                    docs = overnight()
                    docs[1]["markets"][0]["metrics"][0][field] = value
                    docs[0]["sections"][0]["metrics"][0]["freshness"] = label
                    result = evaluate(*docs, evaluated_at="2026-09-29T00:01:00Z")
                    self.assertIn(
                        {
                            "code": "nyfed_publication_clock_not_usable",
                            "subject": "policy.sofr",
                        },
                        result["issues"],
                    )

    def test_own_distribution_observations_must_match_not_only_benchmark(self):
        for index, field, value in (
            (2, "asof", "2026-09-24"),
            (2, "value", 3.97),
            (3, "value", 2990),
        ):
            docs = overnight()
            docs[1]["markets"][0]["metrics"][index][field] = value
            result = evaluate(*docs, evaluated_at="2026-09-29T00:01:00Z")
            self.assertEqual(result["status"], "attention_required")

    def test_duplicate_or_restricted_instruments_and_market_fail(self):
        for mutation in ("duplicate", "missing", "restricted", "timezone", "calendar"):
            docs = overnight()
            market = docs[1]["markets"][0]
            if mutation == "duplicate":
                market["metrics"].append(copy.deepcopy(market["metrics"][0]))
            elif mutation == "missing":
                market["metrics"].pop(0)
            elif mutation == "restricted":
                market["redistribution_status"] = "prohibited"
            elif mutation == "timezone":
                market["timezone"] = "UTC"
            else:
                market["settlement_calendar"] = "weekdays"
            result = evaluate(*docs, evaluated_at="2026-09-29T00:01:00Z")
            self.assertEqual(result["status"], "attention_required", mutation)

    def test_unknown_or_stale_labels_and_other_instruments_remain_exceptions(self):
        for name in ("policy.sofr", "policy.iorb", "liquidity.on_rrp", "liquidity.srf"):
            for label in (
                ("stale", "unknown", None) if name == "policy.sofr" else ("aging",)
            ):
                docs = overnight()
                row = next(
                    x for x in docs[0]["sections"][0]["metrics"] if x["id"] == name
                )
                row["freshness"] = label
                result = evaluate(*docs, evaluated_at="2026-09-29T00:01:00Z")
                self.assertIn(
                    {"code": "required_metric_not_reported_fresh", "subject": name},
                    result["issues"],
                )

    def test_future_deadline_with_zero_misses_cannot_hide_an_older_observation(self):
        docs = overnight("2026-09-24")
        result = evaluate(*docs, evaluated_at="2026-09-29T00:01:00Z")
        self.assertEqual(result["status"], "attention_required")
        self.assertIn(
            "nyfed_publication_clock_not_usable", {x["code"] for x in result["issues"]}
        )


if __name__ == "__main__":
    unittest.main()
