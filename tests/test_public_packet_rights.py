"""Public historical packet projections retain originals and bind returned bytes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_institutional import AT, PID, csv_bytes, fetcher, fixture
from financial_evidence import institutional as store, reliability
from financial_evidence import funding_contract


class PublicPacketRightsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "archive"
        self.events = Path(self.tmp.name) / "events"
        for module in (store, reliability):
            clock = patch.object(module, "now", return_value=AT)
            clock.start()
            self.addCleanup(clock.stop)

    def archive(self, identifier=PID, restricted=True, value=7.123456):
        review, _ = fixture(identifier)
        review.update(freshness_assessments={}, measurement={})
        review["results"][0].update(
            source="New York Fed SOFR via FRED" if restricted else "New York Fed Markets API SOFR",
            value=value,
        )
        review["results"][1]["source"] = "Federal Reserve Board PRATES RESBM_N.D"
        raw = csv_bytes(review["results"])
        attempt = store.archive_once(
            self.root, trigger="manual", fetcher=fetcher(review=review, csv_raw=raw),
            builder=lambda value: (value, csv_bytes(value["results"]), []),
        )
        self.assertIsNone(attempt["error"])
        return review

    def test_projection_preserves_originals_and_binds_returned_json_csv(self):
        self.archive()
        folder = self.root / "packets" / PID
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        original, _, _ = store.packet(self.root, PID)
        manifest, raw, csv_raw = store.public_packet(self.root, PID)
        review = json.loads(raw)
        self.assertIsNone(review["results"][0]["value"])
        self.assertEqual(review["results"][0]["value_state"], "restricted")
        self.assertEqual(review["results"][1]["value"], 0)
        self.assertFalse(review["ready"])
        self.assertNotIn(b"7.123456", raw)
        self.assertNotIn(b"7.123456", csv_raw)
        self.assertEqual(manifest["artifacts"], {
            "review.json": store.digest(raw), "observations.csv": store.digest(csv_raw)})
        self.assertEqual(manifest["original_artifacts"], original["artifacts"])
        self.assertEqual(manifest["original_public_manifest_sha256"], store.digest(store.encoded(original)))
        self.assertFalse(store.public_latest(self.root)["ready"])
        with self.assertRaises(ValueError):
            funding_contract.current(self.root)
        self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_direct_publisher_values_and_exact_bytes_remain(self):
        self.archive(restricted=False)
        self.assertEqual(store.public_packet(self.root, PID), store.packet(self.root, PID))
        self.assertTrue(store.public_latest(self.root)["ready"])
        self.assertEqual(funding_contract.current(self.root)["observations"][0]["value"], 7.123456)

    def test_comparison_withholds_both_sides_and_derived_change(self):
        self.archive()
        other = "20260929T120000.000000Z-" + "c" * 32
        self.archive(other, value=8.654321)
        result = store.compare(self.root, PID, other)
        encoded = store.encoded(result)
        self.assertNotIn(b"7.123456", encoded)
        self.assertNotIn(b"8.654321", encoded)
        self.assertEqual(result["changes"], [])

    def test_corruption_rejected_before_projection(self):
        self.archive()
        path = self.root / "packets" / PID / "observations.csv"
        path.write_bytes(path.read_bytes().replace(b"7.123456", b"9.999999"))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            store.public_packet(self.root, PID)

    def test_http_downloads_latest_compare_and_versioned_route(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("workspace dependencies required")
        from financial_evidence.institutional_api import create_app
        self.archive()
        with TestClient(create_app(self.root, self.events)) as client:
            manifest = client.get(f"/packets/{PID}/manifest.json").json()
            for name in ("review.json", "observations.csv"):
                response = client.get(f"/packets/{PID}/{name}")
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(b"7.123456", response.content)
                self.assertEqual(response.headers["x-packet-sha256"], store.digest(response.content))
                self.assertEqual(manifest["artifacts"][name], store.digest(response.content))
            self.assertFalse(client.get("/latest").json()["ready"])
            self.assertEqual(client.get("/v1/funding/latest").status_code, 503)
            self.assertNotIn(b"7.123456", client.get("/compare", params={"before": PID, "after": PID}).content)
            self.assertEqual(client.get("/history").status_code, 200)
            self.assertEqual(client.get(f"/packets/{PID}/publisher-blobs").status_code, 404)


if __name__ == "__main__":
    unittest.main()
