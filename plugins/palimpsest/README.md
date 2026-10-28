# Palimpsest plugin

Inspect public-record research signals, China and regional evidence catalogs, and sourced newsroom context. Palimpsest helps analysts trace provenance, revisions and access restrictions before using evidence. Restricted economic collections remain metadata only; the plugin does not reconstruct denied observations or present research signals as verified financial conclusions.

This independent plugin package is version 1.0.2; the hosted product has its
own release version. It connects to `https://agents.seiche.info/products/palimpsest/mcp` without a product API key.
Your assistant may require its own account or plan. See the [installation guide](https://beepboop2025.github.io/financial-evidence-skills/plugins/).

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install palimpsest@liquidity-lab
```

```sh
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref main
codex plugin add palimpsest@liquidity-lab
```

GitHub Copilot CLI also recognizes the Claude-compatible catalog:

```sh
copilot plugin marketplace add beepboop2025/financial-evidence-skills
copilot plugin install palimpsest@liquidity-lab
```

Gemini CLI: download and extract `palimpsest-gemini-1.0.2.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google,
Cursor or Microsoft directory approval. [Privacy](https://agents.seiche.info/privacy).
