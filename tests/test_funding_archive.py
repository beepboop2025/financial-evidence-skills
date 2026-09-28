"""Public readers verify latest evidence and reject links, tampering and staleness."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from financial_evidence.funding_archive import load_csv, read_export, read_review
from test_capture_funding_review import capture, fetcher, responses
from test_funding_review import captures, NOW


class FundingArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.output = Path(self.temporary.name)
        with patch.object(capture, "utcnow", return_value=NOW):
            self.path, self.manifest = capture.capture(self.output, fetcher=fetcher())

    def tearDown(self):
        self.temporary.cleanup()

    def read(self, **kwargs):
        return read_review(self.output, now=kwargs.pop("now", NOW), **kwargs)

    def current(self):
        return json.loads((self.output / "current.json").read_bytes())

    def replace_current(self, current):
        (self.output / "current.json").write_bytes(capture.encoded(current))

    def replace_artifact(self, name, raw):
        (self.path / name).write_bytes(raw)
        manifest = json.loads((self.path / "manifest.json").read_bytes())
        manifest["artifact_sha256"][name] = capture.sha256(raw)
        manifest_raw = capture.encoded(manifest)
        (self.path / "manifest.json").write_bytes(manifest_raw)
        current = self.current()
        current["latest"]["manifest_sha256"] = capture.sha256(manifest_raw)
        self.replace_current(current)

    def test_verified_rows_csv_and_environment_default(self):
        result = self.read()
        self.assertTrue(result["available"])
        self.assertTrue(result["ready"])
        self.assertFalse(result["stale"])
        self.assertEqual(result["policy_id"], "usd-funding-review-checks.v2")
        self.assertEqual(len(result["results"]), 9)
        self.assertEqual(result["results"][0]["value"], 0.0)
        self.assertEqual(result["capture_id"], self.path.name)
        self.assertEqual(
            result["manifest_sha256"],
            capture.sha256((self.path / "manifest.json").read_bytes()),
        )
        self.assertEqual(set(result["input_sha256"]), {"desk", "atlas", "health"})
        self.assertEqual(result["source_urls"]["desk"], "https://api.seiche.info/mcp")
        self.assertEqual(
            load_csv(self.output, now=NOW),
            (self.path / "funding-observations.csv").read_bytes(),
        )
        with patch.dict(
            os.environ, {"FINANCIAL_EVIDENCE_REVIEW_DIR": str(self.output)}
        ):
            self.assertEqual(read_review(now=NOW), result)
        self.assertNotIn(str(self.output), json.dumps(result))
        paired, csv_bytes = read_export(self.output, now=NOW)
        self.assertEqual(paired, result)
        self.assertEqual(
            csv_bytes, (self.path / "funding-observations.csv").read_bytes()
        )

    def test_release_mismatch_cannot_leave_passing_rows_or_csv(self):
        with patch.object(capture, "utcnow", return_value=NOW):
            capture.capture(
                self.output,
                backend="https://example.com/openbb",
                expected_release="wrong-release",
                fetcher=fetcher(),
            )
        result, csv_bytes = read_export(self.output, now=NOW)
        self.assertTrue(result["available"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["data_readiness"], "checks_passed")
        self.assertEqual(
            {row["review_status"] for row in result["results"]},
            {"release_identity_mismatch"},
        )
        self.assertIsNone(csv_bytes)

    def test_backend_failure_is_visible_on_each_available_source_row(self):
        with patch.object(capture, "utcnow", return_value=NOW):
            capture.capture(
                self.output,
                backend="https://example.com/openbb",
                fetcher=fetcher(failures={"backend-health"}),
            )
        result, csv_bytes = read_export(self.output, now=NOW)
        self.assertFalse(result["available"])
        self.assertEqual(result["data_readiness"], "checks_passed")
        self.assertEqual(
            {row["review_status"] for row in result["results"]}, {"capture_unavailable"}
        )
        self.assertIsNone(csv_bytes)

    def test_public_release_identity_is_filtered(self):
        bodies = responses()
        bodies["backend-release"] = (
            b'{"release_id":"workspace-1.0.0+abcdef123456","package_version":"0.1.5","secret_path":"/private/host/path"}'
        )
        with patch.object(capture, "utcnow", return_value=NOW):
            capture.capture(
                self.output,
                backend="https://example.com/openbb",
                fetcher=fetcher(bodies),
            )
        result = self.read()
        self.assertEqual(
            result["observed_release"],
            {"release_id": "workspace-1.0.0+abcdef123456", "package_version": "0.1.5"},
        )
        self.assertNotIn("/private/host/path", json.dumps(result))

    def test_stale_capture_visible_but_not_ready_or_csv_downloadable(self):
        later = "2026-09-28T19:38:00Z"
        result = self.read(now=later)
        self.assertTrue(result["available"])
        self.assertTrue(result["stale"])
        self.assertFalse(result["ready"])
        self.assertEqual(
            {r["review_status"] for r in result["results"]}, {"stale_capture"}
        )
        self.assertIsNone(load_csv(self.output, now=later))

    def test_future_clock_does_not_pass_freshness(self):
        result = self.read(now="2026-09-28T19:00:00Z")
        self.assertTrue(result["stale"])
        self.assertFalse(result["ready"])

    def test_failed_latest_does_not_return_previous_good_values(self):
        with patch.object(capture, "utcnow", return_value=NOW):
            path, _ = capture.capture(self.output, fetcher=fetcher(failures={"atlas"}))
        result = self.read()
        self.assertFalse(result["available"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["capture_id"], path.name)
        self.assertEqual(result["results"], [])
        self.assertIsNone(load_csv(self.output, now=NOW))

    def test_attention_required_csv_is_available_and_keeps_null_restrictions(self):
        docs = captures()
        docs[0]["sections"][0]["metrics"][0]["rights_status"] = "metadata_only"
        with patch.object(capture, "utcnow", return_value=NOW):
            capture.capture(self.output, fetcher=fetcher(responses(docs)))
        result = self.read()
        self.assertTrue(result["available"])
        self.assertFalse(result["ready"])
        self.assertEqual(result["data_readiness"], "attention_required")
        self.assertIsNone(result["results"][0]["value"])
        self.assertIsNotNone(load_csv(self.output, now=NOW))

    def test_tampered_manifest_review_or_csv_fail_closed(self):
        for name in ("manifest.json", "review.json", "funding-observations.csv"):
            with self.subTest(name=name):
                path = self.path / name
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                self.assertFalse(self.read()["available"])
                self.assertEqual(self.read()["results"], [])
                self.assertIsNone(load_csv(self.output, now=NOW))
                path.write_bytes(original)

    def test_path_traversal_and_unexpected_capture_reference_are_rejected(self):
        original = self.current()
        for name in ("../outside", "/etc", "captures/other"):
            current = self.current()
            current["latest"]["capture"] = name
            self.replace_current(current)
            self.assertFalse(self.read()["available"])
            self.replace_current(original)

    def test_symlinked_artifact_is_rejected_even_with_matching_bytes(self):
        artifact = self.path / "review.json"
        outside = self.output / "outside.json"
        artifact.rename(outside)
        artifact.symlink_to(outside)
        self.assertFalse(self.read()["available"])

    def test_symlinked_capture_directory_is_rejected(self):
        outside = self.output / "outside-capture"
        self.path.rename(outside)
        self.path.symlink_to(outside, target_is_directory=True)
        self.assertFalse(self.read()["available"])

    def test_fifo_cannot_block_archive_reader(self):
        artifact = self.path / "review.json"
        artifact.unlink()
        os.mkfifo(artifact)
        self.assertFalse(self.read()["available"])

    def test_oversized_current_and_nonfinite_values_fail_closed(self):
        original = (self.output / "current.json").read_bytes()
        (self.output / "current.json").write_bytes(b" " * 131073)
        self.assertFalse(self.read()["available"])
        (self.output / "current.json").write_bytes(original)
        raw = (
            (self.path / "funding-observations.csv")
            .read_bytes()
            .replace(b"policy.sofr,0,", b"policy.sofr,1e999,")
        )
        self.replace_artifact("funding-observations.csv", raw)
        self.assertFalse(self.read()["available"])

    def test_csv_and_review_time_disagreement_fails_closed(self):
        raw = (
            (self.path / "funding-observations.csv")
            .read_bytes()
            .replace(b"2026-09-28T19:17:00+00:00", b"2026-09-28T19:16:00+00:00")
        )
        self.replace_artifact("funding-observations.csv", raw)
        self.assertFalse(self.read()["available"])

    def test_unconfigured_and_invalid_time_do_not_leak_filesystem_paths(self):
        with patch.dict(os.environ, {}, clear=True):
            result = read_review()
        self.assertEqual(result["issues"][0]["code"], "funding_review_not_configured")
        for now in ("invalid", datetime(2026, 1, 1), 0):
            self.assertFalse(self.read(now=now)["available"])
        self.assertTrue(
            self.read(now=datetime(2026, 9, 28, 19, 17, tzinfo=timezone.utc))["ready"]
        )
        result = read_review("/a/private/nonexistent/path", now=NOW)
        self.assertNotIn("/a/private", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
