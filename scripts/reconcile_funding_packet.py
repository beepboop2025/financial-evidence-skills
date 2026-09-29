#!/usr/bin/env python3
"""Repair coalesced path notifications without fetching unchanged source data."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

CAPTURE = re.compile(r"\d{8}T\d{6}\.\d{6}Z-[0-9a-f]{32}")


def read(path):
    if path.is_symlink() or path.stat().st_size > 262144:
        raise ValueError("invalid local reference")
    raw = path.read_bytes()
    return raw, json.loads(raw)


def needs_refresh(source, archive):
    _, current = read(source / "current.json")
    identifier = current["latest"]["capture_id"]
    if not isinstance(identifier, str) or not CAPTURE.fullmatch(identifier):
        raise ValueError("invalid completed source capture")
    try:
        _, reference = read(archive / "latest.json")
        attempt_id = reference["attempt_id"]
        if not isinstance(attempt_id, str) or not re.fullmatch(
            "[0-9a-f]{32}", attempt_id
        ):
            raise ValueError("invalid packet attempt identity")
        raw, attempt = read(archive / "attempts" / (attempt_id + ".json"))
        if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
            raise ValueError("packet attempt reference mismatch")
        return attempt["probe"]["capture_id"] != identifier
    except FileNotFoundError:
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("/var/lib/financial-evidence/funding-review"),
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("/var/lib/financial-evidence-institutional/archive"),
    )
    args = parser.parse_args()
    changed = needs_refresh(args.source, args.archive)
    if changed:
        subprocess.run(
            [
                "/usr/bin/systemctl",
                "start",
                "--no-block",
                "financial-evidence-packet-capture.service",
            ],
            check=True,
            timeout=10,
        )
    print(
        json.dumps(
            {
                "refresh_requested": changed,
                "source_documents_fetched_by_reconciler": False,
            }
        )
    )


if __name__ == "__main__":
    main()
