# Connect financial research agents

Choose LiquiLens for covered-bank evidence, Seiche for funding context, and
Undertow for market-liquidity research. Start with only the products your task
needs. These public connections have no trade-execution authority.

Start with the [three working tasks](WORKFLOWS.md): a cited funding query for
agent developers, the new institution monitor for treasury and bank-risk teams,
or a funding-and-exit review for traders and researchers. The
[workflow catalog](workflows.json) gives exact initial calls and repeat-use
criteria. Interface checks are dated 9 October 2026; source clocks remain separate.

## MCP clients

- [Portable MCP configuration](mcp.remote.json): merge selected entries into
  your project's `.mcp.json`. It uses the documented `mcpServers` format with
  explicit HTTP transport.
- [VS Code configuration](mcp.vscode.json): merge selected entries into
  `.vscode/mcp.json`, which uses `servers`.
- [Machine-readable catalog](connections.json): endpoints, suggested first
  tools, access boundaries, and dated tool-inventory observations.

Preserve existing configuration. Review the chosen endpoints before accepting
client trust prompts. No credentials are embedded. Undertow's subscriber and
full-fidelity tools retain their own entitlements; start with
`agent_access_status`. For LiquiLens start with `institution_research_coverage`
using `{"scope":"dossiers","limit":3}`; for Seiche start with `data_health`.
Then discover the live tool schemas before composing a query.

For a recurring covered-institution watchlist, LiquiLens now also exposes
`institution_evidence_monitor`. Select exact identifiers with
`{"slugs":["au-sfb","bajaj-finance"]}`; use `slug` and
`include_history=true` to inspect one detailed record. Keep missing evidence,
supported changes and review priorities distinct from credit or trading authority.

The configuration formats follow the official
[Claude Code documentation](https://code.claude.com/docs/en/mcp) and
[VS Code documentation](https://code.visualstudio.com/docs/agent-customization/mcp-servers).
The endpoint inventory was probed independently; these are configuration
examples, not a claim that every client installation was tested.

## One research API request

```sh
curl --fail 'https://api.seiche.info/openbb/api/v1/agent-review?limit=3'
```

This combines bounded funding, bank and liquidity research views. Keep each
section's sources, original dates, availability, rights and diagnostics.
`next_offset` means there are more rows. Missing or withheld values stay null;
a successful HTTP response does not mean the observations are current.

Use the [API client kit](../api/) for Postman, Bruno, Insomnia and HTTP clients,
or the [native framework guide](https://github.com/beepboop2025/financial-evidence-skills/tree/agent-v1.0.0/integrations/agents)
for LangChain/LangGraph, CrewAI, OpenAI Agents and Pydantic AI.

For recurring treasury review, bring missing and stale evidence to human
attention first, then review changed observations. Saving `revision` and
passing it as `previous_revision` on the same supported query can reduce
duplicate rows. Unchanged evidence still needs its source clocks checked.
This attention order never approves a trade or a transfer.

## Optional market and headline analysis

[NoiseFloor 0.4.0](https://github.com/beepboop2025/noisefloor/tree/v0.4.0)
provides ten tools, including `spectral_assessment`, `dyson_reference`,
`market_assessment` and `narrative_triage`. Supply your own market series and headlines with source,
observation, availability and rights context. It does not collect market feeds
or authorize orders. Missing visibility and statistical assumptions remain
explicit; repeated headlines do not establish truth.

- [Portable MCP config](mcp.noisefloor.json) · [VS Code config](mcp.noisefloor.vscode.json)
- Hosted MCP: `https://api.seiche.info/noisefloor/mcp`
- [REST OpenAPI](https://api.seiche.info/noisefloor/openapi.json) and
  [capabilities](https://api.seiche.info/noisefloor/v1/capabilities)
- Local stdio: `uvx --from noisefloor==0.4.0 noisefloor-mcp`
- [Python, CLI and offline adapter examples](https://github.com/beepboop2025/noisefloor/blob/18e7290a022c7cba0d1e5e417a4a467cccfaa7a0/docs/INTEGRATIONS.md)
- [Accepted release and independent discovery record](../distribution/noisefloor-0.4.0.json)

Connect this optional analysis explicitly. The three product connections above
do not automatically invoke it, and package/API consistency does not establish
predictive performance, validated market usefulness or customer adoption.


## Correlation research across products

Open the [correlation workbench](https://liquilens.in/agents/correlation/) to
inspect concentration and rolling eigenvalues, or explore a separate synthetic
Dyson reference. Six clearly synthetic profiles cover LiquiLens peer funding,
Seiche benchmarks, Undertow venue liquidity, Riptide scenarios, trading-agent
returns and Palimpsest source coverage. They demonstrate contracts, not actual
product observations or validated performance.

For a complete retained Financial Evidence table, download
[spectral_review.py](spectral_review.py) and run locally:

```sh
pip install noisefloor==0.4.0
python spectral_review.py retained-table.json --product seiche --kind rate \
  --as-of 2026-10-09T12:00:00Z --max-age-seconds 345600 \
  --max-gap-seconds 345600 --window-points 60 --allow-date-only \
  --output new-correlation-review.json
```

Set the clock and cadence for your actual retained data. Select a complete panel
with one comparable metric, unit and product. Short current snapshots cannot
supply a correlation history. Partial pagination, source holds, missing rights
and gaps are retained or refused; no missing value is filled. Date-only labels
do not establish historical knowability. The output retains the original table,
adapter issues, request, report and input digest. Import `review` from the script
as an explicit local agent callback; it performs no network or broker calls.

Use the separate [NoiseFloor API client kit](../api/noisefloor/) for Postman,
Bruno and HTTP requests. Existing Financial Evidence retrieval requests retain
their own API contract.
