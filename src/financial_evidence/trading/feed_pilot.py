"""Bounded top-of-book ingestion model and executable synthetic recovery pilot.

This is a normalized, contiguous per-symbol sequence contract, not a Coinbase,
NSE or Databento decoder. A venue adapter must establish its own channel and
snapshot continuity semantics before translating events into this model.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
from typing import Any, BinaryIO, Iterable, Iterator, Mapping

from .source_contract import SourceContract, USES, iso_time, utc_time

MAX_EVENTS = 256
MAX_EVENT_BYTES = 4096
MAX_REPORT_BYTES = 20_000


@dataclass
class _State:
    sequence: int | None = None
    high_water: int = -1
    event_at: datetime | None = None
    quote_at: datetime | None = None
    quote_received_at: datetime | None = None
    received_at: datetime | None = None
    bid: str | None = None
    ask: str | None = None
    quote_hash: str | None = None
    reason: str = "snapshot_required"


def _price(value: Any) -> str:
    if type(value) not in (str, int, float) or len(str(value)) > 40:
        raise ValueError("invalid_price")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("invalid_price") from None
    if not number.is_finite() or not Decimal("1e-18") <= number <= Decimal("1e18"):
        raise ValueError("invalid_price")
    return str(number)


def _quote_hash(bid: str, ask: str) -> str:
    def canonical(value: str) -> str:
        fixed = format(Decimal(value), "f")
        return fixed.rstrip("0").rstrip(".") if "." in fixed else fixed
    return hashlib.sha256((canonical(bid) + ":" + canonical(ask)).encode()).hexdigest()


class FeedState:
    """One bounded source session; all clock inputs belong to the trusted adapter.

    ``received_at`` and ``now`` are injected by the adapter, not by a remote event.
    Using the replay driver cannot establish production source-clock authenticity.
    """

    def __init__(self, contract: SourceContract, *, synthetic: bool = False,
                 use: str = "internal_research", max_symbols: int = 16,
                 heartbeat_timeout_seconds: float = 3.0,
                 max_source_age_seconds: float = 2.0,
                 max_future_skew_seconds: float = 0.1):
        if not isinstance(contract, SourceContract):
            raise ValueError("invalid_source_contract")
        if type(synthetic) is not bool or not isinstance(use, str) or use not in USES or use == "connect":
            raise ValueError("invalid_feed_use")
        if type(max_symbols) is not int or not 1 <= max_symbols <= 64:
            raise ValueError("invalid_symbol_limit")
        for value, minimum, maximum in (
            (heartbeat_timeout_seconds, 0.001, 3600),
            (max_source_age_seconds, 0.001, 86400),
            (max_future_skew_seconds, 0, 60),
        ):
            if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValueError("invalid_clock_policy")
        self.contract = contract
        self.synthetic = synthetic
        self.use = use
        self.max_symbols = max_symbols
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.max_source_age_seconds = max_source_age_seconds
        self.max_future_skew_seconds = max_future_skew_seconds
        self._states: dict[str, _State] = {}
        self._last_clock: datetime | None = None
        self.accepted = 0
        self.rejected = 0
        self.restarts = 0

    def _rights(self, now: datetime, use: str | None = None) -> str | None:
        if use is not None and (not isinstance(use, str) or use not in USES):
            return "unknown_use"
        for required in dict.fromkeys(("connect", self.use, use or self.use)):
            admission = self.contract.admission(required, now, synthetic=self.synthetic)
            if not admission["allowed"]:
                return admission["reason"]
        return None

    def _quarantine(self, reason: str, symbol: str | None = None) -> None:
        targets = (self._states.values() if symbol is None else
                   [self._states[symbol]] if symbol in self._states else [])
        for state in targets:
            state.reason = reason
            state.bid = state.ask = None
            state.quote_at = None
            state.quote_received_at = None

    def restart(self) -> None:
        """Never restore cached quotes as live after reconnect or process recovery."""
        self.restarts += 1
        self._quarantine("restart_snapshot_required")

    def replace_contract(self, contract: SourceContract) -> None:
        """Trusted operator reload; an edited catalog alone does not reload policy."""
        if (not isinstance(contract, SourceContract) or contract.source_id != self.contract.source_id
                or contract.scope != self.contract.scope):
            raise ValueError("source_contract_identity_changed")
        self.contract = contract
        self._quarantine("policy_reload_snapshot_required")

    def ingest(self, event: Mapping[str, Any], *, received_at: datetime, now: datetime) -> dict[str, Any]:
        symbol = None
        try:
            now = utc_time(now)
            received_at = utc_time(received_at)
            if self._last_clock is not None and now < self._last_clock:
                raise ValueError("local_clock_regression")
            self._last_clock = now
            rights = self._rights(now)
            if rights:
                raise ValueError(rights)
            if received_at > now or (now - received_at).total_seconds() > self.heartbeat_timeout_seconds:
                raise ValueError("invalid_receipt_clock")
            if not isinstance(event, Mapping):
                raise ValueError("invalid_event")
            allowed = {"kind", "source_id", "symbol", "sequence", "event_at", "bid", "ask"}
            if set(event) - allowed:
                raise ValueError("unexpected_event_fields")
            try:
                raw = json.dumps(dict(event), allow_nan=False, separators=(",", ":")).encode()
            except (ValueError, TypeError):
                raise ValueError("invalid_event") from None
            if len(raw) > MAX_EVENT_BYTES:
                raise ValueError("event_too_large")
            if event.get("source_id") != self.contract.source_id:
                raise ValueError("source_mismatch")
            candidate = event.get("symbol")
            if not isinstance(candidate, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{0,31}", candidate):
                raise ValueError("invalid_symbol")
            symbol = candidate
            if symbol not in self._states and len(self._states) >= self.max_symbols:
                self.rejected += 1
                return {"accepted": False, "reason": "symbol_capacity", "symbol": symbol}
            kind = event.get("kind")
            sequence = event.get("sequence")
            if not isinstance(kind, str) or kind not in {"snapshot", "update", "heartbeat"}:
                raise ValueError("unknown_event_kind")
            if type(sequence) is not int or not 0 <= sequence <= 2**63 - 1:
                raise ValueError("invalid_sequence")
            event_at = utc_time(event.get("event_at"))
            age = (now - event_at).total_seconds()
            if (received_at - event_at).total_seconds() < -self.max_future_skew_seconds:
                raise ValueError("source_clock_in_future")
            if age > self.max_source_age_seconds:
                raise ValueError("source_event_stale")
            state = self._states.setdefault(symbol, _State())
            if state.received_at is not None and received_at < state.received_at:
                raise ValueError("receipt_clock_regression")
            if state.event_at is not None and event_at < state.event_at:
                raise ValueError("source_clock_regression")
            if state.reason == "current" and (
                (received_at - state.received_at).total_seconds() > self.heartbeat_timeout_seconds
                or (now - state.quote_at).total_seconds() > self.max_source_age_seconds
            ):
                self._quarantine("liveness_snapshot_required", symbol)
            if kind == "heartbeat":
                if "bid" in event or "ask" in event:
                    raise ValueError("heartbeat_contains_quote")
                if state.reason != "current" or sequence != state.sequence:
                    state.high_water = max(state.high_water, sequence)
                    raise ValueError("heartbeat_continuity_unproven")
                state.received_at, state.event_at = received_at, event_at
            else:
                bid, ask = _price(event.get("bid")), _price(event.get("ask"))
                if Decimal(bid) > Decimal(ask):
                    raise ValueError("crossed_quote")
                quote_hash = _quote_hash(bid, ask)
                if kind == "snapshot":
                    if sequence < state.high_water:
                        raise ValueError("snapshot_behind_observed_sequence")
                    if sequence == state.sequence and state.quote_hash != quote_hash:
                        raise ValueError("conflicting_snapshot")
                elif state.reason != "current":
                    state.high_water = max(state.high_water, sequence)
                    raise ValueError("snapshot_required")
                elif sequence != state.sequence + 1:
                    state.high_water = max(state.high_water, sequence)
                    raise ValueError("sequence_gap" if sequence > state.sequence else "sequence_replay")
                state.sequence = sequence
                state.high_water = max(state.high_water, sequence)
                state.event_at = state.quote_at = event_at
                state.received_at = state.quote_received_at = received_at
                state.bid, state.ask, state.reason = bid, ask, "current"
                state.quote_hash = quote_hash
            self.accepted += 1
            return {"accepted": True, "reason": "current", "symbol": symbol}
        except (ValueError, OverflowError) as exc:
            self.rejected += 1
            # Only our bounded reason codes are emitted; never echo event contents.
            reason = str(exc)
            self._quarantine(reason, symbol)
            return {"accepted": False, "reason": reason}

    def latest(self, symbol: str, *, now: datetime, use: str | None = None) -> dict[str, Any]:
        now = utc_time(now)
        reason = self._rights(now, use)
        state = self._states.get(symbol)
        if self._last_clock is not None and now < self._last_clock:
            reason = "local_clock_regression"
        self._last_clock = max(now, self._last_clock) if self._last_clock else now
        if not reason:
            if state is None:
                reason = "snapshot_required"
            elif state.reason != "current":
                reason = state.reason
            elif (now - state.received_at).total_seconds() > self.heartbeat_timeout_seconds:
                reason = "heartbeat_timeout"
            elif (now - state.quote_at).total_seconds() > self.max_source_age_seconds:
                reason = "quote_stale"
        result = {"source_id": self.contract.source_id, "symbol": symbol,
                  "status": "quarantined" if reason else "current",
                  "reason": reason or "current", "synthetic": self.synthetic,
                  "execution_authority": "none", "production_eligible": False}
        if reason:
            self._quarantine(reason, symbol)
        else:
            result.update(sequence=state.sequence, bid=state.bid, ask=state.ask,
                          source_event_at=iso_time(state.quote_at),
                          received_at=iso_time(state.quote_received_at),
                          last_message_received_at=iso_time(state.received_at),
                          clock_tolerance_ms=round(self.max_future_skew_seconds * 1000, 3),
                          source_age_ms=round((now - state.quote_at).total_seconds() * 1000, 3))
        return result


def fixture_contract(now: datetime) -> SourceContract:
    """Permission applies to invented test values only, never to vendor data."""
    now = utc_time(now)
    expires = now + timedelta(days=1)
    permissions = {use: {"status": "denied", "reason": "synthetic_test_only"} for use in USES}
    for use in ("connect", "internal_research"):
        permissions[use] = {"status": "approved", "reason": "invented_fixture_values_only",
                            "evidence_id": "fixture", "expires_at": iso_time(expires)}
    return SourceContract.from_mapping({
        "source_id": "synthetic-feed", "authority": "locally invented test fixture",
        "scope": "synthetic_fixture", "reviewed_at": iso_time(now - timedelta(days=1)),
        "review_expires_at": iso_time(expires), "revoked": False, "permissions": permissions,
        "evidence": [{"id": "fixture", "url": "fixture://invented/top-of-book-v1",
                      "sha256": hashlib.sha256(b"invented-top-of-book-v1").hexdigest(),
                      "retrieved_at": iso_time(now - timedelta(days=1))}],
    })


def replay_events(records: Iterable[Mapping[str, Any]], *, now: datetime) -> dict[str, Any]:
    """Replay invented JSONL records, bounded at 256; source times stay synthetic.

    A record is {offset_ms, event}; only the fixed synthetic source is accepted.
    Local offsets drive the test clock. They are never production receipt times.
    """
    now = utc_time(now)
    state = FeedState(fixture_contract(now), synthetic=True)
    trace = []
    count = 0
    last = now
    for record in records:
        count += 1
        if count > MAX_EVENTS:
            raise ValueError("replay_event_limit")
        if (not isinstance(record, Mapping) or set(record) != {"offset_ms", "event"}
                or type(record.get("offset_ms")) is not int or not 0 <= record["offset_ms"] <= 60_000):
            raise ValueError("invalid_replay_record")
        last = now + timedelta(milliseconds=record["offset_ms"])
        result = state.ingest(record["event"], received_at=last, now=last)
        # Retain aggregate codes only: bounded regardless of replay length.
        if len(trace) < 16:
            trace.append({"event_number": count, **result})
    report = {"schema": "financial-evidence.feed-replay.v1", "synthetic": True,
              "clock_origin": "synthetic_test_clock", "status": "replayed",
              "events": count, "accepted": state.accepted, "rejected": state.rejected,
              "trace": trace, "trace_truncated": count > len(trace),
              "latest": [state.latest(symbol, now=last) for symbol in sorted(state._states)],
              "source_data_fetched": False, "production_eligible": False,
              "live_latency_measured": False, "execution_authority": "none",
              "external_adoption": "not_measured"}
    if len(json.dumps(report).encode()) > MAX_REPORT_BYTES:
        raise ValueError("replay_report_limit")
    return report


def read_replay_jsonl(stream: BinaryIO) -> Iterator[dict[str, Any]]:
    """Read bounded fixture-only JSONL without retaining or printing raw input."""
    total = 0
    count = 0
    while True:
        raw = stream.readline(MAX_EVENT_BYTES + 1)
        if not raw:
            return
        total += len(raw)
        if len(raw) > MAX_EVENT_BYTES or total > MAX_EVENT_BYTES * MAX_EVENTS:
            raise ValueError("replay_input_limit")
        if not raw.strip():
            continue
        count += 1
        if count > MAX_EVENTS:
            raise ValueError("replay_event_limit")
        try:
            row = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise ValueError("invalid_replay_json") from None
        if not isinstance(row, dict):
            raise ValueError("invalid_replay_record")
        yield row


def run_replay_pilot(*, now: datetime | None = None) -> dict[str, Any]:
    """Run deterministic gap, restart, staleness and rights drills with no I/O."""
    now = utc_time(now or datetime.now(timezone.utc))
    state = FeedState(fixture_contract(now), synthetic=True, max_source_age_seconds=2)
    checks = []

    def event(kind: str, sequence: int, offset: int) -> dict[str, Any]:
        value = {"kind": kind, "source_id": "synthetic-feed", "symbol": "TEST-USD",
                 "sequence": sequence, "event_at": iso_time(now + timedelta(milliseconds=offset))}
        if kind != "heartbeat":
            value.update(bid="100.00", ask="100.01")
        return value

    def ingest(name: str, kind: str, sequence: int, offset: int, expected: str) -> None:
        clock = now + timedelta(milliseconds=offset)
        result = state.ingest(event(kind, sequence, offset), received_at=clock, now=clock)
        checks.append({"check": name, "passed": result["reason"] == expected, "reason": result["reason"]})

    ingest("initial_snapshot", "snapshot", 10, 0, "current")
    ingest("contiguous_update", "update", 11, 10, "current")
    ingest("gap_quarantined", "update", 13, 20, "sequence_gap")
    ingest("updates_cannot_recover_gap", "update", 14, 30, "snapshot_required")
    ingest("old_snapshot_refused", "snapshot", 12, 40, "snapshot_behind_observed_sequence")
    ingest("fresh_snapshot_recovers", "snapshot", 14, 50, "current")
    state.restart()
    ingest("restart_requires_snapshot", "update", 15, 60, "snapshot_required")
    ingest("restart_snapshot_recovers", "snapshot", 15, 70, "current")
    ingest("heartbeat_preserves_quote_clock", "heartbeat", 15, 1900, "current")
    quote = state.latest("TEST-USD", now=now + timedelta(milliseconds=2100))
    checks.append({"check": "heartbeat_does_not_refresh_quote", "passed": quote["reason"] == "quote_stale",
                   "reason": quote["reason"]})
    ingest("staleness_snapshot_recovers", "snapshot", 16, 2200, "current")
    quote = state.latest("TEST-USD", now=now + timedelta(milliseconds=5300))
    checks.append({"check": "quiet_stream_quarantined", "passed": quote["reason"] == "heartbeat_timeout",
                   "reason": quote["reason"]})
    rights = state.contract.admission("trading", now, synthetic=True)
    checks.append({"check": "fixture_cannot_authorize_trading", "passed": not rights["allowed"],
                   "reason": rights["reason"]})
    rights = state.contract.admission("internal_research", now + timedelta(days=1), synthetic=True)
    checks.append({"check": "expired_contract_denied", "passed": not rights["allowed"],
                   "reason": rights["reason"]})
    return {"schema": "financial-evidence.feed-pilot.v1", "status": "passed" if all(
        row["passed"] for row in checks) else "failed", "evaluated_at": iso_time(now),
        "synthetic": True, "clock_origin": "synthetic_test_clock", "checks": checks,
        "source_data_fetched": False, "production_eligible": False, "execution_authority": "none",
        "live_latency_measured": False, "external_adoption": "not_measured",
        "accepted_events": state.accepted, "rejected_events": state.rejected, "restarts": state.restarts}
