# Distribution gap review — 15 October 2026

Source ledger: [`82893bae2140d51ef1187bcc9d7ab502a78f23a9`](https://github.com/beepboop2025/financial-evidence-skills/blob/82893bae2140d51ef1187bcc9d7ab502a78f23a9/docs/marketplaces.json), SHA-256 `eef2b890baf30d38b0e0ba28c8e7c8bc76ada7c6d05edc10be8efc56ab1590dc`. Its full-ledger check is 2026-10-13T07:00:34.293310Z; its top-level update is 2026-10-15T11:04:14.956103+00:00. Individual entry clocks are retained in the JSON. This review does not change ledger states.

The ledger has **159 total records: 62 live and 97 non-live**. After current read-only checks, the 97 gaps classify as **4 actionable, 82 awaiting a third party, 11 gated or owned elsewhere**. The original ledger-only classification was 1/85/11. Product/channel records are not unique platforms or users.

## Findings for the ledger owner

Three existing submissions now have merged PRs and independently verified public default-branch rows:

| Entry | Existing submission | Public evidence | Proposed state |
|---|---|---|---|
| public-apis-seiche-rest | [Existing PR](https://github.com/public-apis/public-apis/pull/7801) | [Immutable README](https://github.com/public-apis/public-apis/blob/642f0c657cb531c6b23331c5d235ef6a588fefda/README.md) | submitted → live; not applied |
| public-apis-undertow-rest | [Existing PR](https://github.com/public-apis/public-apis/pull/7802) | [Immutable README](https://github.com/public-apis/public-apis/blob/642f0c657cb531c6b23331c5d235ef6a588fefda/README.md) | submitted → live; not applied |
| awesome-osint-narcoscope | [Existing PR](https://github.com/jivoi/awesome-osint/pull/1271) | [Immutable README](https://github.com/jivoi/awesome-osint/blob/6ce2c1b5ba7817da378818e691d0408899e3a924/README.md) | submitted → live; not applied |

Gemini’s full gallery returned 200 with no exact owner/repository/tool markers. Two exact Zenodo API searches returned zero records. Datarade returned 403, so its public state is unavailable rather than absent. AgentNDX’s curated 1,636-entry index has no expected family match; its separate free live index exposes four Groundcheck endpoints imported from Bazaar. Those imported endpoints do not establish acceptance of the six pending MCP submissions. URLs, timestamps, response hashes and scopes are in the [JSON receipt](gap-review-20261015.json).

The 22 distinct GitHub objects cover 23 ledger records. Awesome Quant PR 778 represents two products. The 19 other objects remain open except the already closed-unmerged Awesome Copilot PR; Awesome OpenBB’s repository is still archived. MCPFind is mergeable but behind with a successful fork-safe preflight. Aowang is mergeable with an unstable status, but no actionable failing check was returned; do not invent a repair.

## Independently finishable work

| Work | Concrete next action | Inputs |
|---|---|---|
| Vercel AI SDK — root owns this | Build the missing source-preserving npm tool package, native tests and dedicated docs; separately verify publication and registry acceptance. | [Official route](https://github.com/vercel/ai/blob/main/contributing/add-new-tool-to-registry.md); `integrations/activepieces/src/lib/research.ts`, `docs/agents/low-latency.md` |
| Three verified public rows | Hand the proposed corrections above to the ledger owner. | PR merge receipts and immutable default-branch hashes in JSON |
| Cursor native acceptance | Test the already submitted plugin in an isolated native client; preserve publisher review as pending. | `.cursor-plugin/plugin.json`, `integrations/task-mcp.json`, `task-skills/` |
| Dify installed archive | Test accepted 0.1.1 separately from source candidate 0.1.2. This is an existing live record, outside the 97 gaps. | `docs/platforms/downloads/financial_evidence-0.1.1.difypkg`, `docs/integrations/dify-native-proof-20261011.json` |
| Activepieces optional assurance | Close browser-install and worker-artifact hash gaps in an isolated instance. Existing npm/native qualification is already complete. | `docs/platforms/activepieces-registry-20261015.json`, `integrations/activepieces/scripts/native_smoke.py` |

Terminal 01a13ffa owns PyPI, official MCP Registry, version releases and source ledger changes. Zenodo follows its genuine release lane; do not create a release just to trigger a DOI. No unsolicited Activepieces contribution should be sent while the recorded upstream policy pause remains.

## Recent native receipts

- n8n: `docs/platforms/n8n-creator-submission-20261015.json` records the existing 0.1.0 demo submitted and Manual Review Under Review at 11:54:58 UTC. npm 0.1.1 is separate. Do not submit a second application.
- Dify: `docs/distribution/expansion-20261015.json` and the ledger record the public accepted 0.1.1 listing. The older pending-submission receipt is historical; native installed-archive use is still unverified.
- Activepieces: publication, archive installation and native registry installation have separate 15 October receipts under `docs/platforms/`. Browser interaction and worker filesystem byte attestation remain unverified.
- `docs/distribution/agent-tools-distribution-20261015.json` already records the Laplace/Aowang submissions and existing Kilo description update. Current PR checks remain open.

## Complete gap matrix

Every one of the 97 source-ledger non-live IDs appears exactly once below. “Current” identifies new read-only evidence; “Ledger” means no fresh external check. The JSON retains original details, exact source clocks, evidence URLs, classification reasons and proposed corrections.

### Actionable — 4

| Ledger record | Recorded state | Evidence | Next action |
|---|---|---|---|
| [public-apis-seiche-rest](https://github.com/public-apis/public-apis/pull/7801) | submitted | Current + ledger | Ledger owner may reconcile submitted to live using the retained PR merge and default-branch row receipt. No new submission, runtime test or adoption claim is needed. |
| [public-apis-undertow-rest](https://github.com/public-apis/public-apis/pull/7802) | submitted | Current + ledger | Ledger owner may reconcile submitted to live using the retained PR merge and default-branch row receipt. No new submission, runtime test or adoption claim is needed. |
| [awesome-osint-narcoscope](https://github.com/jivoi/awesome-osint/pull/1271) | submitted | Current + ledger | Ledger owner may reconcile submitted to live using the retained PR merge and default-branch row receipt. No new submission, runtime test or adoption claim is needed. |
| [vercel-ai-sdk-tools](https://github.com/vercel/ai/blob/main/contributing/add-new-tool-to-registry.md) | conditional_artifact | Ledger | Root owns implementation of a source-preserving AI SDK npm tool package, native tests and dedicated docs. Verify the current official contribution requirements before publication; a registry contribution is a later ex… |

### Pending third party — 82

| Ledger record | Recorded state | Evidence | Next action |
|---|---|---|---|
| [docker-mcp-catalog](https://github.com/docker/mcp-registry/pull/4765) | submitted | Current + ledger | Await Docker maintainer build approval and catalog acceptance. |
| [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers/pull/12771) | submitted | Current + ledger | Await maintainer review on PR 12771 and verify the upstream entry after merge. |
| [finos-fdc3-app-directory](https://github.com/finos-labs/FDC3-App-Directory/pull/40) | submitted | Current + ledger | Await FINOS directory review. |
| [openbb-app-marketplace](https://app.formbricks.com/s/cms3erjhmnwz901shu03176vk) | submitted | Ledger | Await the current Marketplace review owner and the fee-waiver decision at the submitted company contact. Supply a native Workspace walkthrough if requested; separately approve any future paid terms. Reconcile this rec… |
| [gemini-cli-extension-gallery](https://geminicli.com/extensions/) | eligible_automatic | Current + ledger | Keep the eligible automatic-indexing state: the complete public gallery has no exact owner/repository/tool marker. Recheck on a bounded cadence; no resubmission or acceptance claim. |
| [cline-mcp-marketplace](https://github.com/cline/mcp-marketplace/issues/2903) | submitted | Current + ledger | Await review of issue 2903 and verify the public marketplace entry if accepted. Do not create a duplicate issue. |
| [alternativeto](https://alternativeto.net/software/liquilens/) | submitted | Ledger | Await moderation of the existing submission, then verify an independently accessible public product page. Do not resubmit. |
| [apis-guru-research-api](https://github.com/APIs-guru/openapi-directory/issues/3568) | submitted | Current + ledger | Await maintainer review and verify the listing if accepted. |
| [apislist-research](https://apislist.com/api/add) | submitted | Ledger | Wait for operator review and independently resolve the accepted public URL before marking live. |
| [apislist-liquilens](https://apislist.com/api/add) | submitted | Ledger | Wait for operator review and independently resolve the accepted public URL before marking live. |
| [apislist-seiche](https://apislist.com/api/add) | submitted | Ledger | Wait for operator review and independently resolve the accepted public URL before marking live. |
| [apislist-undertow](https://apislist.com/api/add) | submitted | Ledger | Wait for operator review and independently resolve the accepted public URL before marking live. |
| [apisio-company](https://apis.io/add/) | submitted | Ledger | Await review and the next directory build; do not resubmit the company entry. |
| [mcpservers-org-research-desk](https://mcpservers.org/submit) | submitted | Ledger | Wait for the operator review and verify the research endpoint and public listing if accepted. |
| [allmcps-financial-evidence](https://allmcps.com/mcp/financial-evidence) | listed_incomplete | Ledger | Verify public propagation of the pending edit and AllMCPs own sandbox result before closing listing completeness. |
| [allmcps-undertow](https://allmcps.com/mcp/undertow-market-liquidity-map-2) | listed_incomplete | Ledger | Verify propagation of the pending edit and have the directory reconcile its duplicate and transport labels. Do not attribute subscriber access to the public discovery test. |
| [battlefin-company-map](https://battlefin-global-data-maps.lovable.app/submit) | submitted | Ledger | Await BattleFin review and independently verify a public firm page before marking live. |
| [apyhub-seiche-reference-fx](https://apyhub.com/workspace/mrinallovesbhature/publishing/035397d7-9b8c-450b-86fa-cc14eb66d0d4) | submitted | Ledger | Wait for the existing submitted draft to be reviewed. After approval verify the public catalog, gateway response, attribution, pricing and acquisition attribution; do not resubmit. |
| [saashub-undertow](https://www.saashub.com/undertow-by-liquilens/added) | submitted | Ledger | Await the existing SaaSHub editorial review; do not resubmit or confuse verification with approval. |
| [g2-liquilens](https://www.g2.com/products/liquilens/reviews) | listed_incomplete | Ledger | Read existing category case 00642455 and seller-description case 00643368 for a response, then verify the public taxonomy/copy and syndicated pages; do not create another support case. |
| [g2-seiche](https://www.g2.com/products/seiche/reviews) | listed_incomplete | Ledger | Await G2 confirmation of the existing-case addendum covering the financial-research category and missing network pages, then verify the provider response and corrected public outcomes. |
| [g2-undertow](https://www.g2.com/products/liquilens-private-limited-undertow/reviews) | listed_incomplete | Ledger | Await G2 confirmation of the existing-case addendum covering the financial-research category and unsupported survey features, then verify the corrected public profile. |
| [datarade-company](https://providers.datarade.ai/apply/confirm/success) | approved_pending_public | Current + ledger | Public readback returned 403. Preserve approved_pending_public and the existing product ID; use normal owner access to inspect propagation when available, without replaying activation/submission. |
| [mcpserver-cc-financial-evidence](https://mcpserver.cc/submit) | submitted | Ledger | Await review of the existing submission; verify a canonical public listing before marking live. |
| [public-apis-financial-evidence-mcp](https://github.com/public-apis/public-apis/pull/7884) | submitted | Current + ledger | Await maintainer review and MCP-aware formatter handling on the existing PR; verify the merged README before marking live. |
| [apivault-financial-evidence](https://github.com/exa-studio/ApiVault/issues/327) | submitted | Current + ledger | Await the existing issue review; retain the stated CORS boundary and verify the public entry if accepted. |
| [mcpserverfinder-financial-evidence](https://mcpserverfinder.com/) | sent_delivery_unverified | Ledger | Monitor the original correspondence for delivery or review evidence; do not replay the message or mark a listing live without public readback. |
| [lobehub-liquilens](https://lobehub.com/mcp/beepboop2025-liquilens-mcp) | listed_incomplete | Ledger | Await correction and public reindexing on the existing support thread; use the verified hosted HTTP connection meanwhile. |
| [lobehub-seiche](https://lobehub.com/mcp/beepboop2025-seiche) | listed_incomplete | Ledger | Await correction and public reindexing on the existing support thread; use the verified hosted HTTP connection meanwhile. |
| [lobehub-palimpsest](https://lobehub.com/mcp/beepboop2025-palimpsest) | listed_incomplete | Ledger | Await public catalog synchronization and validation, then recheck the exact existing card against the accepted update receipt. The earlier support request is preserved; no duplicate claim or listing is needed. |
| [lobehub-riptide](https://lobehub.com/mcp/beepboop2025-riptide-mcp) | listed_incomplete | Ledger | Await public catalog synchronization and validation, then recheck the exact existing card against the accepted update receipt. The earlier support request is preserved; no duplicate claim or listing is needed. |
| [lobehub-noisefloor](https://lobehub.com/mcp/beepboop2025-noisefloor) | listed_incomplete | Ledger | Await public catalog synchronization and validation, then recheck the exact existing card against the accepted update receipt. The earlier support request is preserved; no duplicate claim or listing is needed. |
| [lobehub-evidence-carrier](https://lobehub.com/mcp/beepboop2025-liquilens-evidence-carrier) | listed_incomplete | Ledger | Await public catalog synchronization and validation, then recheck the exact existing card against the accepted update receipt. The earlier support request is preserved; no duplicate claim or listing is needed. |
| [fintech-sandbox-provider-intake](https://www.fintechsandbox.org/become-a-data-partner/) | submitted | Ledger | Await qualification review on the existing intake; scope any service, trial or licence terms separately before committing access or source rights. |
| [neudata-company](https://www.neudata.co/data_providers/sign_up?requested_subscription_status=pending_free) | submitted | Ledger | Await provider review and continue the existing application; do not replay signup. |
| [eagle-alpha-company](https://app.selldata.eaglealpha.com/signup) | submitted | Ledger | Await approval of the existing verified provider request; qualify each dataset before upload. |
| [crozdesk-liquilens](https://vendor.revleads.com/user/signup) | submitted | Ledger | Await manual review, then log in and complete the product listing if eligible; do not resubmit the application. |
| [softwaresuggest-liquilens](https://www.softwaresuggest.com/vendors) | ready_account_action | Ledger | Await support guidance, then use a truthful supported billing option to save the existing product and complete the free listing. Do not select an inaccurate billing period or create a duplicate registration. |
| [haystack-financial-evidence](https://github.com/deepset-ai/haystack-integrations/pull/650) | submitted | Current + ledger | Await maintainer review of PR650 and verify the public catalog page after acceptance. |
| [langchain-financial-evidence](https://github.com/langchain-ai/docs/issues/6593) | submitted | Current + ledger | Await maintainer triage and review of issue 6593 and verify the public integration page after acceptance. |
| [awesome-quant-seiche](https://github.com/wilsonfreitas/awesome-quant/pull/778) | submitted | Current + ledger | Check the existing submission for editorial approval and verify the public listing; do not resubmit. |
| [awesome-quant-noisefloor](https://github.com/wilsonfreitas/awesome-quant/pull/778) | submitted | Current + ledger | Check the existing submission for editorial approval and verify the public listing; do not resubmit. |
| [osint-collection-palimpsest](https://github.com/cipher387/osint_stuff_tool_collection/pull/182) | submitted | Current + ledger | Check the existing submission for editorial approval and verify the public listing; do not resubmit. |
| [wealthmcp-financial-evidence](https://wealthmcp.ai/submit) | submitted | Ledger | Check the existing submission for editorial approval and verify the public listing; do not resubmit. |
| [wealthmcp-seiche](https://wealthmcp.ai/submit) | submitted | Ledger | Check the existing submission for editorial approval and verify the public listing; do not resubmit. |
| [wealthmcp-noisefloor](https://wealthmcp.ai/submit) | submitted | Ledger | Check the existing submission for editorial approval and verify the public listing; do not resubmit. |
| [ai4finance-market-brief](https://github.com/AI4Finance-Foundation/Awesome_AI4Finance/pull/26) | submitted | Current + ledger | Await maintainer review of existing PR 26; do not resubmit. |
| [cursor-directory-financial-evidence](https://cursor.directory/plugins/financial-evidence-by-liquilens) | submitted | Ledger | Wait for the existing security scan and verify anonymous public visibility and the actual install configuration before claiming live publication. |
| [finskilz-financial-evidence](https://finskilz.com/servers/submit/) | submitted | Ledger | Await evaluation results and verify the public listing and actual supported-tool results; do not resubmit. |
| [sourceforge-research-desk](https://sourceforge.net/software/vendors/new_submitted) | submitted | Ledger | Await the existing request review and verify a public product page after approval. Create or connect an owner management account only if required by the approval flow; do not resubmit. |
| [capterra-liquilens](https://www.capterra.com/p/10266227/LiquiLens/) | listed_incomplete | Ledger | Track the existing G2 category and profile cases, then recheck syndicated taxonomy and product copy. |
| [getapp-liquilens](https://www.getapp.com/all-software/a/liquilens/) | listed_incomplete | Ledger | Track the existing G2 category and profile cases, then recheck syndicated taxonomy and product copy. |
| [capterra-undertow](https://www.capterra.com/p/10266232/Undertow/) | listed_incomplete | Ledger | Await G2 routing or resolution of the network category and survey-feature issues raised in the existing-case addendum, then verify the public page again. |
| [getapp-undertow](https://www.getapp.com/all-software/a/undertow-1/) | listed_incomplete | Ledger | Await G2 routing or resolution of the network category and survey-feature issues raised in the existing-case addendum, then verify the public page again. |
| [softwareadvice-undertow](https://www.softwareadvice.com/product/773580-Undertow/) | listed_incomplete | Ledger | Await G2 routing or resolution of the network category and survey-feature issues raised in the existing-case addendum, then verify the public page again. |
| [factset-provider-inquiry](https://www.factset.com/contact-us) | submitted | Ledger | Await a response on this existing inquiry; do not submit a duplicate. Confirm provider fit, source-qualified offering, delivery requirements and any commercial terms before proceeding. |
| [nasdaq-data-link-provider-inquiry](https://www.nasdaq.com/products/data/alternative/monetize-your-data) | submitted | Ledger | Await a response on this existing inquiry; do not submit a duplicate. Confirm provider fit, source-qualified offering, delivery requirements and any commercial terms before proceeding. |
| [n8n-creator-financial-evidence](https://creators.n8n.io/nodes/n8n-nodes-financial-evidence/integration) | submitted | Ledger | Await manual review of the existing 0.1.0 submission and respond to reviewer requests. Verify a public approved-node listing before upgrading this state. Do not submit a duplicate application. |
| [pipedream-financial-evidence](https://github.com/PipedreamHQ/pipedream/issues/22210) | submitted | Current + ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [mcp-directory-financial-evidence](https://mcp.directory/submit) | submitted | Ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [agentndx-financial-evidence](https://agentndx.ai/submit/) | submitted | Current + ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [mcp-directory-seiche](https://mcp.directory/submit) | submitted | Ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [agentndx-seiche](https://agentndx.ai/submit/) | submitted | Current + ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [mcp-directory-liquilens](https://mcp.directory/submit) | submitted | Ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [agentndx-liquilens](https://agentndx.ai/submit/) | submitted | Current + ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [mcp-directory-undertow](https://mcp.directory/submit) | submitted | Ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [agentndx-undertow](https://agentndx.ai/submit/) | submitted | Current + ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [apidirectory-seiche](https://apidirectory.com/submit) | submitted | Ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [apidirectory-undertow](https://apidirectory.com/submit) | submitted | Ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [mcp-find-financial-evidence](https://github.com/MCPFind/mcp-find/pull/281) | submitted | Current + ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [kilo-financial-evidence](https://github.com/Kilo-Org/kilo-marketplace/pull/366) | submitted | Current + ledger | Await review of the existing submission; verify its canonical public listing before marking live. Do not resubmit. |
| [apidirectory-liquilens](https://apidirectory.com/api/liquilens) | listed_incomplete | Ledger | Track the existing metadata-refresh request and verify corrected public copy. Do not create a duplicate entry. |
| [opennews-source-financial-evidence](https://source.opennews.org/code/suggest/) | submitted | Ledger | Await review of this existing submission and verify the canonical public project page if accepted; do not send a duplicate code-index introduction. |
| [reuters-connect-supplier-inquiry](https://reutersagency.com/contact-us/enquire/) | submitted | Ledger | Await the supplier-team response on this enquiry; qualify coverage, source rights, delivery and commercial terms before any supply arrangement. Do not duplicate this request or the distinct existing LSEG enquiry. |
| [mcp-so-seiche](https://mcp.so/servers/seiche) | listed_incomplete | Ledger | Await the existing rescan ticket and verify canonical public metadata plus all 16 public tools before closing. |
| [agentndx-wake](https://agentndx.ai/submit/) | submitted | Current + ledger | Await review of this existing submission and independently verify its public listing. Do not resubmit. |
| [agentndx-seiche-agent-community](https://agentndx.ai/submit/) | submitted | Current + ledger | Await review of this existing submission and independently verify its public listing. Do not resubmit. |
| [mcpservers-org-wake](https://mcpservers.org/submit) | submitted | Ledger | Await review of the existing named submission; retain the acknowledgement and independently verify the public listing before marking live. Do not resubmit. |
| [mcpservers-org-seiche-agent-community](https://mcpservers.org/submit) | submitted | Ledger | Await review of the existing named submission; retain the acknowledgement and independently verify the public listing before marking live. Do not resubmit. |
| [cursor-official-marketplace](https://cursor.com/marketplace/publish) | submitted | Ledger | Await review of the existing official application; verify the published plugin and install behavior before calling the listing live. |
| [laplace-awesome-agent-trading-financial-evidence](https://github.com/laplace0x/awesome-agent-trading/pull/30) | submitted | Current + ledger | Await maintainer review of the existing PR; verify the default-branch entry before marking live. Do not submit a duplicate. |
| [aowang-awesome-finance-agents-financial-evidence](https://github.com/aowang-ai/awesome-finance-agents/pull/1) | submitted | Current + ledger | Await maintainer review of the existing PR; verify the default-branch entry before marking live. Do not submit a duplicate. |

### Gated or owned elsewhere — 11

| Ledger record | Recorded state | Evidence | Next action |
|---|---|---|---|
| [awesome-copilot](https://github.com/github/awesome-copilot/pull/2785) | closed_unmerged | Current + ledger | Review the existing closed-unmerged decision before proposing any materially revised contribution; no blind resubmission. |
| [awesome-openbb](https://github.com/OpenBB-finance/awesome-openbb/pull/12) | submitted | Current + ledger | Retain archived, unmerged PR 12 as history. Use the separate existing official Marketplace application; do not submit another directory PR. |
| [openai-plugin-directory](https://platform.openai.com/plugins) | ready_account_action | Ledger | Retain the exact prepared ZIP and submission packet; resume identity verification and the remaining portal steps when the owner lifts the deferral. |
| [claude-plugin-directory](https://claude.ai/directory/manage/new) | ready_account_action | Ledger | Retain the portable submission packet and existing consent approvals; resume publisher work when the owner lifts the deferral. A qualifying paid publisher account remains required. |
| [stackshare](https://stackshare.io/) | ready_account_action | Ledger | Have the account owner continue from the preserved prepared form and resolve the platform access gate; retain a genuine submission receipt before marking submitted. Do not replay the failed automated attempt or bypass… |
| [zenodo](https://zenodo.org/uploads/new) | conditional_artifact | Current + ledger | Hand the exact zero-result searches to terminal 01a13ffa. Verify archive creation for the next genuine owned release through the already enabled integration; do not mint a version or duplicate deposit solely to force … |
| [pulsemcp](https://www.pulsemcp.com/submit) | paused_external | Ledger | Monitor reopening and ingestion of the existing official-registry entry; do not replay or invent a submission receipt. |
| [mcp-so](https://mcp.so/submit?type=server) | skipped_paid | Ledger | Require separate authorization for the exact USD 39 spend before reconsidering. |
| [gumloop-financial-evidence](https://www.gumloop.com/) | skipped_paid | Ledger | Keep the account pending and do not start the trial unless the user later changes the decision. |
| [allmcps-wake](https://allmcps.com/submit) | ready_account_action | Ledger | Reconcile the uncertain prior attempt with the existing account and normal verification flow before any retry. No acknowledgement or listing is established. |
| [microsoft-certified-mcp](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-server-certification) | conditional_artifact | Ledger | Qualify verified-publisher and authentication requirements before preparing the official connector intake; preserve the existing custom-connection guide. |

## Boundaries

No external messages, new submissions, paid requests or product tool calls were made. No owner portal or private account state was inspected; credentials were not printed or retained. Public listings and imported endpoints do not establish independent users, trades or revenue. Dated ledger evidence is not silently promoted to current verification. The source ledger remains unchanged; only these two review files are owned by this task.
