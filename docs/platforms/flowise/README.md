# Financial research in an existing Flowise installation

This download is for existing self-hosted **Flowise 3.1.4** installations. The
official project ended new pull-request acceptance on July 29, 2026, archived its
repository on August 13, and ended core-team support on August 31. No replacement
official template intake was identified when checked on October 11, 2026 (India
time). [Maintainer announcement](https://github.com/FlowiseAI/Flowise/discussions/6727).

## Download and run

Download the [tested Agentflow JSON](financial-evidence-flowise-marketplace-candidate.json),
with its [Flowise licence](FLOWISE-LICENSE.md) and [attribution](NOTICE.md).
The filename retains `marketplace-candidate` to preserve the native receipt's
identity; this template was never submitted to or accepted by Flowise's marketplace.

1. Use your existing installation's Agentflow V2 JSON import function, then save
   the flow. Browser import has not been observed in our validation; the tested
   path used Flowise's normal authenticated save, readback and prediction APIs.
2. Inspect the two nodes: **Start → Financial evidence page**. The Tool node uses
   Custom MCP at `https://agents.seiche.info/products/financial-evidence/mcp`, action
   `financial_evidence_query`, dataset `money_markets`, numeric `limit: 1` and
   numeric `offset: 0`. The template contains no model or financial-data API key.
3. Run the saved flow. Its query arguments are fixed; the chat input does not
   change the requested dataset. Inspect the Tool response and retain its source
   URL, observation date, unit, availability, diagnostics and missing values.

The same native acceptance run also exercised `bank_risk` and
`market_liquidity`. Changing the dataset creates a modified flow; preserve JSON
number types for `limit` and `offset`. The downloadable production template has
no synthetic-traffic header. The three separate acceptance flows were tagged as
synthetic and are retained in the CI artifact, not offered here as user templates.

## What the test established

On October 11, 2026 (India time), four persisted Agentflow V2 workflows ran in
Flowise, flowise-components and flowise-ui 3.1.4, with Node 24.14.0. Each saved
definition was read back byte-for-byte; both native Start and Tool steps finished.
Each response returned one bounded row with source metadata. The final downloaded
template was one of those four runs. Its SHA-256 is:

```text
16b3080f0c2758cbf43c0ac73c02dc02cce8fba3a7b9ffc06e251fae88c81b6c
```

[Native proof](native-proof.json) · [Build and file identities](publication.json) ·
[Successful CI run](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/38091889136)

This is operator-controlled saved-workflow execution, with no model or browser
UI observation. The native MCP implementation supports Streamable HTTP with SSE
fallback; the selected transport branch was not separately instrumented. No
marketplace acceptance or independent-user adoption is established.

Transport completion does not establish data freshness, evidence validity or
redistribution rights. The money-market response retained a source-level
`PARTIAL` state. The market-liquidity row retained its unavailable numeric value
as `null`; bank-risk and market-liquidity rights fields remained `null`. Review
source terms and observation clocks before use. The template performs research
queries and contains no broker connection or order action.
