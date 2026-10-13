# Install and evaluate the native automation packages

## Current hosted clients

Use these versions for the central service at
`https://agents.seiche.info/v1/research`. The exact downloaded bytes passed
the checks in [current package receipts](hosted-native-packages.json).
These are qualified downloads; the new versions are not yet published to npm
or Dify Marketplace.

### n8n hosted 0.1.1

[Download n8n 0.1.1](downloads/n8n-nodes-financial-evidence-0.1.1.tgz).
The archive loaded in native n8n 2.42.6 on Node 24.12.0 and returned one bounded
bank, funding and liquidity page. Build, lint, unit tests and archive source
checks passed. Tests used synthetic labels and removed their temporary database.

For a permitted self-hosted instance, install the downloaded archive from its
community-node directory, then restart n8n:

```sh
npm install /absolute/path/to/n8n-nodes-financial-evidence-0.1.1.tgz
```

Use Node 24 or another version supported by your installed n8n release.
The new candidate has not been published to npm or verified by n8n.

### Dify hosted 0.1.2

[Download Dify 0.1.2](downloads/financial_evidence-0.1.2.difypkg).
The official CLI built the archive. Packaged files matched reviewed source,
Dify SDK 0.10.2 registered the plugin, and its actual packaged tools completed
three central requests. This qualification did not install the archive in a
Dify Cloud or Community Edition workspace. Evaluate it through the supported
local-plugin flow in your permitted workspace and run Get Evidence Page once.
No new marketplace submission or acceptance is claimed.

## Previous native releases

The following versioned downloads and observations remain historical.
For new central connections, choose the current hosted candidates above.

The n8n package is published on npm; the Dify package remains a marketplace
submission candidate. Check each package's publication state, file digest and
validation scope in [package receipts](native-packages.json).

## n8n

**n8n-nodes-financial-evidence 0.1.0 is published on npm.**
[npm package](https://www.npmjs.com/package/n8n-nodes-financial-evidence) ·
[Publication and provenance receipt](n8n-publication-20261011.json) ·
[Exact tested archive](downloads/n8n-nodes-financial-evidence-0.1.0.tgz).

This unverified community package is currently for **self-hosted n8n only**;
unverified community nodes are unavailable on n8n Cloud.
[Official availability rules](https://docs.n8n.io/integrations/community-nodes/installation-and-management/).

An owner or administrator can open **Settings → Community Nodes → Install** and
enter `n8n-nodes-financial-evidence@0.1.0` in a permitted self-hosted development
instance. [Official GUI procedure](https://docs.n8n.io/integrations/community-nodes/installation-and-management/gui-installation/).

If the instance requires manual installation, follow the
[official command-line procedure](https://docs.n8n.io/integrations/community-nodes/installation-and-management/manual-installation/).
From its community-node directory (`~/.n8n/nodes`), install the specific version,
then restart n8n:

```sh
npm install n8n-nodes-financial-evidence@0.1.0
```

Add **Financial Evidence**, choose `money_markets`, set limit `1` and offset `0`,
then run once and inspect the complete response. The public research API needs
no financial-data API key. Keep the workflow inactive until its first result is
reviewed. If your workspace cannot load unverified community packages, use the
[importable research workflows](https://beepboop2025.github.io/financial-evidence-skills/automations/) with ordinary HTTP nodes.

The public tarball matches the native-tested archive exactly. Native n8n 2.42.6
executed one bounded bank, funding and liquidity request. Cryptographic Sigstore
provenance verification, anonymous consumer installation and npm signature
verification passed. The [Creator Portal submission was received](n8n-creator-submission-20261011.json)
after ownership verification. Automated checks passed; manual review is
**awaiting a demo video**. n8n verification and official node-directory acceptance
remain pending. The Approved For Publish step is not complete. This does not
establish n8n Cloud availability or independent-user adoption.

The immutable 0.1.0 package README preserves its prepublication wording, including
the former "not yet published" statement and older release-workflow description.
The current npm publication receipt above supersedes those status statements;
the separate Creator receipt records the later portal submission.
The archive's bytes are unchanged. The recorded native validation is also a
historical test; its earlier `npm_published: false` field is not the current
registry state.

## Dify

[Download Financial Evidence 0.1.1](downloads/financial_evidence-0.1.1.difypkg).

The official Dify CLI produced this archive. SDK tests, manifest registration
and exact source-file checks passed. Three bounded draft workflows passed in
Dify Cloud for `money_markets`, `bank_risk` and `market_liquidity`. The final
archive has the same executable files, dependencies and manifest; only
`PRIVACY.md` changed after remote-debug registration. The separate archive
receipt checks its files; it does not prove installed-archive execution.

[Native Cloud proof](https://beepboop2025.github.io/financial-evidence-skills/integrations/dify-native-proof-20261011.json)
records the tested runtime identity. Community Edition and a published Dify app
were not tested. The liquidity result retained a null/unavailable observation;
a successful workflow is not evidence that every source value is available.

[Marketplace PR 3278](https://github.com/langgenius/dify-plugins/pull/3278) is
submitted and awaiting review; the plugin is not yet published in Marketplace.
The [prior 0.1.0 receipt](https://github.com/beepboop2025/financial-evidence-skills/blob/c767edbf58e173b60b085cf637880b5bd9d4bb52/docs/platforms/native-packages.json)
is historical and must not be relabeled as this 0.1.1 package.

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
