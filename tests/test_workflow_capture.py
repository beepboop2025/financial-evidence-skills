"""A source outage must survive the handoff into a recurring desk workflow."""

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from email.message import Message
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("evidence_job", ROOT / "docs/workflows/evidence_job.py")
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class Response(io.BytesIO):
    def __init__(self, url, document):
        super().__init__(json.dumps(document).encode())
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"

    def geturl(self):
        return self.url


class WorkflowCaptureTests(unittest.TestCase):
    def run_capture(self, root, workflow="funding", opener=None, **kwargs):
        def default(request, **_):
            return Response(request.full_url, {"status": "unavailable", "generated_at": "2020-01-01T00:00:00Z", "value": None})
        return job.collect(workflow, root / "capture", opener=opener or default, **kwargs)

    def test_retrieved_unavailable_evidence_is_not_relabelled_valid_or_fresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.run_capture(root)
            packet = json.loads((root / "capture/packet.json").read_text())
            self.assertEqual(manifest["exit_code"], 0)
            self.assertEqual(manifest["evidence_status"], "not_evaluated")
            self.assertEqual(manifest["freshness_assessment"], "not_performed")
            self.assertEqual(packet["sources"][0]["document"]["status"], "unavailable")
            self.assertIsNone(packet["sources"][0]["document"]["value"])
            row = next(csv.DictReader(io.StringIO((root / "capture/sources.csv").read_text())))
            self.assertIn("2020-01-01", row["source_reported_clocks"])
            self.assertIn("unavailable", row["source_reported_state"])

    def test_partial_failure_retains_both_sources_and_nonzero_exit(self):
        def opener(request, **_):
            if "liquilens.in" in request.full_url:
                raise OSError("upstream unavailable")
            return Response(request.full_url, {"status": "ok"})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.run_capture(root, "bank-context", opener=opener)
            packet = json.loads((root / "capture/packet.json").read_text())
            self.assertEqual(manifest["exit_code"], 1)
            self.assertEqual([s["ok"] for s in packet["sources"]], [False, True])
            self.assertNotIn("document", packet["sources"][0])

    def test_all_failures_remain_unavailable(self):
        def opener(*args, **kwargs):
            raise OSError("offline")
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_capture(Path(directory), opener=opener)
            self.assertEqual(manifest["exit_code"], 2)
            self.assertEqual(manifest["transport_status"], "unavailable")

    def test_existing_capture_is_refused_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "capture").mkdir()
            with patch.object(job, "build_packet") as fetch:
                with self.assertRaises(FileExistsError):
                    self.run_capture(root)
                fetch.assert_not_called()

    def test_manifest_hashes_bind_written_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.run_capture(root)
            for name, proof in manifest["files"].items():
                data = (root / "capture" / name).read_bytes()
                self.assertEqual(proof["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(proof["bytes"], len(data))

    def test_verification_marks_requests_and_receipt(self):
        requests = []
        def opener(request, **_):
            requests.append(dict(request.header_items()))
            return Response(request.full_url, {})
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.run_capture(Path(directory), opener=opener, verification=True)
        self.assertEqual(requests[0]["X-liquilens-traffic-class"], "synthetic")
        self.assertEqual(manifest["traffic_class"], "operator_verification")

    def test_index_treats_formulas_as_text(self):
        for value in ["=HYPERLINK(1)", " +1", "-1", "@SUM(1)", "\tfoo"]:
            self.assertEqual(job.spreadsheet_cell(value), "'" + value)
        self.assertEqual(job.spreadsheet_cell("Seiche"), "Seiche")

    def test_unserializable_packet_leaves_no_completed_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(job, "build_packet", return_value={"value": float("nan")}):
                with self.assertRaises(ValueError):
                    self.run_capture(root)
            self.assertFalse((root / "capture/run.json").exists())


if __name__ == "__main__":
    unittest.main()
