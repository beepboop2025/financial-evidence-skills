import copy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from financial_evidence.funding_horizon import (
    HISTORY_CLOCK,
    HORIZON_RULE,
    REQUIRED,
    common_horizon_evidence,
)

NOW = datetime(2026, 9, 29, 0, 1, tzinfo=timezone.utc)


def horizon_fixture():
    """Small genuine-wire-shaped fixture; returns desk, US market, full history."""
    values = {
        "policy.sofr": 3.9,
        "policy.effr": 3.88,
        "policy.iorb": 3.9,
        "distribution.sofr.p99": 3.99,
        "distribution.sofr.volume": 2914.0,
        "liquidity.reserves": 3000.0,
        "liquidity.tga": 924.63,
        "liquidity.on_rrp": 0.58,
        "liquidity.srf": 0.0,
    }
    cards = [
        {
            "id": name,
            "unit": unit,
            "value": values[name],
            "asof": "2026-09-25",
            "status": "available",
            "freshness": "aging",
            "cadence": "daily",
        }
        for name, unit in REQUIRED.items()
    ]
    desk = {
        "ok": True,
        "schema": "seiche.money-market-desk.v1",
        "asof": "2026-09-25",
        "snapshot_generated_at": "2026-09-28T23:59:00+00:00",
        "methodology": {"evidence_horizon": HORIZON_RULE},
        "freshness": {"desk_asof": "2026-09-25"},
        "sections": [{"id": "test", "metrics": cards}],
    }
    history = copy.deepcopy(desk)
    history["source_metadata"] = [
        {"id": ident, "available": True, "asof": "2026-09-25"}
        for ident in ("fred_iorb", "fred_on_rrp", "nyfed_srf")
    ]
    history["charts"] = {
        "policy": {
            "id": "policy",
            "columns": ["date", "sofr_pct", "effr_pct", "iorb_pct"],
            "rows": [["2026-09-24", 3.88, 3.88, 3.9], ["2026-09-25", 3.9, 3.88, 3.9]],
            "row_limit": 180,
            "no_forward_fill": True,
        },
        "liquidity": {
            "id": "liquidity",
            "columns": [
                "date",
                "reserves_b",
                "tga_b",
                "on_rrp_b",
                "srf_b",
                "discount_window_b",
            ],
            "rows": [
                ["2026-09-24", None, 947.32, 0.63, 0.0, None],
                ["2026-09-25", None, 924.63, 0.58, 0.0, None],
            ],
            "row_limit": 180,
            "no_forward_fill": True,
        },
    }

    def instrument(ident, unit, source, points):
        return {
            "id": ident,
            "unit": unit,
            "source": source,
            "source_tier": "official_open",
            "availability": "AVAILABLE",
            "redistribution_status": "allowed",
            "history_clock": HISTORY_CLOCK,
            "asof": points[-1][0],
            "value": points[-1][1],
            "history": points,
        }

    market = {
        "market_id": "US-USD",
        "timezone": "America/New_York",
        "settlement_calendar": "US-FEDWIRE",
        "metrics": [
            instrument(
                "US.NYFED.SOFR",
                "%",
                "fred",
                [["2026-09-24", 3.88], ["2026-09-25", 3.9]],
            ),
            instrument(
                "US.FED.IORB",
                "%",
                "fred",
                [["2026-09-24", 3.9], ["2026-09-25", 3.9], ["2026-09-28", 3.9]],
            ),
            instrument(
                "US.NYFED.SRF_TAKEUP",
                "local_currency_millions",
                "nyfed_facilities",
                [["2026-09-24", 1.0], ["2026-09-25", 0.0], ["2026-09-28", 100.0]],
            ),
        ],
    }
    return desk, market, history


