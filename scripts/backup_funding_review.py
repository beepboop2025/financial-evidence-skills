#!/usr/bin/env python3
"""Pull completed funding captures over SSH without overwriting retained evidence."""

import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

REMOTE_ROOT = "/var/lib/financial-evidence/funding-review"
INVENTORY = r"""
import base64,hashlib,json,pathlib
root=pathlib.Path('/var/lib/financial-evidence/funding-review')
current=(root/'current.json').read_bytes()
assert len(current)<=131072
captures=[]
for path in sorted((root/'captures').glob('*/manifest.json')):
    if path.is_symlink() or path.parent.is_symlink():raise ValueError('symlink')
    raw=path.read_bytes()
    assert len(raw)<=131072
    doc=json.loads(raw)
    captures.append({'path':path.parent.relative_to(root).as_posix(),
      'manifest_sha256':hashlib.sha256(raw).hexdigest(),
      'artifacts':doc['artifact_sha256']})
assert len(captures)<=100000
print(json.dumps({'current':base64.b64encode(current).decode(),'captures':captures}))
"""


def artifact_limit(name):
    """Match capture limits, including the retained byte proving an oversize response."""
    if Path(name).name in {"manifest.json", "current.json"}:
        return 131072
    response_limit = 4 * 1024 * 1024 if Path(name).name == "atlas.response" else 2 * 1024 * 1024
    return response_limit + 1


def digest(path, limit):
    if path.is_symlink() or not path.is_file():
        raise ValueError("backup artifact is not a regular file")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("backup artifact exceeds bound")
    return hashlib.sha256(raw).hexdigest()


def validate_inventory(inventory):
    files = []
    for capture in inventory["captures"]:
        path = capture["path"]
        if not re.fullmatch(r"captures/[A-Za-z0-9._-]+", path):
            raise ValueError("unsafe capture path")
        if not re.fullmatch(r"[0-9a-f]{64}", capture["manifest_sha256"]):
            raise ValueError("invalid manifest hash")
        files.append(path + "/manifest.json")
        for name, sha in capture["artifacts"].items():
            if not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:json|response|csv)", name):
                raise ValueError("unsafe artifact name")
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise ValueError("invalid artifact hash")
            files.append(path + "/" + name)
    current_bytes = base64.b64decode(inventory["current"], validate=True)
    current = json.loads(current_bytes)
    expected = {c["path"]: c["manifest_sha256"] for c in inventory["captures"]}
    for key in ("latest", "last_available", "last_ready"):
        ref = current.get(key)
        if ref and expected.get(ref["capture"]) != ref["manifest_sha256"]:
            raise ValueError("current references absent or changed evidence")
    return files, current_bytes


def backup(host, output):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host):
        raise ValueError("host must be an SSH alias or hostname")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    if output.is_symlink():
        raise ValueError("backup root cannot be a symlink")
    with (output / ".backup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=15",
                host,
                "python3 -",
            ],
            input=INVENTORY,
            text=True,
            capture_output=True,
            check=True,
            timeout=120,
        )
        inventory = json.loads(result.stdout)
        files, current_bytes = validate_inventory(inventory)
        for name in files:
            target = output
            for part in Path(name).parts:
                target = target / part
                if target.is_symlink():
                    raise ValueError("symlink in backup destination")
        # Existing files are immutable: a changed upstream file is a verification
        # failure, never permission to replace historical backup bytes.
        subprocess.run(
            [
                "rsync",
                "-rt",
                "--ignore-existing",
                "--safe-links",
                "--timeout=60",
                "--files-from=-",
                "-e",
                "ssh -o BatchMode=yes -o ConnectTimeout=15",
                host + ":" + REMOTE_ROOT + "/",
                str(output) + "/",
            ],
            input="\n".join(files) + "\n",
            text=True,
            check=True,
            timeout=600,
        )
        for capture in inventory["captures"]:
            folder = output / capture["path"]
            if folder.is_symlink() or folder.parent.is_symlink():
                raise ValueError("symlink in capture path")
            if digest(folder / "manifest.json", 131072) != capture["manifest_sha256"]:
                raise ValueError("manifest hash mismatch")
            for name, sha in capture["artifacts"].items():
                if digest(folder / name, artifact_limit(name)) != sha:
                    raise ValueError("artifact hash mismatch: " + name)
        receipt = {
            "schema": "financial-evidence.funding-backup.v1",
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "host": host,
            "completed_captures": len(inventory["captures"]),
            "verified_files": len(files),
            "current_sha256": hashlib.sha256(current_bytes).hexdigest(),
            "latest_capture": json.loads(current_bytes)["latest"]["capture_id"],
            "source_retention": "no_deletion",
            "restore_test": "not_performed_by_pull",
        }
        temp = output / ".current.backup.tmp"
        temp.write_bytes(current_bytes)
        os.replace(temp, output / "current.json")
        receipt_dir = output / "backup-receipts"
        receipt_dir.mkdir(mode=0o700, exist_ok=True)
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ.json")
        (receipt_dir / name).write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="liquilens-hetzner")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    backup(args.host, args.output_dir)
