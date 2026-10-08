"""Assess explicit research requirements without promoting evidence authority."""

from datetime import datetime, timezone
import math

from .contracts import HEX, encode
from ..core import ALLOWED_URLS

ALLOWED_RIGHTS = {"allowed", "open", "public", "redistributable"}


def assess(result, workflow, observed_at):
    reasons = set()
    policy = workflow.value["requirements"]
    if not isinstance(result, dict) or result.get("schema") != "financial-evidence.agent-result.v1":
        raise ValueError("unsupported agent result")
    if result.get("financial_authority") != "none":
        raise ValueError("research result claims financial authority")
    if result.get("evidence_status") != "not_evaluated" or result.get("carrier_verification") != "not_performed":
        raise ValueError("unexpected evidence or carrier authority")
    encode(result)
    if result.get("transport_status") != "complete":
        reasons.add("transport_incomplete")
    if result.get("change_status") != "changed":
        raise ValueError("runtime requires full rows, not suppressed change responses")
    sections = result.get("sections", [result])
    if not isinstance(sections, list) or not sections or len(sections) > 3:
        raise ValueError("invalid research sections")
    spec = workflow.value
    expected = ([spec["parameters"]["dataset"]] if spec["operation"] == "query"
                else ["money_markets", "bank_risk", "market_liquidity"])
    if [section.get("dataset") for section in sections if isinstance(section, dict)] != expected:
        raise ValueError("result does not match the registered workflow")
    rows_seen = 0
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get("results"), list):
            raise ValueError("invalid research rows")
        if section.get("transport_status") != "complete":
            reasons.add("section_transport_incomplete")
        if section.get("diagnostics"):
            reasons.add("source_diagnostics")
        if policy["require_complete_page"] and section.get("next_offset") is not None:
            reasons.add("page_incomplete")
        rows = section["results"]
        if len(rows) > spec["parameters"].get("limit", 25 if spec["operation"] == "query" else 10):
            raise ValueError("research row allowance exceeded")
        if not rows:
            reasons.add("no_matching_rows")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("invalid research row")
            rows_seen += 1
            if row.get("financial_authority") != "none":
                raise ValueError("row claims financial authority")
            source_hash = row.get("content_sha256")
            pointer = row.get("source_field")
            if (row.get("source_url") not in ALLOWED_URLS or not isinstance(pointer, str)
                    or (pointer and not pointer.startswith("/")) or not isinstance(source_hash, str)
                    or not HEX.fullmatch(source_hash.removeprefix("sha256:"))):
                reasons.add("missing_provenance")
            value = row.get("value")
            numeric = type(value) is int or (type(value) is float and math.isfinite(value))
            if policy["require_numeric_rows"] and not numeric:
                reasons.add("numeric_value_missing")
            if numeric and not row.get("unit"):
                reasons.add("unit_missing")
            availability = str(row.get("availability", "")).lower()
            if any(term in availability for term in ("restricted", "withheld", "unavailable", "stale", "blocked")):
                reasons.add("source_not_available")
            rights = str(row.get("rights_status", "")).lower()
            if policy["require_known_rights"] and rights not in ALLOWED_RIGHTS:
                reasons.add("rights_not_established")
            if any(term in rights for term in ("restricted", "withheld", "blocked", "hold", "licensed")):
                reasons.add("source_rights_restricted")
            if policy["max_observation_age_seconds"] is not None:
                raw = row.get("as_of")
                try:
                    # Date-only clocks are assessed conservatively from UTC midnight.
                    if not isinstance(raw, str):
                        raise ValueError("missing observation date")
                    clock = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    if len(raw) == 10:
                        clock = clock.replace(tzinfo=timezone.utc)
                    if clock.tzinfo is None:
                        raise ValueError("naive observation time")
                    age = observed_at - clock.timestamp()
                    if age < 0:
                        reasons.add("observation_in_future")
                    elif age > policy["max_observation_age_seconds"]:
                        reasons.add("observation_too_old")
                except (ValueError, TypeError, OverflowError):
                    reasons.add("observation_clock_unknown")
    return {"status": "blocked" if reasons else "requirements_met",
            "reasons": sorted(reasons), "rows_checked": rows_seen,
            "scope": "configured_research_requirements_only",
            "evidence_status": "not_evaluated", "carrier_verification": "not_performed",
            "point_in_time_status": "not_established", "execution_authority": False}
