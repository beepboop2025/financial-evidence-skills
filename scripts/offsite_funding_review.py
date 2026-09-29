#!/usr/bin/env python3
"""Back up completed funding captures, then restore and verify the exact snapshot.

Restic configuration and credentials come from the service environment. This
command never initializes repositories, deletes snapshots, or changes captures.
"""

import argparse
import base64
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import uuid

from backup_funding_review import validate_inventory


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def read_file(root, relative, limit):
    """Read bounded regular files without following any relative symlink."""
    parts = Path(relative).parts
    if (
        not parts
        or Path(relative).is_absolute()
        or any(p in (".", "..") for p in parts)
    ):
        raise ValueError("unsafe relative path")
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor
        )
        with os.fdopen(file_descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise ValueError("artifact is not bounded regular data")
            raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise ValueError("artifact grew beyond its bound")
            return raw
    finally:
        os.close(descriptor)


def stage_archive(source, destination):
    current = read_file(source, "current.json", 131072)
    captures = []
    for folder in sorted((source / "captures").iterdir()):
        if not re.fullmatch(r"[A-Za-z0-9._-]+", folder.name) or folder.is_symlink():
            raise ValueError("unsafe capture directory")
        if not (folder / "manifest.json").exists():
            continue  # The capture service publishes its manifest last.
        relative = "captures/" + folder.name
        raw = read_file(source, relative + "/manifest.json", 131072)
        manifest = json.loads(raw)
        captures.append(
            {
                "path": relative,
                "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                "artifacts": manifest["artifact_sha256"],
            }
        )
        if len(captures) > 100000:
            raise ValueError("capture inventory exceeds bound")
    inventory = {"current": base64.b64encode(current).decode(), "captures": captures}
    validate_inventory(inventory)
    if not captures or not json.loads(current).get("latest"):
        raise ValueError("no completed current capture")
    hashes = {}
    for capture in captures:
        names = {**capture["artifacts"], "manifest.json": capture["manifest_sha256"]}
        if "manifest.json" in capture["artifacts"]:
            raise ValueError("manifest cannot reference itself")
        for name, expected in names.items():
            relative = capture["path"] + "/" + name
            raw = read_file(
                source, relative, 131072 if name == "manifest.json" else 2097153
            )
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError("capture artifact hash mismatch")
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(raw)
            hashes[relative] = expected
    with (destination / "current.json").open("xb") as stream:
        stream.write(current)
    hashes["current.json"] = hashlib.sha256(current).hexdigest()
    return {
        "completed_captures": len(captures),
        "latest_capture": json.loads(current)["latest"]["capture_id"],
        "files": hashes,
    }


def verify_restore(directory, expected):
    actual = set()
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("restored symlink")
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
    if actual != set(expected):
        raise ValueError("restored file inventory differs")
    for relative, digest in expected.items():
        if (
            hashlib.sha256(read_file(directory, relative, 2097153)).hexdigest()
            != digest
        ):
            raise ValueError("restored artifact hash mismatch")


def restic(*arguments):
    result = subprocess.run(
        ["restic", "--json", *arguments], capture_output=True, timeout=1800, check=False
    )
    if result.returncode:
        # Credentials and provider error bodies must never reach public logs.
        raise RuntimeError(
            "restic " + arguments[0] + " exited " + str(result.returncode)
        )
    if len(result.stdout) > 8 * 1024 * 1024:
        raise ValueError("restic output exceeds bound")
    return result.stdout


def atomic_status(path, value):
    temporary = path.with_name(".status-" + uuid.uuid4().hex)
    with temporary.open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def backup(source, state, repository_id):
    if not re.fullmatch(r"[0-9a-f]{64}", repository_id):
        raise ValueError("expected repository identity required")
    if source.is_symlink() or state.is_symlink():
        raise ValueError("source or state root is a symlink")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(state / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = datetime.now(timezone.utc).isoformat()
        result = {
            "schema": "financial-evidence.funding-offsite.v1",
            "started_at": started,
        }
        atomic_status(state / "status.json", {**result, "status": "running"})
        try:
            config = json.loads(restic("cat", "config"))
            if config.get("id") != repository_id:
                raise ValueError("restic repository identity changed")
            with tempfile.TemporaryDirectory(
                prefix=".verified-backup-", dir=state
            ) as temporary:
                work = Path(temporary)
                stage = work / "archive"
                stage.mkdir(mode=0o700)
                inventory = stage_archive(source, stage)
                output = restic(
                    "backup",
                    "--host",
                    "financial-evidence-hetzner",
                    "--tag",
                    "funding-review",
                    "--",
                    str(stage.resolve()),
                )
                summaries = [
                    row
                    for line in output.splitlines()
                    if (row := json.loads(line)).get("message_type") == "summary"
                ]
                if len(summaries) != 1 or not re.fullmatch(
                    r"[0-9a-f]{64}", summaries[0].get("snapshot_id", "")
                ):
                    raise ValueError("backup snapshot identity missing or ambiguous")
                snapshot = summaries[0]["snapshot_id"]
                restored = work / "restore"
                restic("restore", snapshot, "--target", str(restored))
                verify_restore(
                    restored / stage.resolve().relative_to("/"), inventory["files"]
                )
                result.update(
                    status="pass",
                    verified_at=datetime.now(timezone.utc).isoformat(),
                    repository_id=repository_id,
                    snapshot_id=snapshot,
                    completed_captures=inventory["completed_captures"],
                    verified_files=len(inventory["files"]),
                    latest_capture=inventory["latest_capture"],
                    inventory_sha256=hashlib.sha256(
                        encoded(inventory["files"])
                    ).hexdigest(),
                    verification="exact_snapshot_restored_and_all_file_hashes_verified",
                    encryption="restic_repository",
                    mac_required=False,
                    source_writes=False,
                    deletion_policy="no_snapshot_or_source_deletion",
                )
            receipts = state / "receipts"
            receipts.mkdir(mode=0o700, exist_ok=True)
            with (receipts / (uuid.uuid4().hex + ".json")).open("xb") as stream:
                stream.write(encoded(result))
            atomic_status(state / "status.json", result)
            return result
        except Exception as error:
            atomic_status(
                state / "status.json",
                {
                    **result,
                    "status": "failed",
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "error_type": type(error).__name__,
                },
            )
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--repository-id", required=True)
    arguments = parser.parse_args()
    try:
        receipt = backup(arguments.source, arguments.state, arguments.repository_id)
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1)
    print(json.dumps(receipt, sort_keys=True))
