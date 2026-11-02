"""Retired releases keep their own reliability window instead of ending now."""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from financial_evidence import reliability

CURRENT = ("workspace-1.3.0+" + "c" * 12, "c" * 40)
OLD = ("workspace-1.1.1+" + "a" * 12, "a" * 40)
MIDDLE = ("workspace-1.2.0+" + "b" * 12, "b" * 40)
START = datetime(2026, 9, 1, 0, 0, 30, tzinfo=timezone.utc)
SLOT = timedelta(seconds=reliability.CADENCE)


def sample(identity, slot, *, perspective="hetzner_same_host", available=True, ready=True, elapsed=0.07):
    observed = START + slot * SLOT
    release, source = identity
    return {
        "schema": reliability.SCHEMA,
        "observed_at": observed.isoformat(),
        "finished_at": (observed + timedelta(seconds=2)).isoformat(),
        "perspective": perspective,
        "trigger": "schedule",
        "run_id": f"{release}-{perspective}-{slot}",
        "expected_release": release,
        "expected_source": source,
        "available": available,
        "release_matches": available,
        "ready": ready,
        "requests": {"health": {"http_status": 200, "error": None, "elapsed_seconds": elapsed}},
    }


def report(samples, evaluated_at):
    with patch.object(reliability, "RELEASE", CURRENT[0]), patch.object(reliability, "SOURCE", CURRENT[1]):
        return reliability.summarize_releases(samples, evaluated_at=evaluated_at.isoformat())


class RetiredReleaseWindowTests(unittest.TestCase):
    def test_release_retired_more_than_thirty_days_ago_keeps_its_rates_and_latency(self):
        # The live report of 2026-11-02 showed null sampled rates and p95 for
        # releases retired before the trailing 30-day window began.
        old = [sample(OLD, slot, ready=slot % 2 == 0) for slot in range(8)]
        current = [sample(CURRENT, slot) for slot in range(10, 12)]
        evaluated_at = START + timedelta(days=45)
        prior = report(old + current, evaluated_at)["prior_releases"][0]
        self.assertEqual((prior["expected_release"], prior["expected_source"]), OLD)
        view = prior["perspectives"]["hetzner_same_host"]
        self.assertEqual(view["window_started_at"], START.isoformat())
        # Accountable until the next release was first observed, at slot 10.
        self.assertEqual(prior["evaluated_at"], (START + 10 * SLOT).isoformat())
        self.assertEqual((view["expected_slots"], view["observed_slots"], view["missing_slots"]), (10, 8, 2))
        self.assertEqual(view["sampled_availability_pct"], 100.0)
        self.assertEqual(view["sampled_readiness_pct"], 50.0)
        self.assertEqual(view["successful_request_p95_seconds"], 0.07)
        self.assertFalse(view["thirty_days_elapsed"])

    def test_each_retired_release_ends_where_its_successor_began(self):
        old = [sample(OLD, slot) for slot in range(4)]
        middle = [sample(MIDDLE, slot, available=False, ready=False) for slot in range(6, 9)]
        current = [sample(CURRENT, slot) for slot in range(9, 11)]
        prior = {
            item["expected_release"]: item
            for item in report(current + middle + old, START + timedelta(days=60))["prior_releases"]
        }
        old_view = prior[OLD[0]]["perspectives"]["hetzner_same_host"]
        middle_view = prior[MIDDLE[0]]["perspectives"]["hetzner_same_host"]
        # The two-slot hand-off gap belongs to the retiring release, not to nobody.
        self.assertEqual((old_view["expected_slots"], old_view["observed_slots"]), (6, 4))
        self.assertEqual((middle_view["expected_slots"], middle_view["observed_slots"]), (3, 3))
        # Failures stay with the release that produced them.
        self.assertEqual(middle_view["sampled_availability_pct"], 0.0)
        self.assertEqual(old_view["sampled_availability_pct"], 100.0)

    def test_overlapping_observers_and_the_evaluation_clock_bound_the_window(self):
        # One observer saw the new release before the other stopped probing the old one.
        old = [sample(OLD, slot) for slot in range(5)] + [sample(OLD, 6, perspective="github_external")]
        current = [sample(CURRENT, slot) for slot in range(4, 8)]
        prior = report(old + current, START + 8 * SLOT)["prior_releases"][0]
        self.assertEqual(prior["evaluated_at"], (START + 6 * SLOT + timedelta(seconds=2)).isoformat())
        self.assertEqual(prior["perspectives"]["github_external"]["observed_slots"], 1)
        # A window never extends past the time the report is evaluated, and a
        # retired release's observation after that time is still rejected.
        early = report(old + current[:3], START + 6 * SLOT + timedelta(seconds=1))["prior_releases"][0]
        self.assertEqual(early["evaluated_at"], (START + 6 * SLOT + timedelta(seconds=1)).isoformat())
        with self.assertRaisesRegex(ValueError, "invalid observation time"):
            report(old + current[:2], START + 5 * SLOT + timedelta(seconds=10))

    def test_current_release_still_counts_its_tail_gap_at_request_time(self):
        current = [sample(CURRENT, slot) for slot in range(3)]
        result = report([sample(OLD, 0)] + current, START + 10 * SLOT)
        view = result["perspectives"]["hetzner_same_host"]
        self.assertEqual(result["evaluated_at"], (START + 10 * SLOT).isoformat())
        self.assertEqual((view["expected_slots"], view["observed_slots"], view["missing_slots"]), (10, 3, 7))


if __name__ == "__main__":
    unittest.main()
