# Financial Evidence Agent Skills

**Individual product plugins:** [install from the Liquidity Lab catalog](https://beepboop2025.github.io/financial-evidence-skills/plugins/)
in Claude Code, Codex or GitHub Copilot CLI. The catalog contains Financial
Evidence, Market Brief and thirteen product plugins, with Gemini downloads and
Cursor / VS Code connection links. Publisher-maintained availability is separate
from each platform's official directory review.

## Connect and ask one question

Hosted Streamable HTTP MCP; no local server or API key for public read-only tools.

Current-source connections use [the central agent platform](https://agents.seiche.info/connect).
[Download the hosted product configurations](docs/connect/all-products.mcp.json):
seven core products plus five clearly labeled research, editorial, metadata or
sandbox surfaces. Python product clients, fixed-source helpers and current editor
configs use the same platform. Requests produce bounded operational demand
counts; optional learning remains off. Old package pins are historical releases
and do not change automatically. See [the routing contract](docs/CENTRAL_HOSTED_CLIENTS.md).
Add the products you need to Claude Code:

```sh
claude mcp add --transport http seiche https://api.seiche.info/mcp
claude mcp add --transport http liquilens https://api.liquilens.in/mcp
claude mcp add --transport http undertow https://api.seiche.info/undertow/mcp
```

**Try this first:** What is the current US funding stress regime, and which dated funding events are next? Cite source dates and missing evidence.

**Python 0.1.11:** run `financial-evidence start`, then
`financial-evidence review funding --output reviews` for a readable brief,
original JSON and a comparison at your next review. Install with `python3 -m pip install financial-evidence==0.1.11`. [First-review guide](docs/agents/FIRST_REVIEW.md).

[Try it in your browser](https://liquilens.in/start/?task=funding) ·
[Cursor configuration](https://liquilens.in/agents/cursor.json) ·
[Codex commands](https://liquilens.in/agents/codex.txt) ·
[Free three-product starter kit and skill](https://liquilens.in/agents/#connect)

For a connected review, ask for institution evidence → funding context → BTC
exit estimates, with each source date, coverage gap and limitation kept separate.
Client/model costs and fair-use limits may apply. Research calls do not execute trades.

Start with one task: https://beepboop2025.github.io/financial-evidence-skills/connect/ — browser, REST, Python and remote MCP setup for funding, covered institutions and BTC exit research. Public reads need no account or API key; retain source dates and unavailable evidence.

**Run the new workflows:** [funding watch, institution monitoring and BTC exit research](https://beepboop2025.github.io/financial-evidence-skills/start/workflows.html). Save a local baseline, compare your next review, or copy the API request into your agent.
**Recurring agent hooks in source:** the main CLI now includes
`financial-evidence workflow` for automatic comparison with saved reviews,
explicit usefulness feedback, linked outcomes and optional durable delivery.
[Python, LangGraph and AI SDK setup](docs/start/agent-workflows.md).
Published Python 0.1.11 and npm 0.1.1 predate these additions; install from the
repository checkout as described in the guide.

Agent developers can retrieve a cited USD funding observation; treasury and
bank-risk teams can use the new institution monitor; traders and researchers
can retain a funding-and-exit review. Each path includes working calls, source
boundaries and a next-day task. [Copy the instructions](docs/agents/WORKFLOWS.md).

**Verified package 0.1.11:** install `financial-evidence[workspace]==0.1.11` from
[PyPI](https://pypi.org/project/financial-evidence/0.1.11/) for persistent MCP sessions,
source-status snapshots and SSE clients. The separately deployed public router
retains version 0.1.8. Both router versions support
`gift-city`, `forex` and `gold` alongside the five existing research topics.
GIFT City serves gold and treasury desks, investors/fund managers, and banks/IFSC
institutions. The helper reads fixed public context; gold/FX calculations remain
explicit user-input steps. See [topic routing](financial-evidence/references/routing.md)
and the [release verification record](docs/releases/0.1.11.json).

**JavaScript agents:** install `@moomoo202020/financial-evidence-ai-sdk@0.1.1`
from npm for typed AI SDK research and source-status tools.
[Copy the verified setup](docs/platforms/ai-sdk.md).

**Reliability update:** Python 0.1.11 bounds the wait for a complete source-status
event, so partial bytes and comment frames cannot hold a read open indefinitely.
Python and JavaScript streams require an initial reset before accepting a
keepalive; npm 0.1.1 includes the synchronized client. These research tools retain
no trade-execution authority.

**Use your existing tools:** the [research tool hub](https://beepboop2025.github.io/financial-evidence-skills/tools/)
provides a complete capture client, notebook, flat Excel/Power BI query and MCP
project defaults for LiquiLens, Seiche and Undertow. Download the kit or connect
the hosted OpenBB desk. Institutional vendor acceptance remains separate.

**[OpenBB Research Desk](integrations/openbb/README.md), Workspace 1.3.0 source.**
Seven cited datasets, a seven-tab Workspace app, an archived USD funding review,
benchmark history charts, typed REST responses and a nine-tool MCP server connect
all four projects. The hosted service is `https://agents.seiche.info/v1/research`.
Install
`.[openbb,workspace]` from this checkout, then run `openbb-build` and
`financial-evidence-api`. The optional modules are included in the v0.1.11 wheel;
the public router retains its separate three-tool contract. The hosted Workspace release identifies
its exact source commit independently at `/api/v1/release`.

**Check a captured USD funding review:** the [funding review checks](integrations/funding-review/README.md)
compare required inputs, units, publication clocks and own-series observations
across Seiche surfaces. The dated SOFR-IORB review exposes newer individual source
dates; it does not claim the latest print for every instrument. Missing, overdue
or contradictory evidence requires attention. Passing these checks is not an
institutional-readiness certification.

**Run recurring research:** [install the durable runtime](https://beepboop2025.github.io/financial-evidence-skills/agents/runtime.html) for fixed policies, bounded scheduling, retained receipts, private MCP and backup recovery across LiquiLens, Seiche and Undertow.

**Automate funding research:** [versioned packets, captured changes, Python, OpenBB and a local agent tool](https://beepboop2025.github.io/financial-evidence-skills/funding/automate/). Public access requires no account; optional application keys use explicit measurement consent. The hosted packet API and downloadable templates are versioned separately from the v0.1.11 wheel.

**Three concrete jobs:** [funding review, Cosmos Bank NPAs and a $100k BTC exit](https://beepboop2025.github.io/financial-evidence-skills/automations/)
with native n8n workflows and optional Slack/Telegram delivery. The
[Cursor task plugin](.cursor-plugin/plugin.json) bundles the same three focused
skills and public MCP connections. Marketplace acceptance is separate.

**Put it into a recurring workflow:** the [funding and counterparty workflow pack](https://beepboop2025.github.io/financial-evidence-skills/workflows/)
retains source documents, a spreadsheet index and a local integrity manifest.
It includes a reviewed Python runner, an opt-in scheduling template and a
ten-day integration scorecard. These examples use the existing 0.1.5 package;
they do not change its release or evidence semantics.

**Try the underlying evidence first:** [Open three browser research questions](https://liquilens.in/start/)
for bank NPA disclosures, dollar funding and BTC exit estimates. Each example
calls its named public MCP after a click and displays the returned sources,
dates and limits. No key or installation is needed. The page also has setup
and starter questions for Financial Evidence and thirteen other hosted MCPs.
The browser examples call individual services; they do not verify an Evidence
Carrier or evaluate a combined Financial Evidence packet.

[![skills.sh](https://skills.sh/b/beepboop2025/financial-evidence-skills)](https://skills.sh/beepboop2025/financial-evidence-skills/financial-evidence)

[Public documentation](https://beepboop2025.github.io/financial-evidence-skills/)
includes a crawlable integration matrix plus agent-readable `llms.txt`, pricing,
integration metadata, and a dated
[third-party marketplace ledger](MARKETPLACE_STATUS.md).
The [v0.1.5 semantic contract](SEMANTIC_CONTRACT.md) defines transport-only
status, source-reported adapter metadata, and the explicit non-Carrier boundary.
Version 0.1.11 is a signed, independently verified release. Its versioned
Agent Skill, terminal, Codex, Gemini, editor, and bundle installs use the same
release, with published artifacts, container and Registry record.
Homebrew 0.1.11 is published after an independent macOS installation and contract check. The Claude
self-hosted marketplace command follows the repository's mutable default branch; review the checked-out commit before enabling it.

Open, read-only Agent Skills for routing financial research to bounded public
evidence. The first skill connects four complementary products without turning
them into one score:

- **Seiche** — money markets, repo, reserves, Treasury cash and system funding.
- **LiquiLens** — covered bank and lender evidence.
- **Undertow** — market depth, provider concentration and position-sized exit liquidity.
- **Palimpsest** — revision-safe China economy evidence and information-state history.

For a daily research workflow, [Market Brief](https://github.com/beepboop2025/market-brief)
provides free, source-cited funding, capital-market and liquidity briefs with local
change comparisons. This separately versioned browser companion and agent skill
uses the existing public evidence sources.

For direct calls to Seiche, LiquiLens and Undertow, the companion
[free agent starter kit](https://liquilens.in/agents/) includes
[Hermes](https://liquilens.in/agents/hermes/) and
[OpenClaw](https://liquilens.in/agents/openclaw/) setup guides. That kit uses a
separate trading-research skill; it does not install Financial Evidence or connect
Palimpsest. Use the versioned install below for this four-product routing skill.

## Install the agent skill

```bash
npx skills add https://github.com/beepboop2025/financial-evidence-skills/tree/v0.1.11/financial-evidence \
  --skill financial-evidence
```

Or copy [`financial-evidence/`](financial-evidence/) into the Agent Skills
directory supported by your agent. The folder follows the open
[Agent Skills specification](https://agentskills.io/specification).

The skill is also indexed in the public
[skills.sh directory](https://skills.sh/beepboop2025/financial-evidence-skills/financial-evidence).

Once installed, ask your agent to research a money-market, capital-market,
bank-risk, market-liquidity, China-economy, GIFT City, forex or gold question.
The skill's description lets compatible agents activate it when the work matches.

## Use from any terminal

No account or API key is required. On macOS or Linux with Homebrew:

```bash
brew install beepboop2025/tap/financial-evidence
financial-evidence fetch --topic money-market --topic china-economy
```

The formula installs `financial-evidence`, `financial-evidence-mcp`, and native
Bash, Zsh, and Fish completions. Homebrew 0.1.11 is independently installed and verified. Its hosted clients use the central service.
Run the pinned PyPI release without a persistent installation:

```bash
uvx --from financial-evidence==0.1.11 \
  financial-evidence fetch --topic money-market --topic china-economy
```

Or install it as a persistent command:

```bash
uv tool install financial-evidence==0.1.11
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

The current hosted Streamable HTTP workspace requires no local install, account,
or API key:

```text
https://agents.seiche.info/products/financial-evidence/mcp
```

Start with `financial_evidence_datasets`, then call
`financial_evidence_workflow` with `{"workflow":"funding","selection":"USD"}`.
For custom rows use `financial_evidence_agent_query`; for a combined funding,
covered-bank and liquidity review use `financial_evidence_review`. Original
source documents are available through `financial_evidence_packet`. The
workspace exposes nine reviewed read-only tools.

The root [`.mcp.json`](.mcp.json), editor configs and
[`integrations/mcp-config.json`](integrations/mcp-config.json) use this service:

```json
{
  "mcpServers": {
    "financial-evidence": {
      "type": "http",
      "url": "https://agents.seiche.info/products/financial-evidence/mcp"
    }
  }
}
```

Hosted operational measurement records bounded product/tool/dataset demand;
optional learning is separate and off by default. The package's dependency-free
stdio router retains its three-tool `topics`, `route`, and `fetch` contract.
Its fresh source retrieval also uses the central data service; normalization and
replay of captured evidence can run locally. There is no automatic direct-origin
fallback. Historical versioned releases and registry records retain their original
configuration until a separately verified release updates them.

### Install in Gemini CLI or Claude Code

Gemini CLI can install this repository as an extension. Its root
[`gemini-extension.json`](gemini-extension.json) connects only to the fixed
hosted workspace and allowlists its nine read-only tools; the
mirrored `skills/financial-evidence` folder gives Gemini the domain routing
instructions as well. Install the signed 0.1.11 release to use the
central nine-tool workspace:

```bash
gemini extensions install https://github.com/beepboop2025/financial-evidence-skills \
  --ref v0.1.11
```

Claude Code can add this repository as a self-hosted marketplace and install
the bundled plugin:

```bash
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install financial-evidence@liquidity-lab
```

This Claude command follows the mutable default branch. Review the checked-out
commit before enabling the plugin; the versioned install routes above remain
pinned to the verified release.

The Claude plugin loads the same byte-identical Agent Skill plus the root
`.mcp.json` public remote server. These are direct, self-hosted install routes;
they do not imply inclusion in a vendor-operated marketplace or endorsement.

### Install in Codex; prepare ChatGPT

Codex can add the repository's plugin marketplace and then install the plugin:

```bash
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref v0.1.11
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
server. The current VS Code and Cursor workspace files use the same hosted
workspace without a local Python process.

### Install in VS Code or Cursor

The repository also includes editor-specific workspace configuration:
[`.vscode/mcp.json`](.vscode/mcp.json) uses VS Code's top-level `servers`
object, while [`.cursor/mcp.json`](.cursor/mcp.json) uses Cursor's top-level
`mcpServers` object. Both current files use the hosted nine-tool workspace.
The install links below connect to the same central nine-tool workspace.
They require no local Python process.

VS Code can install the server through its protocol handler:

```text
vscode:mcp/install?%7B%22name%22%3A%22financial-evidence%22%2C%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fagents.seiche.info%2Fproducts%2Ffinancial-evidence%2Fmcp%22%7D
```

Or add it to your VS Code user profile from a terminal:

```bash
code --add-mcp '{"name":"financial-evidence","type":"http","url":"https://agents.seiche.info/products/financial-evidence/mcp"}'
```

Cursor can install the same configuration through its base64-encoded deeplink:

```text
cursor://anysphere.cursor-deeplink/mcp/install?name=financial-evidence&config=eyJ0eXBlIjoiaHR0cCIsInVybCI6Imh0dHBzOi8vYWdlbnRzLnNlaWNoZS5pbmZvL3Byb2R1Y3RzL2ZpbmFuY2lhbC1ldmlkZW5jZS9tY3AifQ==
```

Review the hosted URL and configuration before accepting an editor's
install or trust prompt. Calls use the central research service and retain
the original evidence sources and observation dates. Cursor asks for tool approval
by default. VS Code normally asks you to trust a server when it first starts,
but starting directly from `mcp.json` can skip that prompt, so inspect the file
before using its inline start action. These are self-installable compatibility
artifacts, not claims of a VS Code or Cursor marketplace listing or endorsement.

For desktop clients that support one-click MCP Bundles, download
`financial-evidence-0.1.11.mcpb` from the last verified GitHub release. The bundle uses the
cross-platform `uv` runtime and requires no API key or configuration.

## Finance-tool integrations

- **Remote MCP:** connect any Streamable HTTP client to
  `https://agents.seiche.info/products/financial-evidence/mcp`; no local runtime, account, or
  API key is required.
- **Gemini CLI:** the root extension manifest bundles the Agent Skill and
  allowlists the nine tools exposed by the hosted research workspace.
- **Claude Code:** the self-hosted `liquidity-lab` marketplace installs the
  versioned plugin, Agent Skill, and MCP configuration from this repository.
- **Codex:** the repository marketplace installs the Agent Skill and public
  remote MCP package directly.
- **ChatGPT:** the universal-directory submission packet is prepared; public
  availability remains pending account-owned verification, submission,
  review, and publication.
- **OpenBB:** install `.[openbb,workspace]` from current repository source in a
  clean environment and run `openbb-build`. V4 and V5 compatibility is checked
  in CI, including the released v0.1.8 dependency range. The router exposes
  `datasets()`, `query()`, `sources()`, `routes()` and `fetch()` under
  `obb.financial_evidence`. See the [setup guide](integrations/openbb/README.md).
- **DuckDB:** run
  [`integrations/duckdb/financial_evidence.sql`](integrations/duckdb/financial_evidence.sql)
  to create separate HTTP-backed views for all four products.
- **Excel / Power Query:** paste
  [`integrations/excel/FinancialEvidence.pq`](integrations/excel/FinancialEvidence.pq)
  into Advanced Editor and invoke, for example,
  `FinancialEvidence("money-market")`.
  For flat research rows, use [FinancialEvidenceRows](docs/tools/FinancialEvidenceRows.pq)
  from the [research kit](https://beepboop2025.github.io/financial-evidence-skills/tools/).
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

## Quant and research agents

[Native framework tools and cited quant datasets](https://beepboop2025.github.io/financial-evidence-skills/agents/) connect Seiche, LiquiLens and Undertow. Source-pinned agent release 1.0.0 adds compact queries, a three-product review and repeat-call revisions. Use the [current source guide](https://github.com/beepboop2025/financial-evidence-skills/tree/trading-readiness-v1.0.0/integrations/agents) and [connection readiness check](https://beepboop2025.github.io/financial-evidence-skills/agents/readiness.md). These are integration recipes, not evidence of external adoption.

The [agent infrastructure source release](https://beepboop2025.github.io/financial-evidence-skills/agents/low-latency.md)
adds persistent sessions, compact source-status streams, client-side expiry
checks, latency diagnostics and a synthetic feed-recovery pilot. Source
permissions and private outcome consent remain separate from connection access.

## AI execution integration

[Try the browser order-lifecycle simulator](https://beepboop2025.github.io/financial-evidence-skills/agents/execution.html) with synthetic prices, timeout recovery, STOP and an exportable journal. It contacts no broker.

The [source-pinned integration guide](docs/agents/execution-setup.md) covers the separate customer-operated paper REST/MCP host and a live-broker connector candidate. These are in the Evidence Carrier repository; the public Financial Evidence research router remains read-only. Broker activation requires eligible evidence, account controls and the customer's credentials. The [14-day scorecard](docs/agents/pilot-scorecard.md) measures useful independent use and repeat tasks without treating tests or downloads as customers.

## Durable research workflows

The [Financial Evidence Runtime](integrations/agent-runtime/README.md)
adds owner-registered workflows, atomic run limits, offline replay, ordered change
events and backup recovery through Python, CLI and private stdio MCP. It reuses
the existing product clients and preserves source clocks and missingness. See
the [architecture](docs/infrastructure/ARCHITECTURE.md) and
[adoption measurements](docs/infrastructure/ADOPTION.md). Version 0.1.11 includes
the runtime, workspace, trading-research and learning commands. Research data
requests use the central service by default. Local run counts do not establish
external users or paid adoption.
