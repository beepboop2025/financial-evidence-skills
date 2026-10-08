"""Compose existing research clients behind durable, bounded workflows."""

from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import time

from .assessment import assess
from .contracts import (HEX, KEY, MAX_BUNDLE_BYTES, Workflow, decode, digest, encode,
                        integer, moment, utc)
from .store import CLASSES, Store

RUNTIME_VERSION = "1.0.0"


def implementation():
    files = {}
    root = Path(__file__).parent.parent
    for path in sorted(root.rglob("*.py")):
        files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"version": RUNTIME_VERSION, "sha256": digest(files)}


def execute(workflow, *, traffic_class="unverified"):
    """Kill the dedicated worker after 45 seconds, including a trickling source.

    Only this read-only worker is terminated. The caller and unrelated services
    remain untouched. No retry or stale-success substitution happens here.
    """
    process = subprocess.run(
        [sys.executable, "-m", "financial_evidence.runtime.worker", "--traffic-class", traffic_class],
        input=workflow.document, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=45, check=False,
    )
    if process.returncode:
        raise RuntimeError("research_worker_failed")
    return decode(process.stdout)


def verify_bundle(value):
    """Verify receipt bytes and semantics, not issuer identity or source truth."""
    if not isinstance(value, dict) or set(value) != {"schema", "sha256", "record"}:
        raise ValueError("invalid receipt envelope")
    if len(encode(value)) > MAX_BUNDLE_BYTES:
        raise ValueError("receipt exceeds its byte allowance")
    if value["schema"] != "financial-evidence.runtime-bundle.v1" or value["sha256"] != digest(value["record"]):
        raise ValueError("receipt integrity mismatch")
    record = value["record"]
    if not isinstance(record, dict) or set(record) != {
        "schema", "run_id", "workflow", "workflow_sha256", "installation_id", "traffic_class",
        "started_at", "captured_at", "implementation", "result", "assessment", "change", "authority"
    } or record["schema"] != "financial-evidence.runtime-record.v1":
        raise ValueError("invalid runtime record")
    workflow = Workflow.parse(record["workflow"])
    if workflow.sha256 != record["workflow_sha256"]:
        raise ValueError("workflow integrity mismatch")
    for key in ("run_id", "installation_id"):
        if not isinstance(record[key], str) or not re.fullmatch(r"[0-9a-f]{32}", record[key]):
            raise ValueError("invalid receipt identity")
    if (not isinstance(record["traffic_class"], str) or record["traffic_class"] not in CLASSES
            or not isinstance(record["change"], str) or record["change"] not in {"first", "changed", "unchanged"}):
        raise ValueError("invalid receipt classification")
    build = record["implementation"]
    if (not isinstance(build, dict) or set(build) != {"version", "sha256"}
            or build["version"] != RUNTIME_VERSION or not isinstance(build["sha256"], str)
            or not HEX.fullmatch(build["sha256"])):
        raise ValueError("invalid implementation identity")
    try:
        started = datetime.fromisoformat(record["started_at"])
        captured = datetime.fromisoformat(record["captured_at"])
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid capture clocks") from exc
    if started.tzinfo is None or captured.tzinfo is None or captured < started:
        raise ValueError("invalid capture clocks")
    if record["authority"] != {"execution": False, "issuer_verified": False, "source_verified": False}:
        raise ValueError("receipt cannot confer authority")
    revision = record["result"].get("revision") if isinstance(record["result"], dict) else None
    if not isinstance(revision, str) or not HEX.fullmatch(revision):
        raise ValueError("invalid evidence revision")
    if record["assessment"] != assess(record["result"], workflow, captured.timestamp()):
        raise ValueError("research assessment mismatch")
    return {"valid": True, "sha256": value["sha256"], "run_id": record["run_id"],
            "scope": "content_integrity_and_configured_research_checks",
            "issuer_verified": False, "source_verified": False, "execution_authority": False,
            "historical_point_in_time_verified": False}


