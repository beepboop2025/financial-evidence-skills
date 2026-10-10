"""Capture current evidence conservatively for forward research, never backfill it."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA = "financial-evidence.forward-capture.v1"
ROW_SCHEMA = "financial-evidence.forward-row.v1"
HISTORY_SCOPE = "forward_capture_of_current_amended_data_not_original_vintages"
MAX_ROWS = 100
MAX_BYTES = 4 * 1024 * 1024


def utc(value: str) -> datetime:
    """Require a complete, timezone-aware timestamp; dates alone are insufficient."""
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("An ISO timestamp with a timezone is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def capture(packet: dict, *, captured_at: str | None = None) -> dict:
    """Retain one bounded page. Capture time is local receipt, not original publication.

    ``captured_at`` exists for deterministic offline tests and retained receipts;
    live callers omit it. A self-reported timestamp is not independent attestation.
    """
    instant = utc(captured_at) if captured_at else datetime.now(timezone.utc)
    if not isinstance(packet, dict) or packet.get("schema") != "financial-evidence.agent-result.v1":
        raise ValueError("Expected an agent-query evidence envelope")
    if packet.get("transport_status") not in {"complete", "partial", "unavailable"}:
        raise ValueError("Missing transport status")
    rows = packet.get("results")
    if not isinstance(rows, list) or len(rows) > MAX_ROWS or not all(isinstance(row, dict) for row in rows):
        raise ValueError("Expected at most 100 evidence rows")
    if not isinstance(packet.get("sources"), list):
        raise ValueError("Missing source diagnostics")
    if len(encoded(packet)) > MAX_BYTES:
        raise ValueError("Evidence exceeds the four MiB capture budget")
    # Deep copy: a framework or notebook mutating its result cannot alter a capture.
    packet = json.loads(encoded(packet))
    rows = packet["results"]
    packet_digest = digest(packet)
    snapshot = {
        "schema": SCHEMA,
        "captured_at": instant.isoformat(),
        "available_at_basis": "local_capture_completion_not_publisher_first_release",
        "history_scope": HISTORY_SCOPE,
        "financial_authority": "none",
        "coverage_complete": False,
        "coverage_scope": "bounded_query_only_not_full_market",
        "requested_page_complete": packet.get("next_offset") is None and packet["transport_status"] == "complete",
        "packet_sha256": packet_digest,
        "packet": packet,
        "rows": [
            {"schema": ROW_SCHEMA, "event_time": row.get("as_of"),
             "event_time_precision": "date" if isinstance(row.get("as_of"), str) and len(row["as_of"]) == 10 else "source_native",
             "available_at": instant.isoformat(), "history_scope": HISTORY_SCOPE,
             "packet_sha256": packet_digest, "row": row}
            for row in rows
        ],
    }
    if len(encoded(snapshot)) > MAX_BYTES:
        raise ValueError("Capture exceeds the four MiB read budget; reduce the row limit")
    return snapshot


def validate_capture(snapshot: dict) -> dict:
    """Check retained-byte integrity and clock consistency, not source truth or rights."""
    if snapshot.get("schema") != SCHEMA or snapshot.get("history_scope") != HISTORY_SCOPE:
        raise ValueError("Unsupported forward capture")
    expected = capture(snapshot["packet"], captured_at=snapshot["captured_at"])
    if snapshot != expected:
        raise ValueError("Capture contents, clocks or packet digest do not match")
    return snapshot


def for_decision(snapshot: dict, *, decision_at: str, mode: str = "forward_research") -> dict:
    """Refuse historical simulation and use before this workflow captured the data."""
    validate_capture(snapshot)
    if mode != "forward_research":
        raise ValueError("Current-amended evidence is not eligible for historical backtests")
    if utc(decision_at) < utc(snapshot["captured_at"]):
        raise ValueError("Evidence was not yet available to this captured workflow")
    return snapshot


def numeric_record(record: dict) -> dict:
    """Validate one imported funding record; missing/restricted values are never zero."""
    if record.get("schema") != ROW_SCHEMA or record.get("history_scope") != HISTORY_SCOPE:
        raise ValueError("Unsupported forward research record")
    available = utc(record["available_at"])
    row = record["row"]
    if row.get("dataset") not in {"money_markets", "money_market_history"}:
        raise ValueError("This importer covers funding observations only")
    event = record.get("event_time")
    if event != row.get("as_of") or not isinstance(event, str):
        raise ValueError("Observation date is missing or inconsistent")
    event_date = date.fromisoformat(event) if len(event) == 10 else utc(event).date()
    if event_date > available.date() or (len(event) != 10 and utc(event) > available):
        raise ValueError("Observation occurs after this capture")
    value = row.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Missing or nonfinite numeric observation")
    if str(row.get("availability", "")).lower() not in {"available", "published"}:
        raise ValueError("Observation is unavailable or withheld")
    if str(row.get("rights_status", "")).lower() != "allowed":
        raise ValueError("Source has not reported allowed rights; inspect the retained packet")
    for field in ("source_url", "source_field", "unit", "entity_id", "metric"):
        if not isinstance(row.get(field), str) or not row[field]:
            raise ValueError(f"Missing provenance or series field: {field}")
    # A source rights label does not grant a new channel-specific data licence.
    return record


def save(snapshot: dict, directory: Path) -> dict:
    """Create an immutable-by-convention capture folder; never overwrite one."""
    validate_capture(snapshot)
    records, excluded = [], []
    for index, record in enumerate(snapshot["rows"]):
        try:
            numeric_record(record)
        except (ValueError, KeyError, TypeError) as exc:
            excluded.append({"row_index": index, "reason": str(exc)})
        else:
            records.append(record)
    raw = encoded(snapshot)
    numeric = b"".join(encoded(record) for record in records)
    receipt = {
        "schema": "financial-evidence.forward-receipt.v1",
        "captured_at": snapshot["captured_at"], "capture_sha256": hashlib.sha256(raw).hexdigest(),
        "funding_jsonl_sha256": hashlib.sha256(numeric).hexdigest(),
        "retained_rows": len(snapshot["rows"]), "numeric_funding_rows": len(records),
        "excluded_from_numeric_export": excluded,
        "coverage_complete": snapshot["coverage_complete"],
        "requested_page_complete": snapshot["requested_page_complete"],
        "next_offset": snapshot["packet"].get("next_offset"),
        "history_scope": HISTORY_SCOPE, "financial_authority": "none",
    }
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "capture.json").write_bytes(raw)
    (directory / "funding.jsonl").write_bytes(numeric)
    (directory / "receipt.json").write_bytes(encoded(receipt))
    return receipt


def load(path: Path) -> dict:
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Capture exceeds the four MiB read budget")
    return validate_capture(json.loads(raw))
