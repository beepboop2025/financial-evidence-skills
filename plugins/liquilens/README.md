# LiquiLens plugin

Find covered financial institutions, review public asset-quality disclosures, and inspect RBI supervisory evidence with source dates and coverage limits. LiquiLens helps analysts prepare institution review questions while preserving missing or non-comparable evidence. It does not access private accounts, replace professional judgment or certify regulatory compliance.

This independent plugin package is version 1.0.2; the hosted product has its
own release version. It connects to `https://agents.seiche.info/products/liquilens/mcp` without a product API key.
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

Gemini CLI: download and extract `liquilens-gemini-1.0.2.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google,
Cursor or Microsoft directory approval. [Privacy](https://agents.seiche.info/privacy).
