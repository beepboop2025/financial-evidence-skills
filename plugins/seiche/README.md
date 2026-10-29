# Seiche plugin

Research public money markets, regional funding context, GIFT City and gold carry using verified direct-source tools. Inspect source rights, observation dates, coverage and unavailable evidence before using a result. This release explicitly withholds legacy forecasts, backtests and other derived views whose reuse rights are unconfirmed. Seiche supports research; it does not execute trades, approve investments or certify compliance.

This independent plugin package is version 1.0.3; the hosted product has its
own release version. It connects to `https://agents.seiche.info/products/seiche/mcp` without a product API key.
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

Gemini CLI: download and extract `seiche-gemini-1.0.3.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google,
Cursor or Microsoft directory approval. [Privacy](https://agents.seiche.info/privacy).
