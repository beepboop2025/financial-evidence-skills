"""Consumer failures that must never become a silently incomplete research table."""
import csv
from email.message import Message
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("research_client", ROOT / "docs/tools/research_client.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def page(offset=0, values=(0, None), total=2, next_offset=None, digest="a" * 64):
    return {
        "schema": "liquidity-lab.openbb-table.v1", "dataset": "money_markets",
        "offset": offset, "limit": 2, "returned_rows": len(values),
        "total_rows": total, "next_offset": next_offset,
        "transport_status": "complete", "evidence_status": "not_evaluated",
        "carrier_verification": "not_performed", "diagnostics": [],
        "sources": [{"source_url": "https://api.seiche.info/api/v2/money-markets", "content_sha256": "sha256:" + digest}],
        "results": [{"dataset": "money_markets", "value": value, "as_of": "2026-10-01",
                     "unit": "%", "availability": "withheld" if value is None else "published",
                     "context": "=untrusted source", "source_url": "https://example.org/source"}
                    for value in values],
    }


class Response(io.BytesIO):
    def __init__(self, raw, content_type="application/json"):
        super().__init__(raw)
        self.headers = Message()
        self.headers["Content-Type"] = content_type


def opener_for(pages, calls=None):
    pending = iter(pages)
    def open_request(request, timeout):
        if calls is not None:
            calls.append(request)
        value = next(pending)
        return Response(json.dumps(value).encode())
    return open_request


class ResearchClientTests(unittest.TestCase):
    def test_all_pages_preserve_zero_null_dates_and_provenance(self):
        calls = []
        result = client.collect("money_markets", page_size=2, synthetic=True, opener=opener_for([
            page(total=3, next_offset=2), page(offset=2, values=(-1,), total=3),
        ], calls))
        self.assertEqual([row["value"] for row in result["results"]], [0, None, -1])
        self.assertEqual(result["returned_rows"], 3)
        self.assertEqual(len(result["pages"]), 2)
        self.assertEqual(result["results"][1]["as_of"], "2026-10-01")
        self.assertEqual(result["results"][1]["availability"], "withheld")
        self.assertEqual(result["evidence_status"], "not_evaluated")
        self.assertEqual(parse_qs(urlsplit(calls[1].full_url).query)["offset"], ["2"])
        self.assertEqual(calls[0].get_header("X-liquilens-traffic-class"), "synthetic")

    def test_source_change_or_total_change_requires_restart(self):
        for second in [page(offset=2, values=(1,), total=3, digest="b" * 64),
                       page(offset=2, values=(1,), total=4)]:
            with self.subTest(second=second), self.assertRaisesRegex(client.EvidenceError, "snapshot changed"):
                client.collect("money_markets", page_size=2, opener=opener_for([
                    page(total=3, next_offset=2), second]))

    def test_missing_page_or_loop_is_not_a_complete_capture(self):
        for item in [page(total=3), page(total=3, next_offset=0), page(total=3, next_offset=1),
                     page(offset=4), page(total=-1)]:
            with self.subTest(item=item), self.assertRaises(client.EvidenceError):
                client.collect("money_markets", page_size=2, opener=opener_for([item]))

    def test_page_bound_stops_instead_of_exporting_partial_rows(self):
        with self.assertRaisesRegex(client.EvidenceError, "max_pages"):
            client.collect("money_markets", page_size=2, max_pages=1,
                           opener=opener_for([page(total=3, next_offset=2)]))

    def test_failed_source_and_forged_authority_are_rejected(self):
        for changes in [{"transport_status": "partial"}, {"evidence_status": "approved"},
                        {"carrier_verification": "verified"}, {"schema": "other"},
                        {"sources": []}, {"sources": [None]}, {"dataset": "bank_risk"},
                        {"offset": False}, {"returned_rows": 99}]:
            item = page(); item.update(changes)
            with self.subTest(changes=changes), self.assertRaises(client.EvidenceError):
                client.collect("money_markets", page_size=2, opener=opener_for([item]))

    def test_challenge_oversized_and_nonfinite_json_fail(self):
        cases = [(b"<html>challenge</html>", "text/html"),
                 (b"x" * (client.MAX_BYTES + 1), "application/json"),
                 (b'{"number":NaN}', "application/json"),
                 (b'{"number":1e999}', "application/json")]
        for raw, kind in cases:
            with self.subTest(kind=kind, size=len(raw)), self.assertRaises(ValueError):
                client.collect("money_markets", opener=lambda *a, **k: Response(raw, kind))

    def test_invalid_arguments_make_no_request(self):
        for options in [{"dataset": "unknown"}, {"page_size": True}, {"page_size": 2001},
                        {"max_pages": 0}, {"entity": "x" * 101}, {"start_date": "today"},
                        {"start_date": "2026-02-31"}, {"start_date": None},
                        {"start_date": "2026-10-02", "end_date": "2026-10-01"}]:
            args = {"dataset": "money_markets", **options}
            with self.subTest(args=args), self.assertRaises(ValueError):
                client.collect(**args, opener=lambda *a, **k: self.fail("invalid input contacted the network"))

    def test_captures_are_inert_hashed_and_never_overwritten(self):
        result = client.collect("money_markets", page_size=2, opener=opener_for([page(values=(-2, None))]))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "capture"
            receipt = client.save_capture(result, destination)
            raw = json.loads((destination / "evidence.json").read_text())
            self.assertEqual(raw["results"][0]["context"], "=untrusted source")
            with (destination / "rows.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["context"], "'=untrusted source")
            self.assertEqual(rows[0]["value"], "-2")
            self.assertEqual(rows[1]["value"], "")
            for name, digest in receipt["sha256"].items():
                self.assertEqual(hashlib.sha256((destination / name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                client.save_capture(result, destination)

    def test_empty_matching_table_is_not_zero_filled(self):
        result = client.collect("money_markets", page_size=2,
                                opener=opener_for([page(values=(), total=0)]))
        self.assertEqual(result["results"], [])
        self.assertEqual(result["evidence_status"], "not_evaluated")

    def test_redirects_never_contact_an_unexpected_host(self):
        with self.assertRaises(client.EvidenceError):
            client._NoRedirects().redirect_request(None, None, 302, "redirect", {}, "https://other.example/")


if __name__ == "__main__":
    unittest.main()
