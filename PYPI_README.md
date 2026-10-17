# Financial Evidence for Python and AI agents

<!-- mcp-name: io.github.beepboop2025/financial-evidence -->

Use **Seiche, LiquiLens, Undertow and Palimpsest** financial research from Python,
the terminal or an MCP client. Review funding conditions, bank disclosures,
market liquidity and economic source availability with original sources, dates
and coverage gaps attached. Operated by LIQUILENS PRIVATE LIMITED.

[Try the research desk](https://beepboop2025.github.io/financial-evidence-skills/start/workflows.html)
· [First-review guide](https://beepboop2025.github.io/financial-evidence-skills/agents/FIRST_REVIEW.md)
· [Connect your tools](https://beepboop2025.github.io/financial-evidence-skills/connect/)

## Install and save your first review

Python 3.10 or newer. The base package has **no required dependencies**; this
review needs no model, account or data API key:

```sh
python3 -m pip install --upgrade financial-evidence
financial-evidence start
financial-evidence review funding --output reviews
```

`start` shows the available tasks offline. `review` makes one bounded public
research request and saves the original `result.json`, a readable `brief.md` and
a hash receipt. Inspect source dates and gaps before using the evidence. At your
next review, compare against the saved capture:

```sh
financial-evidence review funding --output reviews \
  --previous reviews/YOUR-PREVIOUS-CAPTURE/result.json
```

Other starting tasks include covered institutions and indicative BTC exit costs:

```sh
financial-evidence review institutions --selection au-sfb --output reviews
financial-evidence review exit --selection 10000 --output reviews
```

Use `--verification` for installation or CI checks so those reads are labelled
synthetic. Installation starts no scheduler. An unavailable result remains a gap.

## Choose the product for your question

| Product | Research scope | API and MCP guide |
| --- | --- | --- |
| [Seiche](https://seiche.info/) | Funding, money markets, FX and capital-market context with source clocks. | [Seiche developers](https://seiche.info/developers) |
| [LiquiLens](https://liquilens.in/) | Covered banks and financial institutions, published disclosures and review gaps. | [LiquiLens developers](https://liquilens.in/developers/) |
| [Undertow](https://liquilens-undertow.com/) | Market liquidity and indicative BTC exit estimates at published sizes. | [Undertow developers](https://liquilens-undertow.com/developers/) |
| [Palimpsest](https://www.palimpsest.info/) | China and regional research, public records and source availability. The Financial Evidence China view may be metadata-only. | [Palimpsest developers](https://palimpsest.info/developers.html) |

Coverage and permitted use differ by source. Research results do not grant trade
execution, credit approval or redistribution rights; BTC estimates are not
executable quotes.

## Use Python or connect an AI agent

The same base package can save a review from your application:

```python
from financial_evidence.research import fetch_workflow, save_review

result = fetch_workflow("funding", "USD")
capture = save_review(result, "reviews")
print(result["prepared_response"], capture / "brief.md")
```

For an MCP client, use the hosted Streamable HTTP endpoint:

```text
https://agents.seiche.info/products/financial-evidence/mcp
```

Start with `financial_evidence_agent_query` and
`{"dataset":"money_markets","entity":"USD","limit":3}`.
Download the [product MCP configurations](https://beepboop2025.github.io/financial-evidence-skills/connect/all-products.mcp.json)
to connect individual products; each has its own tools and scope.

For the dependency-free local stdio router:

```sh
uvx --from financial-evidence financial-evidence mcp
```

If already installed, run `financial-evidence mcp`. The local router exposes
`financial_evidence_topics`, `financial_evidence_route` and
`financial_evidence_fetch`; the hosted Research Desk has a separate tool set.

## Repeat reviews in your application

The package includes `AgentWorkflow` and the `workflow` CLI, with a private local
journal and comparisons against the last successful capture. On Linux or macOS:

```sh
financial-evidence workflow run funding --selection USD --state ./funding-reviews
financial-evidence workflow report --state ./funding-reviews
financial-evidence workflow history --state ./funding-reviews
```

This path also needs no optional dependencies. Your application chooses when to
run it; installation does not enable polling or remote learning submissions.
Use `--mode test` on `workflow run` for installation checks. See the
[agent workflow guide](https://beepboop2025.github.io/financial-evidence-skills/start/agent-workflows.md)
for Python hooks, monitor checks, feedback and explicitly enabled sharing.

## Optional persistent MCP sessions and source-status streams

Install the `workspace` extra for persistent MCP/HTTP clients:

```sh
python3 -m pip install --upgrade 'financial-evidence[workspace]'
financial-evidence-trading doctor
financial-evidence-trading context
```

```python
import asyncio
from financial_evidence.trading import ProductClient

async def main():
    async with ProductClient(mode="test", timeout=15) as client:
        first = await client.call("seiche", "data_health")
        again = await client.call("seiche", "data_health")
        print(first["timing"], again["timing"])

asyncio.run(main())
```

`mode="test"` labels verification traffic. Sessions are bounded and failed calls
are not automatically replayed. Source-status snapshots and SSE events report
metadata, not live quotes; session reuse cannot make sources fresher. Follow the
[persistent client and stream guide](https://beepboop2025.github.io/financial-evidence-skills/agents/low-latency.md)
for expiry and reconnect handling. The separate `openbb` extra supports the
[OpenBB integration](https://beepboop2025.github.io/financial-evidence-skills/tools/#openbb).

[Source](https://github.com/beepboop2025/financial-evidence-skills)
· [Issues](https://github.com/beepboop2025/financial-evidence-skills/issues)
· [Privacy](https://beepboop2025.github.io/financial-evidence-skills/privacy/)
· [Licence](https://github.com/beepboop2025/financial-evidence-skills/blob/main/LICENSE)
