"""Operator evidence survives failures and can be replayed without the network."""

import copy
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import capture_funding_review as capture
from test_funding_review import captures, NOW


class FakeResponse(io.BytesIO):
    def __init__(self, body, status=200):
        super().__init__(body)
        self.status = status
        self.headers = {"Content-Type": "application/json"}


class FakeOpener:
    def __init__(self, response):
        self.response = response

    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def responses(docs=None):
    desk, atlas, health = docs or captures()
    # Deliberately noncanonical wire spacing tests exact-byte persistence.
    return {
        "mcp-initialize": b'{"jsonrpc":"2.0", "id":"funding-init", "result":{"protocolVersion":"2025-11-25"}}\n',
        "mcp-initialized": b"",
        "funding-desk": json.dumps(
            {
                "jsonrpc": "2.0",
                "id": "funding-desk",
                "result": {"structuredContent": desk},
            },
            indent=3,
        ).encode(),
        "atlas": json.dumps(atlas, indent=3).encode(),
        "desk-history": json.dumps(desk, indent=3).encode(),
        "health": json.dumps(health, indent=3).encode(),
        "backend-health": b'{"status":"ok","release_id":"workspace-1.0.0+abcdef123456"}',
        "backend-release": b'{"release_id":"workspace-1.0.0+abcdef123456"}',
    }


