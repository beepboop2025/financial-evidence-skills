"""Explicit, bounded projections of public documents for OpenBB and MCP.

No recursive numeric discovery, cross-product score, or inferred source clock.
Every numeric row points into the fetched document with an RFC 6901 pointer.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Literal

from .core import CARRIER_VERIFICATION, EVIDENCE_STATUS, ROUTES

Dataset = Literal[
    "money_markets",
    "money_market_history",
    "capital_markets",
    "bank_risk",
    "market_liquidity",
    "china_economy",
    "source_health",
]

DATASETS = {
    "money_markets": {
        "name": "Global money-market benchmarks",
        "topics": ["money-market"],
        "description": "Published benchmark rates with native units, availability, source clocks and rights. Rate levels across currencies are not stress rankings.",
    },
    "money_market_history": {
        "name": "Money-market benchmark history",
        "topics": ["money-market"],
        "description": "Published native-cadence benchmark history, with date and entity filters. This is the currently published history, not an as-published vintage archive.",
    },
    "capital_markets": {
        "name": "Capital-market observations",
        "topics": ["capital-market"],
        "description": "Source-reported VIX and high-yield spread observations, retaining each observation's own clock. No composite-clock substitution.",
    },
    "bank_risk": {
        "name": "Covered-bank research diagnostics",
        "topics": ["bank-risk"],
        "description": "LiquiLens corpus monitoring scores and 12-month model probabilities with quarter dates and construction-PIT limitations. Not credit ratings or validated forecasts.",
    },
    "market_liquidity": {
        "name": "Public market-liquidity observations",
        "topics": ["market-liquidity"],
        "description": "Undertow's public measure percentiles with segment validation limits. Withheld percentiles stay null and are never reconstructed.",
    },
    "china_economy": {
        "name": "China economic publication coverage",
        "topics": ["china-economy"],
        "description": "Palimpsest publication status and Seiche's NBS series catalog. Metadata only; no restricted economic values or directional signals.",
    },
    "source_health": {
        "name": "Evidence source and transport audit",
        "topics": list(ROUTES),
        "description": "Per-source transport results, reported clocks, byte hashes and errors. HTTP success is not evidence freshness or validation.",
    },
}


def dataset_catalog() -> list[dict[str, Any]]:
    """Return the offline catalog, including supported filters and limits."""
    return [
        {
            "id": key,
            **value,
            "filters": ["entity", "start_date", "end_date"],
            "default_limit": 200,
            "maximum_limit": 2000,
        }
        for key, value in DATASETS.items()
    ]


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str | None:
    return str(value) if isinstance(value, (str, int, float, bool)) else None


def _number(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) else None


def _items(value: Any) -> list:
    return value if isinstance(value, list) else []


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _blocked(value: dict, *, raw_observation: bool = False) -> bool:
    # Fail closed on explicit source restrictions; do not infer approval.
    states = [
        value.get(k)
        for k in ("availability", "status", "redistribution_status", "rights_status")
    ]
    denied = (
        "restricted",
        "withheld",
        "unavailable",
        "not_available",
        "denied",
        "pending",
        "review_required",
        "prohibited",
        "metadata_only",
    )
    if raw_observation:
        # Projecting an upstream number into a new table is still raw
        # redistribution. It does not make a benchmark or price a derivative.
        denied += ("derived_only",)
    return value.get("publication_allowed") is False or any(
        any(
            word in str(state).strip().lower().replace("-", "_").replace(" ", "_")
            for word in denied
        )
        for state in states
        if state is not None
    )


def _row(source: dict, dataset: str, **fields: Any) -> dict:
    return {
        "dataset": dataset,
        "product": source["product"],
        "entity_id": None,
        "entity_name": None,
        "metric": None,
        "value": None,
        "unit": None,
        "as_of": None,
        "source_status": None,
        "availability": "not_reported",
        "source_url": source["source_url"],
        "source_field": "",
        "observation_url": None,
        "retrieved_at": source.get("retrieved_at"),
        "content_sha256": source.get("content_sha256"),
        "published_at": None,
        "knowledge_time": None,
        "rights_status": None,
        "context": None,
        "transport_status": "complete" if source.get("ok") else "unavailable",
        "evidence_status": EVIDENCE_STATUS,
        "financial_authority": source.get("financial_authority", "none"),
        "carrier_verification": CARRIER_VERIFICATION,
        **fields,
    }


def _rates(source: dict, dataset: str) -> list[dict]:
    document = _obj(source.get("document"))
    if document.get("schema") != "seiche.global-money-markets.v1":
        return []
    rows = []
    for index, item in enumerate(_items(document.get("markets"))):
        item = _obj(item)
        benchmark = _obj(item.get("benchmark"))
        base = f"/markets/{index}/benchmark"
        blocked = any(
            _blocked(node, raw_observation=True) for node in (document, item, benchmark)
        )
        fields = {
            "entity_id": _text(item.get("market_id")),
            "entity_name": _text(item.get("display_name")),
            "metric": _text(benchmark.get("mnemonic")) or "benchmark",
            "unit": _text(benchmark.get("unit")),
            "source_status": _text(benchmark.get("status")),
            "availability": _text(benchmark.get("availability")) or "not_reported",
            "observation_url": _text(benchmark.get("source_url")),
            "published_at": _text(benchmark.get("published_at")),
            "knowledge_time": _text(benchmark.get("knowledge_time")),
            "rights_status": _text(benchmark.get("redistribution_status")),
            "context": _text(item.get("countercase")),
        }
        if blocked:
            fields["availability"] = "restricted_or_unavailable"
        if dataset == "money_markets":
            value = None if blocked else _number(benchmark.get("value"))
            if value is None and not blocked:
                fields["availability"] = "unavailable"
            rows.append(
                _row(
                    source,
                    dataset,
                    **fields,
                    value=value,
                    as_of=_text(benchmark.get("asof")),
                    source_field=base + "/value",
                )
            )
        else:
            # A restricted benchmark cannot be recovered through its history.
            history = benchmark.get("history", []) if not blocked else []
            for j, point in enumerate(history if isinstance(history, list) else []):
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or not isinstance(point[0], str)
                ):
                    continue
                history_fields = {
                    **fields,
                    "published_at": None,
                    "knowledge_time": None,
                    "availability": "published"
                    if _number(point[1]) is not None
                    else "unavailable",
                }
                rows.append(
                    _row(
                        source,
                        dataset,
                        **history_fields,
                        value=_number(point[1]),
                        as_of=point[0],
                        source_field=f"{base}/history/{j}/1",
                    )
                )
            if not history:
                rows.append(
                    _row(source, dataset, **fields, source_field=base + "/history")
                )
    return rows


def _capital(source: dict) -> list[dict]:
    document = _obj(source.get("document"))
    if document.get("schema") != "seiche.world-markets.v1":
        return []
    capital = _obj(document.get("capital_markets"))
    risk_context = _obj(capital.get("risk_context"))
    prices = _obj(risk_context.get("market_prices"))
    parent_blocked = any(
        _blocked(item, raw_observation=True)
        for item in (document, capital, risk_context, prices)
    )
    rows = []
    for key, label, unit in (
        ("vix", "CBOE VIX", "index_points"),
        ("high_yield_oas", "High-yield option-adjusted spread", "%"),
    ):
        value = _obj(prices.get(key))
        number = (
            None
            if parent_blocked or _blocked(value, raw_observation=True)
            else _number(value.get("value"))
        )
        rows.append(
            _row(
                source,
                "capital_markets",
                entity_id=key,
                entity_name=label,
                metric=key,
                value=number,
                unit=unit,
                as_of=_text(value.get("as_of")),
                availability="published" if number is not None else "unavailable",
                source_status=_text(value.get("status")),
                source_field=f"/capital_markets/risk_context/market_prices/{key}/value",
                context="Source registry IDs: "
                + _json(value.get("source_registry_ids", [])),
            )
        )
    return rows


def _banks(source: dict) -> list[dict]:
    document = _obj(source.get("document"))
    items = document.get("rows")
    if not isinstance(items, list):
        return []
    rows = []
    for i, raw in enumerate(items):
        item = _obj(raw)
        hazard = _obj(item.get("hazard"))
        historical = _obj(hazard.get("historical_evidence")) or _obj(
            document.get("historical_evidence")
        )
        context = _json(
            {
                "scope": hazard.get(
                    "score_scope", "corpus_monitoring_not_credit_rating"
                ),
                "quarter": item.get("quarter"),
                "age_months": item.get("age_months"),
                "historical_evidence": historical,
                "validated_backtest": hazard.get("validated_backtest"),
                "real_money_eligible": hazard.get("real_money_eligible"),
            }
        )
        for metric, value, unit, suffix in (
            ("monitoring_score", item.get("score"), "score_points", "/score"),
            ("model_pd_12m", hazard.get("pd_12m"), "ratio", "/hazard/pd_12m"),
        ):
            number = (
                None
                if _blocked(document) or _blocked(item) or _blocked(hazard)
                else _number(value)
            )
            rows.append(
                _row(
                    source,
                    "bank_risk",
                    entity_id=_text(item.get("slug")),
                    entity_name=_text(item.get("name")),
                    metric=metric,
                    value=number,
                    unit=unit,
                    as_of=_text(item.get("as_of")),
                    source_status=_text(item.get("tier")),
                    availability="published" if number is not None else "unavailable",
                    source_field=f"/rows/{i}{suffix}",
                    context=context,
                )
            )
    return rows


def _liquidity(source: dict) -> list[dict]:
    document = _obj(source.get("document"))
    items = document.get("segment_reports")
    if not isinstance(items, list):
        return []
    rows = []
    for i, raw in enumerate(items):
        segment = _obj(raw)
        parent_blocked = _blocked(document) or _blocked(segment)
        coverage = _obj(segment.get("coverage"))
        observations = segment.get("observations", [])
        for j, raw_obs in enumerate(
            observations if isinstance(observations, list) else []
        ):
            obs = _obj(raw_obs)
            withheld = obs.get("stress_pctl_withheld") is True
            value = (
                None
                if withheld or parent_blocked or _blocked(obs)
                else _number(obs.get("stress_pctl"))
            )
            rows.append(
                _row(
                    source,
                    "market_liquidity",
                    entity_id=_text(segment.get("segment")),
                    entity_name=_text(obs.get("measure")),
                    metric="stress_percentile",
                    value=value,
                    unit="ratio",
                    as_of=_text(obs.get("asof")),
                    source_status=_text(coverage.get("report_status")),
                    availability="withheld"
                    if withheld
                    else "published"
                    if value is not None
                    else "unavailable",
                    source_field=f"/segment_reports/{i}/observations/{j}/stress_pctl",
                    observation_url=_text(segment.get("report_url")),
                    context=_json(
                        {
                            "coverage": coverage,
                            "observations": obs.get("obs"),
                            "span_days": obs.get("span_days"),
                            "withheld_note": obs.get("stress_pctl_withheld_note"),
                        }
                    ),
                )
            )
    return rows


def _china(source: dict) -> list[dict]:
    document = _obj(source.get("document"))
    if source["product"] == "Palimpsest":
        return [
            _row(
                source,
                "china_economy",
                entity_id="palimpsest_publication",
                entity_name="Palimpsest publication coverage",
                metric="publication_status",
                source_status=_text(document.get("status")),
                availability="metadata_only",
                rights_status=_text(document.get("status")),
                source_field="/status",
                context=_json(
                    {
                        "availability": document.get("availability"),
                        "publication_allowed": document.get("publication_allowed"),
                        "reason": document.get("reason"),
                        "limitations": document.get("limitations"),
                        "counts": document.get("counts"),
                        "rights_evaluated_at": document.get("rights_evaluated_at"),
                    }
                ),
            )
        ]
    china = _obj(document.get("china_macro"))
    rows = []
    for i, raw in enumerate(_items(china.get("series_catalog"))):
        item = _obj(raw)
        rows.append(
            _row(
                source,
                "china_economy",
                entity_id=_text(item.get("series_id")),
                entity_name=_text(item.get("label")),
                metric="series_catalog",
                availability="metadata_only",
                source_status=_text(china.get("evidence_status")),
                rights_status=_text(china.get("rights_status")),
                source_field=f"/china_macro/series_catalog/{i}",
                observation_url=_text(item.get("release_url")),
                context=_json(
                    {
                        "value_publication": item.get("value_publication"),
                        "reason": china.get("reading"),
                        "boundaries": china.get("boundaries"),
                    }
                ),
            )
        )
    return rows


def project_source(source: dict, dataset: str) -> list[dict]:
    """Produce explicit null rows for transport failures and schema changes."""
    if not source.get("ok"):
        return [
            _row(
                source,
                dataset,
                entity_id=source["product"],
                metric="source_status",
                availability="source_unavailable",
                context=source.get("error"),
            )
        ]
    if dataset == "source_health":
        return [
            _row(
                source,
                dataset,
                entity_id=source.get("topic"),
                metric="source_metadata",
                availability="metadata_only",
                context=_json(source.get("source_reported", {})),
            )
        ]
    if dataset in ("money_markets", "money_market_history"):
        rows = _rates(source, dataset)
    else:
        rows = {
            "capital_markets": _capital,
            "bank_risk": _banks,
            "market_liquidity": _liquidity,
            "china_economy": _china,
        }[dataset](source)
    return rows or [
        _row(
            source,
            dataset,
            entity_id=source["product"],
            metric="source_status",
            availability="schema_unavailable",
            context="Expected published collection was absent or empty; inspect the source document.",
        )
    ]


def validate_query(
    dataset: str,
    entity: str | None,
    start_date: str | None,
    end_date: str | None,
    limit: int,
    offset: int,
) -> None:
    if dataset not in DATASETS:
        raise ValueError(
            f"Unknown dataset {dataset!r}; choose from {', '.join(DATASETS)}"
        )
    if entity is not None and (not isinstance(entity, str) or len(entity) > 100):
        raise ValueError("entity must be text of at most 100 characters")
    for name, value in (("start_date", start_date), ("end_date", end_date)):
        if value is not None:
            try:
                if (
                    not isinstance(value, str)
                    or date.fromisoformat(value).isoformat() != value
                ):
                    raise ValueError
            except (ValueError, TypeError):
                raise ValueError(f"{name} must use YYYY-MM-DD") from None
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must not be after end_date")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 2000:
        raise ValueError("limit must be an integer between 1 and 2000")
    if (
        isinstance(offset, bool)
        or not isinstance(offset, int)
        or not 0 <= offset <= 100000
    ):
        raise ValueError("offset must be an integer between 0 and 100000")


def query_packet(
    packet: dict,
    dataset: str,
    *,
    entity: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> dict:
    """Project, filter and paginate deterministically without changing evidence."""
    validate_query(dataset, entity, start_date, end_date, limit, offset)
    rows = [
        row for source in packet["sources"] for row in project_source(source, dataset)
    ]
    diagnostics = [
        row
        for row in rows
        if row["availability"] in {"source_unavailable", "schema_unavailable"}
    ]
    if entity:
        key = entity.strip().casefold()
        rows = [
            row
            for row in rows
            if key in (row["entity_id"] or "").casefold()
            or key in (row["entity_name"] or "").casefold()
        ]
    if start_date or end_date:
        rows = [
            row
            for row in rows
            if row["as_of"]
            and (not start_date or row["as_of"][:10] >= start_date)
            and (not end_date or row["as_of"][:10] <= end_date)
        ]
    total = len(rows)
    selected = rows[offset : offset + limit]
    return {
        "schema": "liquidity-lab.openbb-table.v1",
        "dataset": dataset,
        "description": DATASETS[dataset]["description"],
        "results": selected,
        "total_rows": total,
        "returned_rows": len(selected),
        "offset": offset,
        "limit": limit,
        "next_offset": offset + limit if offset + limit < total else None,
        "transport_status": packet["transport_status"],
        "status_semantics": "transport_only",
        "evidence_status": EVIDENCE_STATUS,
        "carrier_verification": CARRIER_VERIFICATION,
        "absence_policy": packet["absence_policy"],
        "diagnostics": diagnostics,
        "sources": [
            {k: v for k, v in source.items() if k != "document"}
            for source in packet["sources"]
        ],
    }
