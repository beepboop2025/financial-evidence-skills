import copy
import hashlib
import json
from urllib.request import Request

import pytest
from financial_evidence.core import ROUTES, source_reported_metadata
from haystack import Pipeline
from haystack.tools import ComponentTool

from financial_evidence_haystack import FinancialEvidenceQuery
from financial_evidence_haystack import query


MONEY = {
    "schema": "seiche.global-money-markets.v1",
    "generated_at": "2026-10-09T17:00:00Z",
    "markets": [
        {"market_id": "US-USD", "benchmark": {
            "mnemonic": "SOFR", "value": 0, "unit": "%",
            "availability": "AVAILABLE", "status": "FRESH",
            "asof": "2026-10-08", "published_at": "2026-10-09",
            "redistribution_status": "allowed",
        }},
        {"market_id": "XX-XXX", "benchmark": {
            "value": 99, "availability": "RESTRICTED", "asof": None,
        }},
    ],
}


@pytest.fixture
def sources(monkeypatch):
    state = {"calls": [], "document": copy.deepcopy(MONEY), "fail": False}

    def fetch(source, **kwargs):
        state["calls"].append((source.url, kwargs))
        result = {
            "product": source.product, "source_url": source.url,
            "retrieved_at": "2026-10-09T18:00:00Z", "ok": not state["fail"],
            "financial_authority": "none", "carrier_state": "not_published",
        }
        if state["fail"]:
            return {**result, "error": "HTTPError: 503 Service Unavailable"}
        document = copy.deepcopy(state["document"])
        raw = json.dumps(document).encode()
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        return {
            **result, "document": document, "content_sha256": digest,
            "bytes": len(raw), "source_reported": source_reported_metadata(
                source, document, content_sha256=digest
            ),
        }

    monkeypatch.setattr(query, "fetch_source", fetch)
    return state


def test_native_pipeline_preserves_zero_null_rights_and_source_clocks(sources):
    pipeline = Pipeline()
    pipeline.add_component("research", FinancialEvidenceQuery())
    evidence = pipeline.run({"research": {"dataset": "money_markets"}})["research"]["evidence"]
    rows = evidence["results"]
    assert rows[0]["value"] == 0
    assert rows[0]["as_of"] == "2026-10-08"
    assert rows[0]["unit"] == "%"
    assert rows[0]["source_field"] == "/markets/0/benchmark/value"
    assert rows[0]["source_url"] == ROUTES["money-market"][0].url
    assert rows[1]["value"] is None
    assert rows[1]["as_of"] is None
    assert rows[1]["availability"] == "restricted_or_unavailable"
    assert evidence["sources"][0]["retrieved_at"] == "2026-10-09T18:00:00Z"
    assert evidence["sources"][0]["content_sha256"].startswith("sha256:")
    assert evidence["evidence_status"] == "not_evaluated"
    assert evidence["carrier_verification"] == "not_performed"
    assert evidence["financial_authority"] == "none"
    assert len(sources["calls"]) == 1
    assert sources["calls"][0][1]["timeout"] == 10
    assert sources["calls"][0][1]["max_bytes"] == 4_194_304


def test_native_component_tool_and_serialized_pipeline(sources):
    pipeline = Pipeline()
    pipeline.add_component("research", FinancialEvidenceQuery(synthetic=True))
    dumped = pipeline.dumps()
    assert "synthetic: true" in dumped
    assert "2026-10-08" not in dumped
    restored = Pipeline.loads(dumped, allowed_modules=["financial_evidence_haystack.query"])
    assert restored.get_component("research").synthetic is True
    assert restored.run({"research": {"dataset": "money_markets", "limit": 1}})["research"]["evidence"]["returned_rows"] == 1
    tool = ComponentTool(component=FinancialEvidenceQuery(), name="financial_evidence_query")
    assert "money_markets" in tool.parameters["properties"]["dataset"]["enum"]
    assert tool.invoke(dataset="money_markets", limit=1)["evidence"]["returned_rows"] == 1


