"""Synthetic publisher fixtures prove units, dates, completeness and no fallback."""

import copy
import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from test_institutional import fixture

from financial_evidence import original_publishers as source
from financial_evidence.reliability import encoded


def xml_zip(xml):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("PRATES_data.xml", xml)
    return stream.getvalue()


def publisher_fixture():
    reference, _ = fixture()
    desired = [3.9, 3.88, 3.9, 3.99, 2914, 2930.19, 924.63, 0.58, 0]
    for row, value in zip(reference["results"], desired):
        row["value"] = value
        if row["metric_id"] == "liquidity.reserves":
            row["observation_date"] = "2026-09-23"
    documents = {
        "sofr": encoded(
            {
                "refRates": [
                    {
                        "type": "SOFR",
                        "effectiveDate": "2026-09-25",
                        "percentRate": 3.9,
                        "percentPercentile99": 3.99,
                        "volumeInBillions": 2914,
                    }
                ]
            }
        ),
        "effr": encoded(
            {
                "refRates": [
                    {"type": "EFFR", "effectiveDate": "2026-09-25", "percentRate": 3.88}
                ]
            }
        ),
        "iorb": xml_zip(
            '<Root xmlns="urn:fixture"><Series SERIES_NAME="RESBM_N.D" UNIT="Percent" UNIT_MULT="1"><Obs OBS_STATUS="A" TIME_PERIOD="2026-09-25" OBS_VALUE="3.90"/></Series></Root>'
        ),
        "reserves": b'<table><td id="t2h2c1">Week ended<br>Sep 23, 2026</td><td id="t2r16c1">Reserve balances with Federal Reserve Banks</td><td id="t2r16c2">2,930,193</td><td id="t2r16c5">2,969,922</td></table>',
        "tga": encoded(
            {
                "meta": {
                    "dataFormats": {"open_today_bal": "$1,000,000"},
                    "total-pages": 1,
                },
                "data": [
                    {
                        "account_type": "Treasury General Account (TGA) Opening Balance",
                        "record_date": "2026-09-25",
                        "open_today_bal": "924627",
                    }
                ],
            }
        ),
    }
    for key, kind, times, amount in [
        ("on_rrp", "Reverse Repo", ["13:15"], 576000000),
        ("srf", "Repo", ["08:30", "13:45"], 0),
    ]:
        documents[key] = encoded(
            {
                "repo": {
                    "operations": [
                        {
                            "operationDate": "2026-09-25",
                            "operationType": kind,
                            "term": "Overnight",
                            "closeTime": at,
                            "operationId": at,
                            "auctionStatus": "Results",
                            "settlementDate": "2026-09-25",
                            "totalAmtAccepted": amount,
                        }
                        for at in times
                    ]
                }
            }
        )
    return reference, documents


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.reference, self.documents = publisher_fixture()

    def build(self):
        return source.build(
            self.reference, getter=lambda name, url: self.documents[name]
        )

    def test_direct_values_keep_precision_and_original_lineage(self):
        review, csv_raw, sources = self.build()
        values = {x["metric_id"]: x["value"] for x in review["results"]}
        self.assertEqual(values["liquidity.on_rrp"], 0.576)
        self.assertEqual(values["liquidity.reserves"], 2930.193)
        self.assertEqual(values["liquidity.tga"], 924.627)
        self.assertEqual(len(sources), 7)
        self.assertIn(b"0.576", csv_raw)
        for lineage in review["publisher_lineage"].values():
            self.assertTrue(lineage["original_publisher_acquisition"])
            self.assertNotIn("fred.stlouisfed.org", lineage["source_url"])

    def test_missing_source_never_falls_back_to_reference(self):
        self.documents.pop("tga")
        with self.assertRaises(KeyError):
            self.build()

    def test_incorrect_units_or_ambiguous_dates_fail(self):
        for transform in ("units", "duplicate"):
            _, docs = publisher_fixture()
            value = source.strict_json(docs["tga"])
            if transform == "units":
                value["meta"]["dataFormats"]["open_today_bal"] = "$1"
            else:
                value["data"].append(copy.deepcopy(value["data"][0]))
            self.documents["tga"] = encoded(value)
            with self.assertRaises(ValueError):
                self.build()

    def test_partial_srf_fails_and_small_nonzero_is_preserved(self):
        value = source.strict_json(self.documents["srf"])
        value["repo"]["operations"][0]["totalAmtAccepted"] = 1000000
        self.documents["srf"] = encoded(value)
        review, csv_raw, _ = self.build()
        self.assertEqual(review["results"][8]["value"], 0.001)
        self.assertIn(b"0.001", csv_raw)
        value["repo"]["operations"].pop()
        self.documents["srf"] = encoded(value)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.build()

    def test_disagreement_beyond_reference_precision_fails(self):
        value = source.strict_json(self.documents["srf"])
        value["repo"]["operations"][0]["totalAmtAccepted"] = 10000000
        self.documents["srf"] = encoded(value)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            self.build()

    def test_reserves_reject_changed_header_and_wrong_reference_date(self):
        self.reference["results"][5]["observation_date"] = "2026-09-24"
        with self.assertRaisesRegex(ValueError, "date"):
            self.build()
        with self.assertRaisesRegex(ValueError, "column"):
            source.reserve_observation(
                self.documents["reserves"].replace(b"Week ended", b"Wednesday")
            )

    def test_xml_rejects_entities_and_legacy_series(self):
        for xml in (
            '<!DOCTYPE x [<!ENTITY foo "bar">]><x/>',
            '<Root xmlns="urn:fixture"><Series SERIES_NAME="RESBME_N.D" UNIT="Percent" UNIT_MULT="1"/></Root>',
        ):
            with self.assertRaises(ValueError):
                source.iorb_observations(xml_zip(xml))

    def test_bad_numbers_and_transport_failure_fail(self):
        for value in (None, True, "NaN", "Infinity", "."):
            with self.assertRaises(ValueError):
                source.number(value)
        with (
            patch.object(
                source.urllib.request, "build_opener", side_effect=OSError("offline")
            ),
            self.assertRaises(OSError),
        ):
            source.get_source("sofr", source.URLS["sofr"])


if __name__ == "__main__":
    unittest.main()
