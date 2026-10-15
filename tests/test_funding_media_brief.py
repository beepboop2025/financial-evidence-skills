"""Failure-focused checks for the dated media brief's source extraction."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("funding_media", ROOT / "scripts/build_funding_media_brief.py")
media = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(media)


class SourceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.horizon = "2026-10-08"
        self.write("sofr", {"refRates": [
            {"effectiveDate": "2026-10-09", "type": "SOFR", "percentRate": 9.99},
            {"effectiveDate": self.horizon, "type": "SOFR", "percentRate": 3.87,
             "percentPercentile99": 3.95, "volumeInBillions": 2963}]})
        self.write("effr", {"refRates": [{"effectiveDate": self.horizon, "type": "EFFR", "percentRate": 3.88}]})
        self.iorb("Percent")
        document = ''.join(f'<td id="{key}">{value}</td>' for key, value in {
            "t2h1c2": "Averages of daily figures", "t2h2c1": "Week ended Oct 7, 2026",
            "t2r16c1": "Reserve balances with Federal Reserve Banks", "t2r16c2": "3,029,659"}.items())
        (self.base / media.FILES["reserves"]).write_text(document)
        self.write("tga", {"meta": {"dataFormats": {"open_today_bal": "$1,000,000"}}, "data": [
            {"record_date": self.horizon, "account_type": "Treasury General Account (TGA) Opening Balance", "open_today_bal": "885783"}]})
        self.write("srf", {"repo": {"operations": [self.operation("a", "08:15", 3000000), self.operation("b", "13:30", 0)]}})
        self.write("on_rrp", {"repo": {"operations": [self.operation("c", "12:45", 335000000, "Reverse Repo")]}})

    def write(self, name, value):
        (self.base / media.FILES[name]).write_text(json.dumps(value))

    def read(self, name):
        return json.loads((self.base / media.FILES[name]).read_text())

    def iorb(self, unit):
        data = f'<Data><Series SERIES_NAME="RESBM_N.D" UNIT="{unit}"><Obs TIME_PERIOD="2026-10-13" OBS_STATUS="A" OBS_VALUE="8.88"/><Obs TIME_PERIOD="{self.horizon}" OBS_STATUS="A" OBS_VALUE="3.90"/></Series></Data>'
        with zipfile.ZipFile(self.base / media.FILES["iorb"], "w") as archive:
            archive.writestr("PRATES_data.xml", data)

    def operation(self, identifier, release, amount, operation="Repo"):
        return {"operationId": identifier, "operationDate": self.horizon, "operationType": operation,
                "term": "Overnight", "auctionStatus": "Results", "releaseTime": release,
                "totalAmtAccepted": amount}

    def test_selects_exact_dates_and_preserves_small_nonzero_amount(self):
        rows = media.parse_originals(self.base, self.horizon)
        self.assertEqual(str(rows["policy.sofr"][0]), "3.87")
        self.assertEqual(str(rows["policy.iorb"][0]), "3.90")
        self.assertEqual(str(rows["liquidity.srf"][0]), "0.003")
        self.assertEqual(rows["liquidity.reserves"][1], "2026-10-07")

    def test_requires_both_repo_sessions(self):
        value = self.read("srf")
        value["repo"]["operations"].pop()
        self.write("srf", value)
        with self.assertRaisesRegex(ValueError, "operation completeness"):
            media.parse_originals(self.base, self.horizon)

    def test_duplicate_repo_ids_are_rejected(self):
        value = self.read("srf")
        value["repo"]["operations"][1]["operationId"] = "a"
        self.write("srf", value)
        with self.assertRaisesRegex(ValueError, "duplicate operation"):
            media.parse_originals(self.base, self.horizon)

    def test_iorb_wrong_unit_is_rejected(self):
        self.iorb("Basis points")
        with self.assertRaisesRegex(ValueError, "IORB unit"):
            media.parse_originals(self.base, self.horizon)

    def test_cannot_substitute_treasury_closing_balance(self):
        value = self.read("tga")
        value["data"][0]["account_type"] = "Treasury General Account (TGA) Closing Balance"
        self.write("tga", value)
        with self.assertRaisesRegex(ValueError, "TGA date/account"):
            media.parse_originals(self.base, self.horizon)

    def test_duplicate_sofr_date_is_rejected(self):
        value = self.read("sofr")
        value["refRates"].append(value["refRates"][1])
        self.write("sofr", value)
        with self.assertRaisesRegex(ValueError, "SOFR date/type"):
            media.parse_originals(self.base, self.horizon)

    def test_future_weekly_reserves_cannot_replace_horizon(self):
        path = self.base / media.FILES["reserves"]
        path.write_text(path.read_text().replace("Oct 7, 2026", "Oct 14, 2026"))
        with self.assertRaisesRegex(ValueError, "after horizon"):
            media.parse_originals(self.base, self.horizon)


class ChartNoticeTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "optional chart renderer")
    def test_full_publisher_notice_fits_rendered_canvas_and_survives_svg(self):
        sys.path.insert(0, str(ROOT / "src"))
        from financial_evidence.original_publishers import NYFED_NOTICE
        checks = [{"metric_id": key, "value": value} for key, value in {
            "policy.iorb": "3.90", "policy.sofr": "3.87", "policy.effr": "3.88",
            "distribution.sofr.p99": "3.95"}.items()]
        with tempfile.TemporaryDirectory(prefix=".notice-render-", dir=ROOT) as temporary:
            output = Path(temporary)
            media.chart(output, checks, NYFED_NOTICE)
            svg = ET.parse(output / "funding-rate-comparison.svg").getroot()
            notice = svg.find(".//*[@id='publisher-notice']")
            self.assertIsNotNone(notice)
            text = " ".join(" ".join(notice.itertext()).split())
            self.assertIn("products or services offered by LIQUILENS PRIVATE LIMITED", text)
            self.assertIn("parties from which they obtained data have no liability", text)
            self.assertIn("transaction data is claimed.", text)
            self.assertGreater(float(svg.attrib["viewBox"].split()[3]), 7.2 * 72)
            for extension in ("svg", "png", "pdf"):
                self.assertGreater((output / f"funding-rate-comparison.{extension}").stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
