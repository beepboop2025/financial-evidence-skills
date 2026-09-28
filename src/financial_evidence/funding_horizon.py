"""Verify dated common-horizon observations; this is not a publication clock.

Callers must separately validate the current SOFR and EFFR publication clocks
before using this proof to explain an aging card. Values retain their original
dates and publisher freshness labels. No result asserts latest-per-instrument
freshness or manufactures a missing facility observation.
"""

from datetime import date, datetime, timezone
import math

from .tables import _blocked

HORIZON_RULE = "all inputs are clipped to the latest exact-date SOFR-IORB observation"
HISTORY_CLOCK = (
    "native event dates; duplicate vintages collapse at the requested knowledge cutoff"
)
REQUIRED = {
    "policy.sofr": "%",
    "policy.effr": "%",
    "policy.iorb": "%",
    "distribution.sofr.p99": "%",
    "distribution.sofr.volume": "$B",
    "liquidity.reserves": "$B",
    "liquidity.tga": "$B",
    "liquidity.on_rrp": "$B",
    "liquidity.srf": "$B",
}
HISTORICAL_CARDS = {
    "policy.iorb": ("policy", "iorb_pct", "fred_iorb"),
    "liquidity.on_rrp": ("liquidity", "on_rrp_b", "fred_on_rrp"),
    "liquidity.srf": ("liquidity", "srf_b", "nyfed_srf"),
}


def _date(value):
    if not isinstance(value, str):
        raise ValueError("invalid observation date")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("noncanonical observation date")
    return parsed


def _time(value):
    if not isinstance(value, str):
        raise ValueError("missing snapshot identity")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("naive snapshot identity")
    return parsed.astimezone(timezone.utc)


def _number(value):
    try:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    except OverflowError:
        return False


def _equal(left, right):
    return (
        _number(left)
        and _number(right)
        and math.isclose(left, right, rel_tol=0, abs_tol=1e-8)
    )


def _allowed(value):
    if not isinstance(value, dict) or _blocked(value, raw_observation=True):
        raise ValueError("publication rights or shape rejected")


def _cards(document):
    _allowed(document)
    if (
        document.get("ok") is not True
        or document.get("schema") != "seiche.money-market-desk.v1"
    ):
        raise ValueError("unrecognized desk")
    sections = document.get("sections")
    if not isinstance(sections, list) or len(sections) > 32:
        raise ValueError("invalid sections")
    result = {}
    for section in sections:
        _allowed(section)
        metrics = section.get("metrics")
        if not isinstance(metrics, list) or len(metrics) > 100:
            raise ValueError("invalid metrics")
        for row in metrics:
            if not isinstance(row, dict):
                raise ValueError("invalid metric")
            name = row.get("id")
            if not isinstance(name, str) or name in result:
                raise ValueError("duplicate or invalid metric")
            if name in REQUIRED:
                _allowed(row)
            result[name] = row
    return result


def _instrument(market, ident, unit, source, today):
    members = market.get("metrics")
    if not isinstance(members, list) or len(members) > 256:
        raise ValueError("invalid canonical inventory")
    matches = [
        row for row in members if isinstance(row, dict) and row.get("id") == ident
    ]
    if len(matches) != 1:
        raise ValueError("missing or duplicate canonical instrument")
    row = matches[0]
    _allowed(row)
    if (
        row.get("availability") != "AVAILABLE"
        or row.get("unit") != unit
        or row.get("source") != source
        or row.get("source_tier") != "official_open"
        or row.get("redistribution_status") != "allowed"
        or row.get("history_clock") != HISTORY_CLOCK
    ):
        raise ValueError("unrecognized canonical history")
    history = row.get("history")
    if not isinstance(history, list) or not 1 <= len(history) <= 180:
        raise ValueError("canonical history is absent or exceeds bound")
    points = {}
    previous = None
    for item in history:
        if not isinstance(item, list) or len(item) != 2 or not _number(item[1]):
            raise ValueError("invalid canonical observation")
        at = _date(item[0])
        if at > today or previous is not None and at <= previous:
            raise ValueError("future, duplicate or unordered canonical date")
        previous = at
        points[item[0]] = item[1]
    if row.get("asof") != history[-1][0] or not _equal(
        row.get("value"), history[-1][1]
    ):
        raise ValueError("canonical latest point differs from history")
    return row, points


def _chart_point(document, chart_id, column, horizon):
    charts = document.get("charts")
    chart = charts.get(chart_id) if isinstance(charts, dict) else None
    _allowed(chart)
    if (
        chart.get("id") != chart_id
        or chart.get("no_forward_fill") is not True
        or chart.get("row_limit") != 180
    ):
        raise ValueError("unrecognized native chart")
    columns, rows = chart.get("columns"), chart.get("rows")
    if (
        not isinstance(columns, list)
        or not 2 <= len(columns) <= 16
        or any(not isinstance(name, str) for name in columns)
        or len(set(columns)) != len(columns)
        or columns[0] != "date"
        or column not in columns
        or not isinstance(rows, list)
        or not 1 <= len(rows) <= 180
    ):
        raise ValueError("invalid chart shape")
    index = columns.index(column)
    previous, latest = None, None
    for row in rows:
        if not isinstance(row, list) or len(row) != len(columns):
            raise ValueError("invalid chart row")
        at = _date(row[0])
        if at > horizon or previous is not None and at <= previous:
            raise ValueError("chart exceeds horizon or has ambiguous dates")
        if any(value is not None and not _number(value) for value in row[1:]):
            raise ValueError("invalid chart value")
        previous = at
        if row[index] is not None:
            latest = (at, row[index])
    if latest is None or latest[0] != horizon:
        raise ValueError("own historical observation absent at horizon")
    return latest[1]


