# Evaluate the native automation packages

These downloads are candidate packages for a development workspace. They are
separate from marketplace publication. Check the file digest and the validation
scope in [package receipts](native-packages.json).

## n8n

[Download n8n-nodes-financial-evidence 0.1.0](downloads/n8n-nodes-financial-evidence-0.1.0.tgz).

The package contains the built Financial Evidence node. Its native check loads
the exact npm tarball into an isolated n8n 2.42.6 CLI and executes one bounded
bank, funding and liquidity request. npm publication and n8n verification are
still pending.

Use the [source setup and native test procedure](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/n8n-node)
to evaluate it in a separate self-hosted development instance. Your administrator
must decide whether an unpublished community package may be loaded. The
[official manual-installation guide](https://docs.n8n.io/integrations/community-nodes/installation-and-management/manual-installation/)
describes the community-node installation location and restart requirements.

If your workspace cannot load unpublished packages, use the existing
[importable research workflows](https://beepboop2025.github.io/financial-evidence-skills/automations/) with ordinary HTTP nodes.
Keep a workflow inactive until its first result is reviewed.

## Dify

[Download Financial Evidence 0.1.0](downloads/financial_evidence-0.1.0.difypkg).

The official Dify CLI produced this archive. SDK tests, manifest registration
and exact source-file checks passed. Native Dify remote-debug execution and
marketplace review remain outstanding.

Evaluate the archive through your workspace's supported local-plugin or
development flow. Ask the workspace administrator for permitted install/debug
access; keep debug credentials private. Run **Get Evidence Page** for
`money_markets` with a small limit and retain the JSON tool response.
[Plugin source and debug procedure](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/dify)
· [Dify integration management](https://docs.dify.ai/en/cloud/use-dify/workspace/plugins).

## First successful review

Confirm the response retains sources, observation dates, units, availability,
diagnostics and `next_offset`. A successful request is a transport result;
review what the evidence actually covers before using it. These tools need no
financial-data credentials and do not send messages or place orders.

[Return to all platform connections](https://beepboop2025.github.io/financial-evidence-skills/platforms/).
