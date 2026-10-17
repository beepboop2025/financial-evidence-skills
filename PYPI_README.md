# Financial Evidence for AI agents

<!-- mcp-name: io.github.beepboop2025/financial-evidence -->

Read-only MCP and API research infrastructure for AI finance and trading agents.
Connect to funding, bank-risk, market-liquidity and economic evidence while keeping
source dates, coverage gaps and rights attached to the result. Operated by
LIQUILENS PRIVATE LIMITED.

## Install

Python 3.10 or newer:

```sh
python3 -m pip install 'financial-evidence[workspace]==0.1.11'
financial-evidence-trading doctor
financial-evidence-trading context
```

The `workspace` extra supplies the MCP/HTTP dependencies needed by the persistent
clients. The base package has no required dependencies and includes the terminal
and three-tool stdio router. Public hosted research reads need no data API key.
Optional subscriptions and client/model costs have separate terms.

## Complete your first review

Version 0.1.11 adds a guided first result, a readable source-cited brief and
comparison with your next review. No optional dependencies or model are needed:

```sh
python3 -m pip install financial-evidence==0.1.11
financial-evidence start
financial-evidence review funding --output reviews
```

The saved capture retains the original JSON, source dates, gaps and a hash
receipt. At your next useful review, add `--previous` with that capture's
`result.json` to compare evidence. Installation does not start a scheduler.
[Follow the first-review guide](https://github.com/beepboop2025/financial-evidence-skills/blob/v0.1.11/docs/agents/FIRST_REVIEW.md).

## Reuse an MCP connection

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

`mode="test"` labels verification traffic. Repeated reads reuse the bounded
session; failed requests are not automatically replayed. Session reuse does not
make source data fresher or grant trading authority.

## Read compact source-status updates

```python
import asyncio
from financial_evidence.trading.context import ContextClient

async def main():
    async with ContextClient() as client:
        snapshot = await client.snapshot()
        print(snapshot)

asyncio.run(main())
```

The public source-status routes are:

- [Contract](https://agents.seiche.info/v1/context/contract)
- [Snapshot](https://agents.seiche.info/v1/context/snapshot)
- [SSE events](https://agents.seiche.info/v1/context/events)

These report metadata, not live quotes. Source freshness, source rights and stream
liveness are separate. See the [Python/JavaScript stream guide](https://beepboop2025.github.io/financial-evidence-skills/agents/low-latency.md)
for expiry, reset and reconnect handling. The JavaScript companion is available
from that guide and is not represented as a Python module.

## Connect an MCP client

For hosted financial research, add this Streamable HTTP endpoint:

```text
https://agents.seiche.info/products/financial-evidence/mcp
```

Start with `financial_evidence_agent_query` and
`{"dataset":"money_markets","entity":"USD","limit":3}`.
Download the [product MCP configurations](https://beepboop2025.github.io/financial-evidence-skills/connect/all-products.mcp.json)
for LiquiLens, Seiche, Undertow, Palimpsest and the other explicitly labelled
research, metadata and sandbox surfaces. Each endpoint has its own tool schema.

For the local three-tool research router:

```sh
uvx --from financial-evidence==0.1.11 financial-evidence mcp
```

The existing `financial-evidence-mcp` command remains available. The local router
exposes `financial_evidence_topics`, `financial_evidence_route` and
`financial_evidence_fetch`; it is separate from the hosted Research Desk tool set.

## Diagnostics and source admission

`financial-evidence-trading latency --samples 3` performs labelled synthetic reads.
`source-access` inspects the permission catalog, while `feed-pilot` runs invented
recovery fixtures. Neither obtains a feed licence, executes a trade or establishes
a production latency guarantee. Preserve unavailable and restricted results.

[Setup guide](https://beepboop2025.github.io/financial-evidence-skills/distribution/ai-trading-tools.html)
· [Source](https://github.com/beepboop2025/financial-evidence-skills)
· [Issues](https://github.com/beepboop2025/financial-evidence-skills/issues)
· [Licence](https://github.com/beepboop2025/financial-evidence-skills/blob/main/LICENSE)
