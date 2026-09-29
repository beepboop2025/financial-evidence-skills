"""Automation failure paths: stale conditional reuse, atomic cursor and honest attribution."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys
import asyncio
from unittest.mock import patch

import test_institutional as fixtures
from test_institutional import AT, PID, csv_bytes, fixture
from financial_evidence import application_usage as usage
from financial_evidence import institutional as store

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    from fastapi.testclient import TestClient
    from financial_evidence.institutional_api import create_app
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "optional workspace dependencies")
class ApiTests(unittest.TestCase):
    setUp = fixtures.ArchiveTests.setUp
    archive = fixtures.ArchiveTests.archive

    def client(self):
        self.archive()
        clock = patch.object(usage, "now", return_value=AT)
        clock.start()
        self.addCleanup(clock.stop)
        client = TestClient(create_app(self.root, self.events))
        self.addCleanup(client.close)
        return client

    def enroll(self, client, **kwargs):
        response = client.post(
            "/v1/applications", json={"measurement_consent": True}, **kwargs
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_current_contract_and_conditional_identity(self):
        client = self.client()
        first = client.get("/v1/funding/latest")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.json()["observations"]), 9)
        self.assertEqual(
            first.headers["etag"], '"' + hashlib.sha256(first.content).hexdigest() + '"'
        )
        second = client.get(
            "/v1/funding/latest",
            headers={"If-None-Match": "W/" + first.headers["etag"]},
        )
        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.content, b"")
        self.assertIn("must-revalidate", second.headers["cache-control"])
        self.assertIn("authorization", second.headers["vary"].lower())

    def test_stale_or_failed_latest_cannot_receive_304(self):
        client = self.client()
        etag = client.get("/v1/funding/latest").headers["etag"]
        with patch.object(store, "now", return_value="2026-09-29T12:30:00Z"):
            self.assertEqual(
                client.get(
                    "/v1/funding/latest", headers={"If-None-Match": etag}
                ).status_code,
                503,
            )
        self.archive(fail="/api/v1/funding-review")
        self.assertEqual(
            client.get(
                "/v1/funding/latest", headers={"If-None-Match": "*"}
            ).status_code,
            503,
        )

    def test_corrupt_artifact_cannot_receive_304(self):
        client = self.client()
        etag = client.get("/v1/funding/latest").headers["etag"]
        (self.root / "packets" / PID / "observations.csv").write_text("bad")
        self.assertEqual(
            client.get(
                "/v1/funding/latest", headers={"If-None-Match": etag}
            ).status_code,
            503,
        )

    def test_invalid_or_revoked_credentials_never_receive_cached_success(self):
        client = self.client()
        application = self.enroll(client)
        auth = {"Authorization": "Bearer " + application["token"]}
        first = client.get("/v1/funding/latest", headers=auth)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(
            client.delete("/v1/applications/current", headers=auth).status_code, 200
        )
        self.assertEqual(
            client.get(
                "/v1/funding/latest",
                headers=dict(auth, **{"If-None-Match": first.headers["etag"]}),
            ).status_code,
            401,
        )
        self.assertEqual(
            client.get(
                "/v1/funding/latest",
                headers={"Authorization": "Bearer invalid", "If-None-Match": "*"},
            ).status_code,
            401,
        )
        self.assertEqual(client.delete("/v1/applications/current").status_code, 401)
        with usage.connect(self.events) as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM completions").fetchone()[0], 0
            )

    def test_enrollment_requires_consent_and_does_not_prove_external_ownership(self):
        client = self.client()
        for value in (False, 1, "true"):
            self.assertEqual(
                client.post(
                    "/v1/applications", json={"measurement_consent": value}
                ).status_code,
                400,
            )
        self.assertEqual(
            client.post(
                "/v1/applications", json={"measurement_consent": True, "external": True}
            ).status_code,
            400,
        )
        self.assertEqual(
            client.post(
                "/v1/applications",
                headers={"Origin": "https://foreign.invalid"},
                json={"measurement_consent": True},
            ).status_code,
            403,
        )
        application = self.enroll(client)
        self.assertEqual(application["classification"], "unverified")
        self.assertNotIn(
            application["token"].encode(),
            (self.events / "applications.sqlite").read_bytes(),
        )

    def test_operator_events_stay_excluded_and_repeats_are_deduplicated(self):
        client = self.client()
        application = self.enroll(client, headers={"X-Traffic-Class": "synthetic"})
        auth = {"Authorization": "Bearer " + application["token"]}
        first = client.get("/v1/funding/latest", headers=auth)
        client.get("/v1/funding/latest", headers=auth)
        client.get(
            "/v1/funding/latest",
            headers=dict(auth, **{"If-None-Match": first.headers["etag"]}),
        )
        report = usage.report(self.events)
        self.assertEqual(
            report["classes"]["internal"]["deduplicated_data_responses"], 1
        )
        self.assertEqual(
            report["classes"]["external_verified"]["applications_with_data_responses"],
            0,
        )
        self.assertEqual(report["classes"]["internal"]["retention"]["7"]["rate"], None)

    def test_changes_are_bound_to_cursor_and_current_packet(self):
        client = self.client()
        other = "20260929T120000.000000Z-" + "c" * 32
        review, _ = fixture(other)
        review["results"][0]["value"] = 1.5
        self.archive(review=review, csv_raw=csv_bytes(review["results"]))
        result = client.get(
            "/v1/funding/changes", params={"since": PID, "until": other}
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(
            result.json()["changes"][0]["kind"], "same_date_observation_changed"
        )
        self.assertIn("not_confirmed_publisher", result.json()["scope"])
        self.assertEqual(
            client.get(
                "/v1/funding/changes", params={"since": PID, "until": PID}
            ).status_code,
            409,
        )
        self.assertEqual(
            client.get("/v1/funding/changes", params={"since": "../other"}).status_code,
            400,
        )
        self.assertEqual(
            client.get(
                "/v1/funding/changes", params={"since": other.replace("c", "d")}
            ).status_code,
            404,
        )

    def test_conditional_headers_are_bounded(self):
        client = self.client()
        self.assertEqual(
            client.get(
                "/v1/funding/latest", headers={"If-None-Match": "x" * 1025}
            ).status_code,
            431,
        )

    def test_openbb_template_resolves_the_same_checked_observations(self):
        client = self.client()
        widget = client.get("/widgets.json").json()["funding_automation"]
        response = client.get(
            "/" + widget["endpoint"], headers={"Origin": "https://pro.openbb.co"}
        )
        self.assertEqual(
            response.headers["access-control-allow-origin"], "https://pro.openbb.co"
        )
        self.assertEqual(len(response.json()[widget["data"]["dataKey"]]), 9)
        placement = client.get("/apps.json").json()[0]["tabs"]["funding"]["layout"][0]
        self.assertEqual(placement["i"], "funding_automation")


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_eligible_retention_does_not_invent_new_cohorts(self):
        with patch.object(usage, "now", return_value="2026-09-01T12:00:00Z"):
            app = usage.enroll(self.root, {"measurement_consent": True}, {})
            identity = usage.identify(self.root, "Bearer " + app["token"], {})
            usage.record(self.root, identity, PID)
            self.assertIsNone(
                usage.report(self.root)["classes"]["unverified"]["retention"]["7"][
                    "rate"
                ]
            )
        with patch.object(usage, "now", return_value="2026-09-08T12:00:00Z"):
            usage.record(self.root, identity, PID)
            self.assertEqual(
                usage.report(self.root)["classes"]["unverified"]["retention"]["7"][
                    "eligible_applications"
                ],
                0,
            )
        with patch.object(usage, "now", return_value="2026-09-09T00:00:00Z"):
            report = usage.report(self.root)["classes"]["unverified"]
            self.assertEqual(
                report["retention"]["7"],
                {"eligible_applications": 1, "returned_on_day": 1, "rate": 1.0},
            )
            self.assertEqual(report["retention"]["30"]["eligible_applications"], 0)

    def test_reviewed_classification_is_forward_only(self):
        app = usage.enroll(self.root, {"measurement_consent": True}, {})
        identity = usage.identify(self.root, "Bearer " + app["token"], {})
        usage.record(self.root, identity, PID)
        with self.assertRaises(ValueError):
            usage.classify(self.root, app["application_id"], "external_verified")
        evidence = self.root / "review.json"
        evidence.write_text(
            json.dumps(
                {
                    "application_id": app["application_id"],
                    "independent_operator": True,
                    "basis": "Synthetic test review",
                }
            )
        )
        usage.classify(self.root, app["application_id"], "external_verified", evidence)
        self.assertEqual(
            usage.report(self.root)["classes"]["external_verified"][
                "deduplicated_data_responses"
            ],
            0,
        )
        excluded = usage.identify(
            self.root, "Bearer " + app["token"], {"x-traffic-class": "synthetic"}
        )
        usage.record(self.root, excluded, PID)
        self.assertEqual(
            usage.report(self.root)["classes"]["external_verified"][
                "deduplicated_data_responses"
            ],
            0,
        )

    def test_expiry_purges_data_without_new_client_requests(self):
        with patch.object(usage, "now", return_value="2026-01-01T12:00:00Z"):
            app = usage.enroll(self.root, {"measurement_consent": True}, {})
            identity = usage.identify(self.root, "Bearer " + app["token"], {})
            usage.record(self.root, identity, PID)
        with patch.object(usage, "now", return_value="2026-07-01T12:00:00Z"):
            self.assertEqual(
                usage.report(self.root)["classes"]["unverified"][
                    "deduplicated_data_responses"
                ],
                0,
            )
            with self.assertRaises(PermissionError):
                usage.identify(self.root, "Bearer " + app["token"], {})


@unittest.skipUnless(
    TestClient and (ROOT / "docs/funding/daily_job.py").exists(),
    "optional API and standalone template",
)
class DailyJobTests(unittest.TestCase):
    setUp = fixtures.ArchiveTests.setUp
    archive = fixtures.ArchiveTests.archive

    def setup_job(self):
        self.archive()
        self.client = TestClient(create_app(self.root, self.events))
        self.addCleanup(self.client.close)
        self.job = load("daily_job", ROOT / "docs/funding/daily_job.py")
        self.state = Path(self.tmp.name) / "client"

    def request(self, path, headers):
        response = self.client.get(path, headers=headers)
        return response.status_code, dict(response.headers), response.content

    def test_two_runs_reuse_verified_packet_and_conditional_cursor(self):
        self.setup_job()
        first = self.job.update(self.state, request=self.request, operator=True)
        before = (self.state / "cursor.json").read_bytes()
        second = self.job.update(self.state, request=self.request, operator=True)
        self.assertEqual((first["status"], second["status"]), ("updated", "unchanged"))
        self.assertEqual((self.state / "cursor.json").read_bytes(), before)

    def test_failed_new_download_preserves_prior_cursor(self):
        self.setup_job()
        self.job.update(self.state, request=self.request)
        before = (self.state / "cursor.json").read_bytes()
        other = "20260929T120000.000000Z-" + "d" * 32
        review, _ = fixture(other)
        self.archive(review=review)

        def corrupt(path, headers):
            if path.endswith("observations.csv"):
                return 200, {}, b"corrupt"
            return self.request(path, headers)

        with self.assertRaises(ValueError):
            self.job.update(self.state, request=corrupt)
        self.assertEqual((self.state / "cursor.json").read_bytes(), before)
        self.assertFalse((self.state / "packets" / other).exists())

    def test_local_corruption_prevents_conditional_reuse(self):
        self.setup_job()
        self.job.update(self.state, request=self.request)
        (self.state / "packets" / PID / "review.json").write_text("corrupt")
        with self.assertRaises(ValueError):
            self.job.update(
                self.state,
                request=lambda *args: self.fail(
                    "network must not conceal local corruption"
                ),
            )

    def test_stale_response_preserves_cursor(self):
        self.setup_job()
        self.job.update(self.state, request=self.request)
        before = (self.state / "cursor.json").read_bytes()
        with patch.object(store, "now", return_value="2026-09-29T12:30:00Z"):
            with self.assertRaises(ValueError):
                self.job.update(self.state, request=self.request)
        self.assertEqual((self.state / "cursor.json").read_bytes(), before)

    def test_successful_delta_is_saved_before_advancing(self):
        self.setup_job()
        self.job.update(self.state, request=self.request)
        other = "20260929T120000.000000Z-" + "d" * 32
        review, _ = fixture(other)
        review["results"][0]["value"] = 2
        self.archive(review=review, csv_raw=csv_bytes(review["results"]))
        result = self.job.update(self.state, request=self.request)
        change = json.loads(Path(result["changes"]).read_bytes())
        self.assertEqual((change["before"], change["after"]), (PID, other))
        self.assertEqual(
            json.loads((self.state / "cursor.json").read_bytes())["packet_id"], other
        )

    def test_agent_tool_uses_verified_client_and_returns_dates(self):
        self.setup_job()
        try:
            import mcp.server.fastmcp
        except ImportError:
            self.skipTest("optional MCP SDK")
        with patch.dict(sys.modules, {"daily_job": self.job}):
            agent = load("funding_agent", ROOT / "docs/funding/funding_agent.py")
        with patch.object(
            agent,
            "update",
            side_effect=lambda state: self.job.update(state, request=self.request),
        ):
            server = agent.create_server(self.state)
            self.assertEqual(
                [tool.name for tool in asyncio.run(server.list_tools())],
                ["funding_update"],
            )
            response = asyncio.run(server.call_tool("funding_update", {}))
            payload = (
                response[1]
                if isinstance(response, tuple)
                else json.loads(response[0].text)
            )
        self.assertEqual(len(payload["observations"]), 9)
        self.assertEqual(payload["review_asof"], "2026-09-25")


@unittest.skipUnless(
    (ROOT / "scripts/reconcile_funding_packet.py").exists(),
    "host reconciliation script",
)
class ReconciliationTests(unittest.TestCase):
    def test_missed_notification_and_unchanged_capture(self):
        guard = load("packet_guard", ROOT / "scripts/reconcile_funding_packet.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            archive = root / "archive"
            source.mkdir()
            archive.mkdir()
            (archive / "attempts").mkdir()
            (source / "current.json").write_text(
                json.dumps({"latest": {"capture_id": PID}})
            )
            self.assertTrue(guard.needs_refresh(source, archive))
            attempt = store.encoded({"probe": {"capture_id": PID}})
            (archive / "attempts" / ("a" * 32 + ".json")).write_bytes(attempt)
            (archive / "latest.json").write_text(
                json.dumps({"attempt_id": "a" * 32, "sha256": store.digest(attempt)})
            )
            self.assertFalse(guard.needs_refresh(source, archive))
            (source / "current.json").write_text(
                json.dumps({"latest": {"capture_id": PID.replace("a", "b")}})
            )
            self.assertTrue(guard.needs_refresh(source, archive))
            (archive / "attempts" / ("a" * 32 + ".json")).write_text("{}")
            with self.assertRaises(ValueError):
                guard.needs_refresh(source, archive)


if __name__ == "__main__":
    unittest.main()
