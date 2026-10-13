"""Explicit observation clocks and conservative, domain-specific input policies."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
import re
from urllib.parse import urlsplit

PRODUCTS = {"seiche", "liquilens", "undertow", "palimpsest", "noisefloor", "narcoscope", "wake",
            "riptide", "myquant-editorial", "myquant-app", "trade-safety", "financial-evidence", "research-data", "seiche-market-corpus"}


def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO UTC string")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if stamp.tzinfo is None:
        raise ValueError("timestamps require a timezone")
    return stamp.astimezone(timezone.utc)


@dataclass(frozen=True)
class Observation:
    product: str
    series: str
    period: str
    value: float | None
    unit: str
    source_url: str
    observed_at: str
    published_at: str
    available_at: str
    captured_at: str
    revision: str
    rights: str = "unknown"
    quality: str = "unknown"
    context_only: bool = False
    source_sha256: str | None = None

    def __post_init__(self):
        if self.product not in PRODUCTS:
            raise ValueError("unsupported product")
        for field in ("series", "period", "unit", "revision"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value or len(value) > 200:
                raise ValueError(f"invalid {field}")
        if self.value is not None and (type(self.value) not in (float, int) or not math.isfinite(self.value)):
            raise ValueError("observation must be a finite scalar or null")
        clocks = [timestamp(getattr(self, field)) for field in
                  ("observed_at", "published_at", "available_at", "captured_at")]
        if clocks[2] < clocks[1] or clocks[3] < clocks[2]:
            raise ValueError("availability and capture cannot precede publication")
        if self.rights not in {"permitted", "restricted", "unknown"}:
            raise ValueError("unknown rights state")
        if self.quality not in {"observed", "estimate", "forecast", "unknown"}:
            raise ValueError("unknown quality state")
        if type(self.context_only) is not bool:
            raise ValueError("context_only must be boolean")
        url = urlsplit(self.source_url)
        if url.scheme not in {"https", "http"} or not url.hostname or url.username or url.password:
            raise ValueError("invalid evidence URL")
        if self.source_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256):
            raise ValueError("invalid source digest")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class InputPolicy:
    required_series: tuple[str, ...]
    max_observation_age_seconds: int
    allow_estimates: bool = False
    require_captured_by_decision: bool = True

    def __post_init__(self):
        if (not self.required_series or len(set(self.required_series)) != len(self.required_series)
                or any(not isinstance(s, str) or not s for s in self.required_series)):
            raise ValueError("explicit unique required series needed")
        if type(self.max_observation_age_seconds) is not int or not 0 < self.max_observation_age_seconds <= 31_622_400:
            raise ValueError("invalid maximum observation age")


def select_as_of(observations: list[Observation], as_of: str, *, captured=True) -> list[Observation]:
    """Choose latest available vintage per product/series/period, never future revisions."""
    cutoff = timestamp(as_of)
    latest = {}
    for item in observations:
        clocks = [timestamp(item.published_at), timestamp(item.available_at)]
        if captured:
            clocks.append(timestamp(item.captured_at))
        if max(clocks) > cutoff or timestamp(item.observed_at) > cutoff:
            continue
        key = (item.product, item.series, item.period)
        ordering = (timestamp(item.available_at), timestamp(item.published_at), item.revision)
        if key not in latest or ordering > latest[key][0]:
            latest[key] = (ordering, item)
    return [latest[key][1] for key in sorted(latest)]


def assess(observations: list[Observation], policy: InputPolicy, decision_at: str) -> dict:
    cutoff = timestamp(decision_at)
    selected = select_as_of(observations, decision_at, captured=policy.require_captured_by_decision)
    reasons = []
    by_series = {}
    for item in selected:
        qualified = f"{item.product}:{item.series}"
        old = by_series.get(qualified)
        if old is None or timestamp(item.observed_at) > timestamp(old.observed_at):
            by_series[qualified] = item
    for series in policy.required_series:
        item = by_series.get(series)
        if item is None:
            reasons.append({"series": series, "reason": "missing_at_decision"})
            continue
        checks = [
            (item.value is None, "missing_value"),
            (item.rights != "permitted", "rights_not_permitted"),
            (item.context_only, "context_only"),
            ((cutoff - timestamp(item.observed_at)).total_seconds() > policy.max_observation_age_seconds, "stale_observation"),
            (item.quality != "observed" and not (item.quality == "estimate" and policy.allow_estimates), "quality_not_admitted"),
        ]
        reasons.extend({"series": series, "reason": why} for fails, why in checks if fails)
    return {"status": "hold" if reasons else "input_eligible", "reasons": reasons,
            "decision_at": decision_at, "observations": [x.to_dict() for x in selected],
            "execution_authority": "none", "training_permission": "not_inferred"}
