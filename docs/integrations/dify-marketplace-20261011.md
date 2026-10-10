# Dify Marketplace candidate 0.1.1 — 2026-10-11

The Financial Evidence plugin candidate now uses `dify-plugin==0.10.2`, adds
the required public source repository and contact metadata, declares its sole
outbound domain, and documents setup, connection requirements and a native
workflow. It remains an **unpublished candidate** until native acceptance and
the publisher's required submission attestations are complete.

This replaces the unpublished 0.1.0 candidate for future Dify submissions. It
does not change the fixed Seiche endpoint, supported datasets, bounded inputs
or evidence output contract. Existing 0.1.0 download receipts remain historical
evidence and must not be relabeled as the new package.

## Verified locally

Using Python 3.12.12, five unit tests passed, including partial-page preservation,
invalid-input rejection before network access, HTTP/contract failures, the SDK
JSON message and rejection of private or modified archive files. Actual
`PluginRegistration(DifyPluginEnv())` loaded the manifest and provider with SDK
0.10.2.

Official Dify CLI 0.6.11 built the archive. Its Darwin ARM64 executable was
verified against SHA-256
`9f302d7bcad0d9efb6e1b3b620e7f3f309ea26c206c062f5ae569621ae53f654`.
The source verifier checked all ten packaged files byte-for-byte and rejected
any other entry. Initial 0.1.1 candidate SHA-256:
`35cc08c3c26deb0c03bd3fd09336ef13e309e2dd16f9e704c787909d92e27002`.
Rebuild and record a new hash after any packaged-source change.

The [official Marketplace toolkit](https://github.com/langgenius/dify-marketplace-toolkit)
at revision `57a21d1304b1108df3e6b90a15a4f5dd9f0915f9` returned **zero blocking
failures and zero check-execution failures**, with its online OSV check enabled.
It reported no known vulnerabilities for the two directly pinned requirements;
this does not constitute a full transitive-dependency audit. The prepared PR
body was supplied for the sensitive-capability disclosure check.

Five warning categories are retained for review:

- No minimum Dify version is claimed before native compatibility testing.
- The financial-activity scanner matches the README and tool description's
  denials of transaction/trading capability. The tool only performs an HTTPS GET.
- The domain scanner identifies `api.seiche.info` and also warns that the
  `httpx.get(URL, ...)` call uses a variable. `URL` is a fixed module constant,
  not a user input; redirects are disabled and the domain is declared.
- The dependency category contains informational OSV results.
- The capability scanner flags the HTTP request for manual disclosure review.
  The PR body explains the fixed destination and the transmitted entity filter.

These checks do not install the plugin in Dify, execute a native workflow,
verify Marketplace duplicate versions, or approve the publisher agreement.

## Native acceptance and submission

Use a Dify Cloud workspace with administrator-enabled plugin debugging. Keep
the workspace's displayed host and private key outside the repository and all
packages. Run the source with `INSTALL_METHOD=remote`, `REMOTE_INSTALL_URL` and
`REMOTE_INSTALL_KEY`, then `.venv/bin/python -m main` from `integrations/dify`.
In a draft Workflow connect **User Input → Get Evidence Page → Output** and
route the JSON output directly. No model provider is needed. Run `bank_risk`,
`money_markets` and `market_liquidity`, each with limit 1, offset 0 and blank
entity. Retain run IDs, output JSON, source dates and diagnostics. A successful
debug connection by itself does not complete native acceptance.

Self-hosting was assessed but not started: this Mac has 16 GiB RAM, active
UTM/QEMU services and approximately 9.6 GiB swap used. Docker/Colima is stopped.
The current official Mac instructions require an 8 GiB Docker VM, and the
default stack contains roughly fifteen services. Cloud debugging avoids that
additional local resource demand.

The [current submission route](https://docs.dify.ai/en/develop-plugin/publishing/marketplace-listing/submit-plugin-to-marketplace)
is a pull request to `langgenius/dify-plugins` containing one package at
`beepboop2025/financial_evidence/financial_evidence-0.1.1.difypkg`. Creator Center
manages published plugins; it is not the initial upload route. Prepare the
current upstream PR template, disclose the entity filter sent to Seiche as
Medium risk, attach validation/native evidence, and verify the publisher's
Developer Agreement compliance before submission. The native and agreement
checkboxes remain unchecked in the local draft until their evidence exists.

## Retained evidence

Local evidence root:
`/Users/mrinal/SSDWorkspace/artifacts/dify-marketplace-compliance-20261011/`.

It contains the package, exact-file receipt, unit-test and registration output,
official-validator output and summary, pinned toolkit checkout, and the
unsubmitted upstream PR body. These receipts establish local checks only;
Marketplace acceptance and traction remain unverified.
