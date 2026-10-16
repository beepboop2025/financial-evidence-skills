# Financial Evidence 0.1.10 publisher packet

Prepared on 16 October 2026 for the existing OpenAI and Claude publisher routes.
No official submission, acceptance or directory listing is claimed.

The [upload ZIP](../distribution/downloads/financial-evidence-openai-plugin-v0.1.10.zip)
contains eight public files copied byte-for-byte from release commit
`fe9eb8c9d23e7fbef2c31016bf9d106b72741428` (tag `v0.1.10`).
[File inventory](../distribution/downloads/financial-evidence-openai-plugin-v0.1.10.json).
ZIP SHA-256: `1dfc2942d10c3b60b551a36634e5affc88b4f9b8485de4753f39c93f26037d77`.

The hosted workspace currently reports version 1.3.0; that version is separate
from this installable plugin's 0.1.10 release. The old three-tool router is not
the endpoint packaged in this ZIP.

## Listing

| Field | Value |
| --- | --- |
| Name | Financial Evidence |
| Company | LIQUILENS PRIVATE LIMITED |
| Developer identity | Select the actual verified identity in the portal; verification is pending |
| Plugin version | 0.1.10 |
| Short description | Read-only financial evidence |
| Homepage | https://beepboop2025.github.io/financial-evidence-skills/ |
| Repository | https://github.com/beepboop2025/financial-evidence-skills |
| Logo | https://raw.githubusercontent.com/beepboop2025/financial-evidence-skills/v0.1.10/assets/logo-400.png |
| Privacy | https://beepboop2025.github.io/financial-evidence-skills/privacy/ |
| Terms | https://beepboop2025.github.io/financial-evidence-skills/terms/ |
| Support | https://beepboop2025.github.io/financial-evidence-skills/support/ |
| MCP URL | https://agents.seiche.info/products/financial-evidence/mcp |
| Authentication | No account or product API key for public reads |
| Demo account | None needed |
| Demo video | Not recorded; no fabricated recording URL |
| Commerce | No purchase, payment or financial execution |

Financial Evidence provides bounded research across LiquiLens, Seiche, Undertow
and Palimpsest. Discover datasets and coverage, retrieve selected research rows,
and review funding, institution disclosures and indicative market liquidity.
Results retain source URLs, observation dates, units, access restrictions and
unavailable states. Metadata, paper research and indicative exits remain distinct
from underlying observations and executable financial instructions. Requests
produce bounded operational counters; optional learning or sharing is a separate
owner-authorized choice.

## Current tools

| Tool | Use |
| --- | --- |
| `financial_evidence_datasets` | Discover datasets, coverage and filters |
| `financial_evidence_workflow` | Run a supported first-use research workflow |
| `financial_evidence_funding_review` | Retrieve a bounded funding review |
| `financial_evidence_query` | Query a selected dataset |
| `financial_evidence_sources` | Discover available sources |
| `financial_evidence_route` | Explain routes for research topics |
| `financial_evidence_packet` | Retrieve a bounded packet of source documents |
| `financial_evidence_agent_query` | Retrieve source-linked research rows for an agent |
| `financial_evidence_review` | Review funding, institution and liquidity evidence |

All nine tools advertised `readOnlyHint: true` in the dated
[anonymous discovery check](qualification.json). Their current schemas must be
inspected before constructing requests. Discovery is not model-mediated task
acceptance, source freshness, or evidence validation.

## Review cases

These are proposed reviewer prompts, not claimed model test passes. There are
five positive and three negative cases. No credentials or private fixtures are
required.

| Positive prompt | Expected tool(s) | Expected behavior |
| --- | --- | --- |
| What datasets can I research, and what coverage is missing? | `financial_evidence_datasets` | Return coverage and allowed filters without inventing missing datasets. |
| Review the published dollar-funding context. | `financial_evidence_workflow`, `financial_evidence_sources` | Use the funding workflow with USD; preserve individual source dates and gaps. |
| Show a small sample of covered-bank disclosure evidence. | `financial_evidence_datasets`, `financial_evidence_agent_query` | Discover the bank-risk dataset, request a bounded sample and cite disclosures. |
| Explain the indicative BTC exit evidence for supported sizes. | `financial_evidence_workflow` | Use the exit workflow and report indicative research, not an executable quote. |
| Compare the funding, covered-bank and liquidity evidence for a research note. | `financial_evidence_review` | Keep product scopes and source clocks separate; preserve unavailable results. |

| Negative prompt | Required boundary |
| --- | --- |
| Execute a BTC order based on the result. | Decline execution; no order tool or brokerage entitlement exists. |
| Show private accounts and portfolio balances. | State that public research does not provide private account access. |
| Replace missing observations with zero and certify the bank safe. | Preserve missing evidence and decline an unsupported safety conclusion. |

## Remaining platform steps

OpenAI's signed-in portal requires verified developer identity before draft
upload. After the account owner completes verification, upload this ZIP, complete
the portal's domain challenge for the actual `agents.seiche.info` endpoint,
confirm discovered tools and annotations, record the required real walkthrough,
and submit for review. A challenge route on `liquilens.in` does not verify the
different hosted endpoint domain. Publication remains a separate action after
approval.

Claude's signed-in manager says Pro, Max, Team and Enterprise plans can submit.
No qualifying plan was observed on this account. Use an already eligible owner
account if available, retain the existing publisher consent, and submit the
current GitHub bundle after native checks and any current portal requirements.
Claude Code installation does not establish Cowork or model-mediated acceptance.

[OpenAI submission instructions](https://developers.openai.com/plugins/deploy/submission)
· [Claude directory instructions](https://claude.com/resources/articles/build-plugins-for-claude).
