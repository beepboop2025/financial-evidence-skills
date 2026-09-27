#!/usr/bin/env python3
"""Retain a bounded research packet and a spreadsheet index. Requires Financial Evidence 0.1.5.

One invocation reads one or two fixed public routes and writes a NEW directory.
No scheduler, telemetry, model, credentials, trading action or automatic retry.
An exit code describes retrieval only: 0 complete, 1 partial, 2 unavailable.
Code 3 means the local job failed. Source validity and freshness remain unassessed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

from financial_evidence import __version__
from financial_evidence.core import FIXED_ROUTE_OPENER, build_packet, utc_now


WORKFLOWS = {
    "funding": ["money-market"],
    "bank-context": ["bank-risk", "money-market"],
    "liquidity-context": ["market-liquidity", "money-market"],
}
EXIT_CODES = {"complete": 0, "partial": 1, "unavailable": 2}
FIELDS = [
    "topic", "product", "source_url", "retrieved_at", "transport_ok",
    "source_reported_state", "source_reported_clocks", "source_content_sha256",
    "evidence_status", "carrier_verification", "error",
]


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def spreadsheet_cell(value):
    """Treat spreadsheet formulas as text; the packet retains the original value."""
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def source_index(packet):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    for source in packet["sources"]:
        reported = source.get("source_reported", {})
        row = {key: source.get(key, "") for key in ("topic", "product", "source_url", "retrieved_at", "error")}
        row.update(
            transport_ok=str(source["ok"]).lower(),
            source_reported_state=json.dumps(reported.get("state", "not_reported"), ensure_ascii=False),
            source_reported_clocks=json.dumps(reported.get("clocks", "not_reported"), ensure_ascii=False),
            source_content_sha256=source.get("content_sha256", ""),
            evidence_status=packet["evidence_status"],
            carrier_verification=packet["carrier_verification"],
        )
        writer.writerow({key: spreadsheet_cell(value) for key, value in row.items()})
    return output.getvalue().encode("utf-8")


def collect(workflow, destination, *, verification=False, opener=FIXED_ROUTE_OPENER):
    if __version__ != "0.1.5":
        raise ValueError("This example requires financial-evidence 0.1.5; review changes before upgrading.")
    topics = WORKFLOWS[workflow]
    # Refuse to replace a previous capture, including a partially written one.
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)

    def marked_opener(request, **kwargs):
        request.add_header("User-Agent", "financial-evidence-workflow/1.0" if not verification
                           else "LiquiLens-Operator-Growth-Audit/1.0")
        if verification:
            request.add_header("X-Liquilens-Traffic-Class", "synthetic")
        return opener(request, **kwargs)

    packet = build_packet(topics, max_bytes=1_048_576, timeout=15, opener=marked_opener)
    artifacts = {"packet.json": encoded(packet), "sources.csv": source_index(packet)}
    manifest = {
        "schema": "liquidity-lab.workflow-capture.v1",
        "example_version": "1.0.0",
        "financial_evidence_version": __version__,
        "workflow": workflow,
        "topics": topics,
        "completed_at": utc_now(),
        "traffic_class": "operator_verification" if verification else "unattributed",
        "transport_status": packet["transport_status"],
        "status_semantics": "transport_only",
        "evidence_status": "not_evaluated",
        "carrier_verification": "not_performed",
        "freshness_assessment": "not_performed",
        "exit_code": EXIT_CODES[packet["transport_status"]],
        "files": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                  for name, data in artifacts.items()},
        "limits": [
            "Source generation and observation dates are separate from retrieval and completion times.",
            "The CSV indexes source metadata; full observations, units and limitations remain in packet.json.",
            "Local hashes detect file changes; they are not signatures or an independent source audit.",
            "This capture does not establish evidence validity, a trading signal, or an external user.",
        ],
    }
    for name, data in artifacts.items():
        with (destination / name).open("xb") as target:
            target.write(data)
    # Written last. A directory without run.json is an incomplete local write.
    with (destination / "run.json").open("xb") as target:
        target.write(encoded(manifest))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", choices=WORKFLOWS, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new output directory; never overwritten")
    parser.add_argument("--verification", action="store_true", help="mark operator tests, not user adoption")
    args = parser.parse_args(argv)
    try:
        manifest = collect(args.workflow, args.output, verification=args.verification)
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"local_job": "failed", "error": str(error)}), file=sys.stderr)
        return 3
    print(json.dumps(manifest, allow_nan=False))
    return manifest["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
