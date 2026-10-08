"""Encrypted offsite backup with durable intent, exact restore and no upload replay."""

from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import uuid

from ops_common import (HEX, MAX_DATABASE, atomic, bound_identity, decode, encode,
                        inspect_journal, private, regular, runtime_identity, sha, snapshot, utc)


class Restic:
    """Use the owner's existing encrypted repository. Never print provider output."""

    def __call__(self, *args):
        process = subprocess.run(["restic", "--json", *args], capture_output=True, timeout=300, check=False)
        if process.returncode:
            raise RuntimeError("restic_" + args[0] + "_exit_" + str(process.returncode))
        if len(process.stdout) > 8_388_608:
            raise ValueError("restic output exceeds allowance")
        return process.stdout


def repository(restic, expected):
    if json.loads(restic("cat", "config")).get("id") != expected:
        raise ValueError("offsite repository identity changed")


def restored_payload(restic, receipt, destination):
    snapshot_id = receipt["snapshot_id"]
    path = Path(receipt["payload_path"])
    if not HEX.fullmatch(snapshot_id) or not path.is_absolute() or ".." in path.parts or path.name != "payload":
        raise ValueError("invalid exact snapshot receipt")
    restic("restore", snapshot_id, "--target", str(destination))
    expected = destination / path.relative_to("/")
    # This snapshot must contain only the exact two-file research payload.
    actual = set()
    for item in destination.rglob("*"):
        if item.is_symlink():
            raise ValueError("restored symlink refused")
        if item.is_file():
            actual.add(item)
    if actual != {expected / "runtime.sqlite", expected / "manifest.json"}:
        raise ValueError("restored inventory differs")
    manifest_raw = regular(expected / "manifest.json", 65536)
    if sha(manifest_raw) != receipt["manifest_sha256"]:
        raise ValueError("restored manifest differs")
    manifest = decode(manifest_raw, limit=65536)
    database = regular(expected / "runtime.sqlite", MAX_DATABASE)
    if sha(database) != manifest["database_sha256"]:
        raise ValueError("restored database checksum differs")
    inspected = inspect_journal(expected / "runtime.sqlite", full=True)
    if inspected != manifest["journal"]:
        raise ValueError("restored journal semantics differ")
    if inspected["installation_id"] != receipt["installation_id"]:
        raise ValueError("restored installation differs")
    return expected, manifest


