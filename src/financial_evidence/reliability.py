"""Bounded public probes and honest coverage accounting for scheduled samples."""

import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.seiche.info/openbb"
def expected_identity(environ):
    """Bind observers to one operator-selected release, preserving old defaults."""
    release = environ.get("FINANCIAL_EVIDENCE_EXPECTED_RELEASE", "")
    source = environ.get("FINANCIAL_EVIDENCE_EXPECTED_SOURCE", "")
    if not release and not source:
        return ("workspace-1.0.1+6aa5d7a22823", "6aa5d7a22823b2490d7500afeba18174ca2e8822")
    if not re.fullmatch(r"[0-9a-f]{40}", source) or not re.fullmatch(
        r"workspace-[0-9]+\.[0-9]+\.[0-9]+\+" + source[:12], release
    ):
        raise ValueError("Expected Workspace release and full source SHA must form one matching pair")
    return release, source


RELEASE, SOURCE = expected_identity(os.environ)
SCHEMA = "financial-evidence.reliability-sample.v1"
LIMIT = 131072
CADENCE = 900
WINDOW = 30 * 86400


def now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result.astimezone(timezone.utc)


def encoded(value):
    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def strict_json(raw):
    def reject(_):
        raise ValueError("nonfinite JSON")

    def finite(value):
        result = float(value)
        if not math.isfinite(result):
            reject(value)
        return result

    return json.loads(raw, parse_constant=reject, parse_float=finite)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def fetch(path):
    if path not in (
        "/healthz",
        "/api/v1/release",
        "/api/v1/funding-review",
        "/api/v1/funding-review.csv",
        "/packet-latest",
    ):
        raise ValueError("endpoint not allowed")
    start = time.monotonic()
    url = (
        "https://api.seiche.info/funding-evidence/latest"
        if path == "/packet-latest"
        else BASE + path
    )
    receipt = {"http_status": None, "error": None, "url": url}
    raw = b""
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Financial-Evidence-Reliability-Operator/1",
                "X-Liquilens-Traffic-Class": "synthetic",
                "Accept-Encoding": "identity",
            },
        )
        with urllib.request.build_opener(NoRedirect()).open(
            request, timeout=12
        ) as response:
            receipt["http_status"] = response.status
            while True:
                if time.monotonic() - start > 12:
                    raise TimeoutError("response deadline")
                chunk = response.read1(min(16384, LIMIT + 1 - len(raw)))
                if not chunk:
                    break
                raw += chunk
                if len(raw) > LIMIT:
                    raise ValueError("response too large")
    except urllib.error.HTTPError as error:
        receipt.update(http_status=error.code, error="http_error")
        error.close()
    except (OSError, ValueError) as error:
        receipt["error"] = type(error).__name__
    receipt.update(
        elapsed_seconds=round(time.monotonic() - start, 6),
        body_sha256=hashlib.sha256(raw).hexdigest(),
        bytes=len(raw),
    )
    return receipt, raw


def sample(
    *, perspective, trigger, run_id, fetcher=fetch, include_packet_service=False
):
    if perspective not in (
        "github_external",
        "hetzner_same_host",
        "local_verification",
    ):
        raise ValueError("unknown observer perspective")
    if trigger not in ("schedule", "workflow_dispatch", "manual"):
        raise ValueError("unknown trigger")
    observed = now()
    calls, docs = {}, {}
    endpoints = [
        ("health", "/healthz"),
        ("release", "/api/v1/release"),
        ("review", "/api/v1/funding-review"),
    ]
    if include_packet_service:
        endpoints.append(("packet", "/packet-latest"))
    for name, path in endpoints:
        receipt, raw = fetcher(path)
        calls[name] = receipt
        if receipt["http_status"] == 200 and receipt["error"] is None:
            try:
                value = strict_json(raw)
                if not isinstance(value, dict):
                    raise TypeError("object required")
                docs[name] = value
            except (ValueError, TypeError, UnicodeError, RecursionError):
                receipt["error"] = "invalid_json"
    available = len(docs) == len(endpoints) and docs["health"].get("status") == "ok"
    identity = (
        available
        and docs["health"].get("release_id")
        == docs["release"].get("release_id")
        == RELEASE
        and docs["release"].get("source_commit") == SOURCE
    )
    review = docs.get("review", {})
    age = review.get("age_seconds")
    fresh = (
        isinstance(age, (int, float))
        and not isinstance(age, bool)
        and math.isfinite(age)
        and 0 <= age <= 1200
    )
    ready = bool(
        identity
        and fresh
        and review.get("ready") is True
        and review.get("data_readiness") == "checks_passed"
        and review.get("release_identity") == "matched"
        and review.get("runtime_release_identity") == "matched"
        and not review.get("issues")
        and (
            not include_packet_service
            or (
                docs.get("packet", {}).get("ready") is True
                and docs.get("packet", {}).get("packet", {}).get("source_commit")
                == SOURCE
            )
        )
    )
    result = {
        "schema": SCHEMA,
        "observed_at": observed,
        "finished_at": now(),
        "perspective": perspective,
        "trigger": trigger,
        "run_id": str(run_id),
        "expected_release": RELEASE,
        "expected_source": SOURCE,
        "includes_packet_delivery": include_packet_service,
        "observer_source_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "available": bool(available),
        "release_matches": bool(identity),
        "ready": ready,
        "capture_id": review.get("capture_id"),
        "requests": calls,
        "data_readiness": review.get("data_readiness"),
        "capture_age_seconds": age,
        "review_asof": review.get("review_asof"),
        "latest_per_instrument": review.get("latest_per_instrument"),
    }
    return result, docs


