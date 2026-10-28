# Seiche Market Atlas Corpus plugin

Explore registered market corpora, versioned datasets, normalized Seiche coverage and permitted bounded observations. Inspect rights, product eligibility and source-adapter partitions before reading values. Restricted data remains restricted; catalog presence or service health does not prove redistribution permission or freshness.

This independent plugin package is version 1.0.1; the hosted product has its
own release version. It connects to `https://agents.seiche.info/products/seiche-market-corpus/mcp` without a product API key.
Your assistant may require its own account or plan. See the [installation guide](https://beepboop2025.github.io/financial-evidence-skills/plugins/).

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install seiche-market-corpus@liquidity-lab
```

```sh
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref main
codex plugin add seiche-market-corpus@liquidity-lab
```

GitHub Copilot CLI also recognizes the Claude-compatible catalog:

```sh
copilot plugin marketplace add beepboop2025/financial-evidence-skills
copilot plugin install seiche-market-corpus@liquidity-lab
```

Gemini CLI: download and extract `seiche-market-corpus-gemini-1.0.1.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google,
Cursor or Microsoft directory approval. [Privacy](https://agents.seiche.info/privacy).
