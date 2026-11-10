# LiquiLens plugin

Research India's banks and lenders from their own public filings, with every figure's source document and date. LiquiLens reviews 58 banks, among them small finance, urban co-operative, payments and local area banks, and 29 non-bank lenders (NBFCs, housing finance and microfinance lenders) identified by their exact entry in RBI's register. Every served figure was read twice by independent readers. A bank review shows asset quality, capital and liquidity with filing dates, RBI's recorded enforcement actions on that bank since April 2021, and where its core ratios sit among reporting peers of the same type in the same period. You can also read RBI's supervisory tape, the district lending geography of co-operative banks, and the state and district central co-operative banks of the NAFSCOB census.

LiquiLens is research, not a rating, a credit decision or a compliance certificate. It keeps missing, stale and non-comparable evidence visible instead of filling gaps, and it does not access private accounts.

This independent plugin package is version 1.0.3; the hosted product has its
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

Gemini CLI: download and extract `liquilens-gemini-1.0.3.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google,
Cursor or Microsoft directory approval. [Privacy](https://agents.seiche.info/privacy).
