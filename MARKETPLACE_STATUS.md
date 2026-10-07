# Third-party marketplace status

The [product-level ledger](docs/marketplaces.json) records publication and
submission evidence for Financial Evidence and the LiquiLens family. The
[7 October audit](docs/distribution/marketplace-audit.md) tracks 67 platform
and product routes: 44 examined in this sweep and 23 inherited from dated
records. The [cloud listing packet](docs/distribution/cloud-listing-packet.md)
contains the prepared AWS and institutional submission material.

`verified_at` is the observation clock for an entry. `checked_at` remains the
older full-ledger check; `release_verified_at` separately records software
release acceptance. Updating the ledger does not refresh every observation.

## Latest marketplace retries

- **G2:** Seiche and Undertow have explicit profile-approval receipts. LiquiLens
  has an owner-confirmed email and matching operator record. Public visibility
  remains unverified; optional Capterra/GetApp/Software Advice placements are
  subject to separate verification.
- **API.market:** Seiche Reference FX is in review with four fixed endpoints,
  a $0 plan, 1,000 monthly requests, hard limit and no overage charge.
- **Datarade:** the company's confirmed provider application is under review.
- **Zenodo:** automatic preservation is enabled for future Financial Evidence
  releases; no Financial Evidence DOI is yet verified.

The [retry record](docs/distribution/marketplace-retry.md) includes the exact
remaining steps for StackShare, AlternativeTo, SaaSHub and the launch drafts.
The [earlier follow-through](docs/distribution/non-amazon-follow-through.md)
records the public Hugging Face Space, two SaaSHub submissions and native
integration candidates. These results do not establish independent adoption.

## Earlier 7 October sweep

- **Two new public listings:** [Financial Evidence API on FreePublicAPIs](https://www.freepublicapis.com/financial-evidence-api), with four JSON endpoints, and [Financial Evidence Research Desk on AllMCPs](https://allmcps.com/mcp/financial-evidence-research-desk), with the correct hosted MCP endpoint. AllMCPs enrichment, health checks and ownership verification remain pending.
- **Eight received review submissions:** APIsList for the Research API,
  LiquiLens, Seiche and Undertow; one APIs.io company entry; MCPServers.org for
  the distinct eight-tool Research Desk; BattleFin for the company data map;
  ApyHub for the four-endpoint Seiche Reference FX API.
- **Fourteen existing placements reconciled:** six MCPServers.org pages,
  seven unique AllMCPs product pages and one MCP Market page. These were
  discovered, not newly published. AllMCPs has stale router/Undertow metadata;
  an additional Undertow duplicate is excluded from the placement count.

[Receipt summaries](docs/distribution/receipt-summaries.json) preserve evidence
hashes. APIsList states up to 30 days for review and MCPServers.org two weeks;
these windows do not guarantee approval.

## Previously verified public surfaces

Official MCP Registry and the separately accepted Homebrew tap publish the
three-tool source router at v0.1.6. skills.sh serves the Agent Skill. Glama now
exposes all three tools and author verification, resolving its earlier empty
inventory. Smithery has five entries: the router, LiquiLens, Seiche, Undertow
and the distinct Research Desk. The shared REST API has public Postman docs.
Their individual verification dates remain in the ledger.

Concurrent work owns the core RapidAPI, Postman, SwaggerHub definitions and
older API-directory PRs. This sweep did not repeat those publications or
activate paid plans. Another product's release does not close a separate
shared-product artifact entry.

## Existing submissions awaiting operators

- [Docker MCP Catalog #4765](https://github.com/docker/mcp-registry/pull/4765)
- [Awesome MCP Servers #12771](https://github.com/punkpeye/awesome-mcp-servers/pull/12771)
- [FINOS FDC3 #40](https://github.com/finos-labs/FDC3-App-Directory/pull/40)
- [Awesome OpenBB #12](https://github.com/OpenBB-finance/awesome-openbb/pull/12)
- [APIs.guru Research API #3568](https://github.com/APIs-guru/openapi-directory/issues/3568)
- [Awesome Remote MCP Servers #1318](https://github.com/punkpeye/awesome-remote-mcp-servers/pull/1318)

An open or mergeable PR is not an accepted listing. Awesome GitHub Copilot
[#2785](https://github.com/github/awesome-copilot/pull/2785) closed without
merge; no placement is claimed.

## Remaining work

- AllMCPs: the Research Desk verification/submission gate is resolved. Claim the existing page through owner sign-in and monitor enrichment; do not resubmit.
- SourceForge: the prepared Research Desk profile needs its required logo;
  the browser extension rejected local upload because file access is disabled.
- AWS: paused at the owner's request. Sign-in is complete; identity verification,
  business onboarding and offer integration remain. Resume only when requested.
- ApyHub: the [Seiche Reference FX API](docs/distribution/apyhub-reference-fx-rights.md)
  was submitted with four tested CSV endpoints and verified ECB reuse conditions.
  Admin approval and public gateway acceptance remain pending. The separate
  broad Research API draft remains unpublished pending source-specific rights.
- OpenAI, Claude, Cline and other account/native-artifact routes retain their
  own gates. Smithery is no longer account-pending. Paid MCP.so and MCP Market
  remote placements remain unpurchased.

PulseMCP, Gemini and other inherited entries retain their older clocks and
exact product scope. Zenodo's new preservation setting is recorded separately
from an archived release. See the route audit and retry record for each action.

## Adoption and follow-up

The target is one million monthly active **people**. Listings, API calls,
crawlers, packages and advertised directory audiences do not measure that
number. Current verified MAU is unknown in this record. Measure completed
research tasks, distinct returning people and retention separately.

Reconcile receipts before retrying. Resolve the public URL before marking a
listing live. Native tests, data rights, review and adoption remain separate;
publication does not guarantee rankings, endorsements or customer counts.
