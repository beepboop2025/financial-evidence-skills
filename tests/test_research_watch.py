"""Consumer checks for the package-free workflow starter."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("research_watch", ROOT / "docs/start/research_watch.py")
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


def capture():
    evidence = {"schema": "financial-evidence.agent-result.v1", "results": [
        {"entity_id": "USD", "metric": "SOFR", "source_field": "/rate", "value": 3.88,
         "unit": "%", "as_of": "2026-10-07", "availability": "AVAILABLE", "rights_status": "allowed",
         "retrieved_at": "2026-10-09T08:00:00Z"}], "next_offset": None, "transport_status": "complete"}
    return {"schema": "financial-evidence.workflow-result.v1", "workflow": "funding", "selection": "USD",
            "retrieved_at": "2026-10-09T08:00:00Z", "prepared_response": True, "evidence": evidence,
            "content_sha256": hashlib.sha256(watch.encoded(evidence)).hexdigest()}


class ResearchWatchTests(unittest.TestCase):
    def test_original_response_roundtrip_and_tampering(self):
        value = capture()
        self.assertEqual(watch.validate(watch.encoded(value)), value)
        value["evidence"]["results"][0]["value"] = 0
        with self.assertRaisesRegex(ValueError, "digest"):
            watch.validate(watch.encoded(value))

    def test_wrong_selection_nonfinite_and_duplicate_keys_rejected(self):
        value = capture()
        with self.assertRaises(ValueError):
            watch.validate(watch.encoded(value), {"workflow": "funding", "selection": "EUR"})
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e500}', b'[]', b' ' * (watch.LIMIT + 1)]:
            with self.assertRaises(ValueError):
                watch.validate(raw)

    def test_bounded_selection_blocks_arbitrary_targets(self):
        for workflow, selection in [("funding", "https://example.org"), ("institutions", "../secret"),
                                    ("exit", "1000001"), ("exit", "0"), ("exit", "NaN"), ("institutions", "a,b,c,d,e,f")]:
            with self.assertRaises(ValueError):
                watch.settings(workflow, selection)
        self.assertEqual(watch.settings("exit", "10000.00,10000")["selection"], "10000")

    def test_retrieval_time_is_not_a_source_change(self):
        first, later = capture(), capture()
        later["retrieved_at"] = "2026-10-10T08:00:00Z"
        later["evidence"]["results"][0]["retrieved_at"] = later["retrieved_at"]
        self.assertFalse(watch.compare(first, later)["changed"])
        later["evidence"]["results"][0]["as_of"] = "2026-10-08"
        self.assertTrue(watch.compare(first, later)["changed"])

    def test_unavailable_transition_is_not_zero_or_recovery(self):
        first, later = capture(), capture()
        later["evidence"]["results"][0].update(value=None, availability="unavailable")
        result = watch.compare(first, later)
        self.assertTrue(result["changed"])
        self.assertIsNone(result["after"]["rows"][0]["value"])
        later["selection"] = "EUR"
        with self.assertRaises(ValueError):
            watch.compare(first, later)

    def test_institution_fingerprint_catches_hidden_evidence_change(self):
        first = {"workflow": "institutions", "selection": "au-sfb", "evidence": {"rows": [{"slug": "au-sfb", "content_sha256": "a" * 64}]}}
        later = copy.deepcopy(first)
        later["evidence"]["rows"][0]["content_sha256"] = "b" * 64
        self.assertTrue(watch.compare(first, later)["changed"])

    def test_captures_never_overwrite_and_receipt_binds_bytes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(watch, "fetch_workflow", return_value=capture()):
            for _ in range(2):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(watch.main(["--workflow", "funding", "--output", tmp, "--verification"]), 0)
            paths = list(Path(tmp).iterdir())
            self.assertEqual(len(paths), 2)
            for directory in paths:
                receipt = json.loads((directory / "receipt.json").read_text())
                self.assertEqual(receipt["traffic_class"], "synthetic")
                self.assertEqual(receipt["files"]["result.json"], hashlib.sha256((directory / "result.json").read_bytes()).hexdigest())

    def test_invalid_previous_fails_before_network(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(watch, "fetch_workflow") as fetch:
            previous = Path(tmp) / "previous.json"
            previous.write_bytes(watch.encoded(capture()))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(watch.main(["--workflow", "funding", "--selection", "EUR", "--previous", str(previous)]), 1)
            fetch.assert_not_called()

    def test_no_evidence_exit_status_preserves_response(self):
        value = capture(); value["prepared_response"] = False
        with patch.object(watch, "fetch_workflow", return_value=value), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(watch.main(["--workflow", "funding"]), 2)
            self.assertFalse(json.loads(output.getvalue())["prepared_response"])
