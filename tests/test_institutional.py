"""Failure-path proofs for research packets, history, sampling and consent."""

import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from financial_evidence import institutional as store
from financial_evidence import reliability
from financial_evidence.funding_archive import FIELDS, METRICS

AT = "2026-09-29T12:00:00+00:00"
PID = "20260929T115900.000000Z-" + "a" * 32


def fixture(identifier=PID):
    rows = []
    for metric in METRICS:
        rows.append(
            dict(
                zip(
                    FIELDS,
                    [
                        metric,
                        0.0,
                        "%" if metric in METRICS[:4] else "$B",
                        "2026-09-25",
                        "Synthetic test publisher",
                        "daily",
                        "fresh",
                        "available",
                        "2026-09-29T11:59:30+00:00",
                        "checks_passed",
                        "2026-09-25",
                        "common_sofr_iorb_horizon",
                        False,
                        None,
                        None,
                    ],
                )
            )
        )
    review = {
        "schema": "liquidity-lab.funding-review.v1",
        "capture_id": identifier,
        "captured_at": "2026-09-29T11:59:30+00:00",
        "ready": True,
        "available": True,
        "stale": False,
        "review_asof": "2026-09-25",
        "review_scope": "common_sofr_iorb_horizon",
        "latest_per_instrument": False,
        "age_seconds": 30,
        "issues": [],
        "data_readiness": "checks_passed",
        "observed_release": {"source_commit": reliability.SOURCE},
        "runtime_release": {"source_commit": reliability.SOURCE},
        "release_identity": "matched",
        "runtime_release_identity": "matched",
        "manifest_sha256": "b" * 64,
        "results": rows,
    }
    return review, csv_bytes(rows)


def csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    for original in rows:
        row = dict(
            original,
            latest_per_instrument="false",
            canonical_latest_asof=original["canonical_latest_asof"] or "",
            newer_observation_available="unknown"
            if original["newer_observation_available"] is None
            else str(original["newer_observation_available"]).lower(),
        )
        writer.writerow(row)
    return output.getvalue().encode()


def fetcher(review=None, csv_raw=None, fail=None):
    default, default_csv = fixture()
    review = default if review is None else review
    documents = {
        "/healthz": {"status": "ok", "release_id": reliability.RELEASE},
        "/api/v1/release": {
            "release_id": reliability.RELEASE,
            "source_commit": reliability.SOURCE,
        },
        "/api/v1/funding-review": review,
        "/packet-latest": {
            "ready": True,
            "packet": {"source_commit": reliability.SOURCE},
        },
    }

    def get(path):
        raw = (
            csv_raw or default_csv
            if path.endswith(".csv")
            else reliability.encoded(documents[path])
        )
        return {
            "http_status": 502 if path == fail else 200,
            "error": "http_error" if path == fail else None,
            "body_sha256": store.digest(raw),
            "elapsed_seconds": 0.05,
        }, raw

    return get