@pytest.mark.parametrize("arguments", [
    {"dataset": "unknown"}, {"limit": 101}, {"limit": True},
    {"offset": -1}, {"entity": "x" * 101}, {"start_date": "yesterday"},
    {"start_date": "2026-10-10", "end_date": "2026-10-09"},
    {"previous_revision": "not-a-hash"},
])
def test_invalid_input_never_fetches(sources, arguments):
    with pytest.raises(ValueError):
        FinancialEvidenceQuery().run(**{"dataset": "money_markets", **arguments})
    assert sources["calls"] == []


def test_unavailable_source_keeps_errors_and_does_not_invent_rows(sources):
    sources["fail"] = True
    component = FinancialEvidenceQuery()
    first = component.run(dataset="money_markets")["evidence"]
    repeated = component.run(dataset="money_markets", previous_revision=first["revision"])["evidence"]
    assert repeated["transport_status"] == "unavailable"
    assert all(row["value"] is None for row in repeated["results"])
    assert all(row["availability"] == "source_unavailable" for row in repeated["results"])
    assert repeated["sources"][0]["error"] == "HTTPError: 503 Service Unavailable"
    assert repeated["diagnostics"]
    assert repeated["change_status"] == "changed"
    assert "suppressed_rows" not in repeated


def test_partial_source_health_preserves_failed_source(sources, monkeypatch):
    original = query.fetch_source
    failed_url = ROUTES["money-market"][0].url

    def sometimes_unavailable(source, **kwargs):
        result = original(source, **kwargs)
        if source.url == failed_url:
            result = {key: value for key, value in result.items() if key != "document"}
            result.update(ok=False, error="TimeoutError: timed out")
        return result

    monkeypatch.setattr(query, "fetch_source", sometimes_unavailable)
    evidence = FinancialEvidenceQuery().run(dataset="source_health")["evidence"]
    assert evidence["transport_status"] == "partial"
    failed = [source for source in evidence["sources"] if not source["ok"]]
    assert len(failed) == 1
    assert failed[0]["source_url"] == failed_url
    assert failed[0]["error"] == "TimeoutError: timed out"
    assert evidence["financial_authority"] == "none"


def test_unchanged_is_not_fresh_and_rights_changes_are_not_suppressed(sources):
    component = FinancialEvidenceQuery()
    first = component.run(dataset="money_markets")["evidence"]
    second = component.run(dataset="money_markets", previous_revision=first["revision"])["evidence"]
    assert second["change_status"] == "unchanged"
    assert second["results"] == []
    assert second["suppressed_rows"] == 2
    assert second["freshness_status"] == "not_evaluated"
    assert second["sources"] == first["sources"]
    sources["document"]["markets"][0]["benchmark"]["redistribution_status"] = "restricted"
    changed = component.run(dataset="money_markets", previous_revision=first["revision"])["evidence"]
    assert changed["change_status"] == "changed"
    assert changed["results"][0]["value"] is None


def test_synthetic_header_uses_existing_fixed_route_opener(monkeypatch):
    observed = []

    def open_request(request, **kwargs):
        observed.append((dict(request.header_items()), kwargs))
        return "response"

    def fetch(source, *, opener, **kwargs):
        return opener(Request(source.url), timeout=kwargs["timeout"])

    monkeypatch.setattr(query, "FIXED_ROUTE_OPENER", open_request)
    monkeypatch.setattr(query, "fetch_source", fetch)
    FinancialEvidenceQuery(synthetic=True)._fetch_source(ROUTES["money-market"][0], timeout=10, max_bytes=100)
    assert observed[0][0]["X-liquilens-traffic-class"] == "synthetic"
    assert observed[0][1] == {"timeout": 10}


def test_invalid_synthetic_flag_is_rejected():
    with pytest.raises(ValueError):
        FinancialEvidenceQuery(synthetic="false")
