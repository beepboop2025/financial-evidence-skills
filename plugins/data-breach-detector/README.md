# Data Breach Detector plugin

Check whether an organization is named in public breach or ransomware
disclosures. Results are disclosure metadata, never breach contents, and a
leak-site listing is a claim rather than a confirmed breach.

This Claude Code plugin is version 1.0.0; the hosted server has its own release
version. It connects to `https://breach.seiche.info/mcp`, the remote in the
official MCP Registry entry `io.github.beepboop2025/data-breach-detector`,
without an API key.

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install data-breach-detector@liquidity-lab
```

Packaged on 3 November 2026 and not yet installed from the public marketplace.
For Claude Desktop and claude.ai, add the same URL as a custom connector; see the
[Claude connection guide](https://github.com/beepboop2025/financial-evidence-skills/blob/main/docs/platforms/claude-connectors.md).
The catalog is publisher maintained. Inclusion is not Claude directory approval.
