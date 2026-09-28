#!/usr/bin/env python3
"""Check captured USD funding evidence before a research review; no network I/O.

Exit 0 means these bounded consistency checks passed, 1 means attention is
required, and 2 means invalid input. No result establishes investment eligibility,
source accuracy, historical point-in-time coverage, or an availability SLA.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from financial_evidence.core import _parse_finite_float, _reject_nonfinite
from financial_evidence.tables import _blocked

POLICY_ID = "usd-funding-review-checks.v2"
REQUIRED = {
    "policy.sofr": ("%", "daily"),
    "policy.effr": ("%", "daily"),
    "policy.iorb": ("%", "daily"),
    "distribution.sofr.p99": ("%", "daily"),
    "distribution.sofr.volume": ("$B", "daily"),
    "liquidity.reserves": ("$B", "weekly"),
    "liquidity.tga": ("$B", "daily"),
    "liquidity.on_rrp": ("$B", "daily"),
    "liquidity.srf": ("$B", "daily"),
}
# Calendar-day backstops, not central-bank publication calendars. In addition,
# every required metric must retain the publisher's explicit fresh state.
MAX_AGE_DAYS = {"daily": 4, "weekly": 10}
MAX_BYTES = 2_097_152
TGA_SCHEDULE_SOURCE = "https://home.treasury.gov/policy-issues/financial-markets-financial-institutions-and-fiscal-service/cash-and-debt-forecasting"


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("expected an ISO timestamp with a timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("expected an ISO timestamp with a timezone")
    return parsed.astimezone(timezone.utc)


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def publication_denied(value):
    # Use the same publication policy as the REST/OpenBB/MCP projections.
    return _blocked(value, raw_observation=True)


def evaluate(desk, atlas, health, *, evaluated_at, max_snapshot_age_seconds=900):
    """Inspect only named public fields; never infer a missing print or clock."""
    now = timestamp(evaluated_at)
    if (
        not finite_number(max_snapshot_age_seconds)
        or not 1 <= max_snapshot_age_seconds <= 86400
    ):
        raise ValueError("snapshot age limit must be between 1 and 86400 seconds")
    if any(not isinstance(doc, dict) for doc in (desk, atlas, health)):
        raise ValueError("each input must be one JSON object")
    issues = []

    def issue(code, subject):
        issues.append({"code": code, "subject": subject})

    def check_clock(value, subject):
        try:
            age = (now - timestamp(value)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            issue("missing_or_invalid_snapshot_clock", subject)
            return
        if age < -300:
            issue("future_snapshot_clock", subject)
        elif age > max_snapshot_age_seconds:
            issue("snapshot_too_old", subject)

    def observation_day(value, subject):
        try:
            if (
                not isinstance(value, str)
                or date.fromisoformat(value).isoformat() != value
            ):
                raise ValueError
            day = date.fromisoformat(value)
        except (ValueError, TypeError, OverflowError):
            issue("missing_or_invalid_observation_date", subject)
            return None
        if day > now.date():
            issue("future_observation_date", subject)
        return day

    if (
        desk.get("schema") != "seiche.money-market-desk.v1"
        or desk.get("ok") is not True
    ):
        issue("desk_unavailable_or_schema_changed", "desk")
    if desk.get("selection") != "all":
        issue("incomplete_desk_capture", "desk.selection")
    if atlas.get("schema") != "seiche.global-money-markets.v1":
        issue("atlas_schema_changed", "atlas")
    for name, document in (("desk", desk), ("atlas", atlas)):
        if publication_denied(document):
            issue("publication_restricted", name)
    check_clock(desk.get("snapshot_generated_at"), "desk")
    check_clock(atlas.get("generated_at"), "atlas")
    check_clock(health.get("generated_at"), "health")
    metrics = {}
    sections = desk.get("sections")
    if not isinstance(sections, list):
        sections = []
        issue("missing_sections", "desk")
    for section in sections:
        if not isinstance(section, dict) or not isinstance(
            section.get("metrics"), list
        ):
            issue("invalid_section", "desk.sections")
            continue
        for metric in section["metrics"]:
            if not isinstance(metric, dict) or not isinstance(metric.get("id"), str):
                issue("invalid_metric", "desk.sections.metrics")
                continue
            name = metric["id"]
            if name in REQUIRED and publication_denied(section):
                issue("publication_restricted", name)
            if name in metrics:
                issue("duplicate_metric", name)
            else:
                metrics[name] = metric
    for name, (unit, cadence) in REQUIRED.items():
        row = metrics.get(name)
        if row is None:
            issue("missing_required_metric", name)
            continue
        if row.get("status") != "available" or not finite_number(row.get("value")):
            issue("required_value_unavailable", name)
        if publication_denied(row):
            issue("publication_restricted", name)
        if row.get("unit") != unit or row.get("cadence") != cadence:
            issue("unit_or_cadence_changed", name)
        if not isinstance(row.get("source"), str) or not row["source"].strip():
            issue("source_missing", name)
        day = observation_day(row.get("asof"), name)
        scheduled_fresh = False
        if (
            name == "liquidity.tga"
            and row.get("freshness_policy") == "treasury-dts-next-business-day-v1"
        ):
            schedule = row.get("publication_schedule")
            try:
                if not isinstance(schedule, dict):
                    raise ValueError("schedule missing")
                expected = date.fromisoformat(schedule["expected_observation_date"])
                due = timestamp(schedule["latest_due_at"])
                local_due = due.astimezone(ZoneInfo("America/New_York"))
                missed_tga = schedule["missed_publication_opportunities"]
                if (
                    schedule.get("timezone") != "America/New_York"
                    or schedule.get("clock_precision") != "scheduled"
                    or schedule.get("source_url") != TGA_SCHEDULE_SOURCE
                    or isinstance(missed_tga, bool)
                    or not isinstance(missed_tga, int)
                    or missed_tga < 0
                    or due > now
                    or now - due > timedelta(days=4, hours=1)
                    or (
                        local_due.hour,
                        local_due.minute,
                        local_due.second,
                        local_due.microsecond,
                    )
                    != (16, 0, 0, 0)
                    or not 1 <= (local_due.date() - expected).days <= 4
                    or expected > now.date()
                ):
                    raise ValueError("invalid schedule")
                if missed_tga or day is None or day < expected:
                    issue("publication_opportunity_missed", name)
                else:
                    # This is a bounded publisher-schedule check, not an
                    # independent holiday calendar. It never removes the
                    # absolute eight-day backstop for a TGA observation.
                    scheduled_fresh = True
            except (ValueError, TypeError, KeyError, OverflowError):
                issue("publication_schedule_invalid", name)
        if day and (now.date() - day).days > (
            8 if scheduled_fresh else MAX_AGE_DAYS[cadence]
        ):
            issue("observation_exceeds_age_backstop", name)
        if row.get("freshness") != "fresh":
            issue("required_metric_not_reported_fresh", name)

    markets = atlas.get("markets")
    usd = (
        [m for m in markets if isinstance(m, dict) and m.get("market_id") == "US-USD"]
        if isinstance(markets, list)
        else []
    )
    benchmark = usd[0].get("benchmark") if len(usd) == 1 else None
    if not isinstance(benchmark, dict):
        issue("missing_or_duplicate_usd_benchmark", "atlas.US-USD")
        benchmark = {}
    if any(publication_denied(node) for node in [benchmark, *usd]):
        issue("publication_restricted", "atlas.US-USD")
    if (
        benchmark.get("mnemonic") != "SOFR"
        or benchmark.get("unit") != "%"
        or benchmark.get("availability") != "AVAILABLE"
        or benchmark.get("redistribution_status") != "allowed"
        or not finite_number(benchmark.get("value"))
    ):
        issue("usd_benchmark_not_usable", "atlas.US-USD")
    if benchmark.get("status") != "FRESH":
        issue("usd_benchmark_not_reported_fresh", "atlas.US-USD")
    missed = benchmark.get("missed_publication_opportunities")
    if isinstance(missed, bool) or not isinstance(missed, int) or missed < 0:
        issue("publication_schedule_not_reported", "atlas.US-USD")
    elif missed:
        issue("publication_opportunity_missed", "atlas.US-USD")
    observation_day(benchmark.get("asof"), "atlas.US-USD")

    # Compare equal instruments only. Distinct publication cadences for reserves
    # and TGA must never be forced into a common observation date.
    prints = {
        "desk.policy.sofr": metrics.get("policy.sofr", {}),
        "desk.distribution.sofr.rate": metrics.get("distribution.sofr.rate", {}),
        "atlas.US-USD.SOFR": benchmark,
    }
    reference = prints["desk.policy.sofr"]
    for name, row in prints.items():
        if not row:
            issue("sofr_comparison_missing", name)
            continue
        if not row.get("asof") or row.get("asof") != reference.get("asof"):
            issue("sofr_observation_dates_disagree", name)
        elif row.get("unit") != reference.get("unit"):
            issue("sofr_units_disagree", name)
        elif not finite_number(row.get("value")) or not finite_number(
            reference.get("value")
        ):
            issue("sofr_comparison_value_missing", name)
        elif not math.isclose(
            row["value"], reference["value"], rel_tol=0, abs_tol=1e-9
        ):
            issue("sofr_same_date_values_disagree", name)
    provenance = health.get("provenance")
    health_sofr = (
        [p for p in provenance if isinstance(p, dict) and p.get("mnemonic") == "SOFR"]
        if isinstance(provenance, list)
        else []
    )
    if len(health_sofr) != 1 or health_sofr[0].get("asof") != reference.get("asof"):
        issue("health_sofr_date_missing_or_disagrees", "health.SOFR")

    return {
        "schema": "liquidity-lab.funding-review-check.v1",
        "policy_id": POLICY_ID,
        "evaluated_at": now.isoformat(),
        "status": "attention_required" if issues else "checks_passed",
        "scope": "captured_usd_funding_consistency_and_age_backstops",
        "max_snapshot_age_seconds": max_snapshot_age_seconds,
        "required_metrics": list(REQUIRED),
        "issues": issues,
        "sofr_observation_dates": {
            name: row.get("asof") for name, row in prints.items()
        },
        "publisher_coverage": desk.get("coverage"),
        "limits": [
            "This is an operator check, not an institutional-readiness certification or trading signal.",
            "Calendar-day backstops do not implement official publication calendars; a bounded recognized publisher Treasury DTS schedule may extend TGA's age limit to eight days, never remove it.",
            "Publisher freshness and coverage are reported claims, not independent source verification.",
            "Input hashes identify local files, not signed original source evidence or historic vintages.",
            "No data repair, forward fill, financial-authority grant, or external message occurs.",
        ],
    }


def load_document(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("input exceeds 2 MiB")

    return (
        json.loads(
            raw, parse_constant=_reject_nonfinite, parse_float=_parse_finite_float
        ),
        hashlib.sha256(raw).hexdigest(),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("desk", "atlas", "health"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument(
        "--evaluated-at", required=True, help="explicit ISO timestamp with timezone"
    )
    parser.add_argument("--max-snapshot-age-seconds", type=int, default=900)
    args = parser.parse_args(argv)
    try:
        captures = {
            name: load_document(getattr(args, name))
            for name in ("desk", "atlas", "health")
        }
        report = evaluate(
            *(captures[name][0] for name in ("desk", "atlas", "health")),
            evaluated_at=args.evaluated_at,
            max_snapshot_age_seconds=args.max_snapshot_age_seconds,
        )
        report["input_sha256"] = {name: entry[1] for name, entry in captures.items()}
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report["status"] == "checks_passed" else 1
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
        print(json.dumps({"status": "invalid_input", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
