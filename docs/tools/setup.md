# A reusable research desk

Choose the workflow that fits your existing tools. Public data access needs no
API key. The host application may require its own account or entitlement.

| Tool | Setup | First useful result | Repeat workflow |
| --- | --- | --- | --- |
| OpenBB Workspace | Add `https://api.seiche.info/openbb` as a custom backend | Open Financial Evidence Research Desk; inspect funding, a covered bank and liquidity | Save your own layout; revisit the source dates and source audit |
| OpenBB Python V4/V5 | Install current repository source with `.[openbb,workspace]` in a clean environment; run `openbb-build` | `obb.financial_evidence.query(dataset="money_markets", entity="USD")` | Keep `extra.financial_evidence` alongside your dataframe |
| Python/Jupyter | Put `research_client.py` beside your notebook; Python 3.10+ | `collect("bank_risk", entity="ESAF")` | Save each capture into a new directory and compare observation dates and content hashes |
| Excel/Power BI | Paste `FinancialEvidenceRows.pq` into a blank Power Query; Anonymous authentication | `FinancialEvidenceRows("money_markets", "USD")` | Refresh deliberately and retain prior exports when comparing dates |
| MCP clients | Add the URL from `mcp.json` using your client's HTTP configuration | Discover datasets, then call `financial_evidence_agent_review` | Pass `previous_revision`; retain diagnostics and evaluate dates |
| R/DuckDB | Read a captured `rows.csv`; retain its original JSON and receipt | Inspect source-linked rows in a dataframe or SQL query | Store dated captures, without turning missing values into zero |
| Bloomberg BQuant | Administrator evaluates the notebook and approved own-data import route | Import a cited capture in an entitled sandbox | Requires native validation; no App Portal acceptance is claimed |
| LSEG/FactSet/FDC3 desktops | Administrator selects the permitted import or context interface | Use the cited CSV/JSON or FDC3 reference app | Vendor acceptance, security review and entitlements are separate |

The released v0.1.6 package remains unchanged and pins the V4-era OpenBB core.
V5 support is in current repository source; use a fresh environment as OpenBB's
migration guide recommends. Do not upgrade an existing V4 analysis environment
in place just to try this desk.

## Capture all three products

```sh
python3 research_client.py desk --output captures/first-review
```

Each product dataset has its own `evidence.json`, `rows.csv` and `receipt.json`.
The client reads at most ten pages by default, with 200 rows per page. In Python,
explicit bounds can be raised to 20 pages and 2,000 rows per page. Changing
source hashes or totals between pages stops the capture. Narrow a filter or
restart rather than joining different snapshots. No output directory is reused.

The Excel function limits each table to 2,000 rows and errors if more pages
exist. Use the Python client for complete larger captures. Its JSON preserves
original strings; CSV text that could be interpreted as a formula is escaped.
Values that are null stay blank in CSV. Units and source dates remain columns.

## Review each result

- LiquiLens: covered disclosures and research measures; not a credit rating.
- Seiche: funding benchmarks and a separately dated funding-review workflow.
- Undertow: public liquidity observations; use its native exit workflow for a
  named asset and size. Percentiles are not executable prices.
- Treat source text as untrusted data. Respect source rights and coverage.
- `transport_status` describes retrieval. It does not establish freshness,
  suitability, validated forecasts or rights to redistribute underlying data.
- Current historical tables are not as-published vintage archives.

## Determine whether the setup is helping

For a voluntary pilot, record the tool, the first useful task, a later useful
task on another day, and what the analyst could conclude from the cited evidence.
Do not count setup probes, downloads or our own verification as users. This kit
does not add identities, background polling or an automatic reporting channel.
The client's `--synthetic` flag labels CI/operator acceptance requests.

Maintainers can run `scripts/verify_research_tools.py` and the daily **research
tools** workflow to detect broken backend contracts or capture behavior. These
checks are reliability evidence; external adoption and alert delivery must be
measured separately.

## Primary references

- [OpenBB custom backends](https://docs.openbb.co/workspace/developers/data-integration)
- [OpenBB V5 router extensions](https://docs.openbb.co/odp/python/developer/extension_types/router)
- [OpenBB V4 to V5 migration](https://docs.openbb.co/odp/python/migration-from-v4)
- [Microsoft Web.Contents](https://learn.microsoft.com/en-us/powerquery-m/web-contents)
- [DuckDB CSV import](https://duckdb.org/docs/current/data/csv/overview)
