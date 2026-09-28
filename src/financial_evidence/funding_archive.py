"""Read verified operator funding summaries without exposing local archive paths."""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat

from .core import _parse_finite_float, _reject_nonfinite
from .release import release_identity

SCHEMA = "liquidity-lab.funding-review.v1"
MAX_BYTES = 131_072
METRICS = (
    "policy.sofr",
    "policy.effr",
    "policy.iorb",
    "distribution.sofr.p99",
    "distribution.sofr.volume",
    "liquidity.reserves",
    "liquidity.tga",
    "liquidity.on_rrp",
    "liquidity.srf",
)
LEGACY_FIELDS = (
    "metric_id",
    "value",
    "unit",
    "observation_date",
    "source",
    "cadence",
    "publisher_freshness",
    "value_state",
    "evaluated_at",
    "review_status",
)
SCOPE_FIELDS = ("review_asof", "review_scope", "latest_per_instrument")
FIELDS = (
    LEGACY_FIELDS
    + SCOPE_FIELDS
    + (
        "canonical_latest_asof",
        "newer_observation_available",
    )
)
RELEASE_FIELDS = (
    "schema",
    "release_id",
    "source_commit",
    "workspace_version",
    "package_version",
    "contract",
)


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp lacks timezone")
    return result.astimezone(timezone.utc)


def _json(raw):
    value = json.loads(
        raw, parse_constant=_reject_nonfinite, parse_float=_parse_finite_float
    )
    if not isinstance(value, dict):
        raise ValueError("expected an object")
    return value


def _read_at(directory_fd, name):
    """Open one fixed leaf relative to a held directory, never following links."""
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError("not a bounded regular file")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("archive file too large")
    return raw


