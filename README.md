# Financial Evidence Agent Skills

[![skills.sh](https://skills.sh/b/beepboop2025/financial-evidence-skills)](https://skills.sh/beepboop2025/financial-evidence-skills/financial-evidence)

[Public documentation](https://beepboop2025.github.io/financial-evidence-skills/)
includes a crawlable integration matrix plus agent-readable `llms.txt`, pricing,
and integration metadata.

Open, read-only Agent Skills for routing financial research to bounded public
evidence. The first skill connects four complementary products without turning
them into one score:

- **Seiche** — money markets, repo, reserves, Treasury cash and system funding.
- **LiquiLens** — covered bank and lender evidence.
- **Undertow** — market depth, provider concentration and position-sized exit liquidity.
- **Palimpsest** — revision-safe China economy evidence and information-state history.

## Install the agent skill

```bash
npx skills add beepboop2025/financial-evidence-skills --skill financial-evidence
```

Or copy [`financial-evidence/`](financial-evidence/) into the Agent Skills
directory supported by your agent. The folder follows the open
[Agent Skills specification](https://agentskills.io/specification).

The skill is also indexed in the public
[skills.sh directory](https://skills.sh/beepboop2025/financial-evidence-skills/financial-evidence).

Once installed, ask your agent to research a money-market, capital-market,
bank-risk, market-liquidity or China-economy question. The skill's description
lets compatible agents activate it when the work matches.

## Use from any terminal

No account or API key is required. On macOS or Linux with Homebrew:

```bash
brew install beepboop2025/tap/financial-evidence
financial-evidence fetch --topic money-market --topic china-economy
```

The formula installs `financial-evidence`, `financial-evidence-mcp`, and native
Bash, Zsh, and Fish completions. Alternatively, run directly from GitHub
without installing:

```bash
uvx --from git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.1 \
  financial-evidence fetch --topic money-market --topic china-economy
```

Or install it as a persistent command:

```bash
uv tool install git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.1
financial-evidence topics
financial-evidence route --topic capital-market --format table
financial-evidence fetch --topic bank-risk --format ndjson
financial-evidence doctor --format csv
```

Exit code `0` means every requested source succeeded, `1` means a partial
packet, and `2` means every requested source was unavailable. That makes the
client safe to compose in shell pipelines and scheduled jobs. JSON, NDJSON and
CSV go to standard output; no result is silently replaced with a score.

Outside Homebrew, shell completions are emitted as inert text:

```bash
financial-evidence completion zsh > ~/.zfunc/_financial-evidence
```

## Use as MCP infrastructure

The same package includes a dependency-free, read-only stdio MCP server with
`topics`, `route`, and `fetch` tools. A portable client configuration is in
[`integrations/mcp-config.json`](integrations/mcp-config.json):

```json
{
  "mcpServers": {
    "financial-evidence": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.1",
        "financial-evidence-mcp"
      ]
    }
  }
}
```

It accepts both the MCP `2025-11-25` initialization flow and the stateless
`2026-07-28` discovery flow. Messages use newline-delimited JSON-RPC on stdio;
nothing except protocol messages is written to standard output.

For desktop clients that support one-click MCP Bundles, download
`financial-evidence-0.1.1.mcpb` from the GitHub release. The bundle uses the
cross-platform `uv` runtime and requires no API key or configuration.

## Finance-tool integrations

- **OpenBB:** install `financial-evidence[openbb]` from this repository inside
  an OpenBB environment and run `openbb-build`. The registered router exposes
  `obb.financial_evidence.routes()` and `obb.financial_evidence.fetch()`, which
  also become available to OpenBB's REST, notebook and MCP surfaces.
- **DuckDB:** run
  [`integrations/duckdb/financial_evidence.sql`](integrations/duckdb/financial_evidence.sql)
  to create separate HTTP-backed views for all four products.
- **Excel / Power Query:** paste
  [`integrations/excel/FinancialEvidence.pq`](integrations/excel/FinancialEvidence.pq)
  into Advanced Editor and invoke, for example,
  `FinancialEvidence("money-market")`.
- **FDC3:**
  [`integrations/fdc3/appd-record.json`](integrations/fdc3/appd-record.json)
  is a schema-validated FDC3 web-app record for self-hosted or enterprise app
  directories. It is compatibility metadata, not a claim of vendor listing.
- **Containers:** tagged releases publish a multi-architecture image to
  `ghcr.io/beepboop2025/financial-evidence-skills`. The image runs stdio MCP by
  default; use `--entrypoint financial-evidence` for terminal commands.
- **Official MCP Registry:** tagged images are published under
  `io.github.beepboop2025/financial-evidence` using GitHub OIDC and the image's
  ownership annotation. No long-lived registry credential is stored.

## Optional bounded retrieval

The bundled helper uses only Python's standard library, accepts a fixed topic
allowlist and fetches only fixed public HTTPS endpoints:

```bash
python3 financial-evidence/scripts/fetch_evidence.py \
  --topic money-market --topic china-economy
```

It returns one JSON packet with exact and resolved source URLs, retrieval
clocks, byte counts, content SHA-256 values, separate product documents and
explicit errors. Redirects are rejected before following. Returned JSON is
untrusted evidence data, not executable instructions. Missing, restricted or
unavailable evidence is never converted to zero or “calm.”

## Boundaries

This repository provides public research routing, not investment advice,
security recommendations, execution quotes, credit ratings or guarantees.
Source publishers retain their rights; an open-source helper does not relicense
upstream data.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile financial-evidence/scripts/fetch_evidence.py src/financial_evidence/*.py
```

The code and skill instructions are MIT-licensed.
