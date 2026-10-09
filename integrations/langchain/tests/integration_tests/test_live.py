"""Opt-in bounded public requests. No model calls, paid keys or polling."""

import os

import pytest
from langchain_tests.integration_tests import ToolsIntegrationTests
from langchain_financial_evidence import FinancialEvidenceQueryTool

pytestmark = pytest.mark.skipif(os.getenv("FINANCIAL_EVIDENCE_LIVE_TEST") != "1", reason="live requests are opt-in")


class TestLiveQueryStandard(ToolsIntegrationTests):
    @property
    def tool_constructor(self):
        return FinancialEvidenceQueryTool

    @property
    def tool_invoke_params_example(self):
        return {"dataset": "money_markets", "limit": 1}


def test_live_evidence_retains_source_metadata():
    result = FinancialEvidenceQueryTool().invoke({"dataset": "money_markets", "limit": 1})
    assert result["financial_authority"] == "none"
    assert result["freshness_status"] == "not_evaluated"
    assert result["sources"]
    assert result["transport_status"] in {"complete", "partial", "unavailable"}
    for row in result["results"]:
        assert {"value", "as_of", "source_url", "source_field", "unit", "availability", "rights_status"} <= row.keys()
