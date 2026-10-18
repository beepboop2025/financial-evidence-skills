"""Private pilot evidence cannot be inflated into office customer counts."""
import csv
from datetime import date
import importlib.util
import io
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "office_adoption", Path(__file__).parents[1] / "scripts" / "office_adoption.py")
office = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(office)


def event(task="review-1", day="2026-08-01", **overrides):
    row = dict(zip(office.FIELDS, (
        "pilot-01", "analyst", "libreoffice", "funding", task,
        day + "T10:00:00Z", "true", "true", "false", "true", "true",
        "a" * 64, "b" * 64, "c" * 64, "20", "8",
    )))
    return {**row, **overrides}


def encoded(*rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=office.FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def score(*rows, through="2026-09-15", window_days=90):
    return office.score(encoded(*rows), through=date.fromisoformat(through), window_days=window_days)


class OfficeAdoptionTests(unittest.TestCase):
    def test_empty_pilot_is_not_zero_product_users(self):
        report = score()
        self.assertEqual(report["source_records"], 0)
        self.assertEqual(report["participants"]["analyst"]["distinct_useful_tasks"], 0)
        self.assertIsNone(report["all_product_active_people"])
        self.assertIsNone(report["paying_customers"])
        self.assertFalse(report["coverage_complete"])

    def test_retries_and_multiple_same_day_tasks_cannot_create_return(self):
        report = score(event(), event(), event("review-2"))
        self.assertEqual(report["duplicate_retries_ignored"], 1)
        rows = report["participants"]["analyst"]
        self.assertEqual(rows["distinct_useful_tasks"], 2)
        self.assertEqual(rows["reviewed_external_participants_with_useful_returns"], 0)
        with self.assertRaisesRegex(ValueError, "conflicting retry"):
            score(event(), event(day="2026-08-02"))

    def test_operator_unverified_incomplete_and_missing_evidence_are_excluded(self):
        records = [event("synthetic", operator_test="true"),
                   event("unknown", external_participant_confirmed="false"),
                   event("failed", reviewer_task_completed="false"),
                   event("rights", source_scope_accepted="false"),
                   event("no-ref", evidence_sha256="")]
        report = score(*records)
        self.assertEqual(sum(report["exclusions"].values()), 5)
        self.assertEqual(report["participants"]["analyst"]["distinct_useful_tasks"], 0)

    def test_withdrawal_suppresses_all_prior_tasks_for_alias(self):
        report = score(event(), event("review-2", "2026-08-08"),
                       event("withdrawn", "2026-08-09", consent_recorded="false"))
        self.assertEqual(report["exclusions"], {"nonconsenting_or_withdrawn": 3})
        self.assertEqual(report["participants"]["analyst"]["distinct_useful_tasks"], 0)

    def test_exact_day_return_requires_completed_date_and_eligible_denominator(self):
        records = [event(), event("review-2", "2026-08-08")]
        before = score(*records, through="2026-08-07")["participants"]["analyst"]
        self.assertEqual(before["exact_day_retention"]["d7_exact_day"],
                         {"eligible": 0, "returned": 0, "rate": None})
        after = score(*records, through="2026-08-08")["participants"]["analyst"]
        self.assertEqual(after["exact_day_retention"]["d7_exact_day"],
                         {"eligible": 1, "returned": 1, "rate": 1})
        self.assertIsNone(after["exact_day_retention"]["d30_exact_day"]["rate"])

    def test_other_day_return_does_not_count_as_exact_d7(self):
        rows = score(event(), event("review-2", "2026-08-09"))["participants"]["analyst"]
        self.assertEqual(rows["reviewed_external_participants_with_useful_returns"], 1)
        self.assertEqual(rows["exact_day_retention"]["d7_exact_day"]["returned"], 0)

    def test_earlier_history_and_unverified_events_do_not_restart_cohort(self):
        report = score(event(), event("review-2", "2026-09-01"),
                       event("review-3", "2026-09-08"), through="2026-09-15", window_days=30)
        self.assertEqual(report["eligible_records_outside_window"], 1)
        self.assertEqual(report["participants"]["analyst"]["exact_day_retention"]["d7_exact_day"]["eligible"], 0)
        records = [event("not-independent", external_participant_confirmed="false"),
                   event("review-2", "2026-09-01"), event("review-3", "2026-09-08")]
        self.assertEqual(score(*records)["participants"]["analyst"]["exact_day_retention"]["d7_exact_day"]["returned"], 1)

    def test_organizations_separate_and_breakdowns_overlap(self):
        report = score(event(), event("review-2", "2026-08-08", client="excel"),
                       event(participant_alias="org-01", participant_type="organization"))
        self.assertEqual(report["participants"]["analyst"]["reviewed_external_participants_with_useful_tasks"], 1)
        self.assertEqual(report["participants"]["organization"]["reviewed_external_participants_with_useful_tasks"], 1)
        self.assertEqual(report["by_client"]["excel"]["analyst"]["reviewed_external_participants_with_useful_returns"], 0)
        self.assertNotIn("pilot-01", json.dumps(report))
        self.assertNotIn("review-2", json.dumps(report))
        with self.assertRaisesRegex(ValueError, "conflicting participant types"):
            score(event(), event("another", participant_type="organization"))

    def test_missing_zero_and_negative_time_savings_remain_distinct(self):
        self.assertIsNone(score(event(review_minutes=""))["participants"]["analyst"]["operator_reported_net_minutes_saved"])
        report = score(event(manual_baseline_minutes="0", review_minutes="3"))
        self.assertEqual(report["participants"]["analyst"]["operator_reported_net_minutes_saved"], -3)
        for value in ("NaN", "inf", "-1", "10081"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                score(event(review_minutes=value))

    def test_rejects_unbounded_private_fields_and_malformed_flags_dates(self):
        for overrides in ({"participant_alias": "alice@example.com"},
                          {"task_reference": "https://private.example/task"},
                          {"consent_recorded": "yes"},
                          {"consent_sha256": "secret-key"},
                          {"occurred_at_utc": "2026-08-01T10:00:00+05:30"},
                          {"client": "unknown-client"}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                score(event(**overrides))

    def test_partial_current_day_and_oversize_csv_rejected(self):
        with self.assertRaisesRegex(ValueError, "completed UTC date"):
            office.score(encoded(), through=date(2999, 1, 1))
        with self.assertRaisesRegex(ValueError, "8 MiB"):
            office.read_records(b"x" * (office.MAX_BYTES + 1))

    def test_real_empty_template_matches_contract(self):
        template = Path(__file__).parents[1] / "docs" / "office-adoption" / "pilot-template.csv"
        records, duplicates = office.read_records(template.read_bytes())
        self.assertEqual((records, duplicates), ([], 0))


if __name__ == "__main__":
    unittest.main()
