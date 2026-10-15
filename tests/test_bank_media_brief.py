"""Guard the dated issuer comparison against misleading data transformations."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bank_media", ROOT / "scripts/build_bank_media_brief.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BankMediaBriefTests(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads((builder.DEFAULT / "source-facts.json").read_text())

    def test_distinct_ratios_balances_periods_and_missingness(self):
        rows = builder.validate(self.facts)
        self.assertEqual(rows[("gnpa_pct", "2026-06-30")]["value"], 5.4)
        self.assertEqual(rows[("nnpa_pct", "2026-06-30")]["value"] - rows[("nnpa_pct", "2026-03-31")]["value"], -1)
        self.assertAlmostEqual(rows[("gnpa_amount", "2026-06-30")]["value"] - rows[("gnpa_amount", "2026-03-31")]["value"], 39.4)
        self.assertNotEqual(rows[("gnpa_pct", "2026-06-30")]["basis"], rows[("nnpa_pct", "2026-06-30")]["basis"])
        self.assertIsNone(rows[("cet1_pct", "2026-06-30")]["value"])
        self.assertIsNone(rows[("lcr_pct", "2026-06-30")]["value"])

    def test_api_disagreement_or_unit_change_prevents_build(self):
        for key, value in [("api_value", 99), ("unit", "basis_points"), ("basis", "another denominator")]:
            with self.subTest(key=key):
                facts = copy.deepcopy(self.facts)
                facts["rows"][0][key] = value
                with self.assertRaises(ValueError):
                    builder.validate(facts)

    def test_missing_values_cannot_be_replaced_with_zero(self):
        self.facts["rows"][-1]["value"] = 0
        with self.assertRaises(ValueError):
            builder.validate(self.facts)

    def test_primary_only_revisions_cannot_leave_stale_headline(self):
        next(r for r in self.facts["rows"] if r["metric"] == "gnpa_amount")["value"] = 1200
        with self.assertRaisesRegex(ValueError, "Headline inputs changed"):
            builder.validate(self.facts)

    def test_nonfinite_numbers_and_false_completeness_are_rejected(self):
        for mode in ["nan", "coverage", "pdf_hash"]:
            facts = copy.deepcopy(self.facts)
            if mode == "nan":
                facts["rows"][0]["value"] = float("nan")
            elif mode == "coverage":
                facts["api_capture"]["coverage_complete"] = True
            else:
                facts["primary_source"]["pdf_bytes_independently_hashed_in_this_run"] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                builder.validate(facts)

    def test_published_artifacts_retain_review_limits(self):
        data = json.loads((builder.DEFAULT / "data.json").read_text())
        coverage = json.loads((builder.DEFAULT / "coverage.json").read_text())
        validation = json.loads((builder.DEFAULT / "validation.json").read_text())
        self.assertEqual(data["rows"], self.facts["rows"])
        self.assertEqual(coverage["covered_institution_count_in_this_brief"], 1)
        self.assertFalse(coverage["coverage_complete"])
        self.assertFalse(coverage["current_intraday_liquidity"])
        self.assertEqual(validation["missing_rows_retained"], 2)
        self.assertFalse(validation["primary_source_pdf_bytes_independently_hashed"])
        self.assertEqual(validation["api_reconciled_rows"], 10)


if __name__ == "__main__":
    unittest.main()
