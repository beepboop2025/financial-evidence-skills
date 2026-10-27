# Install and evaluate the native automation packages

## Current hosted clients

Use these versions for the central service at
`https://agents.seiche.info/v1/research`. The exact downloaded bytes passed
the checks in [current package receipts](hosted-native-packages.json).
n8n 0.1.1 is published on npm. Dify 0.1.2 passed installed-package tests in Cloud
and is submitted for marketplace review; the approved Dify listing remains 0.1.1.

### n8n hosted 0.1.1

[Download n8n 0.1.1](downloads/n8n-nodes-financial-evidence-0.1.1.tgz).
Install from [npm](https://www.npmjs.com/package/n8n-nodes-financial-evidence/v/0.1.1)
or use this exact archive. Public bytes, anonymous installation, cryptographic
provenance and native execution passed the
[publication checks](n8n-publication-20261013.json).
The archive loaded in native n8n 2.42.6 on Node 24.12.0 and returned one bounded
bank, funding and liquidity page. Build, lint, unit tests and archive source
checks passed. Tests used synthetic labels and removed their temporary database.

For a permitted self-hosted instance, install the package from its
community-node directory, then restart n8n:

```sh
npm install n8n-nodes-financial-evidence@0.1.1
```

Use Node 24 or another version supported by your installed n8n release.
The existing Creator application is for 0.1.0 and is under manual review after
its demo video was submitted on 15 October. [Current review receipt](n8n-creator-submission-20261015.json).
n8n Creator verification remains pending; npm publication does not establish
n8n Cloud availability. Add **Financial Evidence**, select `money_markets`, set
limit `1` and offset `0`, then run once and inspect the sources and diagnostics.
The public research API requires no financial-data API key.

### Dify hosted 0.1.2

[Download Dify 0.1.2](downloads/financial_evidence-0.1.2.difypkg).
The exact 7,477-byte archive (SHA-256
`350d20409d9a3287d0ddc1b939d2cbb5f577ca632f2c20be75a5c7d046f0ba96`)
was installed through Local Package File in a Dify Cloud SANDBOX on
28 October 2026 IST. Three draft workflow cases (`money_markets`, `bank_risk`,
`market_liquidity`) and a repeated liquidity execution passed with limit `1`
and offset `0`; invalid limit `251` was rejected. Outputs retained sources and
diagnostics. The temporary workflow and candidate plugin were removed afterward.
See the [sanitized native proof](../integrations/dify-native-proof-20261028.json).

[Update PR 3534](https://github.com/langgenius/dify-plugins/pull/3534) is submitted
and passed upstream checks; review and marketplace publication are pending.
The [submission receipt](../distribution/dify-submission-20261028.json) records
the exact package and submitted revision. Use the local-package route in a
permitted workspace to evaluate 0.1.2; the approved Marketplace version remains
0.1.1. Outbound policies must permit `agents.seiche.info`; an
`api.seiche.info`-only allowlist is insufficient for 0.1.2.

The repeat used cached provider evidence, not a fresh upstream retrieval.
Money-market data retained a PARTIAL source status, bank data retained
construction-PIT status and unknown rights, and liquidity data retained a
null/unavailable value and failed stress-case limitation. Community Edition
was not executed. Native success does not establish data freshness, financial
validity, redistribution rights, regulatory compliance or customer adoption.

## Previous native releases

The following versioned downloads and observations remain historical.
For new central connections, choose the current hosted clients above.

The n8n package is published on npm; Dify 0.1.1 is approved and publicly listed. Check each package's publication state, file digest and
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
verification passed. The [original Creator Portal submission](n8n-creator-submission-20261011.json)
was received after ownership verification. Its 160.28-second demo video was
uploaded and submitted on 15 October. Automated checks are complete, and a
refreshed portal readback shows Manual Review **Under Review** in the
[current review receipt](n8n-creator-submission-20261015.json). The existing
application remains version 0.1.0; the public npm 0.1.1 release is separate.
n8n verification and official node-directory acceptance remain pending.
Approved For Publish is not complete. This does not establish n8n Cloud
availability or independent-user adoption.

The immutable 0.1.0 package README preserves its prepublication wording, including
the former "not yet published" statement and older release-workflow description.
The current npm publication receipt above supersedes those status statements;
the separate Creator receipts retain the original submission and later manual-review status.
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

[Marketplace PR 3278](https://github.com/langgenius/dify-plugins/pull/3278) was
approved and merged on 11 October. The [public Marketplace listing](https://marketplace.dify.ai/plugin/beepboop2025/financial_evidence)
was verified on 15 October: version 0.1.1, Verified by Dify, with an install link.
This historical proof does not establish installed-archive execution of 0.1.1.
The separate central-hosted 0.1.2 has its own Cloud acceptance and pending
marketplace update [above](#dify-hosted-012).
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