def summarize(
    samples, *, evaluated_at=None, expected_release=None, expected_source=None
):
    release, source = expected_identity({
        "FINANCIAL_EVIDENCE_EXPECTED_RELEASE": (
            RELEASE if expected_release is None else expected_release
        ),
        "FINANCIAL_EVIDENCE_EXPECTED_SOURCE": (
            SOURCE if expected_source is None else expected_source
        ),
    })
    end = timestamp(evaluated_at or now())
    unique = {}
    for item in samples:
        if (
            item.get("schema") != SCHEMA
            or item.get("expected_source") != source
            or item.get("expected_release") != release
        ):
            raise ValueError("mixed or unsupported observer identity")
        at = timestamp(item["observed_at"])
        if at > end or timestamp(item["finished_at"]) < at:
            raise ValueError("invalid observation time")
        key = (item["perspective"], item["run_id"])
        if key in unique and unique[key] != item:
            raise ValueError("conflicting observation identity")
        if any(
            type(item.get(k)) is not bool
            for k in ("available", "ready", "release_matches")
        ):
            raise ValueError("invalid observation state")
        unique[key] = item
    result = {
        "schema": "financial-evidence.reliability-report.v1",
        "evaluated_at": end.isoformat(),
        "expected_release": release,
        "expected_source": source,
        "window_days": 30,
        "scope": "scheduled_samples_not_continuous_uptime",
        "sla_claim": False,
        "perspectives": {},
    }
    for perspective in sorted({p for p, _ in unique}):
        values = sorted(
            (x for (p, _), x in unique.items() if p == perspective),
            key=lambda x: timestamp(x["observed_at"]),
        )
        first = timestamp(values[0]["observed_at"])
        start = max(first.timestamp(), end.timestamp() - WINDOW)
        window_values = [
            x for x in values if timestamp(x["observed_at"]).timestamp() >= start
        ]
        slots = {}
        for item in window_values:
            # Manual probes are useful checks but never replace a missed scheduled run.
            if item["trigger"] == "schedule":
                slot = int(
                    (timestamp(item["observed_at"]).timestamp() - start) // CADENCE
                )
                slots.setdefault(slot, []).append(item)
        expected = max(0, math.ceil((end.timestamp() - start) / CADENCE))
        completed_slots = {k: v for k, v in slots.items() if k < expected}
        available = sum(
            all(x["available"] and x["release_matches"] for x in v)
            for v in completed_slots.values()
        )
        ready = sum(all(x["ready"] for x in v) for v in completed_slots.values())
        latencies = sorted(
            r["elapsed_seconds"]
            for x in window_values
            for r in x["requests"].values()
            if r.get("http_status") == 200 and r.get("error") is None
        )
        elapsed = (end - first).total_seconds()
        result["perspectives"][perspective] = {
            "first_retained_observation_at": first.isoformat(),
            "latest_observation_at": values[-1]["observed_at"],
            "baseline_elapsed_days": round(elapsed / 86400, 6),
            "thirty_days_elapsed": elapsed >= WINDOW,
            "window_started_at": datetime.fromtimestamp(
                start, timezone.utc
            ).isoformat(),
            "expected_slots": expected,
            "observed_slots": len(completed_slots),
            "missing_slots": expected - len(completed_slots),
            "coverage_pct": round(100 * len(completed_slots) / expected, 3)
            if expected
            else None,
            "available_observed_slots": available,
            "ready_observed_slots": ready,
            "sampled_availability_pct": round(100 * available / len(completed_slots), 3)
            if completed_slots
            else None,
            "sampled_readiness_pct": round(100 * ready / len(completed_slots), 3)
            if completed_slots
            else None,
            "successful_request_p95_seconds": latencies[
                max(0, math.ceil(len(latencies) * 0.95) - 1)
            ]
            if latencies
            else None,
            "manual_samples": sum(x["trigger"] != "schedule" for x in window_values),
            "last_available": values[-1]["available"],
            "last_ready": values[-1]["ready"],
            "independent_host": perspective == "github_external",
        }
    return result


def summarize_releases(samples, *, evaluated_at=None):
    """Keep each release's baseline and failures without combining their slots."""
    groups = {}
    for item in samples:
        release = item.get("expected_release")
        source = item.get("expected_source")
        if not isinstance(release, str) or not isinstance(source, str) or not release or not source:
            raise ValueError("missing observer release identity")
        identity = expected_identity({
            "FINANCIAL_EVIDENCE_EXPECTED_RELEASE": release,
            "FINANCIAL_EVIDENCE_EXPECTED_SOURCE": source,
        })
        groups.setdefault(identity, []).append(item)
    end = evaluated_at or now()
    current = summarize(groups.pop((RELEASE, SOURCE), []), evaluated_at=end)
    current["prior_releases"] = [
        summarize(values, evaluated_at=end, expected_release=release,
                  expected_source=source)
        for (release, source), values in sorted(groups.items())
    ]
    return current
