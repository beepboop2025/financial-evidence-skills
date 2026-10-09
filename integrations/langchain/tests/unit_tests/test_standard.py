"""Official LangChain native tool schema/constructor compatibility tests."""

from langchain_tests.unit_tests import ToolsUnitTests
from langchain_financial_evidence import (
    FinancialEvidenceDatasetsTool, FinancialEvidenceQueryTool, FinancialEvidenceReviewTool,
)


class TestDatasetsStandard(ToolsUnitTests):
    @property
    def tool_constructor(self):
        return FinancialEvidenceDatasetsTool

    @property
    def tool_invoke_params_example(self):
        return {}


class TestQueryStandard(ToolsUnitTests):
    @property
    def tool_constructor(self):
        return FinancialEvidenceQueryTool

    @property
    def tool_invoke_params_example(self):
        return {"dataset": "money_markets", "limit": 1}


class TestReviewStandard(ToolsUnitTests):
    @property
    def tool_constructor(self):
        return FinancialEvidenceReviewTool

    @property
    def tool_invoke_params_example(self):
        return {"limit": 1}
