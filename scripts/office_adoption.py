#!/usr/bin/env python3
"""Summarize a private, consenting office pilot CSV. No network or enrollment.

Evidence references are reviewer-supplied SHA-256 digests, not proof that their
contents are authentic. Output contains counts, never participant aliases.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re

FIELDS = (
    "participant_alias", "participant_type", "client", "workflow", "task_reference",
    "occurred_at_utc", "consent_recorded", "external_participant_confirmed",
    "operator_test", "reviewer_task_completed", "source_scope_accepted",
    "consent_sha256", "independence_review_sha256", "evidence_sha256",
    "manual_baseline_minutes", "review_minutes",
)
CLIENTS = ("google_sheets", "excel", "libreoffice", "onlyoffice", "collabora",
           "nextcloud", "jupyter", "openbb", "linux_cli", "other")
WORKFLOWS = ("funding", "institutions", "liquidity", "mixed")
FLAGS = FIELDS[6:11]
LABEL = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
MAX_BYTES = 8 * 1024 * 1024


def read_records(raw: bytes):
    if len(raw) > MAX_BYTES:
        raise ValueError("pilot CSV exceeds 8 MiB")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if reader.fieldnames != list(FIELDS):
        raise ValueError("use the exact pilot-template.csv header")
    records, seen = [], {}
    duplicates = 0
    for line, original in enumerate(reader, 2):
        if line > 10001:
            raise ValueError("pilot CSV exceeds 10000 records")
        if None in original or any(value is None for value in original.values()):
            raise ValueError(f"row {line}: incorrect number of fields")
        row = {key: value.strip() for key, value in original.items()}
        if any(len(value) > 128 for value in row.values()):
            raise ValueError(f"row {line}: field exceeds 128 characters")
        if any(not LABEL.fullmatch(row[key]) for key in ("participant_alias", "task_reference")):
            raise ValueError(f"row {line}: use opaque lowercase aliases, not names or URLs")
        if (row["participant_type"] not in ("analyst", "organization")
                or row["client"] not in CLIENTS or row["workflow"] not in WORKFLOWS):
            raise ValueError(f"row {line}: unsupported category")
        for key in FLAGS:
            if row[key] not in ("true", "false"):
                raise ValueError(f"row {line}: {key} must be true or false")
            row[key] = row[key] == "true"
        try:
            stamp = datetime.strptime(row["occurred_at_utc"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise ValueError(f"row {line}: use YYYY-MM-DDTHH:MM:SSZ") from None
        row["day"] = stamp.date()
        for key in ("consent_sha256", "independence_review_sha256", "evidence_sha256"):
            if row[key] and not DIGEST.fullmatch(row[key]):
                raise ValueError(f"row {line}: invalid evidence digest")
        for key in ("manual_baseline_minutes", "review_minutes"):
            try:
                row[key] = float(row[key]) if row[key] else None
            except ValueError:
                raise ValueError(f"row {line}: invalid duration") from None
            if row[key] is not None and (not math.isfinite(row[key]) or not 0 <= row[key] <= 10080):
                raise ValueError(f"row {line}: duration must be 0..10080 minutes")
        identity = row["participant_alias"], row["task_reference"]
        if identity in seen:
            if seen[identity] != row:
                raise ValueError(f"row {line}: conflicting retry of an existing task")
            duplicates += 1
        else:
            seen[identity] = row
            records.append(row)
    return records, duplicates


def _cohort(rows, start, through):
    people = {}
    for row in rows:
        if row["day"] <= through:
            people.setdefault(row["participant_alias"], set()).add(row["day"])
    active = {alias: days for alias, days in people.items() if any(start <= day <= through for day in days)}
    retention = {}
    for offset in (7, 30):
        eligible = [days for days in people.values()
                    if start <= min(days) and min(days) + timedelta(days=offset) <= through]
        returned = sum(min(days) + timedelta(days=offset) in days for days in eligible)
        retention[f"d{offset}_exact_day"] = {
            "returned": returned, "eligible": len(eligible),
            "rate": returned / len(eligible) if eligible else None,
        }
    window_rows = [row for row in rows if start <= row["day"] <= through]
    timed = [row for row in window_rows if row["manual_baseline_minutes"] is not None and row["review_minutes"] is not None]
    return {
        "reviewed_external_participants_with_useful_tasks": len(active),
        "reviewed_external_participants_with_useful_returns": sum(
            len({day for day in days if start <= day <= through}) >= 2 for days in active.values()),
        "distinct_useful_tasks": len(window_rows),
        "exact_day_retention": retention,
        "paired_duration_observations": len(timed),
        "operator_reported_net_minutes_saved": sum(
            row["manual_baseline_minutes"] - row["review_minutes"] for row in timed) if timed else None,
    }


def score(raw: bytes, *, through: date, window_days=90):
    if not 1 <= window_days <= 365:
        raise ValueError("window_days must be 1..365")
    if through >= datetime.now(timezone.utc).date():
        raise ValueError("through must be a completed UTC date")
    records, duplicates = read_records(raw)
    start = through - timedelta(days=window_days - 1)
    # Any withdrawal/non-consent in the supplied file suppresses that participant.
    # Reviewers should remove the private source rows as their agreed policy requires.
    excluded_aliases = {row["participant_alias"] for row in records if not row["consent_recorded"]}
    types = {}
    for row in records:
        alias = row["participant_alias"]
        if alias in types and types[alias] != row["participant_type"]:
            raise ValueError("one participant alias has conflicting participant types")
        types[alias] = row["participant_type"]
    accepted, reasons = [], {}
    for row in records:
        reason = next((label for label, failed in (
            ("nonconsenting_or_withdrawn", row["participant_alias"] in excluded_aliases),
            ("operator_or_synthetic", row["operator_test"]),
            ("independence_unreviewed", not row["external_participant_confirmed"]),
            ("task_not_confirmed_complete", not row["reviewer_task_completed"]),
            ("source_scope_not_accepted", not row["source_scope_accepted"]),
            ("evidence_reference_missing", not all(row[key] for key in
                ("consent_sha256", "independence_review_sha256", "evidence_sha256"))),
        ) if failed), None)
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
        else:
            accepted.append(row)
    def groups(rows):
        return {kind: _cohort([row for row in rows if row["participant_type"] == kind], start, through)
                for kind in ("analyst", "organization")}
    return {
        "schema": "financial-evidence.office-pilot-scorecard.v1",
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "window": {"start_utc_date": start.isoformat(), "through_utc_date": through.isoformat(), "days": window_days},
        "evidence_basis": "local_reviewer_attestations_with_private_evidence_digests; authenticity_not_verified_by_this_program",
        "source_records": len(records), "duplicate_retries_ignored": duplicates,
        "exclusions": reasons,
        "eligible_records_outside_window": sum(not start <= row["day"] <= through for row in accepted),
        "participants": groups(accepted),
        "by_client": {client: groups([row for row in accepted if row["client"] == client])
                      for client in CLIENTS if any(row["client"] == client for row in accepted)},
        "by_workflow": {workflow: groups([row for row in accepted if row["workflow"] == workflow])
                        for workflow in WORKFLOWS if any(row["workflow"] == workflow for row in accepted)},
        "coverage_complete": False,
        "all_product_active_people": None, "paying_customers": None,
        "limits": [
            "Private pilot participants only; not all visitors, installations or customers.",
            "Aliases must be reviewed and deduplicated by the pilot owner; the program cannot establish independent ownership.",
            "First useful date means first retained qualifying task in the supplied history, not lifetime activation.",
            "D7 and D30 are exact completed UTC days; missing eligible observations are not proof of non-use.",
            "Client and workflow breakdowns overlap; do not add their participant totals.",
            "No network requests, enrollment, remote submission, persistent device identifiers, payment verification or training are added.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--through", type=date.fromisoformat,
                        default=datetime.now(timezone.utc).date() - timedelta(days=1))
    parser.add_argument("--window-days", type=int, default=90)
    args = parser.parse_args()
    try:
        with args.csv.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        result = score(raw, through=args.through, window_days=args.window_days)
    except (ValueError, OSError, UnicodeError, csv.Error) as error:
        parser.exit(2, f"No scorecard emitted: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
