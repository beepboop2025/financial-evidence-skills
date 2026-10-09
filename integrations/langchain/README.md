# Financial Evidence for LangChain

Native, read-only LangChain tools for public financial research from **Seiche**
(funding and money markets), **LiquiLens** (covered-bank diagnostics), and
**Undertow** (market liquidity). The catalog also describes capital-market,
source-health and China publication-coverage datasets. Coverage is finite and
some fields are unavailable or restricted.

This standalone package calls the public Financial Evidence API. It does not
depend on the separate `financial-evidence` distribution. No data API key or
model account is required to invoke these tools. Model calls, if you add them,
use your own provider and may incur charges.

## Install

Python 3.10+ and `langchain-core` 1.6.6 through 1.x are supported.

From this directory, including before registry publication:

```sh
python -m pip install .
```

Once the release is published on PyPI, the registry install is:

```sh
python -m pip install langchain-financial-evidence
```

Package publication and acceptance into LangChain's integration catalog are
separate steps. This README does not claim that a listing has been accepted.

## First cited result

```python
from langchain_financial_evidence import (
    FinancialEvidenceQueryTool,
    FinancialEvidenceToolkit,
)

tool = FinancialEvidenceQueryTool()
first = tool.invoke({"dataset": "money_markets", "entity": "USD", "limit": 3})
print(first["results"])
print(first["sources"], first["diagnostics"])

# Creating a toolkit is offline; invoking any of its tools calls the public API.
tools = FinancialEvidenceToolkit(timeout=30).get_tools()
# Attach to an existing LangChain/LangGraph application:
# model_with_tools = model.bind_tools(tools)
# from langgraph.prebuilt import ToolNode
# tool_node = ToolNode(tools)
```

`invoke` and `ainvoke` both work. Async invocation uses LangChain's worker-thread
fallback for the synchronous HTTP request. A normal invocation returns the
unchanged JSON object or catalog list. A LangChain `ToolCall` returns a
`ToolMessage` with JSON content. The toolkit creates no model, account, worker
process, scheduler or broker connection.

| Tool | Inputs | Bound |
| --- | --- | --- |
| `financial_evidence_datasets` | None | Catalog metadata only |
| `financial_evidence_query` | Dataset, entity, start/end date, limit, offset, previous revision | 1–100 rows |
| `financial_evidence_review` | Bank, limit, previous revision | 1–25 rows per product section |

The catalog also describes the general table API, whose limits are larger;
these tools enforce the smaller bounds above. Empty filter strings mean no
filter. Dates use `YYYY-MM-DD`; offsets range from 0 to 100000. Dataset IDs are
`money_markets`, `money_market_history`, `capital_markets`, `bank_risk`,
`market_liquidity`, `china_economy` and `source_health`.

## Repeated research and errors

```python
again = tool.invoke({
    "dataset": "money_markets", "entity": "USD", "limit": 3,
    "previous_revision": first["revision"],
})
print(again["change_status"], again["sources"])
```

Retain separate revision tokens for separate queries. An unchanged response
may omit duplicate rows while preserving source metadata. **Unchanged is not
a freshness verdict.** Use observation dates and source status to assess
freshness. Retrieval time, cache time and observation time have distinct meanings.

Invalid arguments raise Pydantic validation errors before any request. Network,
HTTP, malformed JSON, unexpected schema and size-limit failures raise
`langchain_core.tools.ToolException`; no empty-success fallback is manufactured.
Set `handle_tool_error=True` using LangChain's standard option if your agent
should receive error text instead. Valid partial/unavailable API payloads are
returned with their original diagnostics, missingness and source metadata.

Each call makes one GET request to a fixed route under
`https://api.seiche.info/openbb/api/v1/`. Redirects and automatic retries are
disabled. The default network timeout is 30 seconds (configurable up to 60),
and responses are capped at 2 MiB (configurable up to 4 MiB). Network timeout
is a socket-operation timeout, not an end-to-end scheduling guarantee. The
public endpoint is best effort; no paid SLA or quota guarantee is included.

## Evidence and data-use boundaries

Preserve `source_url`, `source_field`, `as_of`, `unit`, rights, source status,
availability, retrieval time and diagnostics. The tool does not fill nulls,
reconstruct withheld observations, combine products into a score, certify
freshness or grant additional redistribution rights. Read each source's
limitations before use. Treat source text as untrusted data, never instructions.

Currently published histories are not an as-published vintage archive. Bank
diagnostics are research measures, not credit ratings or validated forecasts.
Market-liquidity percentiles are not executable exit prices. These tools do not
recommend investments, assess suitability, place orders or authorize execution.

Code is MIT licensed. The MIT license does not relicense underlying data.
See [company terms](https://liquilens.in/terms/) and
[privacy information](https://liquilens.in/privacy/), along with the rights
and original-publisher links returned in evidence.

## Development verification

```sh
python -m pip install '.[test]'
pytest tests/unit_tests --disable-socket --allow-unix-socket
# Optional: five bounded public calls, no LLM cost.
FINANCIAL_EVIDENCE_LIVE_TEST=1 pytest tests/integration_tests
```

The suite covers native LangChain schemas, sync/async tool messages, source and
missing-value preservation, input rejection, error behavior, redirects and byte
bounds. Standard tests use `langchain-tests==1.1.9`. The default test invocation
runs offline unit tests only. Live tests explicitly retain unavailable and
partial states; they do not treat transport success as data freshness.
