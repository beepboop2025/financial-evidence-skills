# LangChain financial research tools

[`langchain-financial-evidence`](../integrations/langchain/) is a standalone
native LangChain integration for Seiche funding evidence, LiquiLens covered-bank
research and Undertow market liquidity. It calls the existing public evidence
API and preserves citations, source clocks, missing values, rights and errors.

From a checkout of this repository:

```sh
python -m pip install ./integrations/langchain
```

After PyPI publication, use `python -m pip install langchain-financial-evidence`.
No data API key is needed. This distribution does not depend on a PyPI release
of the separate `financial-evidence` package.

```python
from langchain_financial_evidence import FinancialEvidenceQueryTool, FinancialEvidenceToolkit

query = FinancialEvidenceQueryTool()
evidence = query.invoke({"dataset": "money_markets", "entity": "USD", "limit": 3})
print(evidence["results"])
print(evidence["sources"], evidence["diagnostics"])

tools = FinancialEvidenceToolkit().get_tools()
# Use tools in your existing model.bind_tools(tools) and LangGraph ToolNode(tools).
```

The toolkit provides catalog, query and cross-product review tools. Queries
return at most 100 rows; reviews return at most 25 rows per section. Invocations
are read-only GET requests to the fixed public API. Creating tools is offline.
Source observation dates, rather than successful retrieval, determine freshness.
Partial transport and withheld data remain explicit. No trading or credit-rating
authority is granted.

See the [package guide](../integrations/langchain/README.md) for the complete
input contract, sync/async use, error handling, installation and verification.
See [agent research workflows](../integrations/agents/README.md) for the broader
evidence contract and other supported frameworks.

LangChain's external catalog requires a published package and maintainer review.
Availability in this repository alone does not establish catalog acceptance,
production adoption, users or revenue.
