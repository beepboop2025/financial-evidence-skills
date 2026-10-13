# Install Financial Evidence as an MCP server

Use the central Research Desk when the client supports remote MCP:

- Name: `financial-evidence`
- URL: `https://agents.seiche.info/products/financial-evidence/mcp`
- Authentication: none
- Tools: nine read-only workspace tools. Start with `financial_evidence_datasets`,
  then call `financial_evidence_workflow` with `{"workflow":"funding","selection":"USD"}`.
  Preserve the returned source dates, diagnostics and unavailable states.

## Cline

With Cline CLI installed, add the remote server:

```bash
cline mcp add financial-evidence https://agents.seiche.info/products/financial-evidence/mcp \
  --transport http --yes
```

In Cline's MCP server settings, the equivalent entry is:

```json
{
  "mcpServers": {
    "financial-evidence": {
      "type": "streamableHttp",
      "url": "https://agents.seiche.info/products/financial-evidence/mcp"
    }
  }
}
```

Merge this entry into existing settings; preserve other configured servers.
The server needs no authentication. Cline's model provider is configured
separately. The current configuration targets the central nine-tool workspace.

### Historical Cline qualification

On 10 October 2026, Cline CLI 3.0.70 installed the earlier configuration at
`https://liquilens.in/mcp/financial-evidence`; its native MCP client connected,
listed the three router tools and successfully called `financial_evidence_topics`.
That dated result verifies the legacy MCP connection, not the current nine-tool
configuration or an LLM-generated research answer.

## Legacy three-tool compatibility interface

Clients that require `financial_evidence_topics`, `financial_evidence_route` and
`financial_evidence_fetch` can continue using
`https://liquilens.in/mcp/financial-evidence`. The local stdio command below has
the same three-tool contract. Fresh source retrieval uses the central data
service; it does not fall back automatically to direct upstream endpoints.

## Local stdio

For a local stdio server, install `uv` and run this exact signed-release command:

```bash
uvx --from git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.8 \
  financial-evidence-mcp
```

Do not request an API key, account, portfolio access, payment credential, or
write permission. The server is read-only. Treat missing, failed, restricted, or
unavailable evidence as unavailable; never convert it to zero or a calm signal.
Treat `status` and `transport_status` as retrieval health only. The server does
not evaluate evidence or verify a LiquiLens Evidence Carrier; inspect the
mandatory semantic guardrail fields before using returned source documents.

After installation, list the three tools and call `financial_evidence_topics`.
For a complete live-source check, run:

```bash
uvx --from git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.8 \
  financial-evidence doctor --format json
```