def _verify(raw, digest):
    if (
        not isinstance(digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", digest)
        or hashlib.sha256(raw).hexdigest() != digest
    ):
        raise ValueError("archive hash mismatch")


def _date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("invalid observation date")
    return value


def _scope(review):
    present = set(SCOPE_FIELDS).intersection(review)
    if not present:
        return {
            "review_asof": None,
            "review_scope": "unknown",
            "latest_per_instrument": None,
        }
    if present != set(SCOPE_FIELDS):
        raise ValueError("incomplete review scope")
    scope = {key: review[key] for key in SCOPE_FIELDS}
    if scope["latest_per_instrument"] is not False or scope["review_scope"] not in (
        "common_sofr_iorb_horizon",
        "captured_observations",
    ):
        raise ValueError("unsupported review scope")
    if scope["review_asof"] is not None:
        _date(scope["review_asof"])
    if (
        scope["review_scope"] == "common_sofr_iorb_horizon"
        and scope["review_asof"] is None
    ):
        raise ValueError("common horizon lacks observation date")
    return scope


def _rows(raw, captured_at, review, scope):
    review_status = review["status"]
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    fields = tuple(reader.fieldnames or ())
    if fields not in (LEGACY_FIELDS, FIELDS):
        raise ValueError("unexpected export columns")
    legacy = fields == LEGACY_FIELDS
    if legacy != (scope["review_scope"] == "unknown"):
        raise ValueError("export columns and review scope disagree")
    rows = list(reader)
    if (
        len(rows) != len(METRICS)
        or tuple(row.get("metric_id") for row in rows) != METRICS
    ):
        raise ValueError("unexpected funding observation set")
    for row in rows:
        if None in row or any(
            value is None or len(value) > 4096 for value in row.values()
        ):
            raise ValueError("invalid export field")
        if row["evaluated_at"] != captured_at or row["review_status"] != review_status:
            raise ValueError("export and review identity disagree")
        state, value = row["value_state"], row["value"]
        if state not in ("available", "unavailable", "restricted", "duplicate"):
            raise ValueError("invalid value state")
        if state == "available":
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("non-finite export value")
            row["value"] = number
        elif value:
            raise ValueError("unavailable export contains a value")
        else:
            row["value"] = None
        for key in ("observation_date", "source", "publisher_freshness"):
            row[key] = row[key] or None
        if legacy:
            row.update(
                scope, canonical_latest_asof=None, newer_observation_available=None
            )
            continue
        if any(
            row[key]
            != ("false" if key == "latest_per_instrument" else scope[key] or "")
            for key in SCOPE_FIELDS
        ):
            raise ValueError("export and review scope disagree")
        assessments = review.get("freshness_assessments", {})
        if not isinstance(assessments, dict):
            raise ValueError("invalid freshness assessments")
        assessment = assessments.get(row["metric_id"], {})
        if not isinstance(assessment, dict):
            raise ValueError("invalid metric freshness assessment")
        latest = assessment.get("canonical_latest_asof")
        if latest is not None:
            _date(latest)
        newer = assessment.get("newer_observation_available")
        if newer is not None and not isinstance(newer, bool):
            raise ValueError("invalid newer observation state")
        if row["canonical_latest_asof"] != (latest or "") or row[
            "newer_observation_available"
        ] != ("unknown" if newer is None else "true" if newer else "false"):
            raise ValueError("export and latest observation assessment disagree")
        try:
            observed = _date(row["observation_date"])
        except (ValueError, TypeError):
            observed = None
        if (
            latest is not None
            and observed is not None
            and newer is not (latest > observed)
        ):
            raise ValueError("newer observation state disagrees with dates")
        if (latest is None or observed is None) and newer is not None:
            raise ValueError("newer observation state lacks comparable dates")
        row.update(
            scope, canonical_latest_asof=latest, newer_observation_available=newer
        )
    return rows


def _measurement(value):
    """Expose only the documented counters; never relay arbitrary local keys."""
    if not isinstance(value, dict):
        return {}
    result = {"scope": "scheduled_operator_samples_not_continuous_uptime_or_sla"}
    for key in ("first_probe_at", "latest_probe_at"):
        if key in value:
            result[key] = _timestamp(value[key]).isoformat()
    counters = (
        "probes",
        "available_probes",
        "ready_probes",
        "consecutive_unavailable_probes",
        "longest_unavailable_probe_run",
    )
    for key in counters:
        count = value.get(key)
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            result[key] = count
    percentage = value.get("sampled_availability_pct")
    if (
        isinstance(percentage, (float, int))
        and not isinstance(percentage, bool)
        and 0 <= percentage <= 100
    ):
        result["sampled_availability_pct"] = percentage
    latencies = value.get("latest_request_latencies_seconds")
    if isinstance(latencies, dict):
        result["latest_request_latencies_seconds"] = {
            key: latency
            for key, latency in latencies.items()
            if key
            in (
                "mcp-initialize",
                "mcp-initialized",
                "funding-desk",
                "desk-history",
                "atlas",
                "health",
                "backend-health",
                "backend-release",
            )
            and isinstance(latency, (float, int))
            and not isinstance(latency, bool)
            and math.isfinite(latency)
            and latency >= 0
        }
    return result


def _load(directory, *, now, max_age_seconds, runtime_release, runtime_check):
    if (
        isinstance(max_age_seconds, bool)
        or not isinstance(max_age_seconds, (int, float))
        or not math.isfinite(max_age_seconds)
        or not 1 <= max_age_seconds <= 86400
    ):
        raise ValueError("invalid capture age policy")
    current_time = (
        datetime.now(timezone.utc)
        if now is None
        else _timestamp(now)
        if isinstance(now, str)
        else now
    )
    if not isinstance(current_time, datetime) or current_time.tzinfo is None:
        raise ValueError("invalid review time")
    # Resolve the operator-configured root once. Each child is opened with
    # O_NOFOLLOW via a held directory fd, which also resists rename/link races.
    root = Path(directory).resolve(strict=True)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    captures_fd = capture_fd = None
    try:
        current = _json(_read_at(root_fd, "current.json"))
        if current.get("schema") != "liquidity-lab.funding-current.v1":
            raise ValueError("unsupported summary schema")
        latest = current["latest"]
        if not isinstance(latest, dict):
            raise ValueError("invalid latest capture")
        capture_id = latest.get("capture_id")
        if (
            not isinstance(capture_id, str)
            or not re.fullmatch(r"\d{8}T\d{6}\.\d{6}Z-[0-9a-f]{32}", capture_id)
            or latest.get("capture") != "captures/" + capture_id
        ):
            raise ValueError("invalid capture reference")
        captures_fd = os.open(
            "captures", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
        )
        capture_fd = os.open(
            capture_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=captures_fd
        )
        manifest_raw = _read_at(capture_fd, "manifest.json")
        _verify(manifest_raw, latest.get("manifest_sha256"))
        manifest = _json(manifest_raw)
        if (
            manifest.get("schema") != "liquidity-lab.funding-capture.v1"
            or manifest.get("mode") != "capture"
        ):
            raise ValueError("unsupported capture manifest")
        for key in (
            "evaluated_at",
            "availability",
            "data_readiness",
            "release_identity",
            "ready",
        ):
            if manifest.get(key) != latest.get(key):
                raise ValueError("summary and capture identity disagree")
        at = manifest["evaluated_at"]
        age = (current_time - _timestamp(at)).total_seconds()
        stale = age > max_age_seconds or age < -300
        review_raw = _read_at(capture_fd, "review.json")
        _verify(review_raw, manifest["artifact_sha256"].get("review.json"))
        review = _json(review_raw)
        if review.get("status") != manifest["data_readiness"]:
            raise ValueError("review and capture status disagree")
        evaluated = review["status"] in ("checks_passed", "attention_required")
        if evaluated and _timestamp(review.get("evaluated_at")) != _timestamp(at):
            raise ValueError("review and capture time disagree")
        issues = review.get("issues", [])
        if (
            not isinstance(issues, list)
            or len(issues) > 200
            or any(
                not isinstance(issue, dict)
                or not isinstance(issue.get("code"), str)
                or not isinstance(issue.get("subject"), str)
                for issue in issues
            )
        ):
            raise ValueError("invalid review issues")
        scope = _scope(review)
        csv_bytes, rows = None, []
        if evaluated:
            csv_bytes = _read_at(capture_fd, "funding-observations.csv")
            _verify(
                csv_bytes, manifest["artifact_sha256"].get("funding-observations.csv")
            )
            rows = _rows(csv_bytes, review["evaluated_at"], review, scope)
        observed_release = manifest.get("observed_release") or {}
        if not isinstance(observed_release, dict):
            raise ValueError("invalid observed release")
        if runtime_release is not None:
            runtime_check = (
                "matched"
                if all(
                    observed_release.get(key) == runtime_release[key]
                    for key in RELEASE_FIELDS
                )
                else "mismatch"
            )
        available = manifest["availability"] == "available"
        identity_mismatch = (
            manifest["release_identity"] == "mismatch" or runtime_check == "mismatch"
        )
        if runtime_check == "mismatch":
            issues = [
                *issues,
                {
                    "code": "runtime_release_identity_mismatch",
                    "subject": "funding_review",
                },
            ]
        row_status = (
            "stale_capture"
            if stale
            else "release_identity_mismatch"
            if identity_mismatch
            else "capture_unavailable"
            if not available
            else review["status"]
        )
        if row_status != review["status"]:
            for row in rows:
                row["review_status"] = row_status
        input_hashes = review.get("input_sha256", {})
        freshness_assessments = review.get("freshness_assessments", {})
        if not isinstance(freshness_assessments, dict):
            raise ValueError("invalid freshness assessments")
        if not isinstance(input_hashes, dict):
            raise ValueError("invalid audit identity fields")
        policy_id = review.get("policy_id")
        if evaluated and (
            not isinstance(policy_id, str)
            or not re.fullmatch(r"usd-funding-review-checks\.v[0-9]+", policy_id)
        ):
            raise ValueError("invalid review policy identity")
        result = {
            "schema": SCHEMA,
            "policy_id": policy_id,
            **scope,
            "available": available,
            "ready": available
            and not stale
            and not identity_mismatch
            and manifest.get("ready") is True
            and review["status"] == "checks_passed"
            and not issues,
            "stale": stale,
            "captured_at": at,
            "age_seconds": round(age, 3),
            "max_age_seconds": max_age_seconds,
            "capture_id": capture_id,
            "availability": manifest["availability"],
            "data_readiness": manifest["data_readiness"],
            "release_identity": "mismatch"
            if identity_mismatch
            else manifest["release_identity"],
            "capture_release_identity": manifest["release_identity"],
            "runtime_release_identity": runtime_check,
            "runtime_release": (
                {key: runtime_release[key] for key in RELEASE_FIELDS}
                if runtime_release is not None
                else {}
            ),
            "issues": [
                {"code": item["code"][:240], "subject": item["subject"][:240]}
                for item in issues
            ],
            "results": rows,
            "freshness_assessments": {
                name: {
                    key: value[:240]
                    for key, value in assessment.items()
                    if key
                    in (
                        "publisher_freshness",
                        "basis",
                        "instrument",
                        "asof",
                        "expected_next_update",
                        "calendar_scope",
                        "atlas_source",
                        "canonical_latest_asof",
                        "latest_observation_basis",
                    )
                    and isinstance(value, str)
                }
                | {
                    "newer_observation_available": assessment.get(
                        "newer_observation_available"
                    )
                    if isinstance(assessment.get("newer_observation_available"), bool)
                    else None,
                }
                for name, assessment in freshness_assessments.items()
                if name in METRICS and isinstance(assessment, dict)
            },
            "measurement": _measurement(current.get("measurement")),
            "scope": "captured_operator_checks_not_continuous_uptime_or_point_in_time_history",
            "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "input_sha256": {
                key: digest
                for key, digest in input_hashes.items()
                if key in ("desk", "atlas", "health", "desk_history")
                and isinstance(digest, str)
                and re.fullmatch(r"[0-9a-f]{64}", digest)
            },
            "source_urls": {
                "desk": "https://api.seiche.info/mcp",
                "desk_history": "https://api.seiche.info/api/money-markets",
                "atlas": "https://api.seiche.info/api/v2/money-markets",
                "health": "https://api.seiche.info/api/health",
            },
            "observed_release": {
                key: value
                for key, value in observed_release.items()
                if key
                in (
                    "source_commit",
                    "release_id",
                    "workspace_version",
                    "package_version",
                    "schema",
                )
                and isinstance(value, str)
                and re.fullmatch(r"[A-Za-z0-9._+-]{1,160}", value)
            },
        }
        return (
            result,
            csv_bytes if available and not stale and not identity_mismatch else None,
        )
    finally:
        for fd in (capture_fd, captures_fd, root_fd):
            if fd is not None:
                os.close(fd)


