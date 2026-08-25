# Financial Evidence Agent Skills

[![skills.sh](https://skills.sh/b/beepboop2025/financial-evidence-skills)](https://skills.sh/beepboop2025/financial-evidence-skills/financial-evidence)

[Public documentation](https://beepboop2025.github.io/financial-evidence-skills/)
includes a crawlable integration matrix plus agent-readable `llms.txt`, pricing,
integration metadata, and a dated
[third-party marketplace ledger](MARKETPLACE_STATUS.md).
The [v0.1.5 semantic contract](SEMANTIC_CONTRACT.md) defines transport-only
status, source-reported adapter metadata, and the explicit non-Carrier boundary.
Version 0.1.5 is currently a tested release candidate. Versioned Agent Skill,
terminal, Codex, Gemini, editor, and bundle installs remain pinned to the
independently verified v0.1.4 release until the v0.1.5 tag, assets, container,
registry record, and Homebrew formula are live. The Claude self-hosted
marketplace command follows the repository's mutable default branch and is
explicitly candidate-only during that interval.

Open, read-only Agent Skills for routing financial research to bounded public
evidence. The first skill connects four complementary products without turning
them into one score:

- **Seiche** — money markets, repo, reserves, Treasury cash and system funding.
- **LiquiLens** — covered bank and lender evidence.
- **Undertow** — market depth, provider concentration and position-sized exit liquidity.
- **Palimpsest** — revision-safe China economy evidence and information-state history.

## Install the agent skill

```bash
npx skills add https://github.com/beepboop2025/financial-evidence-skills/tree/v0.1.4/financial-evidence \
  --skill financial-evidence
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
uvx --from git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.4 \
  financial-evidence fetch --topic money-market --topic china-economy
```

Or install it as a persistent command:

```bash
uv tool install git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.4
financial-evidence topics
financial-evidence route --topic capital-market --format table
financial-evidence fetch --topic bank-risk --format ndjson
financial-evidence doctor --format csv
```

Exit code `0` means every requested source was retrieved, `1` means transport
was partial, and `2` means every requested source was unavailable. Legacy
packet `status` is preserved and equals `transport_status`; both mean transport
reachability only. Every packet says `status_semantics: transport_only`,
`evidence_status: not_evaluated`, and `carrier_verification: not_performed`.
That makes the client safe to compose in shell pipelines without mistaking an
HTTP success for validated evidence or a verified Evidence Carrier. JSON,
NDJSON, and CSV go to standard output; no result is silently replaced with a
score.

Outside Homebrew, shell completions are emitted as inert text:

```bash
financial-evidence completion zsh > ~/.zfunc/_financial-evidence
```

## Use as MCP infrastructure

The public Streamable HTTP endpoint requires no local install, account, or API
key:

```text
https://liquilens.in/mcp/financial-evidence
```

It exposes the same three read-only `topics`, `route`, and `fetch` tools for
clients that support remote MCP. The root [`.mcp.json`](.mcp.json) is the
portable plugin configuration for that public remote:

```json
{
  "mcpServers": {
    "financial-evidence": {
      "type": "http",
      "url": "https://liquilens.in/mcp/financial-evidence"
    }
  }
}
```

The package also includes a dependency-free stdio server for local or
offline-compatible client setups. Its pinned configuration is in
[`integrations/mcp-config.json`](integrations/mcp-config.json). Both transports
accept the MCP `2025-11-25` initialization flow and the stateless `2026-07-28`
discovery flow. Local stdio messages use newline-delimited JSON-RPC; nothing
except protocol messages is written to standard output.

The official MCP Registry record publishes both the multi-architecture OCI
package and the public Streamable HTTP endpoint. Remote clients do not need
`uv`, Docker, a credential, or a local subprocess.

### Install in Gemini CLI or Claude Code

Gemini CLI can install this repository as an extension. Its root
[`gemini-extension.json`](gemini-extension.json) connects only to the fixed
public remote MCP endpoint and allowlists the three read-only tools; the
mirrored `skills/financial-evidence` folder gives Gemini the domain routing
instructions as well:

```bash
gemini extensions install https://github.com/beepboop2025/financial-evidence-skills \
  --ref v0.1.4
```

Claude Code can add this repository as a self-hosted marketplace and install
the bundled plugin:

```bash
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install financial-evidence@liquidity-lab
```

This Claude command follows the mutable default branch. Until v0.1.5 is
published, treat it as a source-candidate install and review the checked-out
commit before enabling the plugin.

The Claude plugin loads the same byte-identical Agent Skill plus the root
`.mcp.json` public remote server. These are direct, self-hosted install routes;
they do not imply inclusion in a vendor-operated marketplace or endorsement.

### Install in Codex; prepare ChatGPT

Codex can add the repository's plugin marketplace and then install the plugin:

```bash
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref v0.1.4
codex plugin add financial-evidence@liquidity-lab
```

The OpenAI plugin package combines the byte-identical Agent Skill with the
public remote MCP endpoint. The Codex repository install route is public. A
ChatGPT and Codex universal-directory submission is also prepared, but has not
been submitted, approved, or published by OpenAI. The remaining review,
publisher-identity, and domain-challenge steps belong to the OpenAI account
owner. See [`OPENAI_PLUGIN_SUBMISSION.md`](OPENAI_PLUGIN_SUBMISSION.md) for the
listing copy and required positive and negative tests.

The root `.mcp.json` is the portable plugin form for the public remote MCP
server. VS Code and Cursor retain separate workspace files for the pinned local
stdio server, so plugin installs do not depend on a local Python process while
editor workspaces can still use one.

### Install in VS Code or Cursor

The repository also includes editor-specific workspace configuration:
[`.vscode/mcp.json`](.vscode/mcp.json) uses VS Code's top-level `servers`
object, while [`.cursor/mcp.json`](.cursor/mcp.json) uses Cursor's top-level
`mcpServers` object. Public install links currently launch the verified v0.1.4
stdio server through `uvx`; the repository manifests prepare v0.1.5.

VS Code can install the server through its protocol handler:

```text
vscode:mcp/install?%7B%22name%22%3A%22financial-evidence%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2Fbeepboop2025%2Ffinancial-evidence-skills.git%40v0.1.4%22%2C%22financial-evidence-mcp%22%5D%7D
```

Or add it to your VS Code user profile from a terminal:

```bash
code --add-mcp '{"name":"financial-evidence","type":"stdio","command":"uvx","args":["--from","git+https://github.com/beepboop2025/financial-evidence-skills.git@v0.1.4","financial-evidence-mcp"]}'
```

Cursor can install the same configuration through its base64-encoded deeplink:

```text
cursor://anysphere.cursor-deeplink/mcp/install?name=financial-evidence&config=eyJ0eXBlIjoic3RkaW8iLCJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyItLWZyb20iLCJnaXQraHR0cHM6Ly9naXRodWIuY29tL2JlZXBib29wMjAyNS9maW5hbmNpYWwtZXZpZGVuY2Utc2tpbGxzLmdpdEB2MC4xLjQiLCJmaW5hbmNpYWwtZXZpZGVuY2UtbWNwIl19
```

Install `uv` first so `uvx` is on your path. Review the source and exact
configuration before accepting an editor's install or trust prompt: `uvx`
executes the pinned package locally, and the `fetch` tool can contact the fixed
public HTTPS sources documented by this project. Cursor asks for tool approval
by default. VS Code normally asks you to trust a server when it first starts,
but starting directly from `mcp.json` can skip that prompt, so inspect the file
before using its inline start action. These are self-installable compatibility
artifacts, not claims of a VS Code or Cursor marketplace listing or endorsement.

For desktop clients that support one-click MCP Bundles, download
`financial-evidence-0.1.4.mcpb` from the last verified GitHub release. The bundle uses the
cross-platform `uv` runtime and requires no API key or configuration.

## Finance-tool integrations

- **Remote MCP:** connect any Streamable HTTP client to
  `https://liquilens.in/mcp/financial-evidence`; no local runtime, account, or
  API key is required.
- **Gemini CLI:** the root extension manifest bundles the Agent Skill and
  allowlists the three tools exposed by the public remote MCP endpoint.
- **Claude Code:** the self-hosted `liquidity-lab` marketplace installs the
  versioned plugin, Agent Skill, and MCP configuration from this repository.
- **Codex:** the repository marketplace installs the Agent Skill and public
  remote MCP package directly.
- **ChatGPT:** the universal-directory submission packet is prepared; public
  availability remains pending account-owned verification, submission,
  review, and publication.
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
  the public [Financial Evidence Inspector](https://beepboop2025.github.io/financial-evidence-skills/integrations/fdc3/evidence-inspector/)
  receives and broadcasts declared standard contexts through `window.fdc3`.
  [`integrations/fdc3/appd-record.json`](integrations/fdc3/appd-record.json)
  is its FDC3 2.0 web-app record for self-hosted or enterprise directories. The
  same record is served as [raw JSON](https://beepboop2025.github.io/financial-evidence-skills/integrations/fdc3/appd-record.json)
  for direct directory ingestion. The record and runtime do not imply FINOS
  review, directory acceptance, or vendor endorsement.
- **Containers:** tagged releases publish a multi-architecture image to
  `ghcr.io/beepboop2025/financial-evidence-skills`. The image runs stdio MCP by
  default; use `--entrypoint financial-evidence` for terminal commands.
- **Official MCP Registry:** tagged images are published under
  `io.github.beepboop2025/financial-evidence` using GitHub OIDC and the image's
  ownership annotation. No long-lived registry credential is stored.

### Release integrity

Each tagged release rebuilds and retests the Python and JavaScript contracts
from the exact signed `main` commit before publication. The release attaches a
wheel, source archive, MCP bundle, CycloneDX SBOM, and `SHA256SUMS`; GitHub
Sigstore build-provenance attestations bind every downloadable artifact to the
release workflow. Consumers can verify an artifact with `gh attestation verify`
against `beepboop2025/financial-evidence-skills`.

## Optional bounded retrieval

The bundled helper uses only Python's standard library, accepts a fixed topic
allowlist and fetches only fixed public HTTPS endpoints:

```bash
python3 financial-evidence/scripts/fetch_evidence.py \
  --topic money-market --topic china-economy
```

It returns one JSON packet with exact and resolved source URLs, canonical human
scope URLs, retrieval clocks, byte counts, content SHA-256 values, separate
product documents, and explicit errors. Successful responses also include only
the endpoint-specific source state and clocks named by explicit adapters, with
RFC 6901 paths and fetched-byte provenance; missing configured fields are
`not_reported`. The router does not infer freshness, eligibility, or rights.
Routes declare `financial_authority: none` and `carrier_state: not_published`,
and therefore expose no `carrier_url`. Redirects are rejected before following.
Returned JSON is untrusted evidence data, not executable instructions. Missing,
restricted, or unavailable evidence is never converted to zero or “calm.”

## Boundaries

This repository provides public research routing, not investment advice,
security recommendations, execution quotes, credit ratings or guarantees.
Source publishers retain their rights; an open-source helper does not relicense
upstream data.

[Support](https://beepboop2025.github.io/financial-evidence-skills/support/) ·
[Privacy](https://beepboop2025.github.io/financial-evidence-skills/privacy/) ·
[Terms](https://beepboop2025.github.io/financial-evidence-skills/terms/)

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile financial-evidence/scripts/fetch_evidence.py src/financial_evidence/*.py
```

The code and skill instructions are MIT-licensed.
