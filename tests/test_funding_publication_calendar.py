"""Independent boundary examples from the reviewed NY Fed 2026 notices."""

from datetime import date, datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from financial_evidence.funding_publication_calendar import (
    next_publication_after_observation,
)


class FundingPublicationCalendarTests(unittest.TestCase):
    def assert_due(self, observation, mnemonic, expected):
        actual = next_publication_after_observation(
            date.fromisoformat(observation), mnemonic
        )
        self.assertEqual(actual, datetime.fromisoformat(expected))
        self.assertIs(actual.tzinfo, timezone.utc)

    def test_next_new_observation_is_two_business_days_after_existing_print(self):
        for mnemonic, hour in (("SOFR", 12), ("EFFR", 13)):
            with self.subTest(mnemonic=mnemonic):
                self.assert_due(
                    "2026-09-25", mnemonic, f"2026-09-29T{hour}:00:00+00:00"
                )

    def test_utc_midnight_does_not_advance_the_new_york_release(self):
        for mnemonic, hour in (("SOFR", 12), ("EFFR", 13)):
            with self.subTest(mnemonic=mnemonic):
                due = next_publication_after_observation(date(2026, 9, 25), mnemonic)
                midnight = datetime(2026, 9, 29, tzinfo=timezone.utc)
                self.assertEqual((due - midnight).total_seconds(), hour * 3600)

    def test_spring_dst_changes_utc_hour_without_moving_local_release(self):
        for mnemonic, before, after in (("SOFR", 13, 12), ("EFFR", 14, 13)):
            with self.subTest(mnemonic=mnemonic):
                self.assert_due(
                    "2026-03-04", mnemonic, f"2026-03-06T{before}:00:00+00:00"
                )
                self.assert_due(
                    "2026-03-05", mnemonic, f"2026-03-09T{after}:00:00+00:00"
                )

    def test_autumn_dst_changes_utc_hour_without_moving_local_release(self):
        for mnemonic, before, after in (("SOFR", 12, 13), ("EFFR", 13, 14)):
            with self.subTest(mnemonic=mnemonic):
                self.assert_due(
                    "2026-10-28", mnemonic, f"2026-10-30T{before}:00:00+00:00"
                )
                self.assert_due(
                    "2026-10-29", mnemonic, f"2026-11-02T{after}:00:00+00:00"
                )

    def test_labor_day_skips_both_observation_and_publication_holiday(self):
        for mnemonic, hour in (("SOFR", 12), ("EFFR", 13)):
            with self.subTest(mnemonic=mnemonic):
                self.assert_due(
                    "2026-09-03", mnemonic, f"2026-09-08T{hour}:00:00+00:00"
                )
                self.assert_due(
                    "2026-09-04", mnemonic, f"2026-09-09T{hour}:00:00+00:00"
                )

    def test_good_friday_has_different_secured_and_unsecured_clocks(self):
        self.assert_due("2026-04-01", "SOFR", "2026-04-06T12:00:00+00:00")
        self.assert_due("2026-04-01", "EFFR", "2026-04-03T13:00:00+00:00")
        self.assert_due("2026-04-02", "SOFR", "2026-04-07T12:00:00+00:00")
        self.assert_due("2026-04-02", "EFFR", "2026-04-06T13:00:00+00:00")
        self.assert_due("2026-04-03", "EFFR", "2026-04-07T13:00:00+00:00")
        with self.assertRaises(ValueError):
            next_publication_after_observation(date(2026, 4, 3), "SOFR")

    def test_july_three_is_open_for_effr_but_explicitly_closed_for_sofr(self):
        self.assert_due("2026-07-01", "EFFR", "2026-07-03T13:00:00+00:00")
        self.assert_due("2026-07-01", "SOFR", "2026-07-06T12:00:00+00:00")
        self.assert_due("2026-07-02", "EFFR", "2026-07-06T13:00:00+00:00")
        self.assert_due("2026-07-02", "SOFR", "2026-07-07T12:00:00+00:00")
        self.assert_due("2026-07-03", "EFFR", "2026-07-07T13:00:00+00:00")
        with self.assertRaises(ValueError):
            next_publication_after_observation(date(2026, 7, 3), "SOFR")

    def test_early_close_does_not_suppress_the_next_publication(self):
        self.assert_due("2026-11-24", "SOFR", "2026-11-27T13:00:00+00:00")
        self.assert_due("2026-12-22", "SOFR", "2026-12-24T13:00:00+00:00")

    def test_all_official_2026_holidays_and_weekends_reject_observation_dates(self):
        for day in (
            "2026-01-01",
            "2026-01-19",
            "2026-02-16",
            "2026-05-25",
            "2026-06-19",
            "2026-07-04",
            "2026-09-07",
            "2026-10-12",
            "2026-11-11",
            "2026-11-26",
            "2026-12-25",
            "2026-09-26",
            "2026-09-27",
        ):
            for mnemonic in ("SOFR", "EFFR"):
                with (
                    self.subTest(day=day, mnemonic=mnemonic),
                    self.assertRaises(ValueError),
                ):
                    next_publication_after_observation(
                        date.fromisoformat(day), mnemonic
                    )

    def test_year_end_has_only_the_explicit_january_bridge(self):
        for mnemonic, hour in (("SOFR", 13), ("EFFR", 14)):
            with self.subTest(mnemonic=mnemonic):
                self.assert_due(
                    "2026-12-30", mnemonic, f"2027-01-04T{hour}:00:00+00:00"
                )
                self.assert_due(
                    "2026-12-31", mnemonic, f"2027-01-05T{hour}:00:00+00:00"
                )
                self.assert_due(
                    "2026-01-02", mnemonic, f"2026-01-06T{hour}:00:00+00:00"
                )

    def test_unreviewed_years_and_non_dates_fail_closed(self):
        for value in (
            date(2025, 12, 31),
            date(2027, 1, 4),
            date(2027, 1, 5),
            date(2027, 9, 1),
            date(2099, 1, 1),
            "2026-09-25",
            None,
            True,
            datetime(2026, 9, 25, tzinfo=timezone.utc),
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                next_publication_after_observation(value, "SOFR")

    def test_other_metrics_do_not_inherit_a_nyfed_rate_deadline(self):
        for mnemonic in ("IORB", "SOFR_P99", "sofr", "EFFR ", None, ["SOFR"]):
            with self.subTest(mnemonic=mnemonic), self.assertRaises(ValueError):
                next_publication_after_observation(date(2026, 9, 25), mnemonic)


if __name__ == "__main__":
    unittest.main()
