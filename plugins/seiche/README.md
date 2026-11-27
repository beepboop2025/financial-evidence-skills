# Seiche plugin

Research public money markets, regional funding context, GIFT City and gold carry using verified direct-source tools. Inspect source rights, observation dates, coverage and unavailable evidence before using a result. This release explicitly withholds legacy forecasts, backtests and other derived views whose reuse rights are unconfirmed. Seiche supports research; it does not execute trades, approve investments or certify compliance.

This independent plugin package is version 1.0.4; the hosted product has its
own release version. It connects without a product API key:

- to the MCP Registry URL `https://api.seiche.info/mcp` from its Agent Plugins
  manifest (`plugin.json` with `mcp.json`, which Codex CLI and Kiro read), its
  Antigravity manifest and its Devin package;
- to the documented alias `https://agents.seiche.info/products/seiche/mcp`
  from its Claude-compatible files (`.claude-plugin/plugin.json` with `.mcp.json`,
  which Claude Code and Copilot CLI 1.0.68 read), the prepared OpenAI upload and
  the Gemini extension.

Your assistant may require its own account or plan. See the [installation guide](https://beepboop2025.github.io/financial-evidence-skills/plugins/).

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install seiche@liquidity-lab
```

```sh
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref main
codex plugin add seiche@liquidity-lab
```

GitHub Copilot CLI also recognizes the Claude-compatible catalog:

```sh
copilot plugin marketplace add beepboop2025/financial-evidence-skills
copilot plugin install seiche@liquidity-lab
```

Gemini CLI: download and extract `seiche-gemini-1.0.4.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

## Agent Plugins, Antigravity, Kiro and Devin

The repository folder [`plugins/seiche`](https://github.com/beepboop2025/financial-evidence-skills/tree/main/plugins/seiche)
carries an Agent Plugins 1.0.0 manifest (`plugin.json` with `mcp.json`) and a
Google Antigravity manifest (`.antigravity-plugin/plugin.json` with
`mcp_config.json`). Both connect to `https://api.seiche.info/mcp`.
GitHub's plugin reference says Copilot CLI releases that read Agent Plugins
manifests take `plugin.json` and `mcp.json` over the Claude-compatible files.

Kiro installs the folder as a power: open the powers panel, choose Add Custom
Power, then Import power from a repository URL, and enter
`https://github.com/beepboop2025/financial-evidence-skills/tree/main/plugins/seiche`.

Antigravity installs it from a clone of this repository:

```sh
agy plugin install ./plugins/seiche
```

The Devin package is in [`integrations/devin/seiche`](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/devin/seiche).
Listing in the Antigravity, Kiro or Devin marketplaces is a separate review;
none is claimed here.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google, Cursor, Microsoft, Kiro or Devin directory approval. [Privacy](https://agents.seiche.info/privacy).
