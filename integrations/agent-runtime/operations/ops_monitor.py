"""Operational health, source readiness and local incident transitions."""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

from ops_common import atomic, bound_identity, decode, encode, inspect_journal, private, regular, runtime_identity, utc

UNITS = ("financial-evidence-runtime.timer", "financial-evidence-runtime.service",
         "financial-evidence-runtime-backup.timer", "financial-evidence-runtime-backup.service",
         "financial-evidence-runtime-monitor.timer", "financial-evidence-runtime-dashboard.service")


def units():
    result = subprocess.run(["systemctl", "show", *UNITS, "--property=Id,ActiveState,Result,LastTriggerUSec,ExecMainStatus"],
                            capture_output=True, text=True, timeout=10, check=False)
    if result.returncode or len(result.stdout) > 32768:
        raise ValueError("systemd inspection failed")
    rows = {}
    for block in result.stdout.strip().split("\n\n"):
        value = dict(line.split("=", 1) for line in block.splitlines() if "=" in line)
        if value.get("Id") in UNITS:
            rows[value["Id"]] = value
    return rows


def backup_status(state):
    path = Path(state) / "backup.json"
    if not path.exists():
        return None
    return decode(regular(path, 65536), limit=65536)


def assess(cfg, journal, service_units, backup, free_bytes, now):
    bound_identity(journal, cfg)
    issues = []

    def issue(code, severity="critical", job=None):
        issues.append({"id": code + (":" + job if job else ""), "code": code, "severity": severity, "job": job})

    if journal["last_clock"] > now + 5:
        issue("clock_behind_journal")
    if journal["stopped"]:
        issue("admission_stopped", "warning")
    if free_bytes < cfg["min_free_bytes"]:
        issue("disk_reserve_low")
    for field, amount in (("runs", journal["runs"]), ("receipt_bytes", journal["receipt_bytes"])):
        limit = journal["limits"][field]
        if amount >= limit:
            issue(field + "_capacity_exhausted")
        elif amount >= limit * .8:
            issue(field + "_capacity_warning", "warning")
    for unit in UNITS:
        row = service_units.get(unit)
        if row is None:
            issue("unit_missing:" + unit)
        elif unit.endswith(".timer") or unit.endswith("dashboard.service"):
            if row.get("ActiveState") != "active":
                issue("unit_inactive:" + unit)
        elif row.get("Result") not in {"success", ""} or row.get("ExecMainStatus", "0") != "0":
            issue("unit_failed:" + unit)
    trigger = service_units.get("financial-evidence-runtime.timer", {}).get("LastTriggerUSec", "")
    try:
        sampled = datetime.strptime(trigger, "%a %Y-%m-%d %H:%M:%S %Z").replace(tzinfo=timezone.utc).timestamp()
        if sampled > now + 5 or now - sampled > cfg["due_grace_seconds"]:
            issue("scheduler_heartbeat_stale")
    except ValueError:
        issue("scheduler_heartbeat_unknown")
    for job in journal["jobs"]:
        latest = job["latest"]
        if not job["enabled"]:
            issue("workflow_paused", "warning", job["id"])
        elif not journal["stopped"] and now > max(job["next_due"], job["breaker_until"]) + cfg["due_grace_seconds"]:
            issue("workflow_overdue", job=job["id"])
        if job["breaker_until"] > now:
            issue("source_circuit_open", "warning", job["id"])
        if latest:
            if latest["status"] == "running" and now - latest["started"] > 120:
                issue("claim_interrupted", job=job["id"])
            elif latest["status"] in {"error", "interrupted"}:
                issue("workflow_attempt_failed", job=job["id"])
            elif latest["status"] == "blocked":
                issue("source_requirements_blocked", "source", job["id"])
    backup_age = None
    if not backup:
        issue("offsite_restore_not_verified")
    else:
        verified = backup.get("last_verified")
        if verified:
            if verified.get("installation_id") != cfg["installation_id"] or verified.get("repository_id") != cfg["repository_id"]:
                issue("backup_identity_mismatch")
            else:
                backup_age = now - datetime.fromisoformat(verified["verified_at"]).timestamp()
                if backup_age < -5 or backup_age > cfg["backup_max_age_seconds"]:
                    issue("offsite_restore_stale")
        else:
            issue("offsite_restore_not_verified")
        if backup.get("status") not in {"verified", "running"}:
            issue("offsite_backup_failed")
        if backup.get("status") == "running" and now - backup.get("started_epoch", 0) > 1200:
            issue("offsite_backup_stalled")
    critical = any(i["severity"] == "critical" for i in issues)
    warnings = any(i["severity"] == "warning" for i in issues)
    sources = [i for i in issues if i["severity"] == "source"]
    latest_statuses = [j["latest"]["status"] if j["latest"] else None for j in journal["jobs"]]
    source_status = ("blocked" if sources else "not_observed" if not latest_statuses or None in latest_statuses
                     else "requirements_met" if all(s == "complete" for s in latest_statuses) else "unknown")
    return {"schema": "financial-evidence.runtime-health.v1", "generated_at": utc(now),
            "valid_until": utc(now + cfg["monitor_max_age_seconds"]),
            "operations_status": "critical" if critical else "attention" if warnings else "healthy",
            "source_status": source_status,
            "source_assessment_scope": "last retained attempts; not a new market-data eligibility assessment",
            "installation_id": cfg["installation_id"], "traffic_class": journal["traffic_class"],
            "journal": journal, "units": service_units, "backup": backup,
            "backup_age_seconds": backup_age, "disk_free_bytes": free_bytes, "issues": issues,
            "execution_authority": False, "external_active_users": None, "paid_customers": None,
            "coverage_complete": False, "scope": "private operator diagnostics; source readiness is separate from service health"}