class FundingHorizonTests(unittest.TestCase):
    def setUp(self):
        self.desk, self.market, self.history = horizon_fixture()

    def check(self, now=NOW):
        return common_horizon_evidence(self.desk, self.market, self.history, now)

    def card(self, name, doc=None):
        return next(
            row
            for row in (doc or self.desk)["sections"][0]["metrics"]
            if row["id"] == name
        )

    def test_dated_scope_preserves_aging_and_exposes_newer_canonical_observations(self):
        original = copy.deepcopy((self.desk, self.market, self.history))
        proof = self.check()
        self.assertEqual(proof["review_asof"], "2026-09-25")
        self.assertEqual(proof["review_scope"], "common_sofr_iorb_horizon")
        self.assertIs(proof["latest_per_instrument"], False)
        cards = proof["historical_observation_checks"]
        self.assertEqual(cards["policy.iorb"]["publisher_freshness"], "aging")
        self.assertTrue(cards["policy.iorb"]["newer_observation_available"])
        self.assertEqual(cards["liquidity.srf"]["value"], 0)
        self.assertTrue(cards["liquidity.srf"]["newer_observation_available"])
        self.assertIsNone(cards["liquidity.on_rrp"]["canonical_latest_asof"])
        self.assertIsNone(cards["liquidity.on_rrp"]["newer_observation_available"])
        self.assertEqual((self.desk, self.market, self.history), original)

    def test_changed_real_snapshot_rejected(self):
        self.history["snapshot_generated_at"] = "2026-09-28T23:58:00+00:00"
        with self.assertRaises(ValueError):
            self.check()

    def test_equivalent_timestamp_encoding_is_same_snapshot(self):
        self.history["snapshot_generated_at"] = "2026-09-28T23:59:00Z"
        self.check()

    def test_every_required_card_is_joined_between_responses(self):
        for name in REQUIRED:
            with self.subTest(name=name):
                original = self.card(name, self.history)["value"]
                self.card(name, self.history)["value"] = original + 1
                with self.assertRaises(ValueError):
                    self.check()
                self.card(name, self.history)["value"] = original

    def test_new_latest_common_observation_rejects_old_horizon(self):
        row = self.market["metrics"][0]
        row["history"].append(["2026-09-28", 3.91])
        row.update(asof="2026-09-28", value=3.91)
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_own_rrp_point_is_not_filled_from_sofr(self):
        self.history["charts"]["liquidity"]["rows"][-1][3] = None
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_own_srf_point_is_not_treated_as_zero(self):
        self.history["charts"]["liquidity"]["rows"][-1][4] = None
        with self.assertRaises(ValueError):
            self.check()

    def test_own_iorb_value_must_match_canonical_history(self):
        self.market["metrics"][1]["history"][1][1] = 3.8
        with self.assertRaises(ValueError):
            self.check()

    def test_own_srf_value_must_match_canonical_history(self):
        self.market["metrics"][2]["history"][1][1] = 100
        with self.assertRaises(ValueError):
            self.check()

    def test_nonzero_srf_cannot_qualify_a_rounded_zero(self):
        # $1M is 0.001B and would round to the desk's displayed 0.00B.
        for value in (1, 4.9, -1):
            with self.subTest(canonical_millions=value):
                self.market["metrics"][2]["history"][1][1] = value
                with self.assertRaises(ValueError):
                    self.check()
        self.market["metrics"][2]["history"][1][1] = 0
        proof = self.check()
        self.assertEqual(
            proof["historical_observation_checks"]["liquidity.srf"]["value"], 0
        )

    def test_nonzero_srf_preserves_documented_display_precision(self):
        self.market["metrics"][2]["history"][1][1] = 123
        for document in (self.desk, self.history):
            self.card("liquidity.srf", document)["value"] = 0.12
        self.history["charts"]["liquidity"]["rows"][-1][4] = 0.12
        proof = self.check()
        self.assertEqual(
            proof["historical_observation_checks"]["liquidity.srf"]["value"], 0.12
        )

    def test_duplicate_canonical_dates_rejected(self):
        row = self.market["metrics"][0]
        row["history"].insert(0, row["history"][0][:])
        with self.assertRaises(ValueError):
            self.check()

    def test_duplicate_chart_dates_rejected(self):
        rows = self.history["charts"]["liquidity"]["rows"]
        rows.insert(0, rows[0][:])
        with self.assertRaises(ValueError):
            self.check()

    def test_head_must_match_last_history_point(self):
        self.market["metrics"][0]["asof"] = "2026-09-24"
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_or_restricted_history_rejected(self):
        self.market["metrics"][1]["redistribution_status"] = "restricted"
        with self.assertRaises(ValueError):
            self.check()

    def test_nonfinite_boolean_and_text_values_rejected(self):
        for value in (True, float("nan"), float("inf"), "0.58"):
            with self.subTest(value=value):
                self.history["charts"]["liquidity"]["rows"][-1][3] = value
                with self.assertRaises(ValueError):
                    self.check()

    def test_stale_or_older_horizon_card_rejected(self):
        self.card("liquidity.on_rrp")["freshness"] = "stale"
        with self.assertRaises(ValueError):
            self.check()
        self.card("liquidity.on_rrp")["freshness"] = "aging"
        self.card("liquidity.on_rrp")["asof"] = "2026-09-24"
        self.card("liquidity.on_rrp", self.history)["asof"] = "2026-09-24"
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_methodology_or_own_metadata_rejected(self):
        del self.history["methodology"]
        with self.assertRaises(ValueError):
            self.check()
        self.history["methodology"] = {"evidence_horizon": HORIZON_RULE}
        self.history["source_metadata"] = []
        with self.assertRaises(ValueError):
            self.check()

    def test_future_or_excessively_old_horizon_rejected(self):
        for now in (
            datetime(2026, 9, 24, tzinfo=timezone.utc),
            datetime(2026, 10, 4, tzinfo=timezone.utc),
        ):
            with self.subTest(now=now):
                with self.assertRaises(ValueError):
                    self.check(now)

    def test_unbounded_history_or_forward_fill_rejected(self):
        self.history["charts"]["liquidity"]["no_forward_fill"] = False
        with self.assertRaises(ValueError):
            self.check()
        self.history["charts"]["liquidity"]["no_forward_fill"] = True
        self.market["metrics"][0]["history"] *= 100
        with self.assertRaises(ValueError):
            self.check()

    def test_optional_unavailable_card_does_not_invalidate_required_history(self):
        for doc in (self.desk, self.history):
            doc["sections"][0]["metrics"].append(
                {"id": "repo.gcf_volume_share", "status": "unavailable", "value": None}
            )
        self.check()

    def test_malformed_metadata_is_a_bounded_validation_error(self):
        for value in (None, [], "common"):
            with self.subTest(value=value):
                self.history["methodology"] = value
                with self.assertRaises(ValueError):
                    self.check()

    def test_huge_integer_rejected_without_overflow(self):
        self.history["charts"]["liquidity"]["rows"][-1][3] = 10**10000
        with self.assertRaises(ValueError):
            self.check()

    def test_matching_required_rows_cannot_exceed_declared_horizon(self):
        for name in REQUIRED:
            with self.subTest(name=name):
                for doc in (self.desk, self.history):
                    self.card(name, doc)["asof"] = "2026-09-28"
                with self.assertRaises(ValueError):
                    self.check()
                for doc in (self.desk, self.history):
                    self.card(name, doc)["asof"] = "2026-09-25"


if __name__ == "__main__":
    unittest.main()
