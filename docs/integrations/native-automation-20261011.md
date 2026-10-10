# Native n8n and Dify distribution

These integrations serve one bounded public research page per invocation. They
retain the original page, including sources, diagnostics, missing values and
pagination. The native smoke covers LiquiLens bank-risk evidence, Seiche money
markets and Undertow market liquidity. It does not schedule collection, send
notifications or execute trades.

## What is executable

| Route | Artifact and check | External acceptance still required |
| --- | --- | --- |
| n8n | Passed build, lint, four SDK tests and execution of the exact npm tarball through the custom-extension loader in an isolated real n8n 2.42.6 CLI | npm publication under the publisher account, then Creator Portal review |
| Dify | Passed five SDK/package tests, actual manifest registration, official CLI 0.6.11 packaging and exact archive-file verification | Native Dify remote-debug workflow and Marketplace publisher submission |

`native-marketplace-build.yml` runs both lanes on a clean GitHub runner and
retains installable artifacts with receipts. Its n8n test makes exactly three
bounded read-only requests to the public API, one per research product. It
requires source/network availability and fails when execution or the response
contract fails. An empty or partial research page retains its diagnostics.
The test is synthetic integration evidence and does not demonstrate adoption.

The Dify package verifier accepts only ten named plugin files and compares each
against the checkout. Debug keys, `.env.*`, tests, helper scripts and virtual
environments are excluded. A successful package check does not claim that a
Dify account has executed the plugin.

## Publication procedure

1. Inspect the **Native marketplace packages** run for the exact reviewed
   commit. A local attempt or a queued GitHub run is not a passing native test.
2. Set up the npm package publisher identity and trusted publisher for
   `beepboop2025/financial-evidence-skills`, workflow
   `native-marketplace-npm-publish.yml`. Initial npm package/account setup is a
   separate owner-controlled step. As observed on 11 October 2026, the public
   package lookup returned E404 and the current local `npm whoami` returned
   E401; neither publication nor authenticated ownership was established.
3. Run **Publish native n8n package** on main with the full reviewed SHA and
   `0.1.0`. The default is a dry run. The actual publish switch reruns the
   native checks, publishes the tested tarball with provenance, and reads back
   both registry metadata and public tarball bytes. It does not create a tag,
   increment the version or submit the n8n Creator Portal form.
4. For Dify, use the account's Plugin Manager debug host/key privately and run
   `python -m main`. Execute **Get Evidence Page** in a native workflow and
   retain the successful run. Submit the exact checked `.difypkg` through the
   publisher account only after that run passes. The local preparation has no
   remote-debug credential and cannot attest to that step.

## Local evidence from this execution

Both jobs in [native CI run 38080327701](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/38080327701)
passed. The PR head was `b2d7ee3ea9a86e3479e77702f4b9354fb16a94c0`; GitHub
checked out and tested PR merge revision
`f5f90eaf0a374e0cbbc17747d0dc4801e53ab111`. The retained manifest distinguishes
these identities. All seven n8n package files match the corresponding local
built/source bytes, and all ten Dify package files match the source bytes.

The native n8n receipt, observed at `2026-10-10T19:36:56Z`, contains:

| Dataset | Rows | Sources | Diagnostics | Next offset | Transport status |
| --- | ---: | ---: | ---: | ---: | --- |
| `bank_risk` | 1 | 1 | 0 | 1 | `complete` |
| `money_markets` | 1 | 1 | 0 | 1 | `complete` |
| `market_liquidity` | 1 | 1 | 0 | 1 | `complete` |

This proves that the packaged node loads and makes bounded native requests
while preserving the expected response envelope. The native check accepts
partial or empty pages when the envelope is valid; it does not validate source
freshness, evidence validity, rights or financial fitness. It also does not
demonstrate the user-interface installation flow or independent adoption.

The exact retained files are `n8n-nodes-financial-evidence-0.1.0.tgz`
(4,445 bytes, SHA-256 `9d2fa6ba3950c41a68e025ea6f5c57922697c0b311ef6d77ce52412267b392ae`)
and `financial_evidence.difypkg`
(5,583 bytes, SHA-256 `e9447fc08ec13d428aad4acc20be80c00aab11901818a81dd57907363ca7a68c`).
They remain downloadable candidates, not accepted marketplace listings.

The official Darwin ARM64 Dify CLI download matched release digest
`9f302d7bcad0d9efb6e1b3b620e7f3f309ea26c206c062f5ae569621ae53f654`.
It successfully packaged the plugin, and the archive check accepted exactly
the ten intended files. Evidence is retained under
`SSDWorkspace/artifacts/finance-platform-execution-20261011/native-automation/`.
Final archive hashes are in `dify-package-receipt.json`.

The five Dify tests passed locally, and actual manifest/provider registration
exited successfully. The SDK also fetched one live page for each of the three
datasets above. It emitted an ignored gevent/greenlet finalization warning at
interpreter shutdown; those logs are retained. This does not prove remote-debug
execution. Local n8n build, lint and four SDK tests passed; its redundant full
host installation was stopped during macOS I/O waits after clean-runner testing
was available. Native host proof comes from the successful CI run above.

Complete final CI artifacts, package hashes, run metadata, source-byte checks
and installation notes are retained in the evidence directory's
`final-ci-packages/` subdirectory. Earlier failed receipts remain available:
the first harness hid n8n's raw JSON by using error-only logging. The fixed
run preserves information-level output and verifies the execution result.

## Primary references

- [n8n server CLI](https://docs.n8n.io/hosting/cli-commands/)
- [n8n node development CLI](https://docs.n8n.io/connect/create-nodes/build-your-node/using-the-n8n-node-tool)
- [n8n community submission](https://docs.n8n.io/integrations/creating-nodes/deploy/submit-community-nodes/)
- [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/)
- [Dify plugin CLI](https://docs.dify.ai/en/develop-plugin/getting-started/cli)
- [Dify CLI 0.6.11 release](https://github.com/langgenius/dify-plugin-daemon/releases/tag/0.6.11)
- [Dify plugin development standards](https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct)