def _backup(cfg, restic, state, now):
    active_path = state / "active-backup.json"
    previous = decode(regular(state / "backup.json", 65536), limit=65536) if (state / "backup.json").exists() else {}
    last_verified = previous.get("last_verified")
    repository(restic, cfg["repository_id"])
    if active_path.exists():
        active = decode(regular(active_path, 65536), limit=65536)
        if active["installation_id"] != cfg["installation_id"] or active["repository_id"] != cfg["repository_id"]:
            raise ValueError("pending backup belongs to another installation")
    else:
        if shutil.disk_usage(state).free < cfg["min_free_bytes"]:
            raise ValueError("backup disk reserve exhausted")
        receipts = private(state / "receipts", create=True)
        if len(list(receipts.iterdir())) >= 10000:
            raise ValueError("backup receipt allowance reached")
        pending = private(state / "pending", create=True)
        if list(pending.iterdir()):
            # A preparation crash is retained for inspection, never discarded.
            raise ValueError("orphaned preparation requires inspection")
        operation = uuid.uuid4().hex
        work = private(pending / operation, create=True)
        payload = private(work / "payload", create=True)
        journal = snapshot(cfg["root"], payload / "runtime.sqlite")
        bound_identity(journal, cfg)
        manifest = {"schema": "financial-evidence.runtime-offsite-payload.v1", "created_at": utc(now),
                    "operation_id": operation, "package_version": cfg["package_version"],
                    "implementation_sha256": cfg["implementation_sha256"],
                    "database_sha256": sha(regular(payload / "runtime.sqlite", MAX_DATABASE)), "journal": journal}
        atomic(payload / "manifest.json", manifest)
        active = {"operation_id": operation, "phase": "prepared", "payload_path": str(payload),
                  "manifest_sha256": sha(regular(payload / "manifest.json", 65536)),
                  "installation_id": cfg["installation_id"], "repository_id": cfg["repository_id"],
                  "started_epoch": now, "started_at": utc(now)}
        atomic(active_path, active)
    payload = Path(active["payload_path"])
    if payload != state / "pending" / active["operation_id"] / "payload" or not re.fullmatch(r"[0-9a-f]{32}", active["operation_id"]):
        raise ValueError("unsafe pending operation path")
    completed_path = state / "receipts" / (active["operation_id"] + ".json")
    if completed_path.exists():
        completed = decode(regular(completed_path, 65536), limit=65536)
        if (completed.get("status") != "verified" or completed["snapshot_id"] != active.get("snapshot_id")
                or completed["manifest_sha256"] != active["manifest_sha256"]):
            raise ValueError("completed operation receipt differs")
        atomic(state / "backup.json", {"schema": "financial-evidence.runtime-offsite.v1", "status": "verified", "last_verified": completed})
        if payload.parent.exists():
            shutil.rmtree(payload.parent)
        active_path.unlink()
        return completed
    if sha(regular(payload / "manifest.json", 65536)) != active["manifest_sha256"]:
        raise ValueError("pending manifest changed")
    manifest = decode(regular(payload / "manifest.json", 65536), limit=65536)
    if sha(regular(payload / "runtime.sqlite", MAX_DATABASE)) != manifest["database_sha256"]:
        raise ValueError("pending snapshot changed")
    bound_identity(manifest["journal"], cfg)
    atomic(state / "backup.json", {"schema": "financial-evidence.runtime-offsite.v1", "status": "running",
                                   "started_epoch": active["started_epoch"], "operation_id": active["operation_id"],
                                   "last_verified": last_verified})
    tag = "runtime-operation-" + active["operation_id"]
    if active["phase"] == "prepared":
        active["phase"] = "upload_started"
        atomic(active_path, active)  # Commit intent before the provider mutation.
        output = restic("backup", "--host", "financial-evidence-runtime", "--tag", "runtime-ops-v1",
                        "--tag", "installation-" + cfg["installation_id"], "--tag", tag, "--", str(payload))
        summaries = [row for line in output.splitlines() if (row := json.loads(line)).get("message_type") == "summary"]
        if len(summaries) != 1 or not HEX.fullmatch(summaries[0].get("snapshot_id", "")):
            raise ValueError("upload result requires reconciliation")
        active.update(phase="uploaded", snapshot_id=summaries[0]["snapshot_id"])
        atomic(active_path, active)
    elif active["phase"] == "upload_started":
        rows = json.loads(restic("snapshots", "--host", "financial-evidence-runtime", "--tag", tag))
        matches = [row for row in rows if tag in row.get("tags", []) and row.get("paths") == [str(payload)]
                   and HEX.fullmatch(row.get("id", ""))]
        if len(matches) != 1:
            raise ValueError("uncertain upload retained; exact acceptance not found")
        active.update(phase="uploaded", snapshot_id=matches[0]["id"])
        atomic(active_path, active)
    if active["phase"] != "uploaded":
        raise ValueError("unknown backup phase")
    with tempfile.TemporaryDirectory(prefix=".restore-", dir=state) as temporary:
        _, restored = restored_payload(restic, active, Path(temporary))
    verified = {"schema": "financial-evidence.runtime-offsite-receipt.v1", "status": "verified",
                **{k: active[k] for k in ("operation_id", "snapshot_id", "payload_path", "manifest_sha256",
                                         "installation_id", "repository_id", "started_at")},
                "verified_at": utc(), "database_sha256": restored["database_sha256"],
                "runs": restored["journal"]["runs"], "verified_receipts": restored["journal"]["verified_receipts"],
                "keys_sha256": restored["journal"]["keys_sha256"], "event_cursor": restored["journal"]["event_cursor"],
                "verification": "exact encrypted snapshot restored; all receipts and retry keys checked",
                "source_writes": False, "mac_required": False, "snapshot_deletion": False}
    receipts = private(state / "receipts", create=True)
    receipt_path = receipts / (active["operation_id"] + ".json")
    if receipt_path.exists():
        old = decode(regular(receipt_path, 65536), limit=65536)
        if old["snapshot_id"] != verified["snapshot_id"]:
            raise ValueError("immutable backup receipt differs")
        verified = old
    else:
        atomic(receipt_path, verified)
    atomic(state / "backup.json", {"schema": "financial-evidence.runtime-offsite.v1", "status": "verified", "last_verified": verified})
    # Only temporary local staging belonging to this accepted operation is
    # removed. The source journal, old backups and remote snapshots are retained.
    shutil.rmtree(payload.parent)
    active_path.unlink()
    return verified