class Runtime:
    def __init__(self, store: Store, *, executor=execute, clock=time.time):
        self.store, self.executor, self.clock = store, executor, clock

    def run(self, job, key, *, scheduled=False):
        if not isinstance(key, str) or not KEY.fullmatch(key):
            raise ValueError("invalid idempotency key")
        start = moment(self.clock())
        claim = self.store.claim(job, key, start, scheduled=scheduled)
        if not claim["admitted"]:
            return claim
        identifier = claim["run_id"]
        start = claim["started"]
        workflow = Workflow.parse(claim["workflow"])
        error = None
        record = None
        try:
            prior = self.store.prior_revision(job, identifier)
            result = (execute(workflow, traffic_class=claim["traffic_class"])
                      if self.executor is execute else self.executor(workflow))
            if not isinstance(result, dict) or not isinstance(result.get("revision"), str) or not HEX.fullmatch(result["revision"]):
                raise ValueError("invalid evidence revision")
            end = max(start, moment(self.clock()))
            evaluation = assess(result, workflow, end)
            record = {
                "schema": "financial-evidence.runtime-record.v1", "run_id": identifier,
                "workflow": workflow.value, "workflow_sha256": workflow.sha256,
                "installation_id": claim["installation_id"], "traffic_class": claim["traffic_class"],
                "started_at": utc(start), "captured_at": utc(end), "implementation": implementation(),
                "result": result, "assessment": evaluation,
                "change": ("first" if prior is None else "unchanged"
                           if result["transport_status"] == "complete" and prior == result["revision"] else "changed"),
                "authority": {"execution": False, "issuer_verified": False, "source_verified": False},
            }
            if len(encode(record)) > MAX_BUNDLE_BYTES - 1024:
                raise ValueError("receipt exceeds its byte allowance")
        except subprocess.TimeoutExpired:
            error = "research_deadline_exceeded"
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            error = "invalid_research_result"
        except (OSError, RuntimeError):
            error = "research_worker_failed"
        # Unknown programmer failures deliberately leave an interrupted claim;
        # they are not silently relabelled as completed research.
        finished = self.store.finish(identifier, moment(self.clock()), None if error else record, error)
        return {"admitted": True, "run_id": identifier, "status": finished["status"],
                "error": finished["error"], "sha256": finished["sha256"],
                "assessment": record["assessment"] if not error and "record" in finished else None}

    def tick(self, limit=10):
        integer(limit, 1, 10, "limit")
        now = moment(self.clock())
        jobs = self.store.jobs()
        due = [row for row in jobs if row["enabled"] and datetime.fromisoformat(row["next_due"]).timestamp() <= now]
        # Rejected claims consume no execution slot. Examine at most the store's
        # 100 registered jobs so a throttled job cannot starve eligible work.
        due.sort(key=lambda row: (row["next_due"], row["workflow"]["id"]))
        results = []
        admitted = 0
        for row in due:
            if admitted >= limit:
                break
            spec = row["workflow"]
            key = f"tick:{int(now // spec['interval_seconds'])}"
            attempt = self.run(spec["id"], key, scheduled=True)
            results.append({"job": spec["id"], **attempt})
            admitted += int(attempt["admitted"])
        return {"runs": results, "admitted_count": admitted, "more_due": len(due) > len(results),
                "scope": "bounded_single_tick; no_background_daemon_started"}

    def bundle(self, identifier):
        run = self.store.run(identifier)
        if "record" not in run:
            raise ValueError("run has no retained research receipt")
        bundle = {"schema": "financial-evidence.runtime-bundle.v1", "sha256": run["sha256"], "record": run["record"]}
        verify_bundle(bundle)
        return bundle

    def replay(self, identifier):
        bundle = self.bundle(identifier)
        return {"mode": "offline_replay", "network_calls": 0,
                "verification": verify_bundle(bundle), "bundle": bundle,
                "freshness": "original_capture_only; never_relabelled_current"}
