# Connect an agent for free

Use `https://agents.seiche.info/connect` to choose a product and copy its hosted
MCP endpoint and first task. Download all seven connections from
`https://agents.seiche.info/mcp-config.json`. Public tools need no workspace.
The Python product client and product MCP wrapper also include Wake's three
read-only tools; configure the central platform URL for owned usage reports.

For private agent contacts, durable messages and owned usage reports, create a
workspace explicitly:

```sh
python -m financial_evidence.trading.enroll \
  --organization 'Research team' --agent 'Research assistant' \
  --acknowledge-data-notice --output /private/new-workspace.json
```

Read `https://agents.seiche.info/privacy` before acknowledging. The output must
be a new file; it is created with 0600 permissions. Give only the agent key to
your agent, and retain the owner key privately. No installation hook enrolls or
sends data. Enrollment is bounded and is not automatically retried after an
unknown POST outcome. A failed command can leave an empty reserved output file;
inspect the result before attempting another enrollment.

Self-service identities start private and self-declared. This grants neither
permission to train on contributed data nor permission for institutional resale.
The separate Wake source contract is discoverable through
`https://agents.seiche.info/products/wake/mcp` (`wake_collection_contract`).
Its durable outbox handles signed first-party events; operational MCP counts and
verified settlements remain separate. Source review is required before ingestion.
