# Forward financial research in agent and quant tools

Run a small, source-cited funding review in the tool you already use. These
examples reuse the repository's `EvidenceAgentClient` and native framework
adapters. They add retained capture clocks and refuse historical simulation of
today's amended observations.

| Route | Deliverable | Acceptance scope |
| --- | --- | --- |
| LangChain / LangGraph | One native tool call through a compiled `StateGraph` / `ToolNode` | Actual optional framework runtime; no model call needed |
| CrewAI | Native research tool invocation; same tool can be attached to a researcher | Tool runtime; no autonomous Crew or model quality claim |
| TradingAgents | `get_forward_funding_context` LangChain tool for a local analyst extension | Current UTC date only; upstream TradingAgents graph integration remains unverified |
| QuantConnect / LEAN | `ForwardFundingEvidence(PythonData)` reader candidate | Shared parser tested; LEAN runtime and marketplace admission remain unverified |
| Hummingbot / Freqtrade | Separate capture-and-inspect CLI for the human operator | Standalone research workflow; no bot plugin, strategy, order or account connection |

See [the validation record](validation.json) for actual versions and results.
Framework execution with fixtures is distinct from a public API probe, and
neither demonstrates independent users or adoption.

## Setup

From the repository root, use a Python environment inside the checkout:

```sh
python3.12 -m venv integrations/finance-research/.venv
integrations/finance-research/.venv/bin/pip install -e .
integrations/finance-research/.venv/bin/pip install -r integrations/finance-research/requirements-native.txt
```

Only install the optional framework you intend to use. The companion and shared
capture/parser need no dependencies beyond the root package. These examples
accept public research data only and do not read brokerage credentials.

## LangGraph and CrewAI

Each command requests one USD funding page, capped at five rows, and creates a
new directory. `--output` must name a directory that does not already exist.

```sh
integrations/finance-research/.venv/bin/python integrations/finance-research/framework_workflows.py langgraph --output captures/langgraph-funding-01
integrations/finance-research/.venv/bin/python integrations/finance-research/framework_workflows.py crewai --output captures/crewai-funding-01
```

`langgraph_review` compiles a real graph and sends one explicit read-only tool
call through its execution node. It uses no model and has no looping edge.
`crewai_review` invokes the existing decorated CrewAI tool directly. To use it
inside your own Crew, attach the selected query tool from
`framework_tools("crewai", client)` to your researcher and keep the client open
until the task completes. Follow the original source citations and report gaps.

The examples follow the official [LangGraph graph interface](https://docs.langchain.com/oss/python/langgraph/quickstart)
and [CrewAI custom-tool interface](https://docs.crewai.com/en/learn/create-custom-tools).

## TradingAgents local extension

`tradingagents_funding_tool(client)` returns a native LangChain tool with inputs
`trade_date` and `entity`. It checks that `trade_date` equals today's **UTC** date
before fetching. Historical or future dates fail explicitly. Its result contains
the full funding packet, not a security price, recommendation or target position.

In your local analyst implementation, add this same tool object to the analyst
tool specification before constructing the graph. The current upstream
[market analyst](https://github.com/TauricResearch/TradingAgents/blob/main/tradingagents/agents/analysts/market_analyst.py)
defines a `TOOLS` tuple used by the analyst turn and its tool node. In revisions
with explicit `bind_tools(...)` and `ToolNode(...)` lists, add the tool to both.
Pass the graph's `trade_date` unchanged. Keep funding observations in a separate
research section and preserve `event_time`, `available_at`, source fields, units
and gaps. This repository does not patch upstream TradingAgents or claim that
an extension has been accepted there.

```sh
integrations/finance-research/.venv/bin/python integrations/finance-research/framework_workflows.py tradingagents --output captures/tradingagents-funding-01
```

## QuantConnect forward archive

`quantconnect_data.py` is a custom-data reader candidate following the official
[PythonData interface](https://www.quantconnect.com/docs/v2/research-environment/datasets/custom-data).
Copy it and `forward_evidence.py` into a local LEAN research project. Set
`ARCHIVE_PATH` to the absolute local `funding.jsonl` from a reviewed capture and
set `ENTITY_ID` / `METRIC` for one series (defaults: `US-USD` / `SOFR`). Subscribe
with UTC data time and `fill_forward=False`. Verify the capture and receipt
digests before import. Keep the complete `capture.json` alongside numerical data.

The reader assigns `time` and `end_time` from **available_at**, which is when this
workflow finished capturing the response. The economic date remains a separate
`event_time` field. This means an October capture of a September observation
cannot appear in September's LEAN timeline. Combining captures requires sorting
by `available_at`; archive selection, deduplication and recurrence are the
research owner's responsibility. This first version imports one capture file.

The parser rejects unknown/restricted rights labels, missing/nonfinite values,
missing citations, future observations and unsupported datasets. These checks
do not grant channel-specific redistribution rights. The original packet and
receipt retain every excluded row and reason. Original-vintage history is not
available through this adapter, and a QuantConnect vendor listing still requires
dataset history, delivery and licensing qualification.

This reader has not been run inside LEAN; native subscription behavior and UTC
configuration must be verified there before describing it as a supported
QuantConnect integration. The example contains no algorithm or order methods.

## Hummingbot and Freqtrade research companion

Use the same companion from a separate terminal or research notebook while
reviewing a bot's context. The CLI has no bot API and writes no bot configuration:

```sh
integrations/finance-research/.venv/bin/python integrations/finance-research/research_companion.py capture --entity USD --output captures/operator-funding-01
integrations/finance-research/.venv/bin/python integrations/finance-research/research_companion.py inspect captures/operator-funding-01/capture.json
```

Read the source status and economic date before using any finding. A fresh
capture can contain an old or unavailable observation. Bank and liquidity
research are also available through `--dataset bank_risk --entity YOUR_BANK`
or `--dataset market_liquidity --entity ''`; only eligible funding rows enter
the numeric JSONL file. Each capture is capped at five rows, reports
`next_offset`, and makes no complete-universe claim.

These files are human-review companions. They are not Hummingbot controllers or
Freqtrade strategies. Official [Hummingbot client documentation](https://hummingbot.org/client/)
and [Freqtrade's strategy and look-ahead discussion](https://www.freqtrade.io/en/stable/strategy-customization/)
describe those separate runtime surfaces. No live bot or native bot session was
started in this validation.

## Retained evidence and clocks

Each new capture folder contains:

- `capture.json`: original agent result, source/transport diagnostics, every row,
  exact economic date precision, and conservative local availability time.
- `funding.jsonl`: only eligible numerical funding records, retaining citations,
  units, clocks and the original packet digest.
- `receipt.json`: content digests, retained/exported row counts, excluded-row
  reasons, pagination status and history scope.

`for_decision(..., mode="historical_backtest")` always refuses current-amended
data. A forward research decision earlier than `captured_at` is also refused.
`available_at` is a local receipt clock, not an assertion about the publisher's
first release. Publisher `knowledge_time` and `published_at` are retained
unchanged. Capture hashes detect accidental edits; they do not establish an
independent timestamp, validate the economics or authorize redistribution.

Run the meaningful integrity and native-runtime checks:

```sh
PYTHONPATH=src OTEL_SDK_DISABLED=true CREWAI_TELEMETRY_DISABLED=true LANGCHAIN_TRACING_V2=false LANGSMITH_TRACING=false integrations/finance-research/.venv/bin/python -m unittest discover -s tests -p 'test_finance_research_*.py' -v
```
