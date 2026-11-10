# Riptide plugin

Inspect Riptide's committed daily paper allocation, its paper record and crypto paper record, read-only event-market context, defensive coverage and published methodology. Paper results, verification status and evidence dates stay explicit, and observed history stays apart from future expectations. Historical paper results are research records, not live-account performance, investment advice or an instruction to trade. Riptide places no orders and holds no accounts, wallets or keys.

This independent plugin package is version 1.0.3; the hosted product has its
own release version. It connects to `https://agents.seiche.info/products/riptide/mcp` without a product API key.
Your assistant may require its own account or plan. See the [installation guide](https://beepboop2025.github.io/financial-evidence-skills/plugins/).

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install riptide@liquidity-lab
```

```sh
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref main
codex plugin add riptide@liquidity-lab
```

GitHub Copilot CLI also recognizes the Claude-compatible catalog:

```sh
copilot plugin marketplace add beepboop2025/financial-evidence-skills
copilot plugin install riptide@liquidity-lab
```

Gemini CLI: download and extract `riptide-gemini-1.0.3.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google,
Cursor or Microsoft directory approval. [Privacy](https://agents.seiche.info/privacy).
