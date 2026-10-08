"""Single-host SQLite journal with atomic claims, budgets and immutable receipts."""

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import sqlite3
import uuid

from .contracts import Workflow, decode, encode, integer, moment, utc

DEFAULT_LIMITS = {"jobs": 100, "runs": 10000, "daily_runs": 1000, "receipt_bytes": 67_108_864}
CLASSES = {"unverified", "internal", "synthetic"}


class Store:
    def __init__(self, root, *, traffic_class=None, limits=None):
        self.root = Path(root).expanduser().absolute()
        if self.root.is_symlink():
            raise ValueError("runtime root must not be a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.root.is_dir() or self.root.stat().st_uid != os.getuid():
            raise ValueError("runtime root must be an owned directory")
        if self.root.stat().st_mode & 0o077:
            raise ValueError("runtime root must be private (mode 0700)")
        self.path = self.root / "runtime.sqlite"
        self._check_paths()
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(fd)
        if traffic_class is not None and traffic_class not in CLASSES:
            raise ValueError("installation ownership cannot be self-verified")
        selected = dict(DEFAULT_LIMITS)
        if limits is not None:
            if not isinstance(limits, dict) or set(limits) - set(selected):
                raise ValueError("unknown runtime limit")
            selected.update(limits)
        for key, value in selected.items():
            integer(value, 1, DEFAULT_LIMITS[key], key)
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported runtime database version")
            db.executescript("""
              CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, spec BLOB NOT NULL, sha256 TEXT NOT NULL,
                next_due REAL NOT NULL, failures INTEGER NOT NULL DEFAULT 0,
                breaker_until REAL NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1);
              CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, job TEXT NOT NULL REFERENCES jobs(id), key TEXT NOT NULL,
                status TEXT NOT NULL, started REAL NOT NULL, finished REAL,
                bundle BLOB, sha256 TEXT, error TEXT, UNIQUE(job,key));
              CREATE INDEX IF NOT EXISTS run_started ON runs(started);
              CREATE INDEX IF NOT EXISTS run_job ON runs(job,status);
              CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
                kind TEXT NOT NULL, job TEXT, run TEXT, detail TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS acknowledgements (
                run TEXT PRIMARY KEY REFERENCES runs(id), at REAL NOT NULL,
                outcome TEXT NOT NULL CHECK(outcome IN ('useful','not_useful')));
              PRAGMA user_version=1;
            """)
            db.execute("BEGIN IMMEDIATE")
            values = {"installation_id": uuid.uuid4().hex, "traffic_class": traffic_class or "unverified",
                      "limits": encode(selected).decode(), "stopped": "false", "last_clock": "0"}
            for key, value in values.items():
                db.execute("INSERT OR IGNORE INTO meta VALUES (?,?)", (key, value))
            if traffic_class and self.meta(db, "traffic_class") != traffic_class:
                raise ValueError("existing installation class is immutable")
            if limits is not None and decode(self.meta(db, "limits").encode()) != selected:
                raise ValueError("existing installation limits are immutable")
            db.commit()

    def _check_paths(self):
        for name in ("runtime.sqlite", "runtime.sqlite-journal", "runtime.sqlite-wal", "runtime.sqlite-shm"):
            path = self.root / name
            if path.is_symlink():
                raise ValueError("runtime storage must not contain symlinks")
            if path.exists() and (not path.is_file() or path.stat().st_nlink != 1
                                  or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077):
                raise ValueError("runtime storage must be private and owned")

    @contextmanager
    def connection(self):
        self._check_paths()
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def meta(db, key):
        return db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()[0]

    @staticmethod
    def event(db, at, kind, job=None, run=None, detail=None):
        db.execute("INSERT INTO events(at,kind,job,run,detail) VALUES (?,?,?,?,?)",
                   (at, kind, job, run, encode(detail or {}).decode()))

    def check_clock(self, db, at):
        moment(at)
        previous = float(self.meta(db, "last_clock"))
        # Concurrent callers can sample their clocks before waiting for the DB
        # lock. Clamp a small ordering skew; never reopen a budget/cooldown.
        if at < previous - 5:
            raise ValueError("UTC clock moved backwards; no new work admitted")
        at = max(at, previous)
        db.execute("UPDATE meta SET value=? WHERE key='last_clock'", (str(at),))
        return at

    def register(self, workflow, at):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            at = self.check_clock(db, at)
            existing = db.execute("SELECT sha256 FROM jobs WHERE id=?", (workflow.id,)).fetchone()
            if existing:
                if existing[0] != workflow.sha256:
                    raise ValueError("workflow id is immutable; use a new id for a changed policy")
                return {"id": workflow.id, "created": False, "sha256": workflow.sha256}
            limits = decode(self.meta(db, "limits").encode())
            if db.execute("SELECT count(*) FROM jobs").fetchone()[0] >= limits["jobs"]:
                raise OverflowError("workflow allowance reached")
            db.execute("INSERT INTO jobs(id,spec,sha256,next_due) VALUES (?,?,?,?)",
                       (workflow.id, workflow.document, workflow.sha256, at))
            self.event(db, at, "registered", workflow.id)
            return {"id": workflow.id, "created": True, "sha256": workflow.sha256}

    def jobs(self):
        with self.connection() as db:
            return [{"workflow": decode(r["spec"]), "sha256": r["sha256"],
                     "next_due": utc(r["next_due"]), "failures": r["failures"],
                     "breaker_until": utc(r["breaker_until"]), "enabled": bool(r["enabled"])}
                    for r in db.execute("SELECT * FROM jobs ORDER BY id")]

    def claim(self, job, key, at, *, scheduled=False):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            at = self.check_clock(db, at)
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            if not row:
                raise ValueError("unknown workflow")
            # Expired claims remain receipts; their same idempotency key is never retried.
            for old in db.execute("SELECT id FROM runs WHERE job=? AND status='running' AND started<=?",
                                  (job, at - 120)).fetchall():
                db.execute("UPDATE runs SET status='interrupted',finished=?,error='lease_expired' WHERE id=?", (at, old[0]))
                self.event(db, at, "interrupted", job, old[0])
            previous = db.execute("SELECT id,status FROM runs WHERE job=? AND key=?", (job, key)).fetchone()
            if previous:
                return {"admitted": False, "reason": "existing_run", "run_id": previous[0], "status": previous[1]}
            workflow = Workflow.parse(decode(row["spec"]))
            if workflow.sha256 != row["sha256"]:
                raise ValueError("workflow storage integrity mismatch")
            reason = None
            limits = decode(self.meta(db, "limits").encode())
            start = int(at // 86400) * 86400
            if self.meta(db, "stopped") == "true":
                reason = "stopped"
            elif not row["enabled"]:
                reason = "paused"
            elif db.execute("SELECT 1 FROM runs WHERE job=? AND status='running'", (job,)).fetchone():
                reason = "in_flight"
            elif row["breaker_until"] > at:
                reason = "circuit_open"
            elif row["next_due"] > at:
                reason = "not_due" if scheduled else "cooldown"
            elif db.execute("SELECT count(*) FROM runs WHERE job=? AND started>=?", (job, start)).fetchone()[0] >= workflow.value["daily_run_limit"]:
                reason = "workflow_daily_limit"
            elif db.execute("SELECT count(*) FROM runs WHERE started>=?", (start,)).fetchone()[0] >= limits["daily_runs"]:
                reason = "installation_daily_limit"
            elif db.execute("SELECT count(*) FROM runs").fetchone()[0] >= limits["runs"]:
                reason = "journal_full"
            elif db.execute("SELECT coalesce(sum(length(bundle)),0) FROM runs").fetchone()[0] >= limits["receipt_bytes"]:
                reason = "receipt_storage_full"
            if reason:
                return {"admitted": False, "reason": reason, "run_id": None}
            identifier = uuid.uuid4().hex
            db.execute("INSERT INTO runs(id,job,key,status,started) VALUES (?,?,?,'running',?)",
                       (identifier, job, key, at))
            db.execute("UPDATE jobs SET next_due=? WHERE id=?", (at + workflow.value["interval_seconds"], job))
            self.event(db, at, "started", job, identifier)
            return {"admitted": True, "run_id": identifier, "workflow": workflow.value,
                    "started": at,
                    "installation_id": self.meta(db, "installation_id"),
                    "traffic_class": self.meta(db, "traffic_class")}

    def finish(self, identifier, at, record, error=None):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            at = self.check_clock(db, at)
            row = db.execute("SELECT * FROM runs WHERE id=?", (identifier,)).fetchone()
            if row is None or row["status"] != "running":
                raise ValueError("run no longer owns its claim")
            if at >= row["started"] + 120:
                record, error = None, "lease_expired"
            raw = encode(record) if record is not None else None
            limits = decode(self.meta(db, "limits").encode())
            used = db.execute("SELECT coalesce(sum(length(bundle)),0) FROM runs").fetchone()[0]
            if raw and used + len(raw) > limits["receipt_bytes"]:
                raw, record, error = None, None, "receipt_storage_full"
            status = "error" if error else ("complete" if record["assessment"]["status"] == "requirements_met" else "blocked")
            sha = hashlib.sha256(raw).hexdigest() if raw else None
            db.execute("UPDATE runs SET status=?,finished=?,bundle=?,sha256=?,error=? WHERE id=?",
                       (status, at, raw, sha, error, identifier))
            transport_failed = bool(error) or record["result"]["transport_status"] != "complete"
            failures = db.execute("SELECT failures FROM jobs WHERE id=?", (row["job"],)).fetchone()[0]
            failures = failures + 1 if transport_failed else 0
            until = at + min(3600, 60 * 2 ** min(failures - 3, 6)) if failures >= 3 else 0
            db.execute("UPDATE jobs SET failures=?,breaker_until=? WHERE id=?", (failures, until, row["job"]))
            self.event(db, at, "finished", row["job"], identifier, {
                "status": status, "sha256": sha, "error": error,
                "change": record["change"] if record else None,
                "revision": record["result"]["revision"] if record else None})
        return self.run(identifier)

    def run(self, identifier):
        with self.connection() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (identifier,)).fetchone()
            if row is None:
                raise ValueError("unknown run")
            value = {k: row[k] for k in ("id", "job", "key", "status", "error", "sha256")}
            value.update(started_at=utc(row["started"]), finished_at=utc(row["finished"]) if row["finished"] is not None else None)
            if row["bundle"] is not None:
                if hashlib.sha256(row["bundle"]).hexdigest() != row["sha256"]:
                    raise ValueError("receipt integrity mismatch")
                value["record"] = decode(row["bundle"])
            return value

    def prior_revision(self, job, identifier):
        with self.connection() as db:
            row = db.execute("SELECT id FROM runs WHERE job=? AND id<>? AND bundle IS NOT NULL ORDER BY started DESC,id DESC LIMIT 1",
                             (job, identifier)).fetchone()
        return self.run(row[0])["record"]["result"]["revision"] if row else None

    def control(self, at, *, stopped=None, job=None, enabled=None):
        if job is None and type(stopped) is not bool:
            raise ValueError("explicit stop state required")
        if job is not None and type(enabled) is not bool:
            raise ValueError("explicit enabled state required")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            at = self.check_clock(db, at)
            if job is None:
                current = self.meta(db, "stopped")
                value = "true" if stopped else "false"
                if current != value:
                    db.execute("UPDATE meta SET value=? WHERE key='stopped'", (value,))
                    self.event(db, at, "stopped" if stopped else "resumed")
            else:
                row = db.execute("SELECT enabled FROM jobs WHERE id=?", (job,)).fetchone()
                if row is None:
                    raise ValueError("unknown workflow")
                if bool(row[0]) != enabled:
                    db.execute("UPDATE jobs SET enabled=? WHERE id=?", (int(enabled), job))
                    self.event(db, at, "enabled" if enabled else "paused", job)
        return {"job": job, "enabled": enabled, "stopped": stopped,
                "scope": "admission_of_new_research_runs; in_flight_reads_may_finish"}

    def events(self, after=0, limit=100):
        integer(after, 0, 2**63 - 1, "after")
        integer(limit, 1, 100, "limit")
        with self.connection() as db:
            rows = db.execute("SELECT * FROM events WHERE id>? ORDER BY id LIMIT ?", (after, limit)).fetchall()
            high = db.execute("SELECT coalesce(max(id),0) FROM events").fetchone()[0]
        events = [{"id": r["id"], "at": utc(r["at"]), "kind": r["kind"], "job": r["job"],
                   "run_id": r["run"], "detail": decode(r["detail"].encode())} for r in rows]
        cursor = events[-1]["id"] if events else after
        return {"events": events, "next_cursor": cursor, "high_watermark": high,
                "has_more": cursor < high, "delivery": "cursor_polling; consumer_commits_cursor_after_processing"}

    def acknowledge(self, identifier, outcome, at):
        if outcome not in {"useful", "not_useful"}:
            raise ValueError("outcome must be useful or not_useful")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            at = self.check_clock(db, at)
            row = db.execute("SELECT status FROM runs WHERE id=?", (identifier,)).fetchone()
            if row is None or row[0] not in {"complete", "blocked"}:
                raise ValueError("a finished research response is required")
            old = db.execute("SELECT outcome FROM acknowledgements WHERE run=?", (identifier,)).fetchone()
            if old and old[0] != outcome:
                raise ValueError("acknowledgement is immutable")
            if not old:
                db.execute("INSERT INTO acknowledgements VALUES (?,?,?)", (identifier, at, outcome))
                self.event(db, at, "acknowledged", run=identifier, detail={"outcome": outcome})
        return {"run_id": identifier, "outcome": outcome, "verification": "local_operator_reported"}

    def report(self):
        with self.connection() as db:
            counts = dict(db.execute("SELECT status,count(*) FROM runs GROUP BY status"))
            acknowledgements = dict(db.execute("SELECT outcome,count(*) FROM acknowledgements GROUP BY outcome"))
            return {"schema": "financial-evidence.runtime-metrics.v1",
                    "installation_id": self.meta(db, "installation_id"),
                    "traffic_class": self.meta(db, "traffic_class"),
                    "stopped": self.meta(db, "stopped") == "true",
                    "limits": decode(self.meta(db, "limits").encode()),
                    "runs_by_status": counts, "operator_reported_outcomes": acknowledgements,
                    "stored_receipt_bytes": db.execute("SELECT coalesce(sum(length(bundle)),0) FROM runs").fetchone()[0],
                    "external_active_users": None, "returning_external_users": None,
                    "paid_customers": None, "revenue": None, "coverage_complete": False,
                    "scope": "this_local_installation_only; no_remote_telemetry",
                    "meaning": "complete means research requirements met, not useful work, trade approval or a customer"}

    def backup(self, destination):
        """SQLite online backup; refuse replacement and retain a consistent journal."""
        destination = Path(destination)
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with self.connection() as source:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("backup integrity check failed")
            finally:
                target.close()
        return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "scope": "local_snapshot; offsite_delivery_not_performed"}
