"""Bounded, content-free measurement and explicit private evidence contracts."""

from __future__ import annotations

import hashlib
import json
import math
import re

PURPOSES = frozenset({"measurement", "private_evidence", "research_training", "commercial_training"})
TRAINING = frozenset({"research_training", "commercial_training"})
PRODUCTS = frozenset({"liquilens", "seiche", "undertow", "palimpsest", "noisefloor", "narcoscope", "wake", "financial_evidence",
                      "riptide", "myquant-editorial", "myquant-app", "trade-safety", "financial-evidence", "research-data", "seiche-market-corpus"})
TASKS = frozenset({"money_markets", "funding_review", "liquidity", "institution_evidence", "china_macro", "research", "other"})
MODES = frozenset({"unknown", "test", "backtest", "shadow", "paper", "operator_reported_production"})
FEEDBACK_REASONS = frozenset({
    "missing_data", "stale_data", "incorrect_data", "unclear_output",
    "access_blocked", "slow_response", "workflow_mismatch", "other",
})
DATA_GAPS = frozenset({
    "historical_depth", "country_coverage", "institution_coverage",
    "venue_coverage", "update_frequency", "source_provenance", "series_coverage",
})
FAILURE_REASONS = frozenset({
    "authentication_required", "access_denied", "rate_limited", "access_restricted",
    "upstream_http_error", "monitor_blocked", "context_unavailable",
    "evidence_unavailable", "source_read_or_contract_validation_failed",
})
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
DEFAULT_TARGET = {
    "id": "funding_next_release_change", "unit": "percentage_points",
    "description": "Change in one explicitly identified funding rate at its next observed release; no profit claim.",
}


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def label(value, name="label"):
    if not isinstance(value, str) or not LABEL.fullmatch(value):
        raise ValueError(f"invalid {name}: use a bounded identifier, not free text")
    return value


def number(value, name="number", low=-1e15, high=1e15):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"invalid {name}")
    return value


def moment(value, name="timestamp"):
    return number(value, name, 0, 253402300799)


