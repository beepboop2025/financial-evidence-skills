# Explicit native research workflows

The hosted MCP surface exposes each workflow as a separate read-only tool:

| Tool | Inputs | Operation |
| --- | --- | --- |
| `financial_evidence_funding_workflow` | One three-letter currency, default USD | Bounded money-market evidence with source dates and rights |
| `financial_evidence_institutions_workflow` | One to five exact institution slugs | Public disclosure monitoring and coverage gaps |
| `financial_evidence_exit_workflow` | One to four USD notionals, 0.01–1,000,000, at most two decimals | Indicative BTC exit research with venue and quote-unit limits |

All operations are individually discoverable with input schemas and explicit read-only, non-destructive, idempotent and open-world annotations. The existing `financial_evidence_workflow` tool remains a compatibility entry point for precisely these three exposed operations. REST and existing stdio clients retain the existing generic call contract. No new operation, execution authority, private account access or source-rights exception is introduced.

The individual tools use the same validated workflow implementation, defaults, traffic classification and unavailable-source behavior as the compatibility entry point. `prepared_response` means evidence is present for review; it does not certify freshness, completion, compliance or executable prices. Source restrictions, missing values, observation dates, quote currencies and content hashes remain part of the returned evidence.