def common_horizon_evidence(desk, market, history, now):
    """Return strict historical-point proof, or raise ValueError.

    SOFR/EFFR publication-clock admission is deliberately the caller's separate
    obligation. ``history`` is the captured full /api/money-markets response.
    """
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("explicit aware evaluation time required")
    today = now.astimezone(timezone.utc).date()
    cards, full_cards = _cards(desk), _cards(history)
    horizon = _date(desk.get("asof"))
    if not 0 <= (today - horizon).days <= 8:
        raise ValueError("common horizon exceeds bounded age")
    for document in (desk, history):
        methodology, freshness = document.get("methodology"), document.get("freshness")
        if (
            document.get("asof") != horizon.isoformat()
            or not isinstance(methodology, dict)
            or methodology.get("evidence_horizon") != HORIZON_RULE
            or not isinstance(freshness, dict)
            or freshness.get("desk_asof") != horizon.isoformat()
        ):
            raise ValueError("common-horizon methodology absent or inconsistent")
    snapshot = _time(desk.get("snapshot_generated_at"))
    if snapshot != _time(history.get("snapshot_generated_at")) or snapshot > now:
        raise ValueError("different or future completed snapshots")
    for name, unit in REQUIRED.items():
        left, right = cards.get(name), full_cards.get(name)
        if (
            not isinstance(left, dict)
            or not isinstance(right, dict)
            or left.get("status") != "available"
            or right.get("status") != "available"
            or left.get("asof") != right.get("asof")
            or left.get("unit") != unit
            or right.get("unit") != unit
            or not _equal(left.get("value"), right.get("value"))
        ):
            raise ValueError("MCP and history required observations differ")
        if _date(left.get("asof")) > horizon:
            raise ValueError("required observation exceeds declared common horizon")
    _allowed(market)
    if (
        market.get("market_id") != "US-USD"
        or market.get("timezone") != "America/New_York"
        or market.get("settlement_calendar") != "US-FEDWIRE"
    ):
        raise ValueError("unrecognized canonical market")
    sofr, sofr_points = _instrument(market, "US.NYFED.SOFR", "%", "fred", today)
    iorb, iorb_points = _instrument(market, "US.FED.IORB", "%", "fred", today)
    srf, srf_points = _instrument(
        market,
        "US.NYFED.SRF_TAKEUP",
        "local_currency_millions",
        "nyfed_facilities",
        today,
    )
    common = sofr_points.keys() & iorb_points.keys()
    if (
        not common
        or max(common) != horizon.isoformat()
        or sofr["asof"] != horizon.isoformat()
    ):
        raise ValueError(
            "desk is behind or differs from latest canonical common horizon"
        )
    if not _equal(cards["policy.sofr"]["value"], sofr_points[horizon.isoformat()]):
        raise ValueError("SOFR horizon value differs")
    result = {}
    for name, (chart_id, column, source_id) in HISTORICAL_CARDS.items():
        card = cards[name]
        if (
            card.get("asof") != horizon.isoformat()
            or card.get("freshness") not in ("fresh", "aging")
            or card.get("cadence") != "daily"
        ):
            raise ValueError("card is not an available daily horizon observation")
        metadata = history.get("source_metadata")
        matches = (
            [
                row
                for row in metadata
                if isinstance(row, dict) and row.get("id") == source_id
            ]
            if isinstance(metadata, list) and len(metadata) <= 64
            else []
        )
        if (
            len(matches) != 1
            or matches[0].get("available") is not True
            or matches[0].get("asof") != horizon.isoformat()
        ):
            raise ValueError("own source metadata missing or inconsistent")
        _allowed(matches[0])
        point = _chart_point(history, chart_id, column, horizon)
        if not _equal(card["value"], point):
            raise ValueError("card differs from its own chart point")
        canonical_asof = None
        if name == "policy.iorb":
            if not _equal(card["value"], iorb_points.get(horizon.isoformat())):
                raise ValueError("IORB differs from its canonical historical point")
            canonical_asof = iorb["asof"]
        elif name == "liquidity.srf":
            value = srf_points.get(horizon.isoformat())
            if not _number(value) or round(value / 1000, 2) != card["value"]:
                raise ValueError("SRF differs from its canonical historical point")
            canonical_asof = srf["asof"]
        result[name] = {
            "asof": horizon.isoformat(),
            "own_history_chart": chart_id,
            "own_history_column": column,
            "value": point,
            "unit": card["unit"],
            "publisher_freshness": card["freshness"],
            "canonical_latest_asof": canonical_asof,
            "newer_observation_available": canonical_asof > horizon.isoformat()
            if canonical_asof
            else None,
            "basis": "verified_own_observation_at_common_sofr_iorb_horizon",
        }
    return {
        "review_scope": "common_sofr_iorb_horizon",
        "review_asof": horizon.isoformat(),
        "latest_per_instrument": False,
        "historical_observation_checks": result,
        "snapshot_generated_at": desk["snapshot_generated_at"],
    }
