# Undertow plugin

Check what exiting a position at a given size may cost, and where liquidity has thinned, from public venue data with its timestamps and coverage. Compare indicative BTC exit costs at your size per venue, see realised market-depth collapses, venue concentration and a consensus price when venues disagree, estimate perpetual funding costs, stress a crypto portfolio under price moves you choose, and work through a gold sale, FX and cash-settlement scenario from your own inputs. The liquidity-tier board carries Seiche funding context, and the sealed record of past calls keeps its misses. A PARTIAL reading means the history is not yet sufficient; it is never a calm reading. Results are indicative research, not executable quotes, order placement, investment advice or access to private positions.

This independent plugin package is version 1.0.4; the hosted product has its
own release version. It connects without a product API key:

- to the MCP Registry URL `https://api.seiche.info/undertow/mcp` from its Agent Plugins
  manifest (`plugin.json` with `mcp.json`, which Codex CLI and Kiro read), its
  Antigravity manifest and its Devin package;
- to the documented alias `https://agents.seiche.info/products/undertow/mcp`
  from its Claude-compatible files (`.claude-plugin/plugin.json` with `.mcp.json`,
  which Claude Code and Copilot CLI 1.0.68 read), the prepared OpenAI upload and
  the Gemini extension.

Your assistant may require its own account or plan. See the [installation guide](https://beepboop2025.github.io/financial-evidence-skills/plugins/).

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install undertow@liquidity-lab
```

```sh
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref main
codex plugin add undertow@liquidity-lab
```

GitHub Copilot CLI also recognizes the Claude-compatible catalog:

```sh
copilot plugin marketplace add beepboop2025/financial-evidence-skills
copilot plugin install undertow@liquidity-lab
```

Gemini CLI: download and extract `undertow-gemini-1.0.4.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

## Agent Plugins, Antigravity, Kiro and Devin

The repository folder [`plugins/undertow`](https://github.com/beepboop2025/financial-evidence-skills/tree/main/plugins/undertow)
carries an Agent Plugins 1.0.0 manifest (`plugin.json` with `mcp.json`) and a
Google Antigravity manifest (`.antigravity-plugin/plugin.json` with
`mcp_config.json`). Both connect to `https://api.seiche.info/undertow/mcp`.
GitHub's plugin reference says Copilot CLI releases that read Agent Plugins
manifests take `plugin.json` and `mcp.json` over the Claude-compatible files.

Kiro installs the folder as a power: open the powers panel, choose Add Custom
Power, then Import power from a repository URL, and enter
`https://github.com/beepboop2025/financial-evidence-skills/tree/main/plugins/undertow`.

Antigravity installs it from a clone of this repository:

```sh
agy plugin install ./plugins/undertow
```

The Devin package is in [`integrations/devin/undertow`](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/devin/undertow).
Listing in the Antigravity, Kiro or Devin marketplaces is a separate review;
none is claimed here.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google, Cursor, Microsoft, Kiro or Devin directory approval. [Privacy](https://agents.seiche.info/privacy).
