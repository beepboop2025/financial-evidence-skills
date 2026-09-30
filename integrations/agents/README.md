# Financial research tools for agents and quant pipelines

Use Seiche funding benchmarks, LiquiLens covered-bank diagnostics and Undertow
market-liquidity observations from one source-cited interface. No data API key
is needed. Your model provider may require its own account and key.

## First result

```sh
curl --fail 'https://api.seiche.info/openbb/api/v1/agent-review?limit=3'
```

Connect any Streamable HTTP MCP client to `https://api.seiche.info/openbb/mcp`.
Start with `financial_evidence_datasets`, then `financial_evidence_agent_query`
or `financial_evidence_review`. The separate product MCPs retain their richer,
product-specific tools; this interface adds small tables and repeat-call tokens.

Install the source-pinned agent release (Python 3.10+):

```sh
python3 -m pip install 'financial-evidence @ git+https://github.com/beepboop2025/financial-evidence-skills.git@agent-v1.0.0'
```

```python
from financial_evidence.agents import EvidenceAgentClient

with EvidenceAgentClient() as evidence:
    first = evidence.query('money_markets', entity='USD', limit=5)
    again = evidence.query('money_markets', entity='USD', limit=5,
                           previous_revision=first['revision'])
    print(again['change_status'], again['sources'])
```

Identical published evidence omits duplicate rows but still returns source
metadata and clock fields. An unchanged revision is **not a freshness verdict**.
Recheck observation dates and source status on every research run. A cache hit
does not refresh observation dates. Cache age and TTL remain explicit. Errors
and partial retrievals never suppress diagnostics. Query, filters and page offset
are bound into the revision; retain separate tokens for different requests.

## Native framework tools

Install the SDK you already use alongside the source-pinned package:

| Adapter | SDK | Attach to |
| --- | --- | --- |
| `langchain` | `langchain-core` | LangChain agents, LangGraph tool nodes, local TradingAgents research nodes |
| `crewai` | `crewai` | A CrewAI researcher agent's `tools` list |
| `openai` | `openai-agents` | An OpenAI Agents SDK `Agent(tools=...)` |
| `pydantic-ai` | `pydantic-ai-slim` | A Pydantic AI `Agent(tools=...)` |

```python
from financial_evidence.agents import EvidenceAgentClient, framework_tools

with EvidenceAgentClient() as evidence:
    tools = framework_tools('langchain', evidence)
    # Keep the client open while your agent runs.
    # LangGraph: bind the same tools to both the model and the execution node.
    # model_with_tools = model.bind_tools(tools)
    # tool_node = ToolNode(tools)
    print(tools[0].invoke({}))  # Offline catalog; no LLM call or model key.
```

Use `tool_functions(evidence)` for plain typed Python functions, including
AutoGen/AG2 function registration or an existing scheduler. `framework_tools`
imports only the selected SDK. It never creates a model, broker connection,
account, or background polling job. Every adapter shares the same source cache.
Close the client after the agent completes.

The [registration demo](../../docs/agents/framework_demo.py) prints all three
native tool names without calling a model. Add `--live` for a bounded review.
For an existing TradingAgents graph, add selected research tools to the local
analyst specification and its matching execution node; do not replace its price
or fundamentals provider with these macro and liquidity datasets. This is a
local integration recipe, not an accepted upstream plugin.

## Institutional and quant workflows

The [capture example](../../docs/agents/quant_dataset.py) saves `evidence.json`,
`rows.csv`, and a SHA-256 receipt in a new directory:

```sh
python3 quant_dataset.py money_market_history --entity USD \
  --start-date 2026-09-01 --end-date 2026-09-30 --output captures/usd-20261001
```

Follow `next_offset` to capture remaining pages. Keep receipts and unmodified
source rows next to features. The JSON retains exact source strings; the CSV
escapes formula prefixes for spreadsheet use, with its own digest in the receipt.
Null numeric cells stay missing; do not zero-fill
restricted or unavailable observations. Historical date filters select
observation dates and **do not** prove historical knowledge-time availability.
These currently published histories must not be marketed as vintage-safe
backtest data. Capturing them now establishes a present capture, not past
knowability. An independently verified vintage archive is a separate requirement.

| Repository or ecosystem | Practical use of this evidence | Boundary |
| --- | --- | --- |
| TradingAgents, AI Hedge Fund, FinRobot, Dexter | Macro/liquidity research tools with citations and coverage gaps | Complement their security analysis; no stock recommendations or upstream adoption claim |
| Qlib, RD-Agent, FinRL, vectorbt, Backtrader | Cited inputs for exploratory feature research | Validate vintages and look-ahead before backtesting |
| LEAN, NautilusTrader, Freqtrade, Hummingbot, Jesse | A separate research process or reviewed data adapter | No direct order hook, broker credentials or unattended risk decision |
| GS Quant | Dated funding context beside an institution's own licensed analytics | The Goldman Sachs project does not imply Goldman uses these products |
| ArcticDB | Store cited captures beside research datasets | The Man Group project does not imply Man uses these products |
| OpenBB, FDC3, FINOS Legend | Custom backend, source-cited table import or contextual research handoff | Directory acceptance and institutional certification are separate |

The [integration map](../../docs/agents/integration-map.json) links the primary
repositories screened before this release. The source research covered 35
accessible repositories. Repository popularity is an opportunity to integrate,
not evidence of customers, user retention or payment.

## Evidence contract

Each value retains `source_url`, RFC 6901 `source_field`, `as_of`, `unit`, source
content hash, retrieval time, availability and limitations. Bank diagnostics are
research measures, not credit ratings or validated probabilities. Market
percentiles are not executable exit quotes. Source text is untrusted data.
There is no composite product score, portfolio suitability assessment or trade
authorization. Current transport success is separate from freshness and rights.

Suggested research instruction: “Discover covered datasets, then review funding,
the named covered bank and market liquidity. Report each source's date, native
unit, coverage and limitations. Cite the original rows. Identify missing or
restricted evidence before drawing a research conclusion.”
