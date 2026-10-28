"""Private reference continuity never makes withheld public evidence ready."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_institutional import AT, PID, csv_bytes, fetcher, fixture
from financial_evidence import funding_archive, institutional as store, reliability


class PrivateFundingReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "packets"
        for module in (store, reliability):
            clock = patch.object(module, "now", return_value=AT)
            clock.start()
            self.addCleanup(clock.stop)
        self.reference, _ = fixture()
        self.reference.update(freshness_assessments={}, measurement={})
        self.reference["results"][0].update(source="NY Fed SOFR via FRED", value=3.123456)
        self.raw = csv_bytes(self.reference["results"])
        self.public, _ = funding_archive.public_funding_projection(
            self.reference, self.raw, store.digest(self.raw))
        self.calls = []

    def independent_builder(self, reference):
        self.assertEqual(reference["results"][0]["value"], 3.123456)
        # A synthetic original-publisher response, independent of the public view.
        direct = copy.deepcopy(reference)
        direct["results"][0].update(source="Synthetic independently acquired publisher", value=3.123455)
        return direct, csv_bytes(direct["results"]), []

    def archive(self, private=None, public=None, csv_raw=None):
        base = fetcher(review=self.public if public is None else public)
        def fetch(path):
            self.calls.append(path)
            self.assertFalse(path.endswith(".csv"))
            return base(path)
        with patch.object(funding_archive, "read_operator_reference", return_value=(
            self.reference if private is None else private,
            self.raw if csv_raw is None else csv_raw,
        )) as reader:
            result = store.archive_once(
                self.root, fetcher=fetch, builder=self.independent_builder,
                private_reference_dir="/private/readonly-capture",
            )
            reader.assert_called_once()
        self.assertNotIn(b"/private/readonly-capture", store.encoded(result))
        return result

    def test_independent_capture_remains_ready_while_public_reference_is_restricted(self):
        attempt = self.archive()
        self.assertIsNone(attempt["error"])
        self.assertFalse(attempt["probe"]["workspace_ready"])
        self.assertTrue(attempt["probe"]["ready"])
        self.assertTrue(attempt["private_reference"]["public_projection_verified"])
        self.assertTrue(store.public_latest(self.root)["ready"])
        _, raw, _ = store.public_packet(self.root, PID)
        self.assertEqual(store.strict_json(raw)["results"][0]["value"], 3.123455)

    def test_racing_private_capture_fails_closed(self):
        reference = copy.deepcopy(self.reference)
        reference["capture_id"] = "20260929T120000.000000Z-" + "b" * 32
        attempt = self.archive(private=reference)
        self.assertIn("capture identities differ", attempt["error"])
        self.assertFalse(attempt["probe"]["ready"])
        self.assertIsNone(attempt["packet_id"])

    def test_projection_hash_or_rows_cannot_be_substituted(self):
        for change in ("hash", "rows"):
            with self.subTest(change=change):
                public = copy.deepcopy(self.public)
                if change == "hash":
                    public["publication_projection"]["source_artifact_sha256"] = "sha256:" + "0" * 64
                else:
                    public["results"][1]["value"] = 90
                attempt = self.archive(public=public)
                self.assertIn("does not bind", attempt["error"])
                self.assertFalse(attempt["probe"]["ready"])

    def test_no_readiness_is_inferred_from_available_private_values(self):
        reference = copy.deepcopy(self.reference)
        reference["ready"] = False
        attempt = self.archive(private=reference)
        self.assertFalse(attempt["probe"]["ready"])
        self.assertFalse(store.public_latest(self.root)["ready"])


if __name__ == "__main__":
    unittest.main()
