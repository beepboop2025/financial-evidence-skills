"""Withheld references select dates; only actual publisher responses supply values."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_institutional import AT, PID, csv_bytes, fetcher
from test_original_publishers import publisher_fixture
from financial_evidence import institutional as store, original_publishers as source, reliability

RESTRICTED = {"policy.sofr", "policy.effr", "policy.iorb", "liquidity.reserves", "liquidity.on_rrp"}


class DatedPublisherReferenceTests(unittest.TestCase):
    def setUp(self):
        self.reference, self.documents = publisher_fixture()
        for row in self.reference["results"]:
            if row["metric_id"] in RESTRICTED:
                row.update(value=None, value_state="restricted")

    def build(self, reference=None, **kwargs):
        return source.build(
            self.reference if reference is None else reference,
            getter=lambda name, url: self.documents[name],
            **kwargs,
        )

    def test_restricted_mode_is_explicit_and_does_not_modify_reference(self):
        before = copy.deepcopy(self.reference)
        with self.assertRaises(ValueError):
            self.build()
        review, raw, responses = self.build(allow_restricted_reference=True)
        self.assertEqual(self.reference, before)
        self.assertFalse(review["ready"])
        self.assertEqual(review["data_readiness"], "attention_required")
        self.assertEqual(review["method_version"], "original-publisher-dated-reference.v1")
        self.assertEqual(len(responses), 7)
        self.assertEqual(review["results"][0]["value"], 3.9)
        self.assertEqual(review["results"][5]["value"], 2930.193)
        self.assertEqual(review["results"][7]["value"], 0.576)
        self.assertIn(b"0.576", raw)
        for row in review["results"]:
            self.assertEqual(row["value_state"], "available")
            self.assertEqual(row["review_status"], "attention_required")
            self.assertTrue(review["publisher_lineage"][row["metric_id"]]["original_publisher_acquisition"])
            status = review["reference_value_comparisons"][row["metric_id"]]["status"]
            self.assertEqual(status, "not_performed" if row["metric_id"] in RESTRICTED else "matched_within_display_precision")
        store.verify_pair(review, raw)

    def test_all_available_explicit_mode_is_identical_to_existing_behavior(self):
        reference, _ = publisher_fixture()
        with patch.object(source, "now", return_value=AT):
            default = self.build(reference)
            explicit = self.build(reference, allow_restricted_reference=True)
        self.assertEqual(default, explicit)
        self.assertEqual(default[0]["method_version"], "original-publisher-crosscheck.v1.1")
        self.assertTrue(default[0]["ready"])

    def test_missing_duplicate_unavailable_or_nonnull_restricted_rows_fail(self):
        for case in ("nonnull", "unavailable", "duplicate", "missing", "false_mode"):
            reference = copy.deepcopy(self.reference)
            kwargs = {"allow_restricted_reference": True}
            if case == "nonnull": reference["results"][0]["value"] = 3.9
            elif case == "unavailable": reference["results"][0]["value_state"] = "unavailable"
            elif case == "duplicate": reference["results"][1] = copy.deepcopy(reference["results"][0])
            elif case == "missing": reference["results"].pop()
            else: kwargs["allow_restricted_reference"] = "true"
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.build(reference, **kwargs)

    def test_target_dates_units_sources_and_capture_clock_are_validated(self):
        for key, value in (("observation_date", "2026-09-30"), ("observation_date", "20260925"),
                           ("observation_date", "bad"), ("unit", "$B"), ("source", None)):
            reference = copy.deepcopy(self.reference)
            reference["results"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.build(reference, allow_restricted_reference=True)
        self.reference["captured_at"] = "2026-09-29T11:59:30"
        with self.assertRaises(ValueError):
            self.build(allow_restricted_reference=True)

    def test_available_values_still_require_exact_publisher_crosscheck(self):
        self.reference["results"][3]["value"] = 3.0
        with self.assertRaisesRegex(ValueError, "disagrees"):
            self.build(allow_restricted_reference=True)

    def test_withheld_targets_never_bypass_missing_dates_or_ambiguous_sources(self):
        for case in ("missing_date", "duplicate", "partial_operation", "missing_response"):
            reference, documents = copy.deepcopy(self.reference), copy.deepcopy(self.documents)
            if case == "missing_date": reference["results"][0]["observation_date"] = "2026-09-24"
            elif case == "duplicate":
                body = source.strict_json(documents["sofr"])
                body["refRates"].append(copy.deepcopy(body["refRates"][0]))
                documents["sofr"] = reliability.encoded(body)
            elif case == "partial_operation":
                body = source.strict_json(documents["srf"])
                body["repo"]["operations"].pop()
                documents["srf"] = reliability.encoded(body)
            else: documents.pop("iorb")
            with self.subTest(case=case), self.assertRaises((ValueError, KeyError)):
                source.build(reference, getter=lambda name, url: documents[name], allow_restricted_reference=True)

    def test_archive_dispatches_only_after_csv_binding_and_never_claims_ready(self):
        calls = []
        def builder(reference, **kwargs):
            calls.append(kwargs)
            return self.build(reference, **kwargs)
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "now", return_value=AT), patch.object(reliability, "now", return_value=AT):
            root = Path(directory)
            attempt = store.archive_once(root, fetcher=fetcher(review=self.reference, csv_raw=csv_bytes(self.reference["results"])), builder=builder)
            self.assertIsNone(attempt["error"])
            self.assertEqual(calls, [{"allow_restricted_reference": True}])
            self.assertFalse(attempt["probe"]["ready"])
            self.assertEqual(set(attempt["reference_comparison"]["not_performed"]), RESTRICTED)
            manifest, raw, _ = store.public_packet(root, PID)
            self.assertFalse(manifest["ready_at_capture"])
            self.assertFalse(reliability.strict_json(raw)["ready"])
            self.assertFalse(store.public_latest(root)["ready"])
        calls.clear()
        bad_csv = csv_bytes(self.reference["results"]).replace(b"3.99", b"9.99")
        with tempfile.TemporaryDirectory() as directory, patch.object(reliability, "now", return_value=AT):
            attempt = store.archive_once(directory, fetcher=fetcher(review=self.reference, csv_raw=bad_csv), builder=builder)
            self.assertIn("CSV and review disagree", attempt["error"])
            self.assertEqual(calls, [])

    def test_builder_readiness_cannot_be_inferred_from_ready_reference(self):
        reference, _ = publisher_fixture()
        def builder(value):
            review, raw, blobs = self.build(value)
            review["ready"] = False
            return review, raw, blobs
        with tempfile.TemporaryDirectory() as directory, patch.object(reliability, "now", return_value=AT):
            attempt = store.archive_once(directory, fetcher=fetcher(review=reference, csv_raw=csv_bytes(reference["results"])), builder=builder)
            self.assertIsNone(attempt["error"])
            self.assertTrue(attempt["probe"]["workspace_ready"])
            self.assertFalse(attempt["probe"]["ready"])


if __name__ == "__main__":
    unittest.main()
