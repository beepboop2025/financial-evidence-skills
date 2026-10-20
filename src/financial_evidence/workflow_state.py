"""Private, bounded workflow history and a destination-bound delivery outbox.

Only validated learning contracts enter the outbox. Credentials are never stored.
Delivery is at least once: immutable IDs and digest-matched receipts make retries
safe, including a crash after remote acceptance but before local acknowledgement.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .learning import contracts as c
from .learning.client import LearningDeliveryError
from .learning.insights import summarize

DAY = 86400
VALIDATORS = {"tool": c.tool_event, "decision": c.decision, "outcome": c.outcome}
SENDERS = {"tool": "record_tool", "decision": "record_decision", "outcome": "record_outcome"}


class WorkflowState:
    def __init__(self, directory, *, clock=time.time):
        self.root = Path(directory).expanduser().absolute()
        self.clock = clock
        if self.root.is_symlink():
            raise ValueError("workflow state must not be a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if (not self.root.is_dir() or self.root.stat().st_uid != os.getuid()
                or self.root.stat().st_mode & 0o077):
            raise ValueError("workflow state must be owned and private (0700)")
        self.path = self.root / "workflows.sqlite3"
        self._check()
        os.close(os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600))
        with self.db() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
                raise ValueError("unsupported workflow state version")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, workflow TEXT NOT NULL, selection TEXT NOT NULL,
                    mode TEXT NOT NULL, at REAL NOT NULL, status TEXT NOT NULL,
                    payload TEXT NOT NULL, sha256 TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, at REAL NOT NULL,
                    payload TEXT NOT NULL, sha256 TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS binding (id INTEGER PRIMARY KEY CHECK(id=1), digest TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS outbox (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT,
                    sha256 TEXT NOT NULL, at REAL NOT NULL, state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, due REAL NOT NULL,
                    lease TEXT, lease_until REAL, error TEXT,
                    UNIQUE(kind,id));
                PRAGMA user_version=1;
            """)
        self.prune()

    def _check(self):
        if (self.root.is_symlink() or not self.root.is_dir() or self.root.stat().st_uid != os.getuid()
                or self.root.stat().st_mode & 0o077):
            raise ValueError("workflow state must remain owned and private (0700)")
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = Path(str(self.path) + suffix)
            if path.is_symlink() or (path.exists() and (
                    not path.is_file() or path.stat().st_nlink != 1
                    or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077)):
                raise ValueError("workflow files must be owned, private, and not linked")

    @contextmanager
    def db(self):
        self._check()
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA secure_delete=ON")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def prune(self):
        now = c.moment(self.clock())
        with self.db() as db:
            db.execute("DELETE FROM runs WHERE at<?", (now - 30 * DAY,))
            db.execute("DELETE FROM records WHERE at<?", (now - 30 * DAY,))
            db.execute("UPDATE outbox SET payload=NULL,state='expired',lease=NULL WHERE payload IS NOT NULL AND at<?",
                       (now - 7 * DAY,))
            db.execute("DELETE FROM outbox WHERE payload IS NULL AND at<?", (now - 30 * DAY,))

    @staticmethod
    def _decode(row):
        value = json.loads(row["payload"])
        if c.digest(value) != row["sha256"]:
            raise ValueError("workflow record integrity mismatch")
        return value

    def save_run(self, value):
        raw = c.encode(value)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("workflow capture exceeds 4 MiB")
        with self.db() as db:
            count, size = db.execute("SELECT count(*),coalesce(sum(length(payload)),0) FROM runs").fetchone()
            if count >= 1000 or size + len(raw) > 64 * 1024 * 1024:
                raise ValueError("workflow journal is full; archive retained reviews before continuing")
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)",
                       (value["run_id"], value["workflow"], value["selection"], value["mode"],
                        value["completed_at"], value["status"], raw.decode(), c.digest(value)))

    def run(self, identifier):
        c.label(identifier, "run id")
        self.prune()
        with self.db() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("workflow run not found")
        return self._decode(row)

    def previous(self, workflow, selection, mode):
        self.prune()
        with self.db() as db:
            row = db.execute(
                "SELECT * FROM runs WHERE workflow=? AND selection=? AND mode=? "
                "AND status='ready_for_review' ORDER BY at DESC,rowid DESC LIMIT 1",
                (workflow, selection, mode)).fetchone()
        return self._decode(row) if row else None

    def history(self, *, limit=20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("history limit must be 1..100")
        self.prune()
        with self.db() as db:
            return [dict(row) for row in db.execute(
                "SELECT id AS run_id,workflow,selection,mode,at AS completed_at,status "
                "FROM runs ORDER BY at DESC,rowid DESC LIMIT ?", (limit,))]

    def record(self, kind, value, *, client=None):
        if kind not in VALIDATORS:
            raise ValueError("unknown learning record kind")
        now = c.moment(self.clock())
        value = VALIDATORS[kind](value, now)
        raw, sha = c.encode(value).decode(), c.digest(value)
        self.prune()
        with self.db() as db:
            if kind == "outcome":
                parent = db.execute("SELECT payload,sha256 FROM records WHERE kind='decision' AND id=?",
                                    (value["decision_id"],)).fetchone()
                if parent is None:
                    raise ValueError("outcome requires a retained decision")
                decision = self._decode(parent)
                if value["observed_at"] < decision["decided_at"] + decision["horizon_seconds"]:
                    raise ValueError("outcome precedes the decision horizon")
                for row in db.execute("SELECT payload,sha256 FROM records WHERE kind='outcome'"):
                    existing = self._decode(row)
                    if existing["decision_id"] == value["decision_id"] and existing["id"] != value["id"]:
                        raise ValueError("one immutable outcome per decision")
                if client is not None and not db.execute(
                        "SELECT 1 FROM outbox WHERE kind='decision' AND id=? AND state IN ('pending','sending','delivered')",
                        (value["decision_id"],)).fetchone():
                    raise ValueError("share the retained decision before queuing its outcome")
            old = db.execute("SELECT sha256 FROM records WHERE kind=? AND id=?", (kind, value["id"])).fetchone()
            if old and old["sha256"] != sha:
                raise ValueError("immutable learning record ID conflict")
            count, size = db.execute("SELECT count(*),coalesce(sum(length(payload)),0) FROM records").fetchone()
            if not old and (count >= 10000 or size + len(raw) > 64 * 1024 * 1024):
                raise ValueError("workflow record limit reached")
            db.execute("INSERT OR IGNORE INTO records VALUES(?,?,?,?,?)", (kind, value["id"], now, raw, sha))
            if client is not None:
                self._bind(db, client)
                queued = db.execute("SELECT sha256 FROM outbox WHERE kind=? AND id=?", (kind, value["id"])).fetchone()
                if queued and queued["sha256"] != sha:
                    raise ValueError("immutable outbox ID conflict")
                if not queued:
                    count, size = db.execute("SELECT count(*),coalesce(sum(length(payload)),0) FROM outbox WHERE payload IS NOT NULL").fetchone()
                    if count >= 10000 or size + len(raw) > 64 * 1024 * 1024:
                        raise ValueError("learning outbox is full")
                    db.execute("INSERT INTO outbox(kind,id,payload,sha256,at,state,due) VALUES(?,?,?,?,?,'pending',?)",
                               (kind, value["id"], raw, sha, now, now))
        return {"id": value["id"], "sha256": sha, "stored": True,
                "sharing": "queued" if client is not None else "local_only"}

    def get_record(self, kind, identifier):
        c.label(identifier)
        self.prune()
        with self.db() as db:
            row = db.execute("SELECT * FROM records WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        if row is None:
            raise ValueError("learning record not found in this workflow journal")
        return self._decode(row)

    @staticmethod
    def _bind(db, client):
        fingerprint = client.destination_fingerprint
        old = db.execute("SELECT digest FROM binding WHERE id=1").fetchone()
        if old and old["digest"] != fingerprint:
            raise ValueError("outbox belongs to another learning credential or destination")
        db.execute("INSERT OR IGNORE INTO binding VALUES(1,?)", (fingerprint,))

    def flush(self, client, *, limit=10):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("delivery limit must be 1..100")
        self.prune()
        delivered = 0
        for _ in range(limit):
            now, lease = self.clock(), uuid.uuid4().hex
            with self.db() as db:
                self._bind(db, client)
                row = db.execute("SELECT * FROM outbox WHERE state IN ('pending','sending') ORDER BY sequence LIMIT 1").fetchone()
                if row is None or row["due"] > now or (row["state"] == "sending" and row["lease_until"] > now):
                    break
                db.execute("UPDATE outbox SET state='sending',lease=?,lease_until=? WHERE sequence=?",
                           (lease, now + client.timeout + 60, row["sequence"]))
            failure, terminal, receipt = None, False, None
            try:
                value = self._decode(row)
                VALIDATORS[row["kind"]](value, now)
                if row["kind"] == "outcome":
                    with self.db() as db:
                        parent = db.execute("SELECT state FROM outbox WHERE kind='decision' AND id=?",
                                            (value["decision_id"],)).fetchone()
                    if parent is None or parent["state"] != "delivered":
                        raise ValueError("outcome decision has no delivery receipt")
                receipt = getattr(client, SENDERS[row["kind"]])(value)
                if (not isinstance(receipt, dict) or receipt.get("id") != row["id"]
                        or receipt.get("sha256") != row["sha256"]):
                    raise LearningDeliveryError("learning receipt mismatch")
            except Exception as exc:
                failure = "invalid_local_record" if isinstance(exc, (ValueError, KeyError, TypeError)) else "receipt_or_delivery_failed"
                status = getattr(exc, "status", None)
                terminal = failure == "invalid_local_record" or (isinstance(status, int) and 400 <= status < 500 and status not in {408, 429})
                delay = min(3600, 2 ** min(row["attempts"] + 1, 11))
                delay = max(delay, getattr(exc, "retry_after", None) or 0)
            with self.db() as db:
                if failure is None:
                    changed = db.execute("UPDATE outbox SET state='delivered',payload=NULL,lease=NULL,error=NULL "
                                         "WHERE sequence=? AND lease=?", (row["sequence"], lease)).rowcount
                    delivered += changed
                else:
                    db.execute("UPDATE outbox SET state=?,attempts=attempts+1,due=?,lease=NULL,error=? "
                               "WHERE sequence=? AND lease=?",
                               ("rejected" if terminal else "pending", self.clock() + delay, failure, row["sequence"], lease))
            if failure is not None:
                break
        return {"delivered": delivered, "outbox": self.outbox_status(),
                "scope": "Digest-matched ingestion receipts; not independent outcome verification."}

    def outbox_status(self):
        with self.db() as db:
            return dict(db.execute("SELECT state,count(*) FROM outbox GROUP BY state").fetchall())

    def discard_pending(self):
        """Local withdrawal: stop pending delivery and erase queued contents."""
        with self.db() as db:
            if db.execute("SELECT 1 FROM outbox WHERE state='sending' AND lease_until>?", (self.clock(),)).fetchone():
                raise ValueError("delivery is active; wait for it to finish before discarding")
            changed = db.execute("UPDATE outbox SET state='discarded',payload=NULL,lease=NULL "
                                 "WHERE payload IS NOT NULL").rowcount
        return {"discarded": changed, "remote_withdrawal_performed": False}

    def report(self):
        self.prune()
        with self.db() as db:
            runs = [self._decode(row) for row in db.execute("SELECT payload,sha256 FROM runs")]
            records = [(row["kind"], self._decode(row)) for row in db.execute("SELECT kind,payload,sha256 FROM records")]
        eligible = [run for run in runs if run["mode"] in {"shadow", "paper", "operator_reported_production"}]
        learning = summarize([("local", value) for kind, value in records if kind == "tool"])
        return {"schema": "financial-evidence.workflow-report.v1", "as_of": self.clock(),
                "scope": "This local journal only; no inference of distinct agents, people or organisations.",
                "runs": len(runs), "by_status": dict(Counter(run["status"] for run in runs)),
                "by_mode": dict(Counter(run["mode"] for run in runs)),
                "eligible_usage_runs": len(eligible),
                "active_utc_days": len({int(run["completed_at"] // DAY) for run in eligible}),
                "operator_confirmed_useful_workflows": learning["confirmed_useful_workflows"],
                "usefulness_is_operator_reported": True,
                "product_learning": learning,
                "decision_records": sum(kind == "decision" for kind, _ in records),
                "outcome_records": sum(kind == "outcome" for kind, _ in records),
                "independently_verified_outcomes": None, "outbox": self.outbox_status(),
                "retention_days": 30, "pending_delivery_retention_days": 7}