def object_fields(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError("unknown or missing fields")
    if len(encode(value)) > 65536:
        raise ValueError("record exceeds 64 KiB")


def choice(value, options, name):
    if not isinstance(value, str) or value not in options:
        raise ValueError(f"invalid {name}")
    return value


def tool_event(value, now):
    object_fields(value, {"id", "product", "tool", "task", "occurred_at", "duration_ms", "status", "mode"},
                  {"cached", "useful", "cost_usd", "source_age_seconds", "logical_workflow_id",
                   "client_version", "model_version", "config_version", "available_tools",
                   "event_kind", "failure_reason", "feedback_reason", "data_gaps"})
    for key in ("id", "tool", "logical_workflow_id", "client_version", "model_version", "config_version"):
        if key in value:
            label(value[key], key)
    choice(value["product"], PRODUCTS, "product")
    choice(value["task"], TASKS, "task")
    choice(value["status"], {"success", "error", "refused", "stale"}, "status")
    choice(value["mode"], MODES, "mode")
    if moment(value["occurred_at"]) > now:
        raise ValueError("event is in the future")
    number(value["duration_ms"], "duration_ms", 0, 86_400_000)
    for key in ("cached", "useful"):
        if key in value and not isinstance(value[key], bool):
            raise ValueError(f"invalid {key}")
    if value.get("useful") and value["status"] != "success":
        raise ValueError("a failed/refused/stale result cannot be a useful completion")
    if "event_kind" in value:
        choice(value["event_kind"], {"attempt", "feedback"}, "event kind")
    if value.get("event_kind") == "feedback":
        if "useful" not in value or "logical_workflow_id" not in value:
            raise ValueError("feedback requires usefulness and a logical workflow")
        if value["duration_ms"] != 0 or any(key in value for key in ("cost_usd", "cached", "source_age_seconds")):
            raise ValueError("feedback is not another measured request")
    if "failure_reason" in value:
        choice(value["failure_reason"], FAILURE_REASONS, "failure reason")
        if value["status"] == "success" or value.get("event_kind") == "feedback":
            raise ValueError("failure reason belongs to an unsuccessful attempt")
    if "feedback_reason" in value:
        choice(value["feedback_reason"], FEEDBACK_REASONS, "feedback reason")
        if "useful" not in value:
            raise ValueError("feedback reason requires explicit usefulness")
    if "data_gaps" in value:
        gaps = value["data_gaps"]
        if "useful" not in value or not isinstance(gaps, list) or not 1 <= len(gaps) <= 5:
            raise ValueError("data gaps require explicit usefulness and one to five categories")
        for gap in gaps:
            choice(gap, DATA_GAPS, "data gap")
        if len(set(gaps)) != len(gaps):
            raise ValueError("duplicate data gap")
    for key in ("cost_usd", "source_age_seconds"):
        if key in value:
            number(value[key], key, 0, 1e9)
    if "available_tools" in value:
        options = value["available_tools"]
        if not isinstance(options, list) or len(options) > 32 or len(set(map(str, options))) != len(options):
            raise ValueError("invalid available_tools")
        for item in options:
            label(item, "available tool")
    return json.loads(encode(value))


def is_feedback(value):
    """Recognize explicit feedback and the exact pre-event-kind workflow shape."""
    if "event_kind" in value:
        return value["event_kind"] == "feedback"
    workflow = value.get("logical_workflow_id")
    return (value.get("tool") == "financial_evidence_workflow"
            and isinstance(workflow, str) and value.get("id") == workflow + ":feedback"
            and "useful" in value and value.get("duration_ms") == 0)


def evidence_ref(value):
    if not isinstance(value, dict):
        raise ValueError("invalid evidence reference")
    if value.get("kind") == "runtime":
        object_fields(value, {"kind", "run_id", "sha256"})
        if not isinstance(value["run_id"], str) or not re.fullmatch(r"[a-f0-9]{32}", value["run_id"]):
            raise ValueError("invalid runtime run id")
    else:
        object_fields(value, {"kind", "product", "receipt_id", "sha256"})
        choice(value["kind"], {"product"}, "receipt kind")
        choice(value["product"], PRODUCTS, "product")
        label(value["receipt_id"], "receipt_id")
    if not isinstance(value["sha256"], str) or not SHA.fullmatch(value["sha256"]):
        raise ValueError("invalid receipt digest")


def feature_map(value, decided_at):
    if not isinstance(value, dict) or len(value) > 32:
        raise ValueError("at most 32 numeric features per class")
    for name, item in value.items():
        label(name, "feature name")
        object_fields(item, {"value", "observed_at", "available_at", "source", "revision"})
        number(item["value"], "feature value")
        label(item["source"], "feature source")
        label(item["revision"], "feature revision")
        if not moment(item["observed_at"]) <= moment(item["available_at"]) <= decided_at:
            raise ValueError("feature must be observed and available by the decision time")


def decision(value, now):
    object_fields(value, {"id", "decided_at", "target", "entity", "horizon_seconds", "mode", "evidence_refs", "data_features", "usage_features"})
    for key in ("id", "target", "entity"):
        label(value[key], key)
    choice(value["mode"], MODES, "mode")
    if moment(value["decided_at"]) > now:
        raise ValueError("decision is in the future")
    number(value["horizon_seconds"], "horizon_seconds", 1, 366 * 86400)
    if not isinstance(value["evidence_refs"], list) or not 1 <= len(value["evidence_refs"]) <= 16:
        raise ValueError("one to sixteen exact evidence references required")
    for item in value["evidence_refs"]:
        evidence_ref(item)
    for key in ("data_features", "usage_features"):
        feature_map(value[key], value["decided_at"])
    if not value["data_features"]:
        raise ValueError("domain data baseline needs at least one feature")
    return json.loads(encode(value))


def outcome(value, now):
    object_fields(value, {"id", "decision_id", "value", "unit", "observed_at", "available_at", "source", "revision"})
    for key in ("id", "decision_id", "unit", "source", "revision"):
        label(value[key], key)
    number(value["value"], "outcome value")
    if not moment(value["observed_at"]) <= moment(value["available_at"]) <= now:
        raise ValueError("outcome availability must follow observation and precede receipt")
    return json.loads(encode(value))
