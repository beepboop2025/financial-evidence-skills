"""Behavioral and network-boundary tests; never contact live services."""

import copy
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest
from langchain_core.tools import ToolException
from pydantic import ValidationError

from langchain_financial_evidence import (
    FinancialEvidenceDatasetsTool,
    FinancialEvidenceQueryTool,
    FinancialEvidenceReviewTool,
    FinancialEvidenceToolkit,
)
from langchain_financial_evidence.tools import _RejectRedirects

QUERY = {
    "schema": "financial-evidence.agent-result.v1", "dataset": "money_markets",
    "transport_status": "partial", "freshness_status": "not_evaluated",
    "financial_authority": "none", "change_status": "changed", "revision": "a" * 64,
    "results": [
        {"value": 0, "as_of": "2026-09-01", "unit": "%", "source_url": "https://example.com/rate",
         "source_field": "/rates/0/value", "rights_status": "attributed", "retrieved_at": "2026-10-01"},
        {"value": None, "availability": "withheld", "rights_status": "restricted"},
    ],
    "sources": [{"source_reported": {"as_of": "2026-09-01"}, "retrieved_at": "2026-10-01"}],
    "diagnostics": [{"reason": "one source unavailable"}],
}


def reply(value):
    return io.BytesIO(json.dumps(value).encode())


def test_toolkit_constructs_offline_and_settings_are_not_model_inputs():
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        tools = FinancialEvidenceToolkit(timeout=12).get_tools()
    opener.assert_not_called()
    assert len(tools) == 3
    assert all(t.timeout == 12 for t in tools)
    assert "timeout" not in tools[1].get_input_schema().model_json_schema()["properties"]
    assert "money_markets" in tools[1].args_schema.model_json_schema()["properties"]["dataset"]["enum"]


def test_native_invoke_preserves_source_clocks_missingness_and_partial_diagnostics():
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        opener.return_value.open.return_value = reply(QUERY)
        result = FinancialEvidenceQueryTool().invoke({"dataset": "money_markets", "entity": "A&B / €"})
        request = opener.return_value.open.call_args.args[0]
    assert result == QUERY
    assert result["results"][0]["value"] == 0
    assert result["results"][1]["value"] is None
    assert request.get_method() == "GET"
    assert urlsplit(request.full_url).netloc == "api.seiche.info"
    assert parse_qs(urlsplit(request.full_url).query)["entity"] == ["A&B / €"]
    assert request.data is None


@pytest.mark.parametrize("change", [
    {"dataset": "unknown"}, {"limit": 101}, {"limit": True}, {"limit": "2"},
    {"offset": -1}, {"offset": 100001}, {"entity": "a" * 101},
    {"start_date": "2026-02-30"}, {"start_date": "20261001"},
    {"start_date": "2026-10-02", "end_date": "2026-10-01"},
    {"previous_revision": "wrong"}, {"base_url": "https://example.com"},
])
def test_invalid_arguments_fail_before_network(change):
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        with pytest.raises(ValidationError):
            FinancialEvidenceQueryTool().invoke({"dataset": "money_markets", **change})
    opener.assert_not_called()


def test_unchanged_and_unavailable_responses_are_not_rewritten():
    for status in ["complete", "unavailable"]:
        payload = copy.deepcopy(QUERY)
        payload.update(results=[], transport_status=status, change_status="unchanged", suppressed_rows=2)
        with patch("langchain_financial_evidence.tools.build_opener") as opener:
            opener.return_value.open.return_value = reply(payload)
            result = FinancialEvidenceQueryTool().invoke({"dataset": "money_markets", "previous_revision": "a" * 64})
        assert result == payload
        assert result["diagnostics"]


def test_review_keeps_products_separate():
    payload = copy.deepcopy(QUERY)
    payload.pop("dataset")
    payload.pop("results")
    payload["sections"] = [{"dataset": d, "results": [{"value": None}], "diagnostics": ["unavailable"]}
                           for d in ["money_markets", "bank_risk", "market_liquidity"]]
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        opener.return_value.open.return_value = reply(payload)
        assert FinancialEvidenceReviewTool().invoke({"limit": 1}) == payload
    with pytest.raises(ValidationError):
        FinancialEvidenceReviewTool().invoke({"limit": 26})


@pytest.mark.parametrize("error, message", [
    (HTTPError("https://api.seiche.info", 429, "secret body", {}, None), "HTTP 429"),
    (HTTPError("https://api.seiche.info", 302, "redirect", {}, None), "HTTP 302"),
    (URLError("secret connection data"), "connection failed"),
    (TimeoutError("secret connection data"), "timed out"),
])
def test_network_errors_never_turn_into_empty_success_or_expose_error_bodies(error, message):
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        opener.return_value.open.side_effect = error
        with pytest.raises(ToolException, match=message) as caught:
            FinancialEvidenceQueryTool().invoke({"dataset": "money_markets"})
        assert "secret" not in str(caught.value)
        assert opener.return_value.open.call_count == 1


@pytest.mark.parametrize("raw", [b"<html>error</html>", b'{"value": NaN}', b"\xff"])
def test_invalid_json_is_explicit_error(raw):
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        opener.return_value.open.return_value = io.BytesIO(raw)
        with pytest.raises(ToolException, match="invalid JSON"):
            FinancialEvidenceQueryTool().invoke({"dataset": "money_markets"})


def test_response_byte_and_row_limits_and_schema():
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        for payload, message in [(b" " * 1025, "byte limit"), (b"{}", "schema"),
                                 (json.dumps(QUERY).encode(), "unbounded query")]:
            opener.return_value.open.return_value = io.BytesIO(payload)
            with pytest.raises(ToolException, match=message):
                FinancialEvidenceQueryTool(max_response_bytes=1024).invoke({"dataset": "money_markets", "limit": 1})


def test_redirect_handler_rejects_other_origins():
    assert _RejectRedirects().redirect_request(None, None, 302, "", {}, "https://other.example") is None


@pytest.mark.asyncio
async def test_native_async_and_tool_call_return_evidence():
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        opener.return_value.open.side_effect = lambda *a, **kw: reply(QUERY)
        tool = FinancialEvidenceQueryTool()
        assert await tool.ainvoke({"dataset": "money_markets"}) == QUERY
        message = tool.invoke({"name": tool.name, "args": {"dataset": "money_markets"},
                               "id": "research-1", "type": "tool_call"})
    assert json.loads(message.content) == QUERY
    assert message.tool_call_id == "research-1"


def test_catalog_is_a_live_metadata_request_and_preserves_catalog_limits():
    payload = [{"id": "money_markets", "maximum_limit": 2000}]
    with patch("langchain_financial_evidence.tools.build_opener") as opener:
        opener.return_value.open.return_value = reply(payload)
        assert FinancialEvidenceDatasetsTool().invoke({}) == payload
