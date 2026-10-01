#!/usr/bin/env python3
"""Append a bounded operator observation; retain failures and report missing slots."""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from financial_evidence.reliability import encoded, now, sample, strict_json, summarize_releases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument(
        "--perspective",
        choices=("github_external", "hetzner_same_host", "local_verification"),
        required=True,
    )
    parser.add_argument(
        "--trigger",
        choices=("schedule", "workflow_dispatch", "manual"),
        default="manual",
    )
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    ledger = args.directory / "ledger.json"
    values = strict_json(ledger.read_bytes()) if ledger.exists() else []
    if not isinstance(values, list) or len(values) > 40000:
        raise ValueError("invalid or oversized ledger")
    run_id = (
        os.environ.get("GITHUB_RUN_ID", uuid.uuid4().hex)
        + "-"
        + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    )
    observation, _ = sample(
        perspective=args.perspective,
        trigger=args.trigger,
        run_id=run_id,
        include_packet_service=True,
    )
    values.append(observation)
    report = summarize_releases(values)
    (args.directory / ("sample-" + run_id + ".json")).write_bytes(encoded(observation))
    # The old artifact remains immutable. This run publishes a new cumulative artifact.
    ledger.write_bytes(encoded(values))
    (args.directory / "report.json").write_bytes(encoded(report))
    print(
        json.dumps(
            {
                "observed_at": now(),
                "available": observation["available"],
                "ready": observation["ready"],
                "perspective": args.perspective,
            }
        )
    )
    return (
        0
        if observation["available"]
        and observation["release_matches"]
        and observation["ready"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
