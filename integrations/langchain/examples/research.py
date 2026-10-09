"""A bounded request without an LLM, broker or API key."""

import json

from langchain_financial_evidence import FinancialEvidenceQueryTool


def main() -> None:
    result = FinancialEvidenceQueryTool().invoke({
        "dataset": "money_markets", "entity": "USD", "limit": 3,
    })
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
