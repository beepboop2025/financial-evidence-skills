# Native n8n and Dify distribution

These integrations serve one bounded public research page per invocation. They
retain the original page, including sources, diagnostics, missing values and
pagination. The native smoke covers LiquiLens bank-risk evidence, Seiche money
markets and Undertow market liquidity. It does not schedule collection, send
notifications or execute trades.

## What is executable

| Route | Artifact and check | External acceptance still required |
| --- | --- | --- |
| n8n | `integrations/n8n-node`; build/lint/SDK tests; `scripts/native_smoke.py` executes the npm tarball in an isolated real n8n 2.42.6 CLI | npm publication under the publisher account, then Creator Portal review |
| Dify | `integrations/dify`; SDK tests, actual manifest registration, official CLI 0.6.11 packaging, exact archive-file verification | Native Dify remote-debug workflow and Marketplace publisher submission |

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

The official Darwin ARM64 Dify CLI download matched release digest
`9f302d7bcad0d9efb6e1b3b620e7f3f309ea26c206c062f5ae569621ae53f654`.
It successfully packaged the plugin, and the archive check accepted exactly
the ten intended files. Evidence is retained under
`SSDWorkspace/artifacts/finance-platform-execution-20261011/native-automation/`.
Final archive hashes are in `dify-package-receipt.json`.

The five Dify tests passed, and actual manifest/provider registration exited
successfully. The SDK emitted an ignored gevent/greenlet finalization warning
during interpreter shutdown; those logs are retained. This does not prove
remote-debug execution. Local npm installation and compilation encountered
macOS uninterruptible I/O waits and remain pending at preparation time. The
clean-runner workflow is the reproducible completion path; consult its
exact-commit result and native receipt before promoting that status.

## Primary references

- [n8n server CLI](https://docs.n8n.io/hosting/cli-commands/)
- [n8n node development CLI](https://docs.n8n.io/connect/create-nodes/build-your-node/using-the-n8n-node-tool)
- [n8n community submission](https://docs.n8n.io/integrations/creating-nodes/deploy/submit-community-nodes/)
- [npm trusted publishing](https://docs.npmjs.com/trusted-publishers/)
- [Dify plugin CLI](https://docs.dify.ai/en/develop-plugin/getting-started/cli)
- [Dify CLI 0.6.11 release](https://github.com/langgenius/dify-plugin-daemon/releases/tag/0.6.11)
- [Dify plugin development standards](https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct)
