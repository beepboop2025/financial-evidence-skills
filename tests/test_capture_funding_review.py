"""Operator evidence survives failures and can be replayed without the network."""

from contextlib import redirect_stderr
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

    def snapshot_rechecks(self, documents, **kwargs):
        fakes = [fetcher(responses(docs)) for docs in documents]
        index = -1

        def sequential(name, url, **options):
            nonlocal index
            if name == "mcp-initialize":
                index += 1
            return fakes[min(index, len(fakes) - 1)](name, url, **options)

        with patch.object(capture.time, "sleep") as sleep:
            result = capture.capture_with_snapshot_rechecks(
                self.output, snapshot_rechecks=2, fetcher=sequential, **kwargs
            )
        return result, sleep

    def old_snapshot(self):
        docs = captures()
        docs[0]["snapshot_generated_at"] = "2026-09-28T18:00:00Z"
        docs[1]["generated_at"] = docs[2]["generated_at"] = "2026-09-28T18:00:00Z"
        return docs

    def test_snapshot_recheck_keeps_failure_and_accepts_only_new_passing_capture(self):
        (latest, result, attempts), sleep = self.snapshot_rechecks(
            [self.old_snapshot(), captures()]
        )
        self.assertTrue(result["ready"])
        self.assertEqual(len(attempts), 2)
        sleep.assert_called_once_with(45)
        first = json.loads((attempts[0] / "manifest.json").read_bytes())
        self.assertFalse(first["ready"])
        self.assertEqual(first["max_snapshot_age_seconds"], 900)
        self.assertEqual(self.current()["latest"]["capture_id"], latest.name)
        self.assertEqual(self.current()["measurement"]["probes"], 2)
        before = (self.output / "current.json").read_bytes()
        _, replayed = capture.replay(attempts[0], self.output)
        self.assertFalse(replayed["ready"])
        self.assertEqual(before, (self.output / "current.json").read_bytes())

    def test_snapshot_rechecks_stop_after_three_failed_captures(self):
        (latest, result, attempts), sleep = self.snapshot_rechecks([self.old_snapshot()])
        self.assertFalse(result["ready"])
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(self.current()["latest"]["capture_id"], latest.name)
        self.assertIsNone(self.current()["last_ready"])

    def board_rechecks(self, generation_at, *, after=None, probe_raw=None, elapsed_at_first=0):
        # A 03:03 UTC capture was stale; the next board completed 199 seconds
        # after evaluation, outside the previous two fixed 45-second waits.
        old = list(self.old_snapshot())
        old[1] = captures()[1]  # the independent atlas generation is fresh
        fresh = captures()
        capture_calls, health_probes = [], []
        elapsed = 0

        def advance(seconds):
            nonlocal elapsed
            elapsed += seconds

        def read(name, url, **options):
            if name == "health" and "payload" not in options:
                health_probes.append(elapsed)
                bodies = responses(fresh if elapsed >= generation_at else old)
                if probe_raw is not None:
                    bodies["health"] = probe_raw
                return fetcher(bodies)(name, url, **options)
            if name == "mcp-initialize":
                capture_calls.append(elapsed)
                if len(capture_calls) == 1:
                    advance(elapsed_at_first)
            docs = old if len(capture_calls) == 1 else after or fresh
            return fetcher(responses(docs))(name, url, **options)

        trace = io.StringIO()
        with redirect_stderr(trace), patch.object(capture.time, "sleep", side_effect=advance), \
             patch.object(capture.time, "monotonic", side_effect=lambda: elapsed):
            _, result, attempts = capture.capture_with_snapshot_rechecks(
                self.output, snapshot_rechecks=2, fetcher=read,
                backend="https://evidence.example", timeout=30,
            )
        recorded = json.loads(trace.getvalue())
        self.assertEqual(recorded["polls"], len(health_probes))
        self.assertEqual(recorded["capture_id"], attempts[0].name)
        self.assertEqual(recorded["outcome"], "advanced" if len(attempts) > 1 else "no_advance_within_budget")
        return result, attempts, capture_calls, health_probes

    def test_board_wait_spans_late_publication_without_duplicate_mcp(self):
        result, attempts, calls, probes = self.board_rechecks(199)
        self.assertTrue(result["ready"])
        self.assertEqual(calls, [0, 210])
        self.assertEqual(probes, list(range(15, 211, 15)))
        first = json.loads((attempts[0] / "review.json").read_bytes())
        self.assertEqual({i["subject"] for i in first["issues"]}, {"desk", "desk_history", "health"})
        self.assertEqual(self.current()["measurement"]["probes"], 2)

    def test_board_wait_exhausts_without_charging_another_full_capture(self):
        for raw in (None, b'{"generated_at":"2099-01-01T00:00:00Z"}', b'null', b'bad'):
            with self.subTest(raw=raw):
                result, attempts, calls, probes = self.board_rechecks(1000, probe_raw=raw)
                self.assertFalse(result["ready"])
                self.assertEqual(len(attempts), 1)
                self.assertEqual(calls, [0])
                self.assertLessEqual(probes[-1], 405)

    def test_board_wait_reserves_full_capture_time_after_a_slow_first_attempt(self):
        result, attempts, _, probes = self.board_rechecks(410, elapsed_at_first=380)
        self.assertFalse(result["ready"])
        self.assertEqual(len(attempts), 1)
        self.assertEqual(probes, [395])

    def test_health_advance_cannot_make_a_failed_full_review_ready(self):
        invalid = captures()
        invalid[0]["sections"][0]["metrics"][0]["freshness"] = "stale"
        result, attempts, calls, _ = self.board_rechecks(15, after=invalid)
        self.assertFalse(result["ready"])
        self.assertEqual(len(attempts), 2)
        self.assertEqual(calls, [0, 15])

    def test_snapshot_recheck_does_not_retry_another_data_failure(self):
        docs = self.old_snapshot()
        docs[0]["sections"][0]["metrics"][0]["freshness"] = "stale"
        (_, result, attempts), sleep = self.snapshot_rechecks([docs, captures()])
        self.assertFalse(result["ready"])
        self.assertEqual(len(attempts), 1)
        sleep.assert_not_called()

    def test_snapshot_recheck_does_not_retry_identity_mismatch(self):
        (_, result, attempts), sleep = self.snapshot_rechecks(
            [self.old_snapshot(), captures()], backend="https://evidence.example",
            expected_release="wrong-release",
        )
        self.assertEqual(result["release_identity"], "mismatch")
        self.assertEqual(len(attempts), 1)
        sleep.assert_not_called()

    def test_passing_snapshot_needs_no_recheck(self):
        (_, result, attempts), sleep = self.snapshot_rechecks([captures()])
        self.assertTrue(result["ready"])
        self.assertEqual(len(attempts), 1)
        sleep.assert_not_called()

    def boundary(self, before="2026-09-28T19:15:00Z", after="2026-09-28T19:16:00Z"):
        directory = self.output / "boundary"
        directory.mkdir(exist_ok=True)
        manifest = {"evaluated_at": NOW, "artifact_sha256": {}}
        for name, at in (("desk.json", before), ("desk-history.response", after)):
            document = {"schema": "seiche.money-market-desk.v1", "asof": "2026-09-25",
                        "snapshot_generated_at": at,
                        "methodology": {"evidence_horizon": capture.funding_horizon.HORIZON_RULE}}
            raw = capture.encoded(document)
            (directory / name).write_bytes(raw)
            manifest["artifact_sha256"][name] = capture.sha256(raw)
        issues = [{"code": "common_horizon_not_verified", "subject": "desk.evidence_horizon"}]
        return directory, manifest, issues

    def test_forward_snapshot_boundary_can_be_rechecked_but_not_accepted(self):
        directory, manifest, issues = self.boundary()
        self.assertTrue(capture.snapshot_recheckable(directory, manifest, issues))
        self.assertTrue(capture.snapshot_recheckable(directory, manifest, issues +
            [{"code": "snapshot_too_old", "subject": "desk"}]))
        self.assertFalse(capture.snapshot_recheckable(directory, manifest, issues +
            [{"code": "required_value_unavailable", "subject": "policy.sofr"}]))

    def test_same_backward_and_future_snapshots_are_not_boundary_retries(self):
        for before, after in (("2026-09-28T19:15:00Z", "2026-09-28T19:15:00Z"),
                              ("2026-09-28T19:16:00Z", "2026-09-28T19:15:00Z"),
                              ("2026-09-28T19:15:00Z", "2026-09-28T19:18:00Z")):
            with self.subTest(before=before, after=after):
                self.assertFalse(capture.snapshot_recheckable(*self.boundary(before, after)))

    def test_tampered_snapshot_cannot_authorize_recheck(self):
        directory, manifest, issues = self.boundary()
        (directory / "desk-history.response").write_text("{}")
        with self.assertRaisesRegex(ValueError, "retained snapshot changed"):
            capture.snapshot_recheckable(directory, manifest, issues)

    def test_mcp_and_full_history_reads_are_adjacent(self):
        client = fetcher()
        self.run_capture(fetcher=client)
        names = [row[0] for row in client.calls]
        self.assertEqual(names[names.index("funding-desk")+1], "desk-history")

    def test_snapshot_recheck_count_cannot_be_unbounded(self):
        for value in (-1, 3, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                capture.capture_with_snapshot_rechecks(self.output, snapshot_rechecks=value)

    def test_replay_cannot_request_live_snapshot_rechecks(self):
        with patch.object(capture, "replay") as replay:
            with patch("sys.stdout", new_callable=io.StringIO):
                code = capture.main(["--output-dir", str(self.output), "--replay", "old", "--snapshot-rechecks", "2"])
        self.assertEqual(code, 2)
        replay.assert_not_called()

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

    def test_only_exact_atlas_route_accepts_a_larger_response(self):
        raw = b" " * (capture.MAX_BYTES + 100)
        atlas_url = capture.ORIGIN + "/api/v2/money-markets"
        for name, url, allowed in [("atlas", atlas_url, True), ("health", atlas_url, False),
                                   ("atlas", atlas_url + "?other=1", False),
                                   ("atlas", capture.ORIGIN + "/api/money-markets", False)]:
            with self.subTest(name=name, url=url):
                receipt, saved, _ = capture.fetch(name, url, opener=FakeOpener(FakeResponse(raw)))
                self.assertEqual(receipt["complete"], allowed)
                self.assertEqual(len(saved), len(raw) if allowed else capture.MAX_BYTES + 1)
        receipt, saved, _ = capture.fetch("atlas", atlas_url, opener=FakeOpener(FakeResponse(b" " * (capture.ATLAS_MAX_BYTES + 10))))
        self.assertFalse(receipt["complete"])
        self.assertEqual(len(saved), capture.ATLAS_MAX_BYTES + 1)

    def test_large_atlas_capture_replays_exactly_with_explicit_local_reader_limit(self):
        docs = captures(); docs[1]["test_padding"] = "x" * capture.MAX_BYTES
        raw = responses(docs)
        path, original = self.run_capture(fetcher=fetcher(raw))
        self.assertEqual(original["availability"], "available")
        replay_path, replayed = capture.replay(path, self.output)
        self.assertEqual(original["data_readiness"], replayed["data_readiness"])
        self.assertEqual((path / "review.json").read_bytes(), (replay_path / "review.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "exceeds 2 MiB"):
            capture.load_document(path / "atlas.response")
        loaded, digest = capture.load_document(path / "atlas.response", max_bytes=capture.ATLAS_MAX_BYTES)
        self.assertEqual(loaded, docs[1]); self.assertEqual(digest, capture.sha256(raw["atlas"]))

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
