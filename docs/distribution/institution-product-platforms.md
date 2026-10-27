# Financial evidence for institutions: products and supported routes

Reviewed 28 October 2026. Start with a useful research task and keep the evidence
portable across the institution's authorised tools. Availability, native host
acceptance, marketplace approval and permission to reuse source data are separate
states. This matrix describes the existing public-research products and the
remaining work for private institution data.

## Choose a research workflow

| Product | Useful institutional task | Existing delivery route | Boundary to preserve |
| --- | --- | --- | --- |
| **LiquiLens** | Review covered institutions, source disclosures and asset-quality evidence. RBI supervisory-tape, bank asset-quality review and NPA reconciliation tools support a documented analyst review. | [Product API/MCP guide](https://liquilens.in/developers/), [MCP configuration](../connect/liquilens.mcp.json), publisher plugin; exact institution watchlists in the Office workflow. | Coverage is explicit and can be incomplete. Full product tools are not all native Excel commands. Evidence states are not credit ratings, supervisory approval or a lending decision. |
| **Seiche** | Compare published funding observations and source clocks; review money-market and capital-market context. | [API/MCP guide](https://seiche.info/developers.html), [MCP configuration](../connect/seiche.mcp.json), publisher plugin; funding currencies in the Office workflow. | Keep observation and retrieval dates distinct. Different currencies' rates are not a common stress ranking. A successful response does not establish fresh underlying data. |
| **Source Data Research Workspace** | Discover datasets and exact series identifiers; retrieve bounded observations with capture receipts for reproducible research. | [Hosted guide](https://agents.seiche.info/connect), [research-data MCP configuration](../connect/research-data.mcp.json), publisher plugin. | This is a research wrapper, not permission to redistribute every upstream dataset or a connector to a customer's private subscriptions. No dedicated Office command is claimed. |
| **Palimpsest** | Review China/regional public-source evidence, revisions and coverage gaps. | [API/MCP guide](https://palimpsest.info/developers.html), [MCP configuration](../connect/palimpsest.mcp.json), publisher plugin; the shared Research Desk can expose publication-coverage metadata. | Availability metadata is not a measured economic observation. Restricted or unavailable values remain unavailable. No dedicated Excel command is claimed. |
| **NoiseFloor** | Examine statistical relationships and evidence limits using permitted observations; use the local path for private observations. | [Research/local guide](https://liquilens.in/agents/correlation/#connect), [public MCP configuration](../connect/noisefloor.mcp.json), publisher plugin. | Statistical association is not causation, model validation or an investment signal. A public hosted endpoint is not an approved destination for private institution data. |
| **Undertow** | Inspect published market liquidity and indicative BTC exit evidence where the institution has a relevant research use case. | [API/MCP guide](https://liquilens-undertow.com/developers/), [MCP configuration](../connect/undertow.mcp.json), publisher plugin; bounded optional liquidity tables in the browser desk. | Quotes and costs are indicative, not executable. Public access does not include subscriber-only tools or execution authority. No dedicated Excel command is claimed. |
| **Financial Evidence Workspace** | Combine supported public research views in one source-linked review with coverage, missingness and status retained. | [Browser desk](../start/), [REST/OpenAPI](../api/), [MCP configuration](../connect/financial-evidence.mcp.json), Office exports and publisher plugin. | The wrapper does not create new source rights or institution data access. The native Excel pane currently exposes only funding currencies and institution selections. |

The [14-product connection catalog](../connect/native-connections.json) includes
additional research, editorial, metadata-only and sandbox routes. Their presence
is not a claim that all fourteen are institution-ready applications. Select only
the products relevant to the task and preserve each route's stated scope.

## Use the tools the institution already has

| Analyst environment | Usable route | Acceptance and publication boundary |
| --- | --- | --- |
| Excel for Windows | Financial Evidence task pane: manually refresh funding/institution evidence and insert six new review sheets. | [28 October native receipt](../office/excel/native-acceptance-windows-20261028.json): version 1.0.1.0 operator manifest, ribbon launch, two insertions, 634 inserted cells and original markers checked. Full keyboard traversal, native network-failure case and unchanged production-manifest runtime remain unqualified. Microsoft listing remains a draft until a submission receipt exists. |
| Excel for the web | XLSX snapshots and the previously tested add-in workflow. | [18 October receipt](../office/excel/native-acceptance.json) covers add-in version 1.0.0.0, not a new web acceptance run for 1.0.1.0. |
| Google Sheets | Custom functions, bound research sidebar and Editor add-on test deployment. | [Native acceptance](../office/native-acceptance.md) records installed/enabled test states; Google Marketplace review and scope/brand requirements remain separate. |
| LibreOffice, ONLYOFFICE, Collabora/Nextcloud | Supported XLSX/ODS snapshots, with the original evidence and status files beside them. | [Host compatibility](../office/compatibility.md) records exact tested versions and import/edit limits. Snapshots do not refresh themselves. |
| Compatible AI/IDE MCP clients | Explicitly select product endpoints through the [local institution connection package](../connect/institution-portability.md); client-neutral and VS Code configuration shapes are generated. | Generation is local and makes no research calls. Client installation, permissions and native runtime behavior need the client's own acceptance test. These configurations target public research only. |
| Claude plugin workflows | Install relevant publisher-maintained packages from the [plugin catalog](../plugins/catalog.json). | Repository distribution is distinct from official directory approval; follow the client's plugin policy and keep private data out of public research requests. |
| Notebooks, R, SQL/data tools and approved automation | Documented REST/MCP routes, CSV tables and original evidence JSON; retain source dates, units, status and restrictions through transformations. | [Platform guides](../platforms/) document each adapter. A format or API example is not native acceptance of every platform/version. |
| OpenBB Workspace | Existing Research Desk application and prepared integration. | [Application status](../office/marketplaces/openbb-status.md) records the existing submission. Marketplace approval, commercial terms and supported native access remain separate; do not create duplicate applications. |
| AWS, Google Cloud, Snowflake, Databricks and financial terminals | Use the [cloud/institutional listing packet](cloud-listing-packet.md) to qualify the appropriate offer. | Seller admission, native fulfillment, customer entitlement, rights and platform review must be established for the actual offer. Existing public URLs are not approved native commercial listings. |

## Move across silos and subscriptions with permission

The [connection package](../connect/institution-portability.md) lets an operator
review selected products, a declared workspace, approved public-research egress
and an inventory of existing external subscriptions before writing client
configuration. It rejects unsupported/private-data scope and invalid declared
rights or destinations. Its output and receipt are portable local artifacts.
It does **not** connect external subscriptions, verify a vendor contract, enforce
server-side tenant isolation or prevent a person entering private data in a
client after setup. The subscription inventory is not an entitlement token.

The institutional gateway is further engineering and assurance work. Customer
credentials, private data, search indexes, caches and exports need institution
boundaries enforced on every request. Source rights must cover the actual
purpose, retention and destination, including derived outputs. A subscription
does not automatically permit cross-provider redistribution or AI training.
Reuse across institutions and shared training require separate authority;
private institution data must not enter a common public corpus by default.

| Next institutional capability | Evidence needed before a present-tense sales claim |
| --- | --- |
| SSO, roles and institution isolation | Real identity integration plus failed cross-institution and revoked-access tests across retrieval, cache, search, jobs and export. |
| Existing paid subscriptions | Provider-approved adapter, customer-specific entitlement lifecycle and expiry/revocation tests; contractual rights for each purpose and destination. |
| Migration and switching | Versioned schema, source/transform lineage, row-count/hash/total reconciliation, independent destination readback and institution owner sign-off. |
| Retention, residency and exit | Documented data locations/subprocessors, tested restore, supported export/import into a second platform, and verifiable deletion subject to retention/legal holds. |
| Audit and accountable analysis | Restricted audit access, traceable changes, model/input/version records where relevant and review/approval ownership. A JSON receipt alone is not an immutable audit service. |

## Regulatory and procurement fit

These products can supply evidence for review; they do not provide regulatory
certification. Requirements depend on institution type, service classification,
data and deployment. India's current [SFB technology directions](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=13634&Mode=0)
and [NBFC technology directions](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=13592&Mode=0)
address controls including migration, data definitions and audit/access. The
NBFC Chapter V requirements apply to Middle Layer and above excluding CICs;
they are not a universal small-NBFC checklist. The [NBFC outsourcing directions](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12941&Mode=0)
address applicable outsourcing/cloud arrangements, portability and exit, while
excluding certain fintech retrieval/validation services. Classify the actual
buyer and service before asserting applicability.

For Western institutions, prepare data-flow, provider, security, continuity and
exit documentation for buyer review. The [US community-bank third-party guide](https://www.occ.treas.gov/news-issuances/bulletins/2024/bulletin-2024-11.html)
is voluntary guidance. [PRA SS2/21](https://www.bankofengland.co.uk/prudential-regulation/publication/2021/march/outsourcing-and-third-party-risk-management-ss)
has a current version and a March 2026 publication effective **18 March 2027**;
do not label the future version already effective. [DORA](https://www.eba.europa.eu/activities/direct-supervision-and-oversight/digital-operational-resilience-act/preparation-dora-application)
supports ICT third-party oversight within its scope. The [EU Data Act](https://digital-strategy.ec.europa.eu/en/factpages/data-act-explained)
addresses switching, while [GDPR](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/application-gdpr_en)
requires the applicable processing roles, purposes and instructions to be assessed.
None confers a general right to repurpose licensed financial data.

Where an analytical product is a model, use the relevant model-risk framework.
[US SR26-2](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm),
issued 17 April 2026, supersedes SR11-7; its scope excludes generative/agentic AI
and simple deterministic arithmetic. [PRA SS1/23](https://www.bankofengland.co.uk/prudential-regulation/publication/2023/may/model-risk-management-principles-for-banks-ss)
has its own firm scope. Retrieval, calculations and AI narrative should remain
distinguishable, with review and decision authority held by the institution.
Regulatory sources above were reviewed on 28 October 2026; no private control is
attested by this matrix.

## Publish one accurate offer per supported workflow

The Microsoft listing should describe the implemented funding/institution task
pane and use its actual host screenshot. Broader product routes belong in the
family catalog and relevant platform materials until their own native workflow
exists. Reuse existing publisher and application records; update an existing
submission rather than creating a duplicate to increase listing counts.

Track prepared material, submission receipt, vendor approval, accessible public
listing, successful native use, independent repeat use and paid use separately.
See [Office marketplace status](../office/marketplaces/status.json) and the
[distribution ledger](../marketplaces.json). Neither a listing nor an operator
test establishes customers, revenue or a production-ready private data platform.
