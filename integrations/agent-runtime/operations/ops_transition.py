"""Validate and atomically select two stopped, write-fenced journal directories on Linux."""

import ctypes
import fcntl
import os
from pathlib import Path
import stat
import subprocess

from ops_common import bound_identity, decode, inspect_journal, private, regular
from ops_successor import continuity


def proof(source_cfg, source, candidate):
    """Bind the fully materialized target to the exact live stopped source."""
    source, candidate = Path(source), Path(candidate)
    old = inspect_journal(source / "runtime.sqlite", full=True)
    bound_identity(old, source_cfg)
    new = inspect_journal(candidate / "runtime.sqlite", full=True)
    anchor = new.get("predecessor")
    if not anchor or anchor["installation_id"] != old["installation_id"]:
        raise ValueError("candidate does not retain the selected source namespace")
    rollback = old.get("predecessor") is not None
    kind = "rollback" if rollback else "successor"
    marker = decode(regular(candidate / (kind + ".json"), 65536), limit=65536)
    if (not old["stopped"] or not new["stopped"] or old["runs_by_status"].get("running")
            or new["runs_by_status"].get("running")
            or marker.get("schema") != "financial-evidence.stopped-" + kind + ".v1"
            or marker.get("final_stopped_verified") is not True or marker.get("admission_stopped") is not True
            or marker.get("prior") != anchor or marker.get("installation_id") != new["installation_id"]
            or marker.get("verified_receipts") != new["verified_receipts"]
            or marker.get("event_cursor") != new["event_cursor"]
            or marker.get("installation_limits") != new["limits"]
            or rollback and old["predecessor"]["installation_id"] != new["installation_id"]):
        raise ValueError("stopped preparation receipt or installation identity differs")
    digest = continuity(source / "runtime.sqlite")
    if (marker.get("continuity_sha256") != digest or continuity(candidate / "runtime.sqlite") != digest
            or new["verified_receipts"] != old["verified_receipts"]):
        raise ValueError("prepared candidate has different journal state")
    return new


def fenced(directory):
    # The host operator sets immutable on both SQLite files after draining writers.
    # Immutable blocks writes through an already-open descriptor and blocks unlink.
    directory = Path(directory)
    for parent in directory.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("directory ancestry must be controlled by root")
    info = directory.lstat()
    db = directory / "runtime.sqlite"
    if (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or db.lstat().st_uid != info.st_uid
            or any(p.name not in {"runtime.sqlite", "successor.json", "rollback.json"} for p in directory.iterdir())):
        raise ValueError("private quiescent journal directory required")
    attrs = subprocess.run(["/usr/bin/lsattr", "-d", "--", str(db)], check=True, capture_output=True, text=True)
    if "i" not in attrs.stdout.split()[0]:
        raise ValueError("journal must be immutable before selection")


def exchange(cfg, staged):
    """Idempotent until explicitly unfenced. A partially materialized target cannot be selected."""
    if os.getuid() != 0:
        raise ValueError("root is required to select a write-fenced production journal")
    live, staged = Path(cfg["root"]), Path(staged).absolute()
    private(staged.parent)
    if live == staged or live in staged.parents or staged in live.parents or live.stat().st_dev != staged.stat().st_dev:
        raise ValueError("two distinct generation directories on one filesystem required")
    # All transitions on this stable runtime root serialize on its persistent parent inode.
    lock = os.open(live.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return exchange_locked(cfg, live, staged)
    finally:
        os.close(lock)


def exchange_locked(cfg, live, staged):
    for p in (live, staged):
        fenced(p)
    if live.stat().st_uid != staged.stat().st_uid:
        raise ValueError("candidate and source must belong to the same runtime account")
    active = inspect_journal(live / "runtime.sqlite")["installation_id"]
    if active == cfg["installation_id"]:
        new = proof(cfg, live, staged)
        libc = ctypes.CDLL(None, use_errno=True)
        rename = libc.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(-100, os.fsencode(live), -100, os.fsencode(staged), 2) != 0:  # AT_FDCWD, RENAME_EXCHANGE
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
    else:
        new = proof(cfg, staged, live)
    # A retry after process death or power loss completes the same verification and fsync.
    for parent in {live.parent, staged.parent}:
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    if (inspect_journal(live / "runtime.sqlite")["installation_id"] != new["installation_id"]
            or inspect_journal(staged / "runtime.sqlite")["installation_id"] != cfg["installation_id"]):
        raise ValueError("atomic journal selection readback differs")
    return {"schema": "financial-evidence.stopped-selection.v1", "installation_id": new["installation_id"],
            "previous_installation_id": cfg["installation_id"], "stopped": True, "both_journals_fenced": True,
            "snapshot_id": new["predecessor"]["snapshot_id"], "event_cursor": new["event_cursor"]}
