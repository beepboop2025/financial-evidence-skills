"""A ready dated review must retain both old values and newer-source warnings."""

import copy
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_funding_review import evaluate
from financial_evidence.funding_archive import read_review, load_csv
from test_capture_funding_review import capture, fetcher, responses
from test_funding_horizon import horizon_fixture
from test_funding_publication_review import overnight

NOW = "2026-09-29T00:01:00Z"


def full_review():
    desk, market, history = horizon_fixture()
    _, clock_atlas, health = overnight()
    cards = {x["id"]: x for x in desk["sections"][0]["metrics"]}
    for name, row in cards.items():
        row["source"] = "Synthetic official-source fixture"
        if name == "liquidity.reserves":
            row.update(cadence="weekly", asof="2026-09-23", freshness="fresh")
        elif name == "liquidity.tga":
            row["freshness"] = "fresh"
    desk["selection"] = "all"
    desk["sections"][0]["metrics"].append(
        {**cards["policy.sofr"], "id": "distribution.sofr.rate"}
    )
    history["sections"] = copy.deepcopy(desk["sections"])
    history["selection"] = "all"
    own = {x["id"]: x for x in market["metrics"]}
    for row in clock_atlas["markets"][0]["metrics"]:
        row = copy.deepcopy(row)
        if row["id"] == "US.NYFED.SOFR_P99":
            row["value"] = 3.99
        if row["id"] == "US.NYFED.SOFR_VOLUME":
            row["value"] = 2914000
        if row["id"] in own:
            own[row["id"]].update(row)
        else:
            market["metrics"].append(row)
    market["benchmark"] = copy.deepcopy(clock_atlas["markets"][0]["benchmark"])
    atlas = {**clock_atlas, "markets": [market]}
    health["provenance"].extend(
        [
            {
                "mnemonic": "IORB",
                "source": "fred",
                "unit": "%",
                "freq": "D",
                "asof": "2026-09-28",
            },
            {
                "mnemonic": "RRPONTSYD",
                "source": "fred",
                "unit": "$B",
                "freq": "D",
                "asof": "2026-09-28",
            },
        ]
    )
    return desk, atlas, health, history


class HorizonReviewTests(unittest.TestCase):
    def test_small_srf_survives_capture_reader_csv_and_replay(self):
        desk, atlas, health, history = full_review()
        for document in (desk, history):
            for card in document["sections"][0]["metrics"]:
                if card["id"] == "liquidity.srf":
                    card["value"] = 0.001
        srf = next(
            row for row in atlas["markets"][0]["metrics"]
            if row["id"] == "US.NYFED.SRF_TAKEUP"
        )
        srf["history"][1][1] = 1
        bodies = responses((desk, atlas, health))
        bodies["desk-history"] = json.dumps(history).encode()
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(capture, "utcnow", return_value=NOW),
            patch.dict(os.environ, {"FINANCIAL_EVIDENCE_SOURCE_COMMIT": ""}),
        ):
            path, manifest = capture.capture(Path(folder), fetcher=fetcher(bodies))
            self.assertTrue(manifest["ready"])
            self.assertTrue(read_review(folder, now=NOW)["ready"])
            rows = list(csv.DictReader(io.StringIO(load_csv(folder, now=NOW).decode())))
            row = next(row for row in rows if row["metric_id"] == "liquidity.srf")
            self.assertEqual(row["value"], "0.001")
            replay_path, replay_manifest = capture.replay(path, Path(folder))
            self.assertTrue(replay_manifest["ready"])
            self.assertEqual(
                (replay_path / "funding-observations.csv").read_bytes(),
                (path / "funding-observations.csv").read_bytes(),
            )

    def test_aging_common_horizon_passes_without_calling_old_values_current(self):
        desk, atlas, health, history = full_review()
        result = evaluate(desk, atlas, health, desk_history=history, evaluated_at=NOW)
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["review_asof"], "2026-09-25")
        self.assertEqual(result["review_scope"], "common_sofr_iorb_horizon")
        self.assertIs(result["latest_per_instrument"], False)
        for name in ("policy.iorb", "liquidity.on_rrp", "liquidity.srf"):
            assessment = result["freshness_assessments"][name]
            self.assertEqual(assessment["publisher_freshness"], "aging")
            self.assertEqual(assessment["canonical_latest_asof"], "2026-09-28")
            self.assertIs(assessment["newer_observation_available"], True)
        # Monday's SRF history is $0.1B; Friday's genuine zero stays zero.
        srf = next(
            x for x in desk["sections"][0]["metrics"] if x["id"] == "liquidity.srf"
        )
        self.assertEqual(srf["value"], 0)

    def test_missing_or_ambiguous_own_history_does_not_pass(self):
        for corruption in ("absent", "missing_rrp", "changed_snapshot"):
            desk, atlas, health, history = full_review()
            if corruption == "absent":
                history = None
            elif corruption == "missing_rrp":
                history["charts"]["liquidity"]["rows"][-1][3] = None
            else:
                history["snapshot_generated_at"] = "2026-09-28T23:58:00Z"
            result = evaluate(
                desk, atlas, health, desk_history=history, evaluated_at=NOW
            )
            self.assertIn(
                {
                    "code": "common_horizon_not_verified",
                    "subject": "desk.evidence_horizon",
                },
                result["issues"],
            )
            self.assertEqual(result["status"], "attention_required")

    def test_common_horizon_cannot_excuse_a_missed_reference_release(self):
        desk, atlas, health, history = full_review()
        now = "2026-09-29T12:00:00Z"
        desk["snapshot_generated_at"] = history["snapshot_generated_at"] = now
        atlas["generated_at"] = health["generated_at"] = now
        result = evaluate(desk, atlas, health, desk_history=history, evaluated_at=now)
        self.assertIn(
            {"code": "common_horizon_not_verified", "subject": "desk.evidence_horizon"},
            result["issues"],
        )
        self.assertIn(
            {
                "code": "required_metric_not_reported_fresh",
                "subject": "liquidity.on_rrp",
            },
            result["issues"],
        )

    def test_capture_reader_and_saved_csv_keep_scope_and_newer_dates(self):
        desk, atlas, health, history = full_review()
        bodies = responses((desk, atlas, health))
        bodies["desk-history"] = json.dumps(history).encode()
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(capture, "utcnow", return_value=NOW),
            patch.dict(os.environ, {"FINANCIAL_EVIDENCE_SOURCE_COMMIT": ""}),
        ):
            path, manifest = capture.capture(Path(folder), fetcher=fetcher(bodies))
            self.assertTrue(manifest["ready"])
            review = read_review(folder, now=NOW)
            self.assertTrue(review["ready"])
            self.assertEqual(review["review_asof"], "2026-09-25")
            self.assertIs(review["latest_per_instrument"], False)
            rows = list(csv.DictReader(io.StringIO(load_csv(folder, now=NOW).decode())))
            self.assertEqual(len(rows), 9)
            self.assertEqual(
                {r["review_scope"] for r in rows}, {"common_sofr_iorb_horizon"}
            )
            self.assertEqual({r["latest_per_instrument"] for r in rows}, {"false"})
            rrp = next(r for r in rows if r["metric_id"] == "liquidity.on_rrp")
            self.assertEqual(rrp["observation_date"], "2026-09-25")
            self.assertEqual(rrp["canonical_latest_asof"], "2026-09-28")
            self.assertEqual(rrp["newer_observation_available"], "true")
            replay_path, _ = capture.replay(path, Path(folder))
            self.assertEqual(
                (replay_path / "funding-observations.csv").read_bytes(),
                (path / "funding-observations.csv").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
