"""First-use and repeat-review consumer contracts, without external traffic."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from financial_evidence import cli, research
from financial_evidence.onboarding import starter_catalog
from test_research_watch import capture


class FirstReviewTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = cli.main(argv)
        return result, out.getvalue(), err.getvalue()

    def test_start_is_offline_and_matches_hosted_instructions(self):
        with patch.object(research, "fetch_workflow", side_effect=AssertionError("network")):
            status, text, error = self.run_cli(["start", "--format", "json"])
        self.assertEqual(status, 0)
        self.assertFalse(error)
        value = json.loads(text)
        self.assertFalse(value["network_access_performed"])
        for actual, expected in zip(value["tasks"], starter_catalog()["tasks"]):
            self.assertEqual(actual["arguments"], expected["arguments"])
            self.assertIn(expected["selection"], actual["review_command"])
            self.assertEqual(actual["api_url"], expected["api_url"])

    def test_base_start_and_library_load_without_site_packages(self):
        code = "import sys; sys.path.insert(0, 'src'); from financial_evidence import research, cli; raise SystemExit(cli.main(['start', 'funding']))"
        result = subprocess.run([sys.executable, "-S", "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("financial-evidence review funding", result.stdout)
        self.assertIn("financial_evidence_workflow", result.stdout)
        self.assertNotIn("Review a covered institution", result.stdout)

    def test_review_uses_starter_selection_and_marks_verification(self):
        with patch.object(research, "fetch_workflow", return_value=capture()) as fetch:
            status, text, _ = self.run_cli(["review", "funding", "--verification"])
        fetch.assert_called_once_with("funding", "USD", verification=True)
        self.assertEqual(status, 0)
        self.assertIn("Funding review", text)
        self.assertIn("3.88", text)
        self.assertIn("2026-10-07", text)

    def test_repeat_review_saves_original_brief_comparison_and_receipt(self):
        first, later = capture(), capture()
        later["evidence"]["results"][0].update(value=None, availability="unavailable")
        later["content_sha256"] = hashlib.sha256(research.encoded(later["evidence"])).hexdigest()
        later["prepared_response"] = False
        with tempfile.TemporaryDirectory() as tmp:
            original = research.save_review(first, tmp, verification=True)
            old_bytes = (original / "result.json").read_bytes()
            with patch.object(research, "fetch_workflow", return_value=later):
                status, out, err = self.run_cli(["review", "funding", "--previous", str(original / "result.json"),
                                               "--output", tmp, "--verification", "--format", "json"])
            self.assertEqual(status, 2)
            self.assertFalse(err)
            target = Path(json.loads(out)["capture_directory"])
            self.assertNotEqual(original, target)
            self.assertEqual((original / "result.json").read_bytes(), old_bytes)
            self.assertEqual(json.loads((target / "result.json").read_text()), later)
            self.assertTrue(json.loads((target / "comparison.json").read_text())["changed"])
            self.assertIn("not reported", (target / "brief.md").read_text())
            receipt = json.loads((target / "receipt.json").read_text())
            self.assertEqual(receipt["traffic_class"], "synthetic")
            for name, digest in receipt["files"].items():
                self.assertEqual(digest, hashlib.sha256((target / name).read_bytes()).hexdigest())

    def test_invalid_baseline_does_not_fetch_or_create_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path(tmp) / "previous.json"
            value = capture(); value["evidence"]["results"][0]["value"] = 0
            previous.write_bytes(research.encoded(value))
            with patch.object(research, "fetch_workflow") as fetch:
                status, _, err = self.run_cli(["review", "funding", "--previous", str(previous), "--output", tmp])
            self.assertEqual(status, 1)
            self.assertIn("digest", err)
            fetch.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()), [previous])

    def test_shareable_brief_keeps_missing_values_dates_and_inert_source_text(self):
        value = capture()
        row = value["evidence"]["results"][0]
        row.update(metric="<script>alert(1)</script>|[click](javascript:run)\x1b", value=None,
                   availability="unavailable", source_url="https://example.org/source")
        value["evidence"]["results"] = [copy.deepcopy(row) for _ in range(26)]
        value["evidence"]["next_offset"] = 100
        text = research.render_review(value)
        self.assertNotIn("<script>", text)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("|[click]", text)
        self.assertIn("not reported", text)
        self.assertIn("2026-10-07", text)
        self.assertIn("Showing 25 of 26", text)
        self.assertIn("not a complete dataset", text)
        self.assertIn("https://example.org/source", text)
        self.assertEqual(len(value["evidence"]["results"]), 26)

    def test_institution_and_exit_briefs_retain_coverage_and_unavailability(self):
        institution = {"workflow": "institutions", "selection": "au-sfb", "prepared_response": False,
                       "evidence": {"rows": [{"slug": "au-sfb", "status": "unavailable", "latest_period": "2026-06-30",
                                              "gaps": [{"field": "deposits", "status": "unavailable", "reason": "missing filing"}]}],
                                    "coverage_complete": False}}
        text = research.render_review(institution)
        self.assertIn("missing filing", text)
        self.assertIn("False", text)
        self.assertIn("2026-06-30", text)
        self.assertIn("Reported coverage gaps", text)
        exit_result = {"workflow": "exit", "selection": "10000", "prepared_response": False,
                       "evidence": {"status": "unavailable", "rungs": [], "boundary": {"execution": False},
                                    "venue_freshness": {"example": {"observed_at": "2026-10-16T08:00:00Z", "status": "stale"}}}}
        text = research.render_review(exit_result)
        self.assertIn("No rows reported", text)
        self.assertIn("unavailable", text)
        self.assertIn("execution", text)
        self.assertIn("2026-10-16T08:00:00Z", text)
        self.assertIn("stale", text)

    def test_fetch_failure_returns_failure_without_creating_capture(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(research, "fetch_workflow", side_effect=OSError("offline")) as fetch:
            status, text, error = self.run_cli(["review", "funding", "--output", tmp])
            self.assertEqual(status, 1)
            self.assertFalse(text)
            self.assertIn("offline", error)
            self.assertFalse(list(Path(tmp).iterdir()))
            self.assertEqual(fetch.call_count, 1)

    def test_redirect_is_not_followed(self):
        paths = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/unexpected-target")
                self.end_headers()
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with patch.object(research, "BASE", f"http://127.0.0.1:{server.server_port}/workflow"):
                with self.assertRaises(OSError):
                    research.fetch_workflow("funding", verification=True)
            self.assertEqual(len(paths), 1)
            self.assertNotIn("unexpected-target", paths[0])
        finally:
            server.shutdown(); server.server_close(); worker.join()

    def test_download_is_the_packaged_client_and_completions_include_new_commands(self):
        self.assertEqual((ROOT / "src/financial_evidence/research.py").read_bytes(),
                         (ROOT / "docs/start/research_watch.py").read_bytes())
        for shell in ("bash", "zsh", "fish"):
            _, text, _ = self.run_cli(["completion", shell])
            self.assertIn("start review", text)


if __name__ == "__main__":
    unittest.main()
