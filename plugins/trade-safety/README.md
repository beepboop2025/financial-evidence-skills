# LiquiLens Trade Safety plugin

Inspect Trade Safety's fixed public sources, sandbox authority and documented limits before preparing assessment inputs. Assessments require explicit request and policy objects. Sandbox receipts do not authorize recommendations, broker previews, routing, resizing, custody, settlement or execution.

This independent plugin package is version 1.0.2; the hosted product has its
own release version. It connects to `https://agents.seiche.info/products/trade-safety/mcp` without a product API key.
Your assistant may require its own account or plan. See the [installation guide](https://beepboop2025.github.io/financial-evidence-skills/plugins/).

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install trade-safety@liquidity-lab
```

```sh
codex plugin marketplace add beepboop2025/financial-evidence-skills --ref main
codex plugin add trade-safety@liquidity-lab
```

GitHub Copilot CLI also recognizes the Claude-compatible catalog:

```sh
copilot plugin marketplace add beepboop2025/financial-evidence-skills
copilot plugin install trade-safety@liquidity-lab
```

Gemini CLI: download and extract `trade-safety-gemini-1.0.2.zip`, then run
`gemini extensions install ./extracted-directory`. Inspect the included server
and tool list before enabling it. Native Gemini installation is not yet verified.

The catalogs are publisher-maintained. Inclusion is not OpenAI, Claude, Google,
Cursor or Microsoft directory approval. [Privacy](https://agents.seiche.info/privacy).
