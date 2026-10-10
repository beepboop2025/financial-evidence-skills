# Distribution completion pass — 10 October 2026

Two more free submissions were received: LiquiLens on AlternativeTo and
Financial Evidence in Cline's MCP marketplace. Together with the
[earlier expansion](wide-distribution-20261010.md), this is **11 submission
operations requesting 12 product placements across nine destinations**.
The requested new listings remain in review. Paid placement spend was **₹0**.

This report records the work that can be completed by the publisher and the
specific account or operator steps still outstanding. It does not establish
new users, retention, revenue or complete distribution coverage.

## Completed publisher work

| Destination | Work completed | Current result |
| --- | --- | --- |
| AlternativeTo | Verified the existing account email; submitted LiquiLens with official logo, genuine research screenshot, free public access, company details and OpenBB Terminal as a relevant alternative | Submission `824b49e3-8bc3-49df-9a2f-93e2066b332b` acknowledged. The product is visible only to its owner while awaiting moderation. Optional paid priority declined. |
| [Cline MCP marketplace](https://github.com/cline/mcp-marketplace/issues/2903) | Registered the endpoint using Cline 3.0.70, verified the native MCP client connection, discovered all three router tools and successfully called the topics tool; submitted with accurate install attestations | Issue 2903 open for review. No paid model was used and no end-user chat workflow is claimed. |
| [Cline installation guide](https://github.com/beepboop2025/financial-evidence-skills/blob/main/llms-install.md) | Updated the public install pin to 0.1.7 and added the tested Cline remote configuration | [PR 96](https://github.com/beepboop2025/financial-evidence-skills/pull/96) merged after all 18 checks passed; served main-branch guide matched the source bytes. |
| [AllMCPs Financial Evidence](https://allmcps.com/mcp/financial-evidence) | Submitted its canonical remote endpoint, MIT license, current description and verified Cline compatibility; preserved the versioned wheel configuration | Edit pending. Public propagation and AllMCPs' own sandbox verification remain unproved. |
| [AllMCPs Undertow](https://allmcps.com/mcp/undertow-market-liquidity-map-2) | Submitted the current remote and support URLs plus a description separating 16 public tools from eight subscriber tools | Edit pending. The older duplicate and conflicting transport labels still need directory reconciliation. Subscriber access was not tested. |
| [AllMCPs Research Desk](https://allmcps.com/mcp/financial-evidence-research-desk) | Uploaded the official Financial Evidence logo | Logo pending admin review; the existing eight-tool listing remains live. |
| G2 LiquiLens | Saved the official logo, English language and hosted-only deployment settings | Profile enrichment saved. Existing cases 00642455 and 00643368 still cover the wrong category and contact-lens description; no duplicate case was sent. |
| SaaSHub LiquiLens and Seiche | Saved official logos, genuine product screenshots, free-access pricing, three product-specific features and Web support; completed the free Verify action for each | Both verification receipts observed. Directory approval remains pending; verification is not publication. |
| [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers/pull/12771) | Resolved the existing PR's merge conflict against current upstream and pushed the repair | PR is mergeable, with its submission check passing. The catalog change remains exactly one added entry. |
| [Awesome AI4Finance Market Brief](https://github.com/AI4Finance-Foundation/Awesome_AI4Finance/pull/26) | Resolved the existing PR's merge conflict and preserved current upstream content | PR is mergeable and awaits maintainer review. The catalog change remains exactly one added entry. |
| OpenAI plugin portal | Refreshed the packet to 0.1.7 and assembled a minimal ZIP from exact release files | [Upload ZIP](downloads/financial-evidence-openai-plugin-v0.1.7.zip) and [checksums](downloads/financial-evidence-openai-plugin-v0.1.7.json) prepared. Identity verification blocks draft upload. |
| LobeHub | Generated seven current owner-update manifests using the official publisher CLI; verified native discovery against six public endpoints and the Evidence Carrier local bundle | [Prepared updates and observed tool inventory](lobehub-updates/README.md). Account authorization is still required to apply them. |

## Verification and review outcomes

Cline's native `@cline/core 0.0.92` client connected without authorization,
discovered `financial_evidence_topics`, `financial_evidence_route` and
`financial_evidence_fetch`, and returned a non-error topics response. This is
a native transport/tool test, separate from using an LLM or a complete Cline chat.
The live route catalog contains eight topics.

Undertow's native discovery returned 16 public tools. Its access-status response
reported no subscriber entitlement and listed eight additional subscriber
tools separately. Neither subscriptions nor execution capabilities were enabled.

The pending upstream contributions were read for actionable review feedback.
Two conflict requests were fixed. Other open contributions still await external
review. Awesome Copilot PR 2785 remains closed without merge because the
maintainer found it unsuitable; it was not resubmitted. Haystack's Vercel preview
requires upstream team authorization.

The full Gemini CLI gallery response was fetched and checked for the repository
owner, repository name and tool prefix. No Financial Evidence entry was found.
Automatic indexing remains eligible, with no observed listing.

The G2 administrator view reports Capterra and GetApp published, but public
readback did not verify them in this pass. They are not counted as new public
placements. The generic G2 Undertow page belongs to another company and must
not be attributed to this fleet.

## Remaining steps and their owners

| Remaining step | Owner or condition |
| --- | --- |
| OpenAI publisher verification | Account owner completes business identity verification for LIQUILENS PRIVATE LIMITED in the open organization settings. Both available organizations were unverified. The portal blocks even a draft ZIP upload until this is complete. |
| OpenAI draft, domain token and demo | After identity verification, upload the prepared ZIP, install the exact portal-issued domain token, scan and test the draft, and record the required real ChatGPT and Codex demonstration. No token or demo URL exists to submit yet. |
| Claude publisher sign-in | Approval is pending for the displayed Commercial Terms and Usage Policy. Prepared materials are retained; no submission receipt exists. |
| LobeHub updates | Approval is pending for profile/email/persistent sign-in access by the official publisher CLI, followed by a review of any GitHub ownership grant. No update has been published yet. |
| SoftwareSuggest | Existing ticket 82283 awaits a truthful quote-specific billing option or manual completion. Do not choose an inaccurate fixed billing period. |
| G2 corrections | Existing support cases await the operator's category and seller-description corrections. |
| Datarade | Provider Studio already says Published; independently accessible public provider/product pages remain unverified. Preserve the existing product. |
| SaaSHub Undertow | The operator requires an earlier listing approval before allowing this account's next submission. |
| Directory moderation and upstream PRs | Await the existing review processes, then verify public pages. Submission receipts are not publication. |
| PulseMCP | Intake and edits are paused externally; existing Official MCP Registry publication remains the supported ingestion route. |
| StackShare | The form explicitly denied bot access. No retry or bypass was attempted. |
| ToolHive | Native validation still needs an available container runtime. The prior catalog validation does not prove native startup. |
| SourceForge | The prior draft belongs to a separate concurrent session; its latest outcome is unverified here and no duplicate was created. |
| AWS and Gumloop | AWS remains paused by the owner. Gumloop's paid trial remains declined. |

The [product ledger](../marketplaces.json) retains 112 product/channel records
with per-entry observation dates. These are records, not 112 unique platforms.
The [sanitized completion receipt](completion-20261010.json) records counts,
artifact identities and remaining gates. Earlier dated reports are historical;
this report supersedes their completed email, upload and Cline-validation steps.
