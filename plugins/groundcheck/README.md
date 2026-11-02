# GroundCheck plugin

Check a factual claim against retrieved public sources before relying on it.
GroundCheck returns supported, refuted or unverified with a sufficiency gate,
an error bound and a signed provenance receipt.

This Claude Code plugin is version 1.0.0; the hosted server has its own release
version. It connects to `https://groundcheck.seiche.info/mcp`, the remote in the
official MCP Registry entry `io.github.beepboop2025/groundcheck`, without an API
key. Only `verify_claim` is free. The other tools answer with an x402 payment
offer, and the bundled skill tells Claude never to pay.

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install groundcheck@liquidity-lab
```

Packaged on 3 November 2026 and not yet installed from the public marketplace.
For Claude Desktop and claude.ai, add the same URL as a custom connector; see the
[Claude connection guide](https://github.com/beepboop2025/financial-evidence-skills/blob/main/docs/platforms/claude-connectors.md).
The catalog is publisher maintained. Inclusion is not Claude directory approval.
