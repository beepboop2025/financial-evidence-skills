#!/usr/bin/env python3
"""Look up one retry key in a verified final stopped snapshot. Offline and read only."""

import argparse
from contextlib import closing, contextmanager
from importlib import import_module
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

from financial_evidence.runtime.contracts import KEY, NAME, Workflow, decode, digest
from ops_common import HEX, IDENTITY, MAX_DATABASE, readonly, regular, sha, verify_row


CAN_DESERIALIZE = hasattr(sqlite3.Connection, "deserialize")


class ArchiveUnavailable(ValueError):
    """A safe, machine-readable reason the requested archive could not be verified."""


@contextmanager
def verified_reader(data):
    # The database must be opened from the exact verified bytes. Opening the
    # original pathname again would permit a replacement between verification and query.
    if CAN_DESERIALIZE:
        with closing(sqlite3.connect(":memory:")) as db:
            db.deserialize(data)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA query_only=ON")
            yield db
    else:
        # Python 3.10 and builds without SQLite deserialization use private,
        # bounded temporary storage. No file in the source archive is changed.
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory) / "snapshot.sqlite"
            fd = os.open(local, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            with readonly(local) as db:
                yield db


@contextmanager
def verified_archive(journal, receipt, receipt_sha256, snapshot):
    if not (HEX.fullmatch(receipt_sha256) and HEX.fullmatch(snapshot)):
        raise ArchiveUnavailable("invalid_lookup_parameters")
    raw = regular(receipt, 65536)
    if sha(raw) != receipt_sha256:
        raise ArchiveUnavailable("receipt_digest_mismatch")
    binding = decode(raw, limit=65536)
    if (not isinstance(binding, dict) or binding.get("schema") != "financial-evidence.runtime-offsite-receipt.v1"
            or binding.get("status") != "verified" or binding.get("snapshot_id") != snapshot
            or not isinstance(binding.get("installation_id"), str) or not IDENTITY.fullmatch(binding["installation_id"])
            or not all(isinstance(binding.get(field), str) and HEX.fullmatch(binding[field])
                       for field in ("database_sha256", "repository_id", "keys_sha256"))):
        raise ArchiveUnavailable("receipt_binding_mismatch")
    data = regular(journal, MAX_DATABASE)
    if sha(data) != binding["database_sha256"]:
        raise ArchiveUnavailable("database_digest_mismatch")
    with verified_reader(data) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        meta = dict(db.execute("SELECT key,value FROM meta"))
        if (version not in (1, 2) or meta.get("installation_id") != binding["installation_id"]
                or meta.get("stopped") != "true" or db.execute("SELECT 1 FROM runs WHERE status='running' LIMIT 1").fetchone()):
            raise ArchiveUnavailable("final_stopped_snapshot_required")
        if version == 2:
            try:
                reader = import_module("financial_evidence.runtime.history")
            except ImportError as error:
                raise ArchiveUnavailable("successor_reader_required") from error
            if not callable(getattr(reader, "receipt_bytes", None)):
                raise ArchiveUnavailable("successor_reader_required")
        rows = [list(row) for row in db.execute("SELECT id,job,key,status,sha256 FROM runs ORDER BY id LIMIT 10001")]
        if len(rows) > 10000 or len(rows) != binding.get("runs") or digest(rows) != binding["keys_sha256"]:
            raise ArchiveUnavailable("retry_inventory_mismatch")
        yield db, meta, binding, version


def archive_outcome(db, meta, version, run, workflows):
    origin = meta["installation_id"]
    job = run["job"]
    if run["sha256"] is not None:
        if job not in workflows:
            spec = db.execute("SELECT spec,sha256 FROM jobs WHERE id=?", (job,)).fetchone()
            workflow = Workflow.parse(decode(spec["spec"]))
            if workflow.id != job or workflow.sha256 != spec["sha256"]:
                raise ArchiveUnavailable("workflow_binding_mismatch")
            workflows[job] = workflow
        origin = verify_row(db, run, meta, workflows[job])["installation_id"]
    elif run["status"] not in {"error", "interrupted"}:
        raise ArchiveUnavailable("terminal_outcome_unverified")
    elif version == 2 and db.execute("SELECT 1 FROM predecessor_runs WHERE run_id=?", (run["id"],)).fetchone():
        origin = db.execute("SELECT installation_id FROM predecessor").fetchone()[0]
    return {"outcome": run["status"], "origin_installation": origin, "run_id": run["id"], "receipt_sha256": run["sha256"]}


def lookup(journal, receipt, receipt_sha256, snapshot, job, key):
    if not (NAME.fullmatch(job) and KEY.fullmatch(key)):
        raise ArchiveUnavailable("invalid_lookup_parameters")
    with verified_archive(journal, receipt, receipt_sha256, snapshot) as (db, meta, binding, version):
        context = {"snapshot_id": snapshot, "archive_installation": meta["installation_id"], "acquisition_authority": False}
        run = db.execute("SELECT * FROM runs WHERE job=? AND key=?", (job, key)).fetchone()
        if run is None:
            return {**context, "status": "absent_in_this_snapshot"}
        return {**context, "status": "found", **archive_outcome(db, meta, version, run, {})}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--receipt-sha256", required=True, help="Trusted digest from the separately retained archive handoff")
    parser.add_argument("--snapshot", required=True, help="Exact 64-character snapshot ID")
    parser.add_argument("--job", required=True)
    parser.add_argument("--key", required=True)
    try:
        result = lookup(**vars(parser.parse_args(argv)))
    except ArchiveUnavailable as error:
        result = {"status": "unknown", "reason": str(error), "acquisition_authority": False}
    except (OSError, sqlite3.Error, ImportError, KeyError, IndexError, TypeError, ValueError):
        result = {"status": "unknown", "reason": "archive_unreadable_or_invalid", "acquisition_authority": False}
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] == "unknown" else 0


if __name__ == "__main__":
    sys.exit(main())
