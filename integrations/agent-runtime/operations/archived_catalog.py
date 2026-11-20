#!/usr/bin/env python3
"""Verify retry history across an explicitly pinned, bounded set of stopped offsite archives."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

from archived_lookup import ArchiveUnavailable, archive_outcome, verified_archive
from financial_evidence.runtime.contracts import KEY, NAME, decode
from ops_common import HEX, IDENTITY, regular, sha
from ops_successor import inspect_predecessor


MAX_ARCHIVES = 8
FIELDS = {"installation_id", "repository_id", "snapshot_id", "receipt_sha256", "journal", "receipt"}
ANCHOR = ("installation_id", "snapshot_id", "database_sha256", "keys_sha256", "runs")


def archive_path(parent, value):
    if not isinstance(value, str) or not 1 <= len(value) <= 4096:
        raise ArchiveUnavailable("invalid_archive_path")
    location = Path(value)
    if ".." in location.parts:
        raise ArchiveUnavailable("invalid_archive_path")
    path = location if location.is_absolute() else parent / location
    if path.resolve(strict=True) != path:
        raise ArchiveUnavailable("invalid_archive_path")
    return path


def inspect_catalog(catalog, catalog_sha256, job=None, key=None, *, live=None):
    if (not HEX.fullmatch(catalog_sha256) or (job is None) != (key is None)
            or job is not None and not (NAME.fullmatch(job) and KEY.fullmatch(key))):
        raise ArchiveUnavailable("invalid_catalog_parameters")
    catalog = Path(catalog).absolute()
    raw = regular(catalog, 65536)
    if sha(raw) != catalog_sha256:
        raise ArchiveUnavailable("catalog_digest_mismatch")
    inventory = decode(raw, limit=65536)
    if (not isinstance(inventory, dict) or set(inventory) != {"schema", "archives"}
            or inventory["schema"] != "financial-evidence.runtime-archive-catalog.v1"
            or not isinstance(inventory["archives"], list) or not 1 <= len(inventory["archives"]) <= MAX_ARCHIVES):
        raise ArchiveUnavailable("invalid_archive_catalog")
    by_installation = {}
    snapshots = set()
    outcomes = {}
    matches = []
    scanned = 0
    for item in inventory["archives"]:
        if (not isinstance(item, dict) or set(item) != FIELDS or not all(isinstance(v, str) for v in item.values())
                or not IDENTITY.fullmatch(item["installation_id"])
                or not all(HEX.fullmatch(item[k]) for k in ("repository_id", "snapshot_id", "receipt_sha256"))
                or item["snapshot_id"] in snapshots or item["installation_id"] in by_installation):
            raise ArchiveUnavailable("duplicate_or_invalid_archive_identity")
        snapshot = item["snapshot_id"]
        journal = archive_path(catalog.parent, item["journal"])
        receipt = archive_path(catalog.parent, item["receipt"])
        with verified_archive(journal, receipt, item["receipt_sha256"], snapshot) as (db, meta, proof, version):
            if proof["repository_id"] != item["repository_id"] or meta["installation_id"] != item["installation_id"]:
                raise ArchiveUnavailable("archive_identity_mismatch")
            if version == 2:
                predecessor = inspect_predecessor(db, meta, decode(meta["limits"].encode()), True)
                parent = by_installation.get(predecessor["installation_id"])
                if parent is None or any(parent[field] != predecessor[field] for field in ANCHOR):
                    raise ArchiveUnavailable("missing_or_mismatched_predecessor")
            by_installation[item["installation_id"]] = {field: proof[field] for field in ANCHOR}
            snapshots.add(snapshot)
            workflows = {}
            rows = (db.execute("SELECT * FROM runs ORDER BY id") if job is None
                    else db.execute("SELECT * FROM runs WHERE job=? AND key=?", (job, key)))
            for row in rows:
                outcome = archive_outcome(db, meta, version, row, workflows)
                identifier = row["job"], row["key"]
                if identifier in outcomes and outcomes[identifier] != outcome:
                    raise ArchiveUnavailable("conflicting_retry_outcomes")
                outcomes[identifier] = outcome
                scanned += 1
                if job is not None:
                    matches.append(snapshot)
    if live:
        if live["installation_id"] in by_installation:
            raise ArchiveUnavailable("active_installation_listed_as_final")
        predecessor = live.get("predecessor")
        if not isinstance(predecessor, dict):
            raise ArchiveUnavailable("live_predecessor_anchor_required")
        parent = by_installation.get(predecessor.get("installation_id"))
        if parent is None or any(parent[field] != predecessor.get(field) for field in ANCHOR):
            raise ArchiveUnavailable("live_predecessor_not_in_catalog")
    report = {"coverage": "pinned_stopped_archives", "catalog_sha256": catalog_sha256, "archives_verified": len(snapshots), "acquisition_authority": False}
    if job is None:
        return {**report, "status": "catalog_verified", "retry_keys": len(outcomes), "retained_rows_verified": scanned}
    if not matches:
        return {**report, "status": "absent_in_catalog"}
    return {**report, "status": "found", **outcomes[job, key], "matched_snapshots": matches}


def capacity_warning(health, installation_id, now):
    if not IDENTITY.fullmatch(installation_id):
        raise ArchiveUnavailable("invalid_live_installation")
    value = decode(regular(health, 262144), limit=262144)
    if (not isinstance(value, dict) or not isinstance(value.get("journal"), dict)
            or value.get("schema") != "financial-evidence.runtime-health.v1" or value.get("execution_authority") is not False
            or value.get("installation_id") != installation_id or value["journal"]["installation_id"] != installation_id):
        raise ArchiveUnavailable("health_identity_mismatch")
    started, expires = (datetime.fromisoformat(value[k]) for k in ("generated_at", "valid_until"))
    if not started <= now < expires or not 60 <= (expires - started).total_seconds() <= 3600:
        raise ArchiveUnavailable("health_outside_validity_window")
    runs = value["journal"]["runs"]
    limit = value["journal"]["limits"]["runs"]
    if type(runs) is not int or type(limit) is not int or limit != 10000 or not 0 <= runs <= limit:
        raise ArchiveUnavailable("unexpected_run_limit_or_count")
    issue = "runs_capacity_exhausted" if runs == limit else "runs_capacity_warning" if runs >= 8000 else None
    actual = [i["code"] for i in value["issues"] if i["code"] in ("runs_capacity_exhausted", "runs_capacity_warning")]
    if actual != ([issue] if issue else []):
        raise ArchiveUnavailable("health_capacity_issue_mismatch")
    return {"status": "capacity_warning" if issue else "below_capacity_warning", "issue": issue,
            "installation_id": installation_id, "predecessor": value["journal"].get("predecessor"), "retained_runs": runs, "run_limit": limit, "acquisition_authority": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--catalog-sha256", required=True)
    parser.add_argument("--job")
    parser.add_argument("--key")
    parser.add_argument("--on-capacity-warning", type=Path, metavar="HEALTH_JSON")
    parser.add_argument("--installation-id")
    args = parser.parse_args(argv)
    try:
        if (args.on_capacity_warning is None) != (args.installation_id is None) or (args.on_capacity_warning and (args.job or args.key)):
            raise ArchiveUnavailable("invalid_capacity_warning_parameters")
        warning = capacity_warning(args.on_capacity_warning, args.installation_id, datetime.now(timezone.utc)) if args.on_capacity_warning else None
        if warning and warning["status"] == "below_capacity_warning":
            result = warning
        else:
            result = inspect_catalog(args.catalog, args.catalog_sha256, args.job, args.key, live=warning)
            if warning:
                result["capacity"] = warning
    except ArchiveUnavailable as error:
        result = {"status": "unknown", "reason": str(error), "acquisition_authority": False}
    except (OSError, sqlite3.Error, ImportError, KeyError, IndexError, TypeError, ValueError):
        result = {"status": "unknown", "reason": "catalog_or_archive_unreadable_or_invalid", "acquisition_authority": False}
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] == "unknown" else 0


if __name__ == "__main__":
    sys.exit(main())
