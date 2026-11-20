"""Read-only scheduler admission after a journal actually reports exhaustion."""

import argparse
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys


def admission(journal, installation):
    path = Path(journal).absolute()
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_mode & 0o077
        or info.st_uid != os.getuid()
    ):
        raise ValueError("private scheduler-owned journal required")
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=4)
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (1, 2):
            raise ValueError("unsupported journal version")
        meta = dict(db.execute("SELECT key,value FROM meta WHERE key IN ('limits','installation_id')"))
        if meta["installation_id"] != installation:
            raise ValueError("scheduler installation differs")
        limits = json.loads(meta["limits"])
        limit = limits["receipt_bytes"]
        run_limit = limits["runs"]
        if type(run_limit) is not int or not 1 <= run_limit <= 10_000:
            raise ValueError("invalid run allowance")
        if type(limit) is not int or not 1 <= limit <= 67_108_864:
            raise ValueError("invalid receipt allowance")
        runs, used = db.execute("SELECT count(*), coalesce(sum(length(bundle)),0) FROM runs").fetchone()
        # A successor retains predecessor keys and outcomes. Only proof from
        # this installation may prevent the new installation from acquiring.
        sql = "SELECT id FROM runs WHERE error='receipt_storage_full'"
        if version == 2:
            sql += " AND NOT EXISTS (SELECT 1 FROM predecessor_runs WHERE run_id=runs.id)"
        failure = db.execute(sql + " ORDER BY started LIMIT 1").fetchone()
        return {
            "schema": "financial-evidence.capacity-admission.v1",
            "admitted": runs < run_limit and used < limit and failure is None,
            "stored_receipt_bytes": used,
            "runs": runs,
            "run_limit": run_limit,
            "limit": limit,
            "first_unrecordable_run": failure[0] if failure else None,
        }
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal")
    parser.add_argument("installation")
    args = parser.parse_args()
    try:
        report = admission(args.journal, args.installation)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({"admitted": False, "inspection_error": type(exc).__name__}), file=sys.stderr)
        sys.exit(255)
    if not report["admitted"]:
        print(json.dumps(report), file=sys.stderr)
        sys.exit(255)  # systemd records a visible failure and starts no acquisition.
