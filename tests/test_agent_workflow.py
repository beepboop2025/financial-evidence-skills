"""Recurring workflow and delivery tests; all source and contributor traffic is local."""
import contextlib
import copy
import io
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
from email.message import Message
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
import unittest
from typing import TypedDict
from unittest.mock import patch

from financial_evidence import cli, research
from financial_evidence.agent_workflow import AgentWorkflow
from financial_evidence import agent_workflow
from financial_evidence.learning import contracts as c
from financial_evidence.learning.client import LearningDeliveryError, RemoteLearningClient
from financial_evidence.learning.store import LearningStore
from test_research_watch import capture
from test_trading_context import fresh_snapshot, NOW


class FakeLearning:
    destination_fingerprint = "a" * 64
    timeout = 5

    def __init__(self):
        self.calls = []
        self.failure = None
        self.wrong_receipt = False

    def _send(self, kind, value):
        self.calls.append((kind, copy.deepcopy(value)))
        if self.failure:
            raise self.failure
        return {"id": value["id"], "sha256": "b" * 64 if self.wrong_receipt else c.digest(value)}

    def record_tool(self, value):
        return self._send("tool", value)

    def record_decision(self, value):
        return self._send("decision", value)

    def record_outcome(self, value):
        return self._send("outcome", value)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = NOW
        self.learning = FakeLearning()
        self.context = fresh_snapshot()
        self.source = capture()
        self.fetches = []
        self.root = Path(self.temp.name) / "journal"
        self.workflow = self.new_workflow()

    def new_workflow(self, **kwargs):
        return AgentWorkflow(self.root, clock=lambda: self.now, mode="paper",
                             context_fetcher=self.context_fetch, review_fetcher=self.review_fetch, **kwargs)

    def context_fetch(self, **kwargs):
        self.fetches.append(("context", kwargs))
        return copy.deepcopy(self.context)

    def review_fetch(self, *args, **kwargs):
        self.fetches.append(("evidence", kwargs))
        return copy.deepcopy(self.source)

    def decision(self, identifier="decision-1"):
        return {"id": identifier, "decided_at": self.now, "target": "funding_next_release_change",
                "entity": "USD", "horizon_seconds": 1, "mode": "paper", "data_features": {
                    "funding_rate": {"value": 3.88, "observed_at": self.now - 20,
                                     "available_at": self.now - 10, "source": "test-source", "revision": "test-v1"}},
                "usage_features": {}}

    def outcome(self):
        return {"id": "outcome-1", "decision_id": "decision-1", "value": .01,
                "unit": "percentage_points", "observed_at": self.now, "available_at": self.now,
                "source": "test-source", "revision": "test-v2"}

    def test_default_is_local_even_with_client_and_never_counts_request_as_useful(self):
        workflow = self.new_workflow(learning=self.learning)
        result = workflow.run("funding", "USD")
        self.assertEqual(result["status"], "ready_for_review")
        self.assertEqual(result["measurement"]["sharing"], "local_only")
        self.assertEqual(self.learning.calls, [])
        self.assertEqual(workflow.report()["operator_confirmed_useful_workflows"], 0)
        self.assertEqual(workflow.report()["independently_verified_outcomes"], None)
        self.assertEqual(workflow.state.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)

    def test_repeated_run_compares_source_fields_and_keeps_original(self):
        first = self.workflow.run("funding")
        old = self.workflow.state.run(first["run_id"])
        second = self.workflow.run("funding")
        self.assertEqual(second["previous_run_id"], first["run_id"])
        self.assertFalse(second["comparison"]["changed"])
        self.assertEqual(self.workflow.state.run(first["run_id"]), old)
        self.source["evidence"]["results"][0]["value"] = 4.1
        self.source["content_sha256"] = c.digest(self.source["evidence"])
        third = self.workflow.run("funding")
        self.assertTrue(third["comparison"]["changed"])
        history = self.workflow.state.history(limit=2)
        self.assertEqual([row["run_id"] for row in history], [third["run_id"], second["run_id"]])
        self.assertNotIn("result", history[0])

    def test_expired_or_source_blocked_monitor_prevents_downstream_read(self):
        for field in ("expiry", "upstream"):
            with self.subTest(field=field):
                self.context = fresh_snapshot()
                self.now = NOW + 900 if field == "expiry" else NOW
                if field == "upstream":
                    self.context["input_eligibility"] = "blocked_monitor"
                self.fetches.clear()
                result = self.workflow.run("funding")
                self.assertEqual(result["status"], "blocked_monitor")
                self.assertEqual([name for name, _ in self.fetches], ["context"])
                self.assertIsNone(result["result"])
                with self.assertRaises(ValueError):
                    self.workflow.feedback(result["run_id"], useful=True)

    def test_monitor_expiry_during_read_is_not_promoted_to_ready(self):
        def read(*args, **kwargs):
            self.now += 901
            return copy.deepcopy(self.source)
        self.workflow.review_fetcher = read
        result = self.workflow.run("funding")
        self.assertEqual(result["status"], "blocked_monitor")
        self.assertIsNotNone(result["result"])  # Retain evidence with its blocked status.

    def test_source_failures_are_retained_without_echoing_private_error(self):
        def fail(**kwargs):
            raise ValueError("secret-token-and-private-selector")
        self.workflow.context_fetcher = fail
        result = self.workflow.run("funding")
        self.assertEqual(result["status"], "context_unavailable")
        self.assertNotIn("secret-token", json.dumps(result))
        self.assertEqual(self.workflow.report()["by_status"], {"context_unavailable": 1})

    def test_bad_source_digest_is_quarantined_as_unavailable(self):
        self.source["content_sha256"] = "0" * 64
        result = self.workflow.run("funding")
        self.assertEqual(result["status"], "evidence_unavailable")
        self.assertIsNone(result["result"])

    def test_comparison_failure_cannot_leave_a_successful_review_status(self):
        self.workflow.run("funding")
        self.source["evidence"].pop("results")
        self.source["content_sha256"] = c.digest(self.source["evidence"])
        result = self.workflow.run("funding")
        self.assertEqual(result["status"], "evidence_unavailable")
        self.assertEqual(result["measurement"]["sharing"], "local_only")

    def test_context_transport_labels_verification_and_bounds_the_body(self):
        headers = Message(); headers["Content-Type"] = "application/json"
        for raw, valid in ((c.encode(self.context), True), (b"x" * 16385, False)):
            response = io.BytesIO(raw); response.headers = headers
            with patch.object(agent_workflow, "build_opener") as opener:
                opener.return_value.open.return_value = response
                if valid:
                    self.assertEqual(agent_workflow.fetch_context(verification=True), self.context)
                else:
                    with self.assertRaises(ValueError):
                        agent_workflow.fetch_context(verification=True)
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(request.full_url, "https://agents.seiche.info/v1/context/snapshot")
                self.assertEqual(request.get_header("X-financial-evidence-traffic-class"), "synthetic")
                self.assertIsNone(request.get_header("Authorization"))

    def test_slow_learning_body_is_bounded_and_retry_after_supports_seconds_or_date(self):
        client = RemoteLearningClient("https://example.test/learning", "a" * 32, timeout=1)
        with patch.object(client._opener, "open", return_value=io.BytesIO(b'{}')), \
                patch("financial_evidence.learning.client.time.monotonic", side_effect=[0, 0, 2]):
            with self.assertRaises(LearningDeliveryError):
                client.record_tool({})
        for header in ("60", formatdate(NOW + 60, usegmt=True)):
            headers = Message(); headers["Retry-After"] = header
            error = HTTPError("https://example.test", 429, "rate limit", headers, io.BytesIO(b"private body"))
            with patch.object(client._opener, "open", side_effect=error), \
                    patch("financial_evidence.learning.client.time.time", return_value=NOW):
                with self.assertRaises(LearningDeliveryError) as raised:
                    client.record_tool({})
                self.assertEqual(raised.exception.status, 429)
                self.assertEqual(raised.exception.retry_after, 60)
                self.assertNotIn("private body", str(raised.exception))

    def test_feedback_is_explicit_idempotent_and_never_infers_trades(self):
        run = self.workflow.run("funding")
        first = self.workflow.feedback(run["run_id"], useful=True)
        self.now += 1
        self.assertEqual(self.workflow.feedback(run["run_id"], useful=True), first)
        with self.assertRaises(ValueError):
            self.workflow.feedback(run["run_id"], useful=False)
        report = self.workflow.report()
        self.assertEqual(report["operator_confirmed_useful_workflows"], 1)
        self.assertEqual(report["outcome_records"], 0)

    def test_test_and_backtest_usage_is_excluded_and_labelled_at_both_reads(self):
        for mode in ("test", "backtest"):
            self.workflow.mode = mode
            result = self.workflow.run("funding")
            self.workflow.feedback(result["run_id"], useful=True)
        self.assertTrue(all(options["verification"] for _, options in self.fetches))
        report = self.workflow.report()
        self.assertEqual(report["eligible_usage_runs"], 0)
        self.assertEqual(report["operator_confirmed_useful_workflows"], 0)

    def test_decision_binds_actual_evidence_and_outcome_requires_its_horizon(self):
        run = self.workflow.run("funding")
        self.workflow.record_decision(run["run_id"], self.decision())
        stored = self.workflow.state.get_record("decision", "decision-1")
        self.assertEqual(stored["evidence_refs"][0]["sha256"], self.source["content_sha256"])
        self.assertEqual(stored["evidence_refs"][0]["receipt_id"], run["run_id"] + ":evidence")
        with self.assertRaises(ValueError):
            self.workflow.record_outcome(self.outcome())
        self.now += 1
        self.assertEqual(self.workflow.record_outcome(self.outcome())["verification"], "operator_reported")
        with self.assertRaises(ValueError):
            self.workflow.record_outcome({**self.outcome(), "id": "second-outcome"})

    def test_decisions_cannot_promote_test_usage_or_precede_available_evidence(self):
        run = self.workflow.run("funding")
        for changes in ({"mode": "operator_reported_production"}, {"decided_at": NOW - 1},
                        {"prompts": "private input"}):
            with self.assertRaises(ValueError):
                self.workflow.record_decision(run["run_id"], {**self.decision(), **changes})

    def test_opt_in_queues_only_bounded_metadata_and_preserves_receipts(self):
        workflow = self.new_workflow(learning=self.learning, share_usage=True)
        run = workflow.run("funding")
        self.assertEqual(self.learning.calls, [])
        self.assertEqual(run["measurement"]["sharing"], "queued")
        delivery = workflow.deliver()
        self.assertEqual(delivery["delivered"], 1)
        event = self.learning.calls[0][1]
        self.assertNotIn("selection", event)
        self.assertNotIn("result", event)
        self.assertNotIn("evidence", event)
        self.assertNotIn("useful", event)
        with workflow.state.db() as db:
            self.assertIsNone(db.execute("SELECT payload FROM outbox").fetchone()[0])
        self.assertEqual(workflow.deliver()["delivered"], 0)

    def test_failed_delivery_survives_restart_and_retries_same_record(self):
        workflow = self.new_workflow(learning=self.learning, share_usage=True)
        workflow.run("funding")
        self.learning.failure = LearningDeliveryError("failed", status=429, retry_after=60)
        self.assertEqual(workflow.deliver()["outbox"], {"pending": 1})
        first = self.learning.calls[0][1]
        workflow = self.new_workflow(learning=self.learning)
        self.learning.failure = None
        self.now += 59
        self.assertEqual(workflow.deliver()["delivered"], 0)
        self.now += 1
        self.assertEqual(workflow.deliver()["delivered"], 1)
        self.assertEqual(self.learning.calls[-1][1], first)

    def test_wrong_receipt_cannot_be_counted_as_delivered(self):
        workflow = self.new_workflow(learning=self.learning, share_usage=True)
        workflow.run("funding")
        self.learning.wrong_receipt = True
        self.assertEqual(workflow.deliver()["outbox"], {"pending": 1})

    def test_revocation_is_terminal_and_pending_can_be_discarded(self):
        workflow = self.new_workflow(learning=self.learning, share_usage=True)
        workflow.run("funding")
        self.learning.failure = LearningDeliveryError("denied", status=403)
        self.assertEqual(workflow.deliver()["outbox"], {"rejected": 1})
        workflow.deliver()
        self.assertEqual(len(self.learning.calls), 1)
        self.assertEqual(workflow.state.discard_pending()["discarded"], 1)
        self.assertEqual(workflow.state.outbox_status(), {"discarded": 1})

    def test_queue_cannot_be_redirected_to_another_credential(self):
        workflow = self.new_workflow(learning=self.learning, share_usage=True)
        workflow.run("funding")
        self.learning.destination_fingerprint = "b" * 64
        with self.assertRaises(ValueError):
            workflow.deliver()
        self.assertEqual(self.learning.calls, [])

    def test_lease_prevents_duplicate_concurrent_send_and_recovers_after_crash(self):
        workflow = self.new_workflow(learning=self.learning, share_usage=True)
        workflow.run("funding")
        with workflow.state.db() as db:
            db.execute("UPDATE outbox SET state='sending',lease='abandoned',lease_until=?", (NOW + 65,))
        self.assertEqual(workflow.deliver()["delivered"], 0)
        with self.assertRaises(ValueError):
            workflow.state.discard_pending()
        self.now += 66
        self.assertEqual(workflow.deliver()["delivered"], 1)

    def test_expired_queue_erases_payload_without_delivery(self):
        workflow = self.new_workflow(learning=self.learning, share_usage=True)
        workflow.run("funding")
        self.now += 7 * 86400 + 1
        self.assertEqual(workflow.deliver()["outbox"], {"expired": 1})
        self.assertEqual(self.learning.calls, [])
        with workflow.state.db() as db:
            self.assertIsNone(db.execute("SELECT payload FROM outbox").fetchone()[0])

    def test_long_lived_client_cannot_read_expired_records(self):
        run = self.workflow.run("funding")
        self.now += 30 * 86400 + 1
        with self.assertRaises(ValueError):
            self.workflow.state.run(run["run_id"])
        with self.assertRaises(ValueError):
            self.workflow.state.get_record("tool", run["run_id"] + ":read")

    def test_corrupt_queued_record_is_rejected_without_upload_or_endless_retry(self):
        workflow = self.new_workflow(learning=self.learning, share_usage=True)
        workflow.run("funding")
        with workflow.state.db() as db:
            db.execute("UPDATE outbox SET sha256=?", ("f" * 64,))
        self.assertEqual(workflow.deliver()["outbox"], {"rejected": 1})
        self.assertEqual(self.learning.calls, [])

    def test_outcome_requires_shared_parent_and_does_not_follow_rejected_parent(self):
        workflow = self.new_workflow(learning=self.learning)
        run = workflow.run("funding")
        decision = self.decision()
        workflow.record_decision(run["run_id"], decision)
        self.now += 1
        with self.assertRaisesRegex(ValueError, "share the retained decision"):
            workflow.record_outcome(self.outcome(), share=True)
        workflow.record_decision(run["run_id"], decision, share=True)
        workflow.record_outcome(self.outcome(), share=True)
        self.learning.failure = LearningDeliveryError("denied", status=403)
        workflow.deliver()
        self.learning.failure = None
        self.assertEqual(workflow.deliver()["outbox"], {"rejected": 2})
        self.assertEqual([kind for kind, _ in self.learning.calls], ["decision"])

    def test_two_concurrent_outcomes_cannot_claim_the_same_decision(self):
        run = self.workflow.run("funding")
        self.workflow.record_decision(run["run_id"], self.decision())
        self.now += 1
        barrier, answers = threading.Barrier(2), []
        def record(identifier):
            barrier.wait()
            try:
                self.workflow.record_outcome({**self.outcome(), "id": identifier})
                answers.append("stored")
            except ValueError:
                answers.append("refused")
        threads = [threading.Thread(target=record, args=(identifier,)) for identifier in ("first", "second")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(answers), ["refused", "stored"])
        self.assertEqual(self.workflow.report()["outcome_records"], 1)

    def test_state_permissions_links_and_mutated_history_are_refused(self):
        os.chmod(self.root, 0o755)
        with self.assertRaises(ValueError):
            self.new_workflow()
        os.chmod(self.root, 0o700)
        run = self.workflow.run("funding")
        with self.workflow.state.db() as db:
            db.execute("UPDATE runs SET sha256=?", ("f" * 64,))
        with self.assertRaises(ValueError):
            self.workflow.state.run(run["run_id"])
        alias = Path(self.temp.name) / "alias"
        alias.symlink_to(self.root)
        with self.assertRaises(ValueError):
            AgentWorkflow(alias)

    def test_cli_is_part_of_main_product_and_report_is_offline(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = cli.main(["workflow", "report", "--state", str(self.root)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["runs"], 0)
        with contextlib.redirect_stdout(io.StringIO()) as history:
            self.assertEqual(cli.main(["workflow", "history", "--state", str(self.root)]), 0)
        self.assertEqual(json.loads(history.getvalue()), [])
        with patch.dict(os.environ, {"FINANCIAL_LEARNING_CREDENTIAL": ""}), contextlib.redirect_stdout(io.StringIO()):
            status = cli.main(["workflow", "run", "funding", "--share-usage", "--state", str(self.root)])
        self.assertEqual(status, 1)
        self.assertEqual(self.fetches, [])

    def test_real_langgraph_node_preserves_review_and_repeated_comparison(self):
        if importlib.util.find_spec("langgraph") is None:
            if os.environ.get("FINANCIAL_EVIDENCE_REQUIRED_FRAMEWORK") == "langgraph":
                self.fail("Required LangGraph SDK must be installed and exercised")
            self.skipTest("Optional LangGraph SDK is not installed")
        from langgraph.graph import StateGraph, START, END
        adapter_path = Path(__file__).resolve().parents[1] / "integrations/trading-agents/recurring_review.py"
        spec = importlib.util.spec_from_file_location("recurring_review", adapter_path)
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        class ReviewState(TypedDict, total=False):
            financial_review: dict
        with patch.object(adapter, "AgentWorkflow", return_value=self.workflow):
            node = adapter.review_node(self.root)
        self.assertEqual(self.fetches, [])  # Constructing an integration sends nothing.
        builder = StateGraph(ReviewState)
        builder.add_node("review", node)
        builder.add_edge(START, "review")
        builder.add_edge("review", END)
        graph = builder.compile()
        first = graph.invoke({})["financial_review"]
        again = graph.invoke({})["financial_review"]
        self.assertEqual(first["status"], "ready_for_review")
        self.assertEqual(first["result"], self.source)
        self.assertEqual(again["previous_run_id"], first["run_id"])
        self.assertFalse(again["comparison"]["changed"])
        self.assertEqual(self.learning.calls, [])

    def test_real_http_delivery_uses_existing_enrollment_and_outcome_contracts(self):
        store = LearningStore(Path(self.temp.name) / "server", clock=lambda: self.now)
        enrolled = store.enroll(purposes=["measurement", "private_evidence"], policy_version="test",
                                expires_at=self.now + 86400, retention_days=1)
        credential = enrolled["credential"]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(handler):
                body = json.loads(handler.rfile.read(int(handler.headers["Content-Length"])))
                self.assertEqual(handler.headers["Authorization"], "Bearer " + credential)
                method = {"/v1/events": store.record_tool, "/v1/decisions": store.record_decision,
                          "/v1/outcomes": store.record_outcome}[handler.path]
                try:
                    response = method(credential, body)
                except ValueError:
                    handler.send_error(400)
                    return
                raw = c.encode(response)
                handler.send_response(200)
                handler.send_header("Content-Type", "application/json")
                handler.send_header("Content-Length", str(len(raw)))
                handler.end_headers()
                handler.wfile.write(raw)
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        client = RemoteLearningClient(f"http://127.0.0.1:{server.server_port}", credential)
        workflow = self.new_workflow(learning=client, share_usage=True)
        run = workflow.run("funding")
        workflow.feedback(run["run_id"], useful=True, share=True)
        workflow.record_decision(run["run_id"], self.decision(), share=True)
        self.now += 1
        workflow.record_outcome(self.outcome(), share=True)
        self.assertEqual(workflow.deliver()["delivered"], 4)
        report = store.report(credential)
        self.assertEqual(report["confirmed_useful_workflows"], 1)
        self.assertEqual(report["outcome_coverage"]["linked_outcomes"], 1)
        self.assertEqual(report["outcome_coverage"]["reviewer_verified_outcomes"], 0)
        self.assertNotIn(credential, workflow.state.path.read_bytes().decode("latin1"))


if __name__ == "__main__":
    unittest.main()
