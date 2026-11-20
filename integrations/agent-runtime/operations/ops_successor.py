"""Prepare a stopped, self-contained successor from a verified predecessor snapshot."""

from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import uuid
import zlib

from ops_backup import Restic, repository, restored_payload
from ops_common import (
    HEX,
    IDENTITY,
    atomic,
    bound_identity,
    decode,
    encode,
    inspect_journal,
    private,
    regular,
    sha,
)


def inspect_predecessor(db, meta, limits, full):
    rows = db.execute("SELECT * FROM predecessor LIMIT 2").fetchall()
    if len(rows) != 1:
        raise ValueError("successor must have one sealed predecessor")
    row = dict(rows[0])
    if (
        not IDENTITY.fullmatch(row["installation_id"])
        or row["installation_id"] == meta["installation_id"]
        or not all(HEX.fullmatch(row[k]) for k in ("database_sha256", "snapshot_id", "keys_sha256"))
        or not 0 <= row["canonical_bytes"] <= limits["receipt_bytes"]
        or not 0 <= row["runs"] <= limits["runs"]
    ):
        raise ValueError("invalid predecessor anchor")
    if full:
        found = db.execute("SELECT count(*),coalesce(sum(raw_size),0) FROM predecessor_runs").fetchone()
        if tuple(found) != (row["runs"], row["canonical_bytes"]):
            raise ValueError("predecessor inventory differs")
        keys = [
            list(item)
            for item in db.execute(
                "SELECT r.id,r.job,r.key,r.status,r.sha256 FROM runs r JOIN predecessor_runs p "
                "ON p.run_id=r.id ORDER BY r.id"
            )
        ]
        if sha(encode(keys)) != row["keys_sha256"]:
            raise ValueError("predecessor retry keys differ")
        if db.execute(
            "SELECT 1 FROM predecessor_runs p JOIN runs r ON r.id=p.run_id "
            "WHERE r.bundle IS NOT NULL OR (p.payload IS NULL) != (r.sha256 IS NULL) LIMIT 1"
        ).fetchone():
            raise ValueError("predecessor receipt state differs")
    return row


def seal(database, receipt, archived):
    """Transform only a private copy of the already verified predecessor database."""
    if archived.get("predecessor") or archived["runs_by_status"].get("running"):
        raise ValueError("requires a first-generation predecessor with no in-flight claims")
    with closing(sqlite3.connect(database)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "CREATE TABLE predecessor (installation_id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL, "
            "database_sha256 TEXT NOT NULL, keys_sha256 TEXT NOT NULL, runs INTEGER NOT NULL, "
            "canonical_bytes INTEGER NOT NULL)"
        )
        db.execute(
            "CREATE TABLE predecessor_runs (run_id TEXT PRIMARY KEY REFERENCES runs(id), "
            "payload BLOB, raw_size INTEGER NOT NULL)"
        )
        db.execute(
            "INSERT INTO predecessor VALUES (?,?,?,?,?,?)",
            (
                archived["installation_id"],
                receipt["snapshot_id"],
                receipt["database_sha256"],
                archived["keys_sha256"],
                archived["runs"],
                archived["receipt_bytes"],
            ),
        )
        for run in db.execute("SELECT id,bundle FROM runs ORDER BY id"):
            raw = run["bundle"]
            packed = zlib.compress(raw) if raw is not None else None
            db.execute("INSERT INTO predecessor_runs VALUES (?,?,?)", (run["id"], packed, len(raw or b"")))
        db.execute("UPDATE runs SET bundle=NULL WHERE bundle IS NOT NULL")
        db.execute("UPDATE meta SET value=? WHERE key='installation_id'", (uuid.uuid4().hex,))
        db.execute("UPDATE meta SET value='true' WHERE key='stopped'")
        db.execute("PRAGMA user_version=2")
        db.commit()
        db.execute("VACUUM")


def prepare(cfg, receipt_path, target, *, restic=None):
    """No live data writes. The operator has to select and configure a new installation."""
    target = Path(target).absolute()
    private(target.parent)
    if target.exists() or target.is_symlink():
        raise ValueError("a new successor directory is required")
    receipt = decode(regular(receipt_path, 65536), limit=65536)
    if (
        receipt.get("status") != "verified"
        or receipt["repository_id"] != cfg["repository_id"]
        or receipt["installation_id"] != cfg["installation_id"]
    ):
        raise ValueError("verified predecessor receipt required")
    restic = restic or Restic()
    repository(restic, cfg["repository_id"])
    with tempfile.TemporaryDirectory(dir=target.parent) as temp:
        payload, manifest = restored_payload(restic, receipt, Path(temp))
        archived = manifest["journal"]
        bound_identity(archived, cfg)
        if (
            manifest["database_sha256"] != receipt["database_sha256"]
            or archived["keys_sha256"] != receipt["keys_sha256"]
            or archived["event_cursor"] != receipt["event_cursor"]
        ):
            raise ValueError("predecessor verification receipt differs from recovered journal")
        db_path = Path(temp) / "successor.sqlite"
        shutil.copyfile(payload / "runtime.sqlite", db_path)
        db_path.chmod(0o600)
        seal(db_path, receipt, archived)
        new = inspect_journal(db_path, full=True)
        for key in (
            "keys_sha256",
            "event_cursor",
            "runs",
            "runs_by_status",
            "jobs",
            "verified_receipts",
            "limits",
            "last_clock",
            "traffic_class",
        ):
            if new[key] != archived[key]:
                raise ValueError("successor differs in " + key)
        if (
            not new["stopped"]
            or new["receipt_bytes"]
            or new["installation_id"] == archived["installation_id"]
        ):
            raise ValueError("successor admission state is invalid")
        report = {
            "schema": "financial-evidence.stopped-successor.v1",
            "source_writes": False,
            "source_cutover": False,
            "installation_id": new["installation_id"],
            "admission_stopped": True,
            "prior": new["predecessor"],
            "verified_receipts": new["verified_receipts"],
            "event_cursor": new["event_cursor"],
            "installation_limits": new["limits"],
        }
        with db_path.open("rb") as stream:
            os.fsync(stream.fileno())
        target.mkdir(mode=0o700, exist_ok=False)
        os.replace(db_path, target / "runtime.sqlite")
        atomic(target / "successor.json", report)
    return report
