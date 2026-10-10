# Install Financial Evidence as an MCP server

Use the public Streamable HTTP server when the client supports remote MCP:

- Name: `financial-evidence`
- URL: `https://liquilens.in/mcp/financial-evidence`
- Authentication: none
- Tools: `financial_evidence_topics`, `financial_evidence_route`, and
  `financial_evidence_fetch`

## Cline

With Cline CLI installed, add the remote server:

```bash
cline mcp add financial-evidence https://liquilens.in/mcp/financial-evidence \
  --transport http --yes
```

In Cline's MCP server settings, the equivalent entry is:

```json
{
  "mcpServers": {
    "financial-evidence": {
      "type": "streamableHttp",
      "url": "https://liquilens.in/mcp/financial-evidence"
    }
  }
}
```

Merge this entry into existing settings; preserve other configured servers.
The server needs no authentication. Cline's model provider is configured
separately. On 10 October 2026, Cline CLI 3.0.70 installed this configuration,
and its native MCP client connected, listed the three tools and successfully
called `financial_evidence_topics`. This verifies the MCP connection, not an
LLM-generated research answer.

## Local stdio

For a local stdio server, install `uv` and run this exact signed-release command:

```bash
uvx --from git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.7 \
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
uvx --from git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.7 \
  financial-evidence doctor --format json
```
