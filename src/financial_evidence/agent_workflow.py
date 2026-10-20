"""Recurring research workflow for explicit application hooks and schedulers.

Public reads need no enrollment. Sharing is a separate, explicit action using
the existing learning service contracts. Nothing places orders or schedules itself.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError
from urllib.request import Request, build_opener
import uuid

from . import __version__, research
from .hosted import PLATFORM_URL
from .learning import contracts as c
from .trading.context import MAX_SNAPSHOT, validate_snapshot
from .workflow_state import WorkflowState

PRODUCTS = {"funding": "seiche", "institutions": "liquilens", "exit": "undertow"}
TASKS = {"funding": "funding_review", "institutions": "institution_evidence", "exit": "liquidity"}


def _access_failure(error, *, stage, now):
    """Keep a bounded status and next step, never an upstream body or URL."""
    reasons = {
        401: ("authentication_required", "Review the credential and source authorization before retrying."),
        403: ("access_denied", "Review source access before retrying; do not switch routes to bypass the refusal."),
        429: ("rate_limited", "Wait for Retry-After when supplied; otherwise use bounded backoff on the authorized route."),
        451: ("access_restricted", "Review the reported source restriction before retrying."),
    }
    reason, next_step = reasons.get(error.code, ("upstream_http_error", "Review the HTTP failure before retrying."))
    value = {"http_status": error.code, "stage": stage, "reason": reason,
             "automatic_retry": False, "next_step": next_step}
    header = error.headers.get("Retry-After", "") if error.headers else ""
    if error.code == 429 and len(header) <= 128:
        try:
            if header.isascii() and header.isdecimal() and len(header) <= 10:
                delay = int(header)
            else:
                date = parsedate_to_datetime(header)
                delay = max(0, math.ceil(date.timestamp() - now)) if date.tzinfo else None
            if delay is not None:
                value["retry_after_seconds"] = delay
        except (ValueError, TypeError, OverflowError):
            pass
    return value


def fetch_context(*, verification=False):
    """Read only bounded anonymous source-status metadata from the main gateway."""
    request = Request(PLATFORM_URL + "/v1/context/snapshot", headers={
        "Accept": "application/json", "Accept-Encoding": "identity",
        "User-Agent": "FinancialEvidenceWorkflow/1",
        "X-Financial-Evidence-Traffic-Class": "synthetic" if verification else "unknown"})
    started = time.monotonic()
    with build_opener(research._NoRedirect()).open(request, timeout=10) as response:
        if (response.headers.get_content_type() != "application/json"
                or response.headers.get("Content-Encoding", "identity") != "identity"):
            raise ValueError("unexpected source-status response")
        raw = bytearray()
        read = getattr(response, "read1", response.read)
        while True:
            chunk = read(min(4096, MAX_SNAPSHOT + 1 - len(raw)))
            raw.extend(chunk)
            if len(raw) > MAX_SNAPSHOT or time.monotonic() - started > 15:
                raise ValueError("source-status response exceeds its bound")
            if not chunk:
                break
    value = json.loads(raw, object_pairs_hook=research._object)
    c.encode(value)
    return value


class AgentWorkflow:
    """One local journal, explicit optional learning destination, no ambient token."""

    def __init__(self, directory, *, mode="unknown", learning=None, share_usage=False,
                 clock=time.time, context_fetcher=fetch_context, review_fetcher=research.fetch_workflow):
        c.choice(mode, c.MODES, "usage mode")
        if type(share_usage) is not bool or (share_usage and learning is None):
            raise ValueError("usage sharing requires an explicit enrolled learning client")
        self.state = WorkflowState(directory, clock=clock)
        self.mode, self.learning, self.share_usage, self.clock = mode, learning, share_usage, clock
        self.context_fetcher, self.review_fetcher = context_fetcher, review_fetcher

    def run(self, workflow, selection=None):
        selected = research.settings(workflow, selection)
        self.state.prune()
        previous = self.state.previous(workflow, selected["selection"], self.mode)
        started, monotonic = c.moment(self.clock()), time.monotonic()
        result = {"schema": "financial-evidence.agent-workflow.v1", **selected,
                  "run_id": uuid.uuid4().hex, "mode": self.mode, "started_at": started,
                  "status": "context_unavailable", "context": None, "result": None,
                  "comparison": None, "previous_run_id": previous["run_id"] if previous else None,
                  "review_required": True, "input_eligibility": "not_evaluated",
                  "execution_authority": "none", "outcome_verification": "not_observed"}
        verification = self.mode in {"test", "backtest"}
        stage = "context"
        try:
            context = validate_snapshot(self.context_fetcher(verification=verification), now=self.clock())
            result["context"] = context
            if not context["client_monitor_current"] or context["input_eligibility"] != "not_evaluated":
                result["status"] = "blocked_monitor"
            else:
                result["status"] = "evidence_unavailable"
                stage = "evidence"
                evidence = self.review_fetcher(workflow, selected["selection"], verification=verification)
                evidence = research.validate(research.encoded(evidence), selected)
                # The monitor lease may expire while the evidence request is in flight.
                result["context"] = validate_snapshot(context, now=self.clock())
                result["result"] = evidence
                if previous is not None:
                    result["comparison"] = research.compare(previous["result"], evidence)
                if not result["context"]["client_monitor_current"]:
                    result["status"] = "blocked_monitor"
                else:
                    result["status"] = "ready_for_review" if evidence["prepared_response"] else "evidence_unavailable"
        except HTTPError as error:
            result["error"] = "source_http_failure"
            result["access_failure"] = _access_failure(error, stage=stage, now=self.clock())
            error.close()
        except (OSError, ValueError, TypeError, KeyError):
            result["error"] = "source_read_or_contract_validation_failed"
        result["completed_at"] = c.moment(self.clock())
        result["duration_ms"] = round((time.monotonic() - monotonic) * 1000, 3)
        self.state.save_run(result)
        event = self._event(result)
        try:
            recorded = self.state.record("tool", event, client=self.learning if self.share_usage else None)
            result["measurement"] = recorded
        except (OSError, ValueError, sqlite3.Error):
            # Optional reporting must never erase a completed public review.
            result["measurement"] = {"sharing": "not_queued", "reason": "local_measurement_failed"}
        return result

    @staticmethod
    def _event(run):
        status = {"ready_for_review": "success", "blocked_monitor": "stale"}.get(run["status"], "error")
        failure = (run.get("access_failure") or {}).get("reason")
        if failure in {"authentication_required", "access_denied", "access_restricted", "rate_limited"}:
            status = "refused"
        event = {"id": run["run_id"] + ":read", "logical_workflow_id": run["run_id"],
                "product": PRODUCTS[run["workflow"]], "tool": "financial_evidence_workflow",
                "task": TASKS[run["workflow"]], "occurred_at": run["completed_at"],
                "duration_ms": run["duration_ms"], "status": status, "mode": run["mode"],
                "client_version": __version__, "config_version": "agent-workflow.v2",
                "event_kind": "attempt"}
        if status != "success":
            event["failure_reason"] = failure or (
                "monitor_blocked" if run["status"] == "blocked_monitor"
                else run.get("error", run["status"]))
        return event

    def feedback(self, run_id, *, useful, reason=None, data_gaps=None, share=False):
        """A separate operator confirmation; never inferred from HTTP success."""
        if type(useful) is not bool:
            raise ValueError("useful must be an explicit boolean")
        client = self._sharing(share)
        run = self.state.run(run_id)
        if useful and run["status"] != "ready_for_review":
            raise ValueError("a blocked or unavailable review cannot be a useful completion")
        event = {**self._event(run), "id": run_id + ":feedback",
                 "occurred_at": c.moment(self.clock()), "useful": useful, "duration_ms": 0,
                 "event_kind": "feedback"}
        event.pop("failure_reason", None)
        if reason is not None:
            event["feedback_reason"] = reason
        if data_gaps is not None:
            event["data_gaps"] = data_gaps
        event = c.tool_event(event, self.clock())
        try:
            previous = self.state.get_record("tool", event["id"])
        except ValueError as exc:
            if str(exc) != "learning record not found in this workflow journal":
                raise
        else:
            if any(previous.get(key) != event.get(key) for key in ("useful", "feedback_reason", "data_gaps")):
                raise ValueError("workflow feedback is immutable")
            event = previous
        return self.state.record("tool", event, client=client)

    def _sharing(self, share):
        if type(share) is not bool or (share and self.learning is None):
            raise ValueError("sharing requires an explicitly enrolled learning client")
        return self.learning if share else None

    def record_decision(self, run_id, decision, *, share=False):
        """Bind supplied numeric decision evidence to an actual retained review."""
        client = self._sharing(share)
        run = self.state.run(run_id)
        if run["status"] != "ready_for_review":
            raise ValueError("decision evidence requires a prepared review")
        value = json.loads(c.encode(decision))
        if not isinstance(value, dict):
            raise ValueError("decision must be an object")
        refs = value.setdefault("evidence_refs", [])
        if not isinstance(refs, list):
            raise ValueError("evidence_refs must be a list")
        reference = {"kind": "product", "product": "financial_evidence",
                     "receipt_id": run_id + ":evidence", "sha256": run["result"]["content_sha256"]}
        if reference not in refs:
            refs.append(reference)
        value = c.decision(value, self.clock())
        if value["mode"] != run["mode"] or value["decided_at"] < run["completed_at"]:
            raise ValueError("decision mode/time must match evidence available at that decision")
        return self.state.record("decision", value, client=client)

    def record_outcome(self, outcome, *, share=False):
        """Store an operator-reported outcome; the server owns independent review."""
        client = self._sharing(share)
        value = c.outcome(outcome, self.clock())
        # The journal checks the parent/horizon and uniqueness in one write transaction.
        return {**self.state.record("outcome", value, client=client), "verification": "operator_reported"}

    def deliver(self, *, limit=10):
        if self.learning is None:
            raise ValueError("delivery requires an explicitly enrolled learning client")
        return self.state.flush(self.learning, limit=limit)

    def report(self):
        return self.state.report()
