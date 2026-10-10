# Claude directory submission packet

Status as of 10 October 2026: prepared and deferred by the owner, not submitted.
Publisher sign-in and directory terms have been approved. The former Console form can no longer
create or submit applications and directs publishers to
[the current directory manager](https://claude.ai/directory/manage/new).
That manager requires a qualifying Pro, Max, Team or Enterprise plan; the
current publisher account does not qualify. No plan has been purchased and no
submission receipt exists.

Anthropic's [directory submission announcement](https://claude.com/resources/articles/build-plugins-for-claude)
also describes the paid-plan requirement and the GitHub-hosted plugin-bundle
submission route. This packet retains the prepared listing copy for that route.

## Listing fields

| Field | Prepared value |
| --- | --- |
| Name | Financial Evidence |
| Developer | Liquidity Lab |
| Company | LIQUILENS PRIVATE LIMITED |
| Version | 0.1.7 |
| Repository | https://github.com/beepboop2025/financial-evidence-skills |
| Homepage | https://beepboop2025.github.io/financial-evidence-skills/ |
| License | MIT |
| Support email | mrinal@liquilens.in |
| Support page | https://beepboop2025.github.io/financial-evidence-skills/support/ |
| Privacy policy | https://beepboop2025.github.io/financial-evidence-skills/privacy/ |
| Terms | https://beepboop2025.github.io/financial-evidence-skills/terms/ |
| Logo | https://raw.githubusercontent.com/beepboop2025/financial-evidence-skills/v0.1.7/assets/logo-400.png |
| Submission type | Plugin bundle containing an Agent Skill and remote MCP server |
| Requested surface | Claude Code only |
| MCP endpoint | https://liquilens.in/mcp/financial-evidence |
| Authentication | None for the plugin's public reads; no test account or API key required |
| Product payment | No payment required for these public research reads |

### Short description

Read-only, source-linked financial evidence across four research products.

### Full description

Financial Evidence routes sourced research across LiquiLens, Seiche, Undertow
and Palimpsest. Its eight topics cover money markets, capital-market
transmission, China economy, bank and institution risk, market liquidity, GIFT
City, forex and gold. The plugin combines an Agent Skill with three read-only
MCP tools that list topics, explain a route or retrieve evidence for up to five
topics per call.

Evidence retains source URLs, retrieval clocks, content hashes and explicit
unavailable states. Source observation times, product coverage and evidence
classes remain separate. Retrieval success does not establish evidence
validation, verified balances or a single financial-risk score. Public reads
require no authentication or payment. The plugin supports research; it does
not execute trades, access private portfolios or provide personalized
investment advice.

## Use cases and suggested prompts

| Use case | Suggested prompt | Expected behavior |
| --- | --- | --- |
| Money markets and transmission | Trace public funding conditions and how they may transmit into capital markets. | Route `money-market` and `capital-market` to Seiche, retaining separate source clocks and unavailable states. |
| China observations and revisions | Research China economic signals and explain the available revision history. | Route `china-economy` to Palimpsest observations and Seiche context, keeping their evidence separate. |
| Institution risk and exit conditions | Compare covered bank-risk evidence with market-depth and position-sized exit-liquidity context. | Keep LiquiLens institution diagnostics separate from Undertow market-liquidity evidence; request inputs before any native scenario calculation. |
| GIFT City, forex and gold | Gather sourced GIFT City funding, forex-reference and gold context for a treasury research note. | Retrieve `gift-city`, `forex` and `gold`, retaining quote dates, null prices, missing eligibility data and source limitations. |

These are proposed review prompts, not a claim that model-mediated sessions
have already passed. The router does not supply invented prices, positions,
fees or settlement assumptions for a calculation.

## Tools and access

| Tool | Purpose | External access |
| --- | --- | --- |
| `financial_evidence_topics` | List supported topics and product routes | None; static catalog |
| `financial_evidence_route` | Explain the deterministic route for one topic | None; static route lookup |
| `financial_evidence_fetch` | Retrieve public evidence for up to five topics | Bounded reads from fixed public source endpoints |

All three tools are read-only and non-destructive. No account, portfolio,
payment, trading or write permission is requested. The fetch result records
`status_semantics: transport_only`, `evidence_status: not_evaluated` and
`carrier_verification: not_performed`. A partial or unavailable source remains
explicit rather than being replaced with a zero or an inferred reassuring
value.

## Tested installation

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install financial-evidence@liquidity-lab
claude plugin details financial-evidence@liquidity-lab
claude mcp list
```

The native test on 10 October 2026 used Claude Code 2.1.228 and an isolated
configuration. It fetched public repository commit
`3e13efae890d832adc76b776b785c4132fa34974` and installed version 0.1.7.
The client resolved one skill and one MCP server, connected to the public HTTP
endpoint without authentication and observed server version 0.1.7. The
marketplace command follows the repository's mutable default branch; review
the fetched commit before enabling a later installation.

The exact installed retrieval helper was also executed manually. Bank-risk
succeeded with its default 1 MB byte limit. The current money-market document
was 2,180,119 bytes, so the default limit returned an explicit unavailable
result; an explicit `--max-bytes 4194304` succeeded. This known size limitation
must remain visible in review notes.

No model call was made. Native installation, component discovery, HTTP
connection and manual helper execution do not establish a model-mediated MCP
tool call. Cowork has not been tested and must not be selected as a verified
surface. The [publisher follow-through receipt](docs/distribution/publisher-completion-20261010.json)
records these boundaries.

## Remaining submission steps

1. Resume only after the owner lifts the deferral. Then continue in the current
   directory manager using an existing qualifying
   publisher account, or obtain an owner decision on the required plan.
2. Transfer this packet into the GitHub plugin-bundle application and select
   Claude Code only. Sign-in and directory consent are already approved.
3. Complete any additional current portal validation using actual evidence;
   do not infer a model or Cowork test from the native connection receipt.
4. Retain the submitted application receipt and operator scan/review outcome.
   Approval, owner publication and public listing readback remain separate
   steps; none is currently claimed.