def fetcher(bodies=None, failures=()):
    bodies = bodies or responses()
    calls = []

    def fake(name, url, **kwargs):
        calls.append((name, url, kwargs))
        raw = bodies[name]
        failed = name in failures
        return (
            {
                "name": name,
                "url": url,
                "http_status": 503 if failed else 200,
                "complete": True,
                "error": "http_error" if failed else None,
                "started_at": NOW,
                "finished_at": NOW,
                "elapsed_seconds": 0.125,
                "bytes": len(raw),
                "sha256": capture.sha256(raw),
            },
            raw,
            "ephemeral-session" if name == "mcp-initialize" else None,
        )

    fake.calls = calls
    return fake


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.output = Path(self.temporary.name)
        self.clock = patch.object(capture, "utcnow", return_value=NOW)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        self.temporary.cleanup()

    def run_capture(self, **kwargs):
        return capture.capture(
            self.output, fetcher=kwargs.pop("fetcher", fetcher()), **kwargs
        )

    def current(self):
        return json.loads((self.output / "current.json").read_bytes())

    def test_exact_bytes_replay_determinism_and_mcp_session(self):
        raw = responses()
        fake = fetcher(raw)
        path, original = self.run_capture(fetcher=fake)
        self.assertTrue(original["ready"])
        for name in capture.SOURCE_NAMES:
            self.assertEqual((path / (name + ".response")).read_bytes(), raw[name])
            self.assertEqual(
                original["requests"][name]["sha256"], capture.sha256(raw[name])
            )
        self.assertEqual(fake.calls[1][2]["session"], "ephemeral-session")
        self.assertEqual(fake.calls[2][2]["session"], "ephemeral-session")
        self.assertNotIn("ephemeral-session", (path / "manifest.json").read_text())
        current_before = (self.output / "current.json").read_bytes()
        with patch.object(
            capture, "fetch", side_effect=AssertionError("network during replay")
        ):
            replay_path, replayed = capture.replay(path, self.output)
        self.assertEqual(original["data_readiness"], replayed["data_readiness"])
        self.assertEqual(
            original["checker_source_sha256"], replayed["checker_source_sha256"]
        )
        self.assertEqual(
            original["capture_tool_sha256"], replayed["capture_tool_sha256"]
        )
        self.assertEqual(
            original["publication_policy_sha256"], replayed["publication_policy_sha256"]
        )
        self.assertEqual(original["policy_id"], replayed["original_policy_id"])
        for name in ("review.json", "desk.json", "funding-observations.csv"):
            self.assertEqual(
                (path / name).read_bytes(), (replay_path / name).read_bytes()
            )
        self.assertEqual(current_before, (self.output / "current.json").read_bytes())

    def test_same_time_capture_paths_are_distinct_and_exclusive(self):
        first, _ = self.run_capture()
        second, _ = self.run_capture()
        self.assertNotEqual(first, second)
        before = (first / "manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            capture.write_new(first / "manifest.json", b"replacement")
        self.assertEqual(before, (first / "manifest.json").read_bytes())

    def test_failed_capture_preserves_previous_success_and_reports_failure(self):
        good, _ = self.run_capture()
        bad, report = self.run_capture(fetcher=fetcher(failures={"atlas"}))
        current = self.current()
        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(report["availability"], "unavailable")
        self.assertEqual(report["data_readiness"], "not_evaluated")
        self.assertEqual(current["latest"]["capture_id"], bad.name)
        self.assertEqual(current["last_ready"]["capture_id"], good.name)
        self.assertEqual(current["last_available"]["capture_id"], good.name)
        self.assertTrue((good / "funding-observations.csv").exists())
        self.assertFalse((bad / "funding-observations.csv").exists())
        self.assertEqual(current["measurement"]["probes"], 2)
        self.assertEqual(current["measurement"]["sampled_availability_pct"], 50)

    def test_available_but_stale_data_is_not_ready(self):
        docs = captures()
        docs[0]["sections"][0]["metrics"][0]["freshness"] = "stale"
        _, result = self.run_capture(fetcher=fetcher(responses(docs)))
        self.assertEqual(result["availability"], "available")
        self.assertEqual(result["data_readiness"], "attention_required")
        self.assertFalse(result["ready"])
        self.assertEqual(result["exit_code"], 1)
        self.assertIsNone(self.current()["last_ready"])

    def test_backend_outage_does_not_erase_source_data_readiness(self):
        _, result = self.run_capture(
            backend="https://evidence.example",
            fetcher=fetcher(failures={"backend-health"}),
        )
        self.assertEqual(result["source_availability"], "available")
        self.assertEqual(result["backend_availability"], "unavailable")
        self.assertEqual(result["data_readiness"], "checks_passed")
        self.assertEqual(result["exit_code"], 2)

    def test_wrong_release_is_available_but_not_ready(self):
        _, result = self.run_capture(
            backend="https://evidence.example", expected_release="different-release"
        )
        self.assertEqual(result["availability"], "available")
        self.assertEqual(result["release_identity"], "mismatch")
        self.assertEqual(result["exit_code"], 1)

    def test_backend_release_switch_between_calls_requires_attention(self):
        bodies = responses()
        bodies["backend-health"] = b'{"status":"ok","release_id":"different-release"}'
        _, result = self.run_capture(
            backend="https://evidence.example", fetcher=fetcher(bodies)
        )
        self.assertEqual(result["availability"], "available")
        self.assertEqual(result["release_identity"], "mismatch")
        self.assertFalse(result["ready"])

    def test_malformed_json_and_mcp_error_are_availability_failures(self):
        for name, raw in (
            ("atlas", b'{"value":1e999}'),
            (
                "funding-desk",
                b'{"jsonrpc":"2.0","id":"funding-desk","error":{"code":-1}}',
            ),
        ):
            bodies = responses()
            bodies[name] = raw
            _, result = self.run_capture(fetcher=fetcher(bodies))
            self.assertEqual(result["exit_code"], 2)
            self.assertEqual(result["data_readiness"], "not_evaluated")

    def test_tampered_capture_cannot_be_replayed(self):
        path, _ = self.run_capture()
        (path / "atlas.response").write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "hash or size mismatch"):
            capture.replay(path, self.output)

    def test_replay_rejects_a_different_implementation_or_policy(self):
        path, _ = self.run_capture()
        original = (path / "manifest.json").read_bytes()
        for key, replacement in (
            ("checker_source_sha256", "0" * 64),
            ("capture_tool_sha256", "0" * 64),
            ("publication_policy_sha256", "0" * 64),
            ("publication_calendar_sha256", "0" * 64),
            ("funding_horizon_sha256", "0" * 64),
            ("policy_id", "usd-funding-review-checks.v0"),
        ):
            with self.subTest(key=key):
                manifest = json.loads(original)
                manifest[key] = replacement
                (path / "manifest.json").write_bytes(capture.encoded(manifest))
                with self.assertRaisesRegex(
                    capture.ReplayPolicyMismatch, "use the original release"
                ):
                    capture.replay(path, self.output)
        (path / "manifest.json").write_bytes(original)
        review = json.loads((path / "review.json").read_bytes())
        review["policy_id"] = "usd-funding-review-checks.v0"
        changed = capture.encoded(review)
        (path / "review.json").write_bytes(changed)
        manifest = json.loads(original)
        manifest["artifact_sha256"]["review.json"] = capture.sha256(changed)
        (path / "manifest.json").write_bytes(capture.encoded(manifest))
        with self.assertRaises(capture.ReplayPolicyMismatch):
            capture.replay(path, self.output)

    def test_failed_capture_can_replay_under_the_original_implementation(self):
        path, original = self.run_capture(fetcher=fetcher(failures={"atlas"}))
        replay_path, result = capture.replay(path, self.output)
        self.assertEqual(original["exit_code"], 2)
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(
            (path / "review.json").read_bytes(),
            (replay_path / "review.json").read_bytes(),
        )

    def test_current_summary_failure_does_not_destroy_capture_or_previous_summary(self):
        first, _ = self.run_capture()
        previous = (self.output / "current.json").read_bytes()
        with patch.object(capture.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.run_capture()
        self.assertEqual(previous, (self.output / "current.json").read_bytes())
        self.assertEqual(
            len(list((self.output / "captures").glob("*/manifest.json"))), 2
        )
        self.assertTrue((first / "manifest.json").is_file())
        self.assertFalse(list(self.output.glob(".current-*.tmp")))

    def test_csv_preserves_zero_suppresses_restricted_parent_and_formulas(self):
        for level in ("document", "section", "metric"):
            docs = captures()
            desk = docs[0]
            row = desk["sections"][0]["metrics"][0]
            row["source"] = '=HYPERLINK("https://example.invalid")'
            node = (
                desk
                if level == "document"
                else desk["sections"][0]
                if level == "section"
                else row
            )
            node["rights_status"] = "derived_only"
            path, _ = self.run_capture(fetcher=fetcher(responses(docs)))
            with (path / "funding-observations.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 9)
            self.assertEqual(rows[0]["value"], "")
            self.assertEqual(rows[0]["value_state"], "restricted")
            self.assertTrue(rows[0]["source"].startswith("'="))
            if level == "metric":
                self.assertEqual(rows[1]["value"], "0")

    def test_duplicate_or_missing_values_remain_blank(self):
        docs = captures()
        metrics = docs[0]["sections"][0]["metrics"]
        metrics.append(copy.deepcopy(metrics[0]))
        metrics[1]["value"] = None
        path, _ = self.run_capture(fetcher=fetcher(responses(docs)))
        rows = list(
            csv.DictReader(io.StringIO((path / "funding-observations.csv").read_text()))
        )
        self.assertEqual(rows[0]["value_state"], "duplicate")
        self.assertEqual(rows[0]["value"], "")
        self.assertEqual(rows[1]["value"], "")

    def test_oversized_response_is_bounded_and_cannot_count_as_available(self):
        opener = FakeOpener(FakeResponse(b"x" * (capture.MAX_BYTES + 100)))
        receipt, raw, _ = capture.fetch("atlas", capture.ORIGIN, opener=opener)
        self.assertEqual(len(raw), capture.MAX_BYTES + 1)
        self.assertFalse(receipt["complete"])
        self.assertIn("exceeds 2 MiB", receipt["error"])
        self.assertEqual(receipt["sha256"], capture.sha256(raw))

    def test_http_failure_keeps_exact_body_and_network_failure_records_exception(self):
        raw = b'{"error":"not available"}\n'
        error = urllib.error.HTTPError(
            capture.ORIGIN,
            503,
            "unavailable",
            {"Content-Type": "application/json"},
            io.BytesIO(raw),
        )
        receipt, saved, _ = capture.fetch(
            "atlas", capture.ORIGIN, opener=FakeOpener(error)
        )
        self.assertEqual(saved, raw)
        self.assertEqual(receipt["http_status"], 503)
        self.assertEqual(receipt["error"], "http_error")
        receipt, saved, _ = capture.fetch(
            "atlas", capture.ORIGIN, opener=FakeOpener(urllib.error.URLError("offline"))
        )
        self.assertEqual(saved, b"")
        self.assertFalse(receipt["complete"])
        self.assertIn("URLError", receipt["error"])

    def test_sse_reply_and_text_payload_decode(self):
        desk = captures()[0]
        reply = {
            "jsonrpc": "2.0",
            "id": "funding-desk",
            "result": {"content": [{"type": "text", "text": json.dumps(desk)}]},
        }
        raw = ("event: message\r\ndata: " + json.dumps(reply) + "\r\n\r\n").encode()
        self.assertEqual(capture.decode_desk(raw), desk)
        with self.assertRaises(ValueError):
            capture.decode_desk(raw + raw)

    def test_redirects_and_unsafe_backend_origins_rejected(self):
        self.assertIsNone(capture.NoRedirect().redirect_request(None, None, None, None))
        for url in (
            "http://example.com",
            "https://user:pass@example.com",
            "https://example.com/../api",
            "https://example.com?secret=x",
        ):
            with self.assertRaises(ValueError):
                capture.backend_origin(url)
        self.assertEqual(
            capture.backend_origin("http://127.0.0.1:8000/"), "http://127.0.0.1:8000"
        )
        self.assertEqual(
            capture.backend_origin("https://api.seiche.info/openbb/"),
            "https://api.seiche.info/openbb",
        )


if __name__ == "__main__":
    unittest.main()
