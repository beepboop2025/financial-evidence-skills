"""Strict configuration and portable JSON contracts; stdlib only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re

from ..tables import DATASETS, validate_query

SCHEMA = "financial-evidence.workflow.v1"
MAX_BUNDLE_BYTES = 2_097_152
NAME = re.compile(r"[a-z][a-z0-9_-]{0,63}")
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
HEX = re.compile(r"[0-9a-f]{64}")


def encode(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def decode(raw: bytes, *, limit=MAX_BUNDLE_BYTES):
    if not isinstance(raw, bytes) or len(raw) > limit:
        raise ValueError("JSON exceeds its byte allowance")

    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError("duplicate JSON key")
            obj[key] = value
        return obj

    def reject(_):
        raise ValueError("nonfinite JSON")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
        # Also reject exponent overflow (1e999), invalid UTF-8 and excessive nesting.
        encode(value)
        return value
    except (UnicodeError, RecursionError, OverflowError) as exc:
        raise ValueError("invalid bounded JSON") from exc


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in {low}..{high}")
    return value


def moment(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("UTC clock must be numeric")
    if not math.isfinite(value) or not 0 <= value <= 32_503_680_000:
        raise ValueError("UTC clock outside supported range")
    return float(value)


def utc(value):
    return datetime.fromtimestamp(moment(value), timezone.utc).isoformat()


@dataclass(frozen=True)
class Workflow:
    """An immutable read-only job; changing a policy requires a new job ID."""

    document: bytes

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict):
            raise ValueError("workflow must be an object")
        required = {"schema", "id", "operation", "parameters", "interval_seconds",
                    "daily_run_limit", "requirements"}
        if set(value) != required or value["schema"] != SCHEMA:
            raise ValueError("unsupported workflow contract or fields")
        if not isinstance(value["id"], str) or not NAME.fullmatch(value["id"]):
            raise ValueError("invalid workflow id")
        integer(value["interval_seconds"], 60, 604800, "interval_seconds")
        integer(value["daily_run_limit"], 1, 1440, "daily_run_limit")
        args = value["parameters"]
        if not isinstance(args, dict):
            raise ValueError("parameters must be an object")
        if value["operation"] == "query":
            if not {"dataset"} <= set(args) <= {"dataset", "entity", "start_date", "end_date", "limit", "offset"}:
                raise ValueError("unknown query parameter")
            if args["dataset"] not in DATASETS:
                raise ValueError("unknown dataset")
            for field in ("entity", "start_date", "end_date"):
                if field in args and not isinstance(args[field], str):
                    raise ValueError(f"{field} must be a string")
            validate_query(args["dataset"], args.get("entity", ""), args.get("start_date") or None,
                           args.get("end_date") or None, args.get("limit", 25), args.get("offset", 0))
            integer(args.get("limit", 25), 1, 100, "limit")
        elif value["operation"] == "review":
            if not set(args) <= {"bank", "limit"} or not isinstance(args.get("bank", ""), str):
                raise ValueError("unknown review parameter")
            validate_query("bank_risk", args.get("bank", ""), None, None, args.get("limit", 10), 0)
            integer(args.get("limit", 10), 1, 25, "limit")
        else:
            raise ValueError("only research query and review operations are supported")
        policy = value["requirements"]
        if not isinstance(policy, dict) or set(policy) != {
            "max_observation_age_seconds", "require_numeric_rows", "require_known_rights", "require_complete_page"
        }:
            raise ValueError("explicit research requirements are required")
        age = policy["max_observation_age_seconds"]
        if age is not None:
            integer(age, 60, 31_622_400, "max_observation_age_seconds")
        for name in ("require_numeric_rows", "require_known_rights", "require_complete_page"):
            if type(policy[name]) is not bool:
                raise ValueError(f"{name} must be boolean")
        raw = encode(value)
        if len(raw) > 8192:
            raise ValueError("workflow too large")
        return cls(raw)

    @property
    def value(self):
        return decode(self.document)

    @property
    def id(self):
        return self.value["id"]

    @property
    def sha256(self):
        return hashlib.sha256(self.document).hexdigest()


def presets():
    """Explicit research policies; none grants trade or redistribution authority."""
    rows = []
    for identifier, dataset, age in (
        ("funding-watch", "money_markets", 345600),
        ("bank-evidence", "bank_risk", 15_552_000),
        ("liquidity-watch", "market_liquidity", 86400),
        ("source-watch", "source_health", None),
    ):
        numeric = dataset != "source_health"
        rows.append(Workflow.parse({
            "schema": SCHEMA, "id": identifier, "operation": "query",
            "parameters": {"dataset": dataset, "limit": 25},
            "interval_seconds": 900, "daily_run_limit": 96,
            "requirements": {"max_observation_age_seconds": age,
                             "require_numeric_rows": numeric,
                             "require_known_rights": numeric,
                             "require_complete_page": True},
        }).value)
    return rows
