"""Explain retained source blocks without fetching, changing policy or granting rights."""

from collections import Counter
from datetime import datetime
from pathlib import Path
import time

from financial_evidence.runtime.assessment import assess
from financial_evidence.runtime.contracts import Workflow
from ops_common import bound_identity, decode, encode, inspect_journal, readonly, runtime_identity, utc, verify_row


GUIDANCE = {
    "rights_not_established": "The source must publish an applicable rights status or the owner must complete a rights review. Public access alone is not permission.",
    "source_rights_restricted": "Keep restricted values blocked. Obtain the required entitlement or use a separately authorized source; do not relax the registered policy.",
    "numeric_value_missing": "Inspect the cited field. Missing and withheld values stay missing; repair the upstream publication or register a separately scoped question.",
    "observation_too_old": "Check the original observation date and native publication cadence. Acquire a newer eligible observation; a fresh retrieval timestamp does not refresh the value.",
    "page_incomplete": "The retained result contains only one page. Register an explicitly narrower question or use a bounded client to inspect all pages before defining a new workflow.",
    "source_not_available": "Inspect the source's unavailable, withheld, stale or blocked status. Restore eligible upstream coverage before using the affected rows.",
    "unit_missing": "The upstream source must supply the native unit; do not infer it from the value.",
    "observation_clock_unknown": "Obtain the source observation date with a timezone where needed. Build and retrieval times cannot replace it.",
    "observation_in_future": "Check the source clock and local UTC clock before using the observation.",
    "missing_provenance": "Restore the allowlisted source URL, content hash and field pointer. A value without its provenance remains blocked.",
    "no_matching_rows": "Check the dataset and entity/date scope against published coverage. An empty result is not a zero value.",
    "transport_incomplete": "Inspect the source transport diagnostic and restore source availability. Retry only as a new registered attempt with a new key.",
    "section_transport_incomplete": "Inspect the affected section's source transport; partial acquisition remains explicit.",
    "source_diagnostics": "Inspect the retained source diagnostic before relying on the affected section.",
}


def text(value, limit=160):
    return value[:limit] if isinstance(value, str) else None


def explain(record):
    """Use the runtime's own assessment at the original capture time for each row."""
    specification = record["workflow"]
    result = record["result"]
    sections = result.get("sections", [result])
    at = datetime.fromisoformat(record["captured_at"]).timestamp()
    counts = Counter()
    samples, covered = [], set()
    rows_checked = 0
    for section in sections:
        row_policy = Workflow.parse({**specification, "operation": "query",
                                     "parameters": {"dataset": section["dataset"], "limit": 1}})
        for index, row in enumerate(section["results"]):
            # Isolate row conditions. Whole-result transport, pagination and
            # section diagnostics remain in the original aggregate assessment.
            single = {key: value for key, value in result.items() if key != "sections"}
            single.update(dataset=section["dataset"], results=[row], transport_status="complete", diagnostics=[], next_offset=None)
            reasons = assess(single, row_policy, at)["reasons"]
            rows_checked += 1
            counts.update(reasons)
            if set(reasons) - covered and len(samples) < 8:
                samples.append({"dataset": section["dataset"], "row_index": index,
                    "entity_id": text(row.get("entity_id")), "entity_name": text(row.get("entity_name")),
                    "metric": text(row.get("metric")), "as_of": text(row.get("as_of"), 64),
                    "availability": text(row.get("availability")), "rights_status": text(row.get("rights_status")),
                    "source_url": text(row.get("source_url"), 256), "source_field": text(row.get("source_field"), 256),
                    "reasons": reasons})
                covered.update(reasons)
    reasons = record["assessment"]["reasons"]
    return {"job": specification["id"], "run_id": record["run_id"], "captured_at": record["captured_at"],
            "status": record["assessment"]["status"], "requirements": specification["requirements"],
            "query": specification["parameters"], "reasons": reasons, "rows_checked": rows_checked,
            "affected_row_counts": dict(sorted(counts.items())), "representative_rows": samples,
            "unrepresented_row_reasons": sorted(set(counts) - covered),
            "example_scope": "one example per newly encountered row condition; not the complete result",
            "assessment_time": "original_capture_only", "source_verified": False, "execution_authority": False}


def diagnose(cfg, *, job=None, now=None, journal=None):
    now = time.time() if now is None else now
    runtime_identity(cfg)
    if job is not None and job not in cfg["jobs"]:
        raise ValueError("unknown registered workflow")
    journal = inspect_journal(Path(cfg["root"]) / "runtime.sqlite") if journal is None else journal
    bound_identity(journal, cfg)
    reports = []
    with readonly(Path(cfg["root"]) / "runtime.sqlite") as db:
        meta = dict(db.execute("SELECT key,value FROM meta"))
        for entry in journal["jobs"]:
            if job is not None and entry["id"] != job:
                continue
            latest = entry["latest"]
            row = db.execute("SELECT * FROM runs WHERE id=?", (latest["id"],)).fetchone() if latest else None
            if row is None or row["bundle"] is None:
                reports.append({"job": entry["id"], "status": "no_retained_receipt", "run_id": latest["id"] if latest else None})
                continue
            stored = db.execute("SELECT spec FROM jobs WHERE id=?", (entry["id"],)).fetchone()
            workflow = Workflow.parse(decode(stored["spec"]))
            if workflow.sha256 != cfg["jobs"][entry["id"]]:
                raise ValueError("diagnostic workflow binding differs")
            report = explain(verify_row(row, meta, workflow))
            report["receipt_sha256"] = row["sha256"]
            reports.append(report)
    used = {reason for report in reports for reason in report.get("reasons", [])}
    response = {"schema": "financial-evidence.runtime-source-diagnostics.v1", "generated_at": utc(now),
        "valid_until": utc(now + cfg["monitor_max_age_seconds"]), "status": "observed",
        "installation_id": cfg["installation_id"], "jobs": reports,
        "guidance": {code: GUIDANCE.get(code, "Inspect the retained receipt and source policy before changing the workflow.") for code in sorted(used)},
        "scope": "verified retained receipts at their original capture times; not current source eligibility",
        "source_network_calls": 0, "policy_changes": False, "execution_authority": False}
    if len(encode(response)) > 1_048_576:
        raise ValueError("diagnostic output exceeds allowance")
    return response
