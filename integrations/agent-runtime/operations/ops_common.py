"""Bounded, read-only inspection of an existing Financial Evidence installation."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import uuid

from financial_evidence.runtime.contracts import Workflow, decode, encode
from financial_evidence.runtime.engine import implementation, verify_bundle

OPS_VERSION = "1.0.3"
MAX_DATABASE = 134_217_728
HEX = re.compile(r"[0-9a-f]{64}\Z")
IDENTITY = re.compile(r"[0-9a-f]{32}\Z")


def utc(at=None):
    return datetime.fromtimestamp(time.time() if at is None else at, timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path, limit):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ValueError("not a bounded regular file")
        raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("file exceeds allowance")
        return raw


def private(path, *, create=False):
    path = Path(path).absolute()
    if create:
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("private directory missing or symlinked")
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("operations directory must be private and owned")
    # A privileged backup must not put credentials or restored data below a
    # directory another account can replace.
    if os.getuid() == 0:
        for parent in path.parents:
            info = parent.stat()
            if parent.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError("unsafe privileged directory ancestry")
    return path


def atomic(path, value, *, raw=False):
    path = Path(path)
    content = value if raw else encode(value) + b"\n"
    temporary = path.with_name(".write-" + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def config(path):
    value = decode(regular(path, 32_768), limit=32_768)
    expected = {"schema", "root", "state", "installation_id", "package_version",
                "implementation_sha256", "repository_id", "jobs", "due_grace_seconds",
                "backup_max_age_seconds", "monitor_max_age_seconds", "min_free_bytes"}
    if not isinstance(value, dict) or set(value) != expected or value["schema"] != "financial-evidence.runtime-ops.v1":
        raise ValueError("invalid operations configuration")
    for key in ("root", "state"):
        p = Path(value[key])
        if not p.is_absolute() or ".." in p.parts or p.is_symlink():
            raise ValueError("operations paths must be absolute and nonsymlinked")
    if Path(value["root"]).resolve() == Path(value["state"]).resolve():
        raise ValueError("operations state must be separate from the research journal")
    if not IDENTITY.fullmatch(value["installation_id"]):
        raise ValueError("invalid installation identity")
    if not all(HEX.fullmatch(value[key]) for key in ("implementation_sha256", "repository_id")):
        raise ValueError("exact implementation and repository identities required")
    if value["package_version"] != "0.1.7":
        raise ValueError("unsupported runtime package")
    if not isinstance(value["jobs"], dict) or not 1 <= len(value["jobs"]) <= 100:
        raise ValueError("expected workflows required")
    for name, digest in value["jobs"].items():
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name) or not HEX.fullmatch(digest):
            raise ValueError("invalid expected workflow")
    for key, low, high in (("due_grace_seconds", 60, 3600), ("backup_max_age_seconds", 300, 172800),
                           ("monitor_max_age_seconds", 60, 3600), ("min_free_bytes", 1048576, 107374182400)):
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError("invalid operational threshold")
    return value


@contextmanager
def readonly(path):
    path = Path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_DATABASE or info.st_mode & 0o077:
        raise ValueError("invalid private journal file")
    db = sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    deadline = time.monotonic() + 30
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        yield db
    finally:
        db.close()


def inspect_journal(path, *, full=False):
    """Never construct Store here: diagnostics must not create or migrate state."""
    with readonly(path) as db:
        if db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("unsupported journal schema")
        if full and (db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or db.execute("PRAGMA foreign_key_check").fetchone()):
            raise ValueError("journal integrity failure")
        meta = dict(db.execute("SELECT key,value FROM meta"))
        if not IDENTITY.fullmatch(meta.get("installation_id", "")) or meta.get("traffic_class") not in {"internal", "synthetic", "unverified"}:
            raise ValueError("invalid installation metadata")
        if meta.get("stopped") not in {"true", "false"}:
            raise ValueError("invalid admission state")
        clock = float(meta["last_clock"])
        if not math.isfinite(clock):
            raise ValueError("invalid journal clock")
        limits = decode(meta["limits"].encode())
        jobs = []
        count = db.execute("SELECT count(*) FROM jobs").fetchone()[0]
        total = db.execute("SELECT count(*) FROM runs").fetchone()[0]
        if count > 100 or total > 10000:
            raise ValueError("journal exceeds supported bounds")
        for row in db.execute("SELECT * FROM jobs ORDER BY id"):
            workflow = Workflow.parse(decode(row["spec"]))
            if workflow.id != row["id"] or workflow.sha256 != row["sha256"]:
                raise ValueError("workflow integrity mismatch")
            last = db.execute("SELECT * FROM runs WHERE job=? ORDER BY started DESC,id DESC LIMIT 1", (row["id"],)).fetchone()
            latest = None
            if last:
                latest = {k: last[k] for k in ("id", "status", "started", "finished", "error")}
                if last["bundle"] is not None:
                    record = verify_row(last, meta, workflow)
                    latest.update(reasons=record["assessment"]["reasons"], rows=record["assessment"]["rows_checked"],
                                  observation_dates=sorted({r["as_of"] for r in record["result"].get("results", []) if r.get("as_of")}))
            jobs.append({"id": row["id"], "sha256": row["sha256"], "interval_seconds": workflow.value["interval_seconds"],
                         "next_due": row["next_due"], "enabled": bool(row["enabled"]), "failures": row["failures"],
                         "breaker_until": row["breaker_until"], "latest": latest})
        verified = 0
        if full:
            specs = {row["id"]: Workflow.parse(decode(row["spec"])) for row in db.execute("SELECT * FROM jobs")}
            for row in db.execute("SELECT * FROM runs ORDER BY id"):
                if row["bundle"] is not None:
                    verify_row(row, meta, specs[row["job"]])
                    verified += 1
                elif row["status"] not in {"error", "running", "interrupted"}:
                    raise ValueError("completed attempt lacks receipt")
        keys = [[row["id"], row["job"], row["key"], row["status"], row["sha256"]]
                for row in db.execute("SELECT id,job,key,status,sha256 FROM runs ORDER BY id")]
        return {"installation_id": meta["installation_id"], "traffic_class": meta["traffic_class"],
                "stopped": meta["stopped"] == "true", "last_clock": clock, "limits": limits, "jobs": jobs,
                "runs": total, "runs_by_status": dict(db.execute("SELECT status,count(*) FROM runs GROUP BY status")),
                "receipt_bytes": db.execute("SELECT coalesce(sum(length(bundle)),0) FROM runs").fetchone()[0],
                "event_cursor": db.execute("SELECT coalesce(max(id),0) FROM events").fetchone()[0],
                "keys_sha256": sha(encode(keys)), "verified_receipts": verified}


def verify_row(row, meta, workflow):
    record = decode(row["bundle"])
    verify_bundle({"schema": "financial-evidence.runtime-bundle.v1", "sha256": row["sha256"], "record": record})
    if (sha(row["bundle"]) != row["sha256"] or record["run_id"] != row["id"]
            or record["installation_id"] != meta["installation_id"] or record["traffic_class"] != meta["traffic_class"]
            or record["workflow_sha256"] != workflow.sha256
            or abs(datetime.fromisoformat(record["started_at"]).timestamp() - row["started"]) > .00001
            or row["finished"] is None or row["finished"] < datetime.fromisoformat(record["captured_at"]).timestamp() - .00001
            or row["status"] != ("complete" if record["assessment"]["status"] == "requirements_met" else "blocked")):
        raise ValueError("receipt journal binding mismatch")
    return record


def bound_identity(value, cfg):
    if value["installation_id"] != cfg["installation_id"]:
        raise ValueError("unexpected installation")
    if {j["id"]: j["sha256"] for j in value["jobs"]} != cfg["jobs"]:
        raise ValueError("workflow inventory changed; review operations configuration")


def runtime_identity(cfg):
    if (importlib.metadata.version("financial-evidence") != cfg["package_version"]
            or implementation()["sha256"] != cfg["implementation_sha256"]):
        raise ValueError("installed runtime identity differs")


def snapshot(root, target):
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    with readonly(Path(root) / "runtime.sqlite") as source:
        destination = sqlite3.connect(target)
        try:
            deadline = time.monotonic() + 60
            def progress(*_):
                if time.monotonic() > deadline:
                    raise TimeoutError("snapshot deadline exceeded")
            source.backup(destination, pages=256, progress=progress)
        finally:
            destination.close()
    return inspect_journal(target, full=True)
