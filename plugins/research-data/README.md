# Source Data Research Workspace plugin

Discover scoped research datasets, exact series and regulator identifiers; inspect source-bound changes and retrieve bounded cited observations. Preserve native units, capture receipts, snapshot identifiers, independent source clocks, rights and coverage gaps so an analyst can reproduce a captured review. Historical vintages do not establish earlier point-in-time availability; stale or unverified current analysis may be withheld.

This independent plugin package is version 1.0.1; the hosted product has its
own release version. It connects to `https://agents.seiche.info/products/research-data/mcp` without a product API key.
Your assistant may require its own account or plan. See the [installation guide](https://beepboop2025.github.io/financial-evidence-skills/plugins/).

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install research-data@liquidity-lab
```

```sh
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref main
codex plugin add research-data@liquidity-lab
```

GitHub Copilot CLI also recognizes the Claude-compatible catalog:

```sh
copilot plugin marketplace add beepboop2025/financial-evidence-skills
copilot plugin install research-data@liquidity-lab
```

Gemini CLI: download and extract `research-data-gemini-1.0.1.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google,
Cursor or Microsoft directory approval. [Privacy](https://agents.seiche.info/privacy).