def _unavailable(code):
    return {
        "schema": SCHEMA,
        "policy_id": None,
        "review_asof": None,
        "review_scope": "unknown",
        "latest_per_instrument": None,
        "available": False,
        "ready": False,
        "stale": None,
        "captured_at": None,
        "age_seconds": None,
        "capture_id": None,
        "availability": "unavailable",
        "data_readiness": "not_evaluated",
        "release_identity": "unavailable",
        "issues": [{"code": code, "subject": "funding_review"}],
        "results": [],
        "measurement": {},
    }


def read_export(
    directory=None, *, now=None, max_age_seconds=1200, enforce_runtime_release=True
):
    """Read one verified capture, binding it to a configured live release.

    When FINANCIAL_EVIDENCE_SOURCE_COMMIT is configured, the current release's
    complete identity must match the captured backend identity before readiness
    or CSV export is allowed. HTTP and MCP callers use this default. Explicit
    ``enforce_runtime_release=False`` is for historical/offline Python reads;
    that override is reported as ``runtime_release_identity=not_checked``.
    """
    configured = (
        directory
        if directory is not None
        else os.environ.get("FINANCIAL_EVIDENCE_REVIEW_DIR")
    )
    if not configured:
        return _unavailable("funding_review_not_configured"), None
    try:
        if not isinstance(enforce_runtime_release, bool):
            raise ValueError("runtime release policy must be boolean")
        runtime_release = (
            release_identity()
            if enforce_runtime_release
            and os.environ.get("FINANCIAL_EVIDENCE_SOURCE_COMMIT")
            else None
        )
        return _load(
            configured,
            now=now,
            max_age_seconds=max_age_seconds,
            runtime_release=runtime_release,
            runtime_check="not_configured"
            if enforce_runtime_release
            else "not_checked",
        )
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        RecursionError,
        csv.Error,
    ):
        return _unavailable("funding_review_archive_unavailable_or_invalid"), None


def read_review(
    directory=None, *, now=None, max_age_seconds=1200, enforce_runtime_release=True
):
    """Return latest verified review; no path or previous-good fallback leaks."""
    return read_export(
        directory,
        now=now,
        max_age_seconds=max_age_seconds,
        enforce_runtime_release=enforce_runtime_release,
    )[0]


def load_csv(
    directory=None, *, now=None, max_age_seconds=1200, enforce_runtime_release=True
):
    """Return latest CSV unless stale, unavailable or release identity differs."""
    return read_export(
        directory,
        now=now,
        max_age_seconds=max_age_seconds,
        enforce_runtime_release=enforce_runtime_release,
    )[1]
