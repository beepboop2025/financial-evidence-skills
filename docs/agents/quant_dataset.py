#!/usr/bin/env python3
"""Save a cited research table and receipt for a quant pipeline.

This is a capture of currently published evidence, not an as-published vintage
or proof that the data were knowable on the historical observation date.
"""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from financial_evidence.agents import EvidenceAgentClient
from financial_evidence.tables import DATASETS


def csv_cell(value):
    """Keep source strings inert in spreadsheets; preserve numeric signs."""
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n"))
        or value.lstrip().startswith(("=", "+", "-", "@"))
    ):
        return "'" + value
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=list(DATASETS))
    parser.add_argument("--entity", default="")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with EvidenceAgentClient() as client:
        result = client.query(args.dataset, args.entity, args.start_date, args.end_date, 100, args.offset)
    # A new directory prevents quietly replacing a previously captured cut.
    args.output.mkdir(parents=True, exist_ok=False)
    raw = (json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    (args.output / "evidence.json").write_bytes(raw)
    receipt = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "dataset": args.dataset, "row_count": result["returned_rows"],
        "next_offset": result["next_offset"],
        "history_scope": "currently_published_not_as_published_vintages",
        "financial_authority": "none", "transport_status": result["transport_status"],
    }
    rows = result["results"]
    if rows:
        csv_path = args.output / "rows.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows({key: csv_cell(value) for key, value in row.items()} for row in rows)
        receipt["csv_sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        receipt["csv_string_policy"] = "formula_prefixes_escaped_raw_values_in_evidence_json"
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
    return 0 if result["transport_status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