def backup(cfg, *, restic=None, now=None):
    state = private(cfg["state"])
    runtime_identity(cfg)
    fd = os.open(state / "backup.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            return _backup(cfg, restic or Restic(), state, time.time() if now is None else now)
        except Exception as error:
            existing = decode(regular(state / "backup.json", 65536), limit=65536) if (state / "backup.json").exists() else {}
            atomic(state / "backup.json", {"schema": "financial-evidence.runtime-offsite.v1", "status": "failed",
                                           "failed_at": utc(), "error_type": type(error).__name__,
                                           "last_verified": existing.get("last_verified"),
                                           "pending_intent_retained": (state / "active-backup.json").exists()})
            raise


def recover(cfg, receipt_path, target, *, restic=None):
    """Restore into a new stopped installation. Never touch an active scheduler."""
    runtime_identity(cfg)
    restic = restic or Restic()
    repository(restic, cfg["repository_id"])
    receipt = decode(regular(receipt_path, 65536), limit=65536)
    if receipt.get("status") != "verified" or receipt["repository_id"] != cfg["repository_id"] or receipt["installation_id"] != cfg["installation_id"]:
        raise ValueError("verified installation receipt required")
    return restore_stopped(cfg, receipt, target, restic=restic)


def restore_stopped(cfg, receipt, target, *, restic, selection="retained_verified_receipt"):
    """Common full verification and stopped admission for both recovery paths."""
    target = Path(target).absolute()
    if target.exists() or target.is_symlink():
        raise ValueError("restore target must not exist")
    private(target.parent)
    target.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix=".recovery-", dir=target) as temporary:
        payload, manifest = restored_payload(restic, receipt, Path(temporary))
        bound_identity(manifest["journal"], cfg)
        # Only publish a database after its stop flag is durable. A crash or
        # failed stop transaction cannot leave an apparently usable live copy.
        database = Path(temporary) / "stopped.sqlite"
        fd = os.open(database, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(regular(payload / "runtime.sqlite", MAX_DATABASE))
            stream.flush()
            os.fsync(stream.fileno())
        # Admission is stopped before this directory can be selected by an
        # operator. No source fetch or interrupted-key replay occurs in recovery.
        with closing(sqlite3.connect(database)) as db:
            db.execute("UPDATE meta SET value='true' WHERE key='stopped'")
            db.commit()
        restored = inspect_journal(database, full=True)
        if restored["keys_sha256"] != receipt["keys_sha256"] or not restored["stopped"]:
            raise ValueError("recovery did not preserve retry keys and stop state")
        with database.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(database, target / "runtime.sqlite")
        report = {"schema": "financial-evidence.runtime-recovery.v1", "status": "verified", "restored_at": utc(),
                  "snapshot_id": receipt["snapshot_id"], "installation_id": receipt["installation_id"],
                  "restored_receipts": restored["verified_receipts"], "keys_sha256": restored["keys_sha256"],
                  "source_network_calls": 0, "admission_stopped": True, "target": str(target), "selection": selection}
        atomic(target / "recovery.json", report)
        return report
