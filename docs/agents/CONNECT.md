# Connect financial research agents

Choose LiquiLens for covered-bank evidence, Seiche for funding context, and
Undertow for market-liquidity research. Start with only the products your task
needs. These public connections have no trade-execution authority.

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
