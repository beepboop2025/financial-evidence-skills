# LiquiLens plugin

Research India's banks and lenders from their own public filings, with every figure's source document and date. LiquiLens reviews 58 banks, among them small finance, urban co-operative, payments and local area banks, and 29 non-bank lenders (NBFCs, housing finance and microfinance lenders) identified by their exact entry in RBI's register. Every served figure was read twice by independent readers. A bank review shows asset quality, capital and liquidity with filing dates, RBI's recorded enforcement actions on that bank since April 2021, and where its core ratios sit among reporting peers of the same type in the same period. You can also read RBI's supervisory tape, the district lending geography of co-operative banks, and the state and district central co-operative banks of the NAFSCOB census.

LiquiLens is research, not a rating, a credit decision or a compliance certificate. It keeps missing, stale and non-comparable evidence visible instead of filling gaps, and it does not access private accounts.

This independent plugin package is version 1.0.4; the hosted product has its
own release version. It connects without a product API key:

- to the MCP Registry URL `https://api.liquilens.in/mcp` from its Agent Plugins
  manifest (`plugin.json` with `mcp.json`, which Codex CLI and Kiro read), its
  Antigravity manifest and its Devin package;
- to the documented alias `https://agents.seiche.info/products/liquilens/mcp`
  from its Claude-compatible files (`.claude-plugin/plugin.json` with `.mcp.json`,
  which Claude Code and Copilot CLI 1.0.68 read), the prepared OpenAI upload and
  the Gemini extension.

Your assistant may require its own account or plan. See the [installation guide](https://beepboop2025.github.io/financial-evidence-skills/plugins/).

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install liquilens@liquidity-lab
```

```sh
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref main
codex plugin add liquilens@liquidity-lab
```

GitHub Copilot CLI also recognizes the Claude-compatible catalog:

```sh
copilot plugin marketplace add beepboop2025/financial-evidence-skills
copilot plugin install liquilens@liquidity-lab
```

Gemini CLI: download and extract `liquilens-gemini-1.0.4.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

## Agent Plugins, Antigravity, Kiro and Devin

The repository folder [`plugins/liquilens`](https://github.com/beepboop2025/financial-evidence-skills/tree/main/plugins/liquilens)
carries an Agent Plugins 1.0.0 manifest (`plugin.json` with `mcp.json`) and a
Google Antigravity manifest (`.antigravity-plugin/plugin.json` with
`mcp_config.json`). Both connect to `https://api.liquilens.in/mcp`.
GitHub's plugin reference says Copilot CLI releases that read Agent Plugins
manifests take `plugin.json` and `mcp.json` over the Claude-compatible files.

Kiro installs the folder as a power: open the powers panel, choose Add Custom
Power, then Import power from a repository URL, and enter
`https://github.com/beepboop2025/financial-evidence-skills/tree/main/plugins/liquilens`.

Antigravity installs it from a clone of this repository:

```sh
agy plugin install ./plugins/liquilens
```

The Devin package is in [`integrations/devin/liquilens`](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/devin/liquilens).
Listing in the Antigravity, Kiro or Devin marketplaces is a separate review;
none is claimed here.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google, Cursor, Microsoft, Kiro or Devin directory approval. [Privacy](https://agents.seiche.info/privacy).
