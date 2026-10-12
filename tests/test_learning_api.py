"""Optional ingestion never exposes local administration or another tenant."""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from financial_evidence.learning import LearningStore
from financial_evidence.learning.client import LearningDeliveryError, RemoteLearningClient, _NoRedirect


@unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"), "optional workspace dependencies required")
class LearningAPITests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from financial_evidence.learning.api import create_app
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1_800_000_000
        self.store = LearningStore(Path(self.temp.name) / "state", clock=lambda: self.now)
        self.enrollment = self.store.enroll(purposes=["measurement"], policy_version="v1", expires_at=self.now + 10000)
        self.token = self.enrollment["credential"]
        self.client = TestClient(create_app(self.store))
        self.addCleanup(self.client.close)
        self.headers = {"Authorization": "Bearer " + self.token}
        self.event = {"id": "event1", "product": "seiche", "tool": "funding", "task": "funding_review",
                      "occurred_at": self.now, "duration_ms": 2, "status": "success", "mode": "unknown"}

    def test_optin_bearer_required_and_admin_not_exposed(self):
        self.assertTrue(self.client.get("/health").json()["explicit_enrollment_required"])
        self.assertEqual(self.client.post("/v1/events", json=self.event).status_code, 401)
        self.assertEqual(self.client.post("/v1/events", headers=self.headers, json=self.event).status_code, 200)
        for route in ("/v1/enroll", "/v1/admit", "/v1/review-outcome", "/v1/export", "/v1/verify-organisation"):
            self.assertEqual(self.client.post(route, headers=self.headers, json={}).status_code, 404)
        self.assertNotIn(self.token, self.client.get("/v1/me", headers=self.headers).text)
        self.assertEqual(self.client.get("/v1/me", headers=self.headers).headers["cache-control"], "no-store")

    def test_idle_service_runs_retention_without_traffic(self):
        from fastapi.testclient import TestClient
        from financial_evidence.learning.api import create_app
        self.store.record_tool(self.token, self.event)
        with TestClient(create_app(self.store, purge_interval=.01)):
            self.now += 10001
            deadline = time.monotonic() + 2
            remaining = 1
            while remaining and time.monotonic() < deadline:
                time.sleep(.02)
                with self.store.connection() as db:
                    remaining = db.execute("SELECT count(*) FROM records").fetchone()[0]
            self.assertEqual(remaining, 0)

    def test_retention_failure_marks_degraded_then_recovers_without_secret_logging(self):
        from fastapi.testclient import TestClient
        from financial_evidence.learning.api import create_app
        broken = threading.Event()
        failure_entered = threading.Event()
        release_failure = threading.Event()
        original = self.store.expire
        def flaky():
            if broken.is_set():
                failure_entered.set()
                if not release_failure.wait(timeout=2):
                    raise AssertionError("Test did not release the failing retention check")
                raise OSError("PRIVATE-CUSTOMER-CREDENTIAL-DO-NOT-LOG")
            return original()
        app = create_app(self.store, purge_interval=.02)
        with patch.object(self.store, "expire", side_effect=flaky), TestClient(app) as client:
            initial = client.get("/health")
            self.assertEqual(initial.status_code, 200)
            with self.assertLogs("financial_evidence.learning.api", level="WARNING") as logs:
                broken.set()
                try:
                    # The serial worker cannot enter its next expire call until
                    # any prior healthy check has recorded its success. Hold
                    # this failing call while capturing that settled baseline.
                    self.assertTrue(failure_entered.wait(timeout=2))
                    baseline = client.get("/health")
                    self.assertEqual(baseline.status_code, 200)
                    before = baseline.json()["retention"]["last_successful_check_at"]
                finally:
                    release_failure.set()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    response = client.get("/health")
                    if response.status_code == 503:
                        break
                    time.sleep(.01)
                self.assertEqual(response.status_code, 503)
                self.assertTrue(response.json()["retention"]["worker_running"])
                self.assertEqual(response.json()["retention"]["last_successful_check_at"], before)
                broken.clear()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    response = client.get("/health")
                    if response.status_code == 200:
                        break
                    time.sleep(.01)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["retention"]["consecutive_failures"], 0)
            self.assertGreaterEqual(response.json()["retention"]["last_successful_check_at"], before)
            self.assertNotIn("PRIVATE-CUSTOMER", " ".join(logs.output))

    def test_retention_startup_failure_retries_and_database_work_uses_worker_thread(self):
        from fastapi.testclient import TestClient
        from financial_evidence.learning.api import create_app
        attempts = []
        original = self.store.expire
        def initially_broken():
            attempts.append(1)
            if len(attempts) == 1:
                raise OSError("private-startup-error")
            return original()
        app = create_app(self.store, purge_interval=.04)
        @app.get("/testing-loop")
        async def loop_thread():
            return {"thread": threading.get_ident()}
        with patch.object(self.store, "expire", side_effect=initially_broken), TestClient(app) as client:
            self.assertEqual(client.get("/health").status_code, 503)
            deadline = time.monotonic() + 2
            while client.get("/health").status_code != 200 and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertEqual(client.get("/health").status_code, 200)
            loop_id = client.get("/testing-loop").json()["thread"]
            worker_ids = []
            original_report = self.store.report
            def report(*args):
                worker_ids.append(threading.get_ident())
                return original_report(*args)
            with patch.object(self.store, "report", side_effect=report):
                self.assertEqual(client.get("/v1/report", headers=self.headers).status_code, 200)
            self.assertTrue(worker_ids)
            self.assertNotEqual(worker_ids[0], loop_id)

    def test_payload_limits_and_no_raw_capture(self):
        self.assertEqual(self.client.post("/v1/events", headers=self.headers, json={**self.event, "prompt": "private"}).status_code, 422)
        self.assertEqual(self.client.post("/v1/events", headers={**self.headers, "Content-Type": "application/json"}, content=b" " * 65537).status_code, 413)
        self.assertEqual(self.client.post("/v1/events", headers=self.headers, content="{}",).status_code, 415)
        self.assertEqual(self.store.report(self.token)["requests"], 0)

    def test_withdraw_and_delete_own_records_only(self):
        other = self.store.enroll(purposes=["measurement"], policy_version="v1", expires_at=self.now + 10000)
        self.client.post("/v1/events", headers=self.headers, json=self.event)
        second_headers = {"Authorization": "Bearer " + other["credential"]}
        self.assertEqual(self.client.get("/v1/report", headers=second_headers).json()["requests"], 0)
        self.assertEqual(self.client.post("/v1/withdraw", headers=self.headers, json={"purposes": ["measurement"], "delete": True}).status_code, 200)
        self.assertEqual(self.client.post("/v1/events", headers=self.headers, json=self.event).status_code, 403)
        self.assertEqual(self.client.delete("/v1/me", headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/v1/me", headers=self.headers).status_code, 401)
        self.assertEqual(self.client.get("/v1/me", headers=second_headers).status_code, 200)


class RemoteClientTests(unittest.TestCase):
    def test_remote_requests_identify_the_learning_client(self):
        client = RemoteLearningClient("https://example.test/learning", "x" * 43)
        with patch.object(client._opener, "open", return_value=io.BytesIO(b'{}')) as opened:
            self.assertEqual(client.report(), {})
        request = opened.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), "Financial-Evidence-Learning/0.1")
        self.assertEqual(request.full_url, "https://example.test/learning/v1/report")

    def test_construction_is_quiet_and_transport_requires_secure_destination(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("network must not run")):
            RemoteLearningClient("https://example.test/learning", "x" * 43)
        for endpoint in ("http://example.test", "https://user:password@example.test", "https://example.test/?token=private", "file:///tmp/data"):
            with self.assertRaises(ValueError):
                RemoteLearningClient(endpoint, "x" * 43)

    def test_failure_is_explicit_and_does_not_echo_credentials(self):
        client = RemoteLearningClient("https://example.test/learning", "x" * 43)
        with patch.object(client._opener, "open", side_effect=OSError("secret-upstream")):
            with self.assertRaises(LearningDeliveryError) as raised:
                client.record_tool({"id": "bounded"})
        self.assertNotIn("secret-upstream", str(raised.exception))
        self.assertNotIn("x" * 43, str(raised.exception))
        with self.assertRaises(LearningDeliveryError):
            _NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.test")


if __name__ == "__main__":
    unittest.main()
