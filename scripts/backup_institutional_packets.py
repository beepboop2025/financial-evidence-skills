#!/usr/bin/env python3
"""Restore-verify a tagged packet snapshot; exclude private usage and credentials."""

import argparse
import fcntl
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from offsite_funding_review import atomic_status, encoded, read_file, restic

from financial_evidence.institutional import packet, read_json


def _backup(source, state, repository_id):
    if (
        not re.fullmatch(r"[0-9a-f]{64}", repository_id)
        or source.is_symlink()
        or state.is_symlink()
    ):
        raise ValueError("invalid repository or directory identity")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / ".backup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        atomic_status(
            state / "status.json",
            {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()},
        )
        if json.loads(restic("cat", "config"))["id"] != repository_id:
            raise ValueError("unexpected repository")
        with tempfile.TemporaryDirectory(prefix=".packets-", dir=state) as temporary:
            work = Path(temporary)
            stage = work / "public-packets"
            stage.mkdir()
            hashes = {}
            with (source / ".archive.lock").open("r") as source_lock:
                fcntl.flock(source_lock, fcntl.LOCK_SH)
                for folder in (source / "packets").iterdir():
                    if folder.name.startswith("."):
                        continue
                    manifest, _, _ = packet(source, folder.name)
                    for receipt in manifest.get("publisher_receipts", {}).values():
                        relative = "publisher-blobs/" + receipt["sha256"]
                        if (
                            hashlib.sha256(
                                read_file(source, relative, 2000000)
                            ).hexdigest()
                            != receipt["sha256"]
                        ):
                            raise ValueError("publisher blob hash mismatch")
                latest = read_json(source / "latest.json")
                attempt = read_file(
                    source, "attempts/" + latest["attempt_id"] + ".json", 262144
                )
                if hashlib.sha256(attempt).hexdigest() != latest["sha256"]:
                    raise ValueError("latest attempt hash mismatch")
                for folder in ("packets", "attempts", "publisher-blobs"):
                    for path in sorted((source / folder).rglob("*")):
                        if path.is_symlink():
                            raise ValueError("archive contains symlink")
                        if not path.is_file() or any(
                            part.startswith(".")
                            for part in path.relative_to(source).parts
                        ):
                            continue
                        relative = str(path.relative_to(source))
                        raw = read_file(source, relative, 2000000)
                        destination = stage / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(raw)
                        hashes[relative] = hashlib.sha256(raw).hexdigest()
                for name in ("latest.json", "reliability.json", "coverage.json"):
                    raw = read_file(source, name, 262144)
                    (stage / name).write_bytes(raw)
                    hashes[name] = hashlib.sha256(raw).hexdigest()
            if not hashes or not any(name.startswith("packets/") for name in hashes):
                raise ValueError("no public packets to protect")
            summary = [
                json.loads(line)
                for line in restic(
                    "backup",
                    "--host",
                    "financial-evidence-institutional",
                    "--tag",
                    "funding-original-publisher-packets-v1",
                    str(stage),
                ).splitlines()
            ]
            identifier = next(
                x["snapshot_id"] for x in summary if x.get("message_type") == "summary"
            )
            if not re.fullmatch(r"[0-9a-f]{8,64}", identifier):
                raise ValueError("unexpected snapshot identity")
            snapshots = json.loads(restic("snapshots", identifier))
            if len(snapshots) != 1:
                raise ValueError("ambiguous snapshot")
            snapshot = snapshots[0]["id"]
            restored = work / "restore"
            restored.mkdir()
            restic("restore", snapshot, "--target", str(restored))
            root = restored / str(stage).lstrip("/")
            actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
            if actual != set(hashes):
                raise ValueError("restored inventory differs")
            for relative, expected in hashes.items():
                if (
                    hashlib.sha256(read_file(root, relative, 2000000)).hexdigest()
                    != expected
                ):
                    raise ValueError("restored packet differs")
            result = {
                "schema": "financial-evidence.packet-backup.v1",
                "status": "PASS",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "repository_id": repository_id,
                "snapshot_id": snapshot,
                "verified_files": len(hashes),
                "inventory_sha256": hashlib.sha256(encoded(hashes)).hexdigest(),
                "usage_data_included": False,
                "credentials_included": False,
                "source_modified": False,
            }
            atomic_status(state / ("inventory-" + snapshot + ".json"), hashes)
            atomic_status(state / "status.json", result)
            with (state / ("receipt-" + snapshot + ".json")).open("x") as stream:
                json.dump(result, stream, indent=2)
                stream.write("\n")
            return result


def backup(source, state, repository_id):
    if source.is_symlink() or state.is_symlink():
        raise ValueError("invalid source or state")
    try:
        return _backup(source, state, repository_id)
    except BlockingIOError:
        raise
    except Exception as error:
        if state.is_dir():
            atomic_status(
                state / "status.json",
                {
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
    args = parser.parse_args()
    print(json.dumps(backup(args.source, args.state, args.repository_id)))