def transitions(previous, current, at):
    before = {row["id"]: row for row in (previous or {}).get("issues", [])}
    after = {row["id"]: row for row in current["issues"]}
    result = [{"at": at, "transition": "opened", "issue": after[key]} for key in sorted(after.keys() - before.keys())]
    result += [{"at": at, "transition": "resolved", "issue": before[key]} for key in sorted(before.keys() - after.keys())]
    return result


def metrics(report):
    lines = ["# Financial Evidence private operations; no customer or execution metrics",
             f'financial_runtime_operations_healthy {int(report["operations_status"] == "healthy")}',
             f'financial_runtime_monitor_timestamp_seconds {datetime.fromisoformat(report["generated_at"]).timestamp()}',
             f'financial_runtime_source_blocked {int(report["source_status"] == "blocked")}',
             f'financial_runtime_disk_free_bytes {report.get("disk_free_bytes", 0)}']
    if report.get("backup_age_seconds") is not None:
        lines.append(f'financial_runtime_backup_age_seconds {report["backup_age_seconds"]}')
    for job in report.get("journal", {}).get("jobs", []):
        # Workflow IDs are constrained by the runtime schema.
        lines.append(f'financial_runtime_workflow_next_due_seconds{{job="{job["id"]}"}} {job["next_due"]}')
    return ("\n".join(lines) + "\n").encode()


def monitor(cfg, *, now=None, service_units=None):
    now = time.time() if now is None else now
    state = private(cfg["state"])
    previous = decode(regular(state / "health.json", 262144), limit=262144) if (state / "health.json").exists() else None
    try:
        runtime_identity(cfg)
        journal = inspect_journal(Path(cfg["root"]) / "runtime.sqlite")
        report = assess(cfg, journal, units() if service_units is None else service_units,
                        backup_status(state), shutil.disk_usage(cfg["root"]).free, now)
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError) as error:
        report = {"schema": "financial-evidence.runtime-health.v1", "generated_at": utc(now),
                  "valid_until": utc(now + cfg["monitor_max_age_seconds"]), "operations_status": "critical",
                  "source_status": "unknown", "issues": [{"id": "inspection_failed", "code": "inspection_failed",
                  "severity": "critical", "job": None}], "error_type": type(error).__name__,
                  "execution_authority": False, "external_active_users": None, "coverage_complete": False}
    changes = transitions(previous, report, report["generated_at"])
    ledger = state / "incidents.jsonl"
    if changes:
        existing = regular(ledger, 1_048_576) if ledger.exists() else b""
        appended = b"".join(encode(row) + b"\n" for row in changes)
        if len(existing) + len(appended) > 1_048_576:
            report["operations_status"] = "critical"
            report["issues"].append({"id": "incident_ledger_full", "code": "incident_ledger_full", "severity": "critical", "job": None})
        else:
            atomic(ledger, existing + appended, raw=True)
    atomic(state / "health.json", report)
    atomic(state / "metrics.prom", metrics(report), raw=True)
    return report


def dashboard():
    """A private live view; all upstream text is inserted with textContent."""
    return b'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Financial Evidence operations</title><style>
body{background:#f6f5ef;color:#202b26;font:16px system-ui;max-width:1100px;margin:3rem auto;padding:0 1.2rem}h1{font-size:2.5rem}h2{margin-top:2rem}button{padding:.6rem 1rem}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:.8rem;border-bottom:1px solid #ccd2c9}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;padding:1rem}.bad{color:#992e22}.good{color:#236442}.sub{color:#58665d}#status{font-size:1.4rem;font-weight:650}a{color:#236442}</style>
<h1>Financial Evidence operations</h1><p class="sub">Private research runtime. This console grants no trading permission.</p>
<p id="status">Loading current health...</p><p id="clock"></p><button id="refresh">Refresh</button>
<h2>Research workflows</h2><table><thead><tr><th>Workflow</th><th>Last attempt</th><th>Source observations</th><th>Next due</th></tr></thead><tbody id="jobs"></tbody></table>
<h2>Recovery</h2><pre id="recovery">Loading...</pre><h2>Active issues</h2><pre id="issues"></pre>
<p class="sub">Green operations describes the service. Source blocks retain their own reasons. Internal runs are not users or revenue. Refreshes every 20 seconds.</p>
<script>let latest=null;const byId=id=>document.getElementById(id);function freshness(){if(latest&&Date.now()>Date.parse(latest.valid_until)){byId('status').textContent='STALE: monitor has stopped reporting';byId('status').className='bad';}}
async function refresh(){try{const response=await fetch('/status.json',{cache:'no-store'});const r=await response.json();latest=r;byId('status').textContent='Operations: '+r.operations_status+' | Source data: '+r.source_status;byId('status').className=r.operations_status==='healthy'?'good':'bad';byId('clock').textContent='Observed '+r.generated_at;byId('jobs').replaceChildren();for(const j of (r.journal?.jobs||[])){const tr=document.createElement('tr');for(const text of [j.id,j.latest?.status||'No attempt',(j.latest?.observation_dates||[]).join(', '),new Date(j.next_due*1000).toISOString()]){const td=document.createElement('td');td.textContent=text;tr.append(td);}byId('jobs').append(tr);}byId('recovery').textContent=JSON.stringify(r.backup||{status:'Unknown'},null,2);byId('issues').textContent=JSON.stringify(r.issues,null,2);freshness();}catch(e){byId('status').textContent='UNAVAILABLE: cannot read the private monitor';byId('status').className='bad';}}
byId('refresh').addEventListener('click',refresh);refresh();setInterval(refresh,20000);setInterval(freshness,1000);</script></html>'''
