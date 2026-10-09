# LangChain financial research tools

[`langchain-financial-evidence`](../integrations/langchain/) is a standalone
native LangChain integration for Seiche funding evidence, LiquiLens covered-bank
research and Undertow market liquidity. It calls the existing public evidence
API and preserves citations, source clocks, missing values, rights and errors.

Install the verified [PyPI release 0.1.0](https://pypi.org/project/langchain-financial-evidence/0.1.0/):

```sh
python -m pip install langchain-financial-evidence==0.1.0
```

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

The [LangChain catalog submission](https://github.com/langchain-ai/docs/issues/6593)
is open for maintainer triage and review. The published package and its verified clean
install do not establish catalog acceptance, production adoption, users or revenue.