class ReliabilityTests(unittest.TestCase):
    def probe(self, **kwargs):
        with patch.object(reliability, "now", return_value=AT):
            return reliability.sample(
                perspective="github_external", trigger="schedule", run_id="1", **kwargs
            )[0]

    def test_real_readiness_requires_current_identity_and_age(self):
        self.assertTrue(self.probe(fetcher=fetcher())["ready"])
        for key, value in (
            ("age_seconds", 1201),
            ("age_seconds", -1),
            ("runtime_release_identity", "mismatch"),
            ("ready", False),
        ):
            review, _ = fixture()
            review[key] = value
            self.assertFalse(self.probe(fetcher=fetcher(review=review))["ready"])

    def test_upstream_failure_is_retained(self):
        value = self.probe(fetcher=fetcher(fail="/healthz"))
        self.assertFalse(value["available"])
        self.assertEqual(value["requests"]["health"]["http_status"], 502)

    def test_external_observer_checks_packet_delivery_too(self):
        self.assertTrue(
            self.probe(fetcher=fetcher(), include_packet_service=True)["ready"]
        )
        value = self.probe(
            fetcher=fetcher(fail="/packet-latest"), include_packet_service=True
        )
        self.assertFalse(value["available"])
        self.assertFalse(value["ready"])

    def test_missing_slots_and_manual_probes_are_not_uptime(self):
        one = self.probe(fetcher=fetcher())
        manual = dict(
            one,
            run_id="2",
            trigger="manual",
            observed_at="2026-09-29T12:15:00+00:00",
            finished_at="2026-09-29T12:15:01+00:00",
        )
        report = reliability.summarize(
            [one, manual], evaluated_at="2026-09-29T12:45:00+00:00"
        )["perspectives"]["github_external"]
        self.assertEqual(
            (
                report["expected_slots"],
                report["observed_slots"],
                report["missing_slots"],
            ),
            (3, 1, 2),
        )
        self.assertEqual(report["manual_samples"], 1)
        self.assertFalse(report["thirty_days_elapsed"])

    def test_failure_in_same_slot_is_not_overwritten_by_success(self):
        one = self.probe(fetcher=fetcher())
        two = dict(one, run_id="2", available=False, ready=False)
        report = reliability.summarize(
            [one, two], evaluated_at="2026-09-29T12:15:00+00:00"
        )["perspectives"]["github_external"]
        self.assertEqual(report["sampled_availability_pct"], 0)

    def test_future_and_conflicting_samples_are_rejected(self):
        one = self.probe(fetcher=fetcher())
        with self.assertRaises(ValueError):
            reliability.summarize([one], evaluated_at="2026-09-29T11:00:00+00:00")
        with self.assertRaises(ValueError):
            reliability.summarize([one, dict(one, ready=False)], evaluated_at=AT)

    def test_fault_domains_stay_separate(self):
        one = self.probe(fetcher=fetcher())
        two = dict(one, run_id="2", perspective="hetzner_same_host")
        report = reliability.summarize([one, two], evaluated_at=AT)["perspectives"]
        self.assertTrue(report["github_external"]["independent_host"])
        self.assertFalse(report["hetzner_same_host"]["independent_host"])


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "archive"
        self.events = Path(self.tmp.name) / "events"
        self.clock = patch.object(store, "now", return_value=AT)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.probe_clock = patch.object(reliability, "now", return_value=AT)
        self.probe_clock.start()
        self.addCleanup(self.probe_clock.stop)

    def archive(self, **kwargs):
        return store.archive_once(
            self.root,
            trigger="manual",
            fetcher=fetcher(**kwargs),
            builder=lambda review: (review, csv_bytes(review["results"]), []),
        )

    def test_packet_is_immutable_and_csv_verified(self):
        self.assertIsNone(self.archive()["error"])
        manifest, _review, csv_raw = store.packet(self.root, PID)
        self.assertEqual(
            manifest["artifacts"]["observations.csv"], store.digest(csv_raw)
        )
        original = (self.root / "packets" / PID / "manifest.json").read_bytes()
        self.archive()
        self.assertEqual(
            (self.root / "packets" / PID / "manifest.json").read_bytes(), original
        )
        self.assertEqual(store.history(self.root)["packet_count"], 1)

    def test_packet_binds_its_generator_separately_from_the_reference(self):
        import os

        with patch.dict(os.environ, {"FINANCIAL_EVIDENCE_SOURCE_COMMIT": "e" * 40}):
            self.archive()
        manifest, _, _ = store.packet(self.root, PID)
        self.assertEqual(manifest["producer_source_commit"], "e" * 40)
        self.assertEqual(manifest["source_commit"], reliability.SOURCE)
        for name, value in manifest["producer_modules_sha256"].items():
            self.assertEqual(
                value, store.digest(Path(store.__file__).with_name(name).read_bytes())
            )

    def test_as_of_does_not_backfill_capture_or_observation_date(self):
        self.archive()
        self.assertEqual(
            store.history(self.root, as_of="2026-09-29T11:59:59+00:00")["packet_count"],
            0,
        )
        self.assertEqual(store.history(self.root, as_of=AT)["packet_count"], 1)
        with self.assertRaises(ValueError):
            store.history(self.root, as_of="2027-01-01T00:00:00Z")

    def test_csv_race_and_outage_do_not_fall_back_to_prior_success(self):
        self.archive()
        review, _ = fixture()
        review["results"][0]["value"] = 999
        failed = self.archive(review=review)
        self.assertIsNotNone(failed["error"])
        self.assertFalse(failed["probe"]["ready"])
        self.assertTrue(failed["probe"]["workspace_ready"])
        self.assertFalse(store.latest(self.root)["available"])
        self.assertIsNone(store.latest(self.root)["packet"])
        self.archive(fail="/api/v1/funding-review")
        self.assertFalse(store.latest(self.root)["available"])
        self.assertEqual(store.history(self.root)["packet_count"], 1)

    def test_corruption_and_path_traversal_are_rejected(self):
        self.archive()
        with self.assertRaises(ValueError):
            store.packet(self.root, "../latest")
        path = self.root / "packets" / PID / "observations.csv"
        path.write_text("tampered")
        with self.assertRaises(ValueError):
            store.packet(self.root, PID)

    def test_changed_publisher_value_cannot_reuse_an_immutable_capture(self):
        self.archive()
        review, _ = fixture()
        review["results"][0]["value"] = 1.0
        result = self.archive(review=review, csv_raw=csv_bytes(review["results"]))
        self.assertIn("changed within reference capture", result["error"])
        self.assertFalse(store.latest(self.root)["available"])
        self.assertEqual(
            store.strict_json(store.packet(self.root, PID)[1])["results"][0]["value"], 0
        )

    def test_stopped_collector_becomes_stale(self):
        self.archive()
        with patch.object(store, "now", return_value="2026-09-29T13:00:00+00:00"):
            self.assertFalse(store.latest(self.root)["available"])

    def test_malformed_publisher_xml_or_zip_records_failed_attempt(self):
        self.archive()
        for error in (store.ParseError("bad XML"), store.BadZipFile("bad ZIP")):

            def fail(_, error=error):
                raise error

            attempt = store.archive_once(
                self.root, trigger="manual", fetcher=fetcher(), builder=fail
            )
            self.assertIsNotNone(attempt["error"])
            self.assertFalse(store.latest(self.root)["available"])

    def test_same_date_change_is_not_a_claim_of_publisher_revision(self):
        self.archive()
        other = "20260929T120000.000000Z-" + "c" * 32
        review, _ = fixture(other)
        review["results"][0]["value"] = 1.5
        self.archive(review=review, csv_raw=csv_bytes(review["results"]))
        diff = store.compare(self.root, PID, other)
        self.assertEqual(diff["changes"][0]["kind"], "same_date_observation_changed")
        self.assertIn("not_confirmed_publisher", diff["scope"])

    def body(self):
        return {
            "visitor": "d" * 32,
            "consent": True,
            "packet_id": PID,
            "kind": "packet_download",
            "traffic_class": "browser",
        }

    def test_consent_operator_exclusion_deduplication_and_erasure(self):
        self.archive()
        body = self.body()
        with self.assertRaises(ValueError):
            store.usage_event(self.events, self.root, dict(body, consent=False))
        self.assertFalse(
            store.usage_event(
                self.events, self.root, dict(body, traffic_class="operator")
            )["recorded"]
        )
        self.assertTrue(store.usage_event(self.events, self.root, body)["recorded"])
        self.assertFalse(store.usage_event(self.events, self.root, body)["recorded"])
        self.assertEqual(
            store.usage_report(self.events)["consented_download_events"], 1
        )
        db, _ = store.connect_events(self.events)
        visitor = db.execute("SELECT visitor FROM events").fetchone()[0]
        db.close()
        self.assertNotEqual(visitor, body["visitor"])
        store.usage_event(
            self.events,
            self.root,
            {"visitor": body["visitor"], "consent": True},
            forget=True,
        )
        self.assertEqual(
            store.usage_report(self.events)["consented_download_events"], 0
        )

    def test_usage_retention_expires_after_thirty_days(self):
        self.archive()
        store.usage_event(self.events, self.root, self.body())
        with patch.object(store, "now", return_value="2026-11-01T00:00:00Z"):
            self.assertEqual(
                store.usage_report(self.events)["consented_download_events"], 0
            )

    def test_api_restart_reads_same_packets_and_rejects_untrusted_events(self):
        try:
            from fastapi.testclient import TestClient

            from financial_evidence.institutional_api import create_app
        except ImportError:
            self.skipTest("optional workspace dependencies")
        self.archive()
        for _ in range(2):
            with TestClient(create_app(self.root, self.events)) as client:
                self.assertEqual(
                    client.get("/latest").json()["packet"]["packet_id"], PID
                )
                self.assertEqual(
                    client.post("/events", json=self.body()).status_code, 403
                )
                self.assertEqual(
                    client.post(
                        "/events", headers={"Origin": store.SITE}, json=self.body()
                    ).status_code,
                    200,
                )
                self.assertEqual(
                    client.post(
                        "/events",
                        headers={
                            "Origin": store.SITE,
                            "Content-Type": "application/json",
                        },
                        content="x" * 1025,
                    ).status_code,
                    413,
                )
                self.assertEqual(
                    client.get("/packets/" + PID + "/review.json").status_code, 200
                )


if __name__ == "__main__":
    unittest.main()
