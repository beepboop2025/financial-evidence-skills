# Financial Evidence Research Desk: platform evaluation brief

Prepared 7 October 2026 by **LIQUILENS PRIVATE LIMITED**, operating the
LiquiLens product family. This is a proposal for evaluation, not a statement
of vendor acceptance, certified data rights or institutional adoption.

## The proposed workflow

A treasury, bank-risk or market-liquidity analyst starts a review with three
questions: what changed in funding, what does a covered institution disclose,
and what does the market-liquidity evidence show? The Research Desk brings
these separately scoped results into a repeatable API, notebook or desktop
workflow. Each result retains native units, observation and retrieval clocks,
source links, hashes, diagnostics, missing values and rights labels.

LiquiLens supplies covered-bank evidence; Seiche supplies funding and capital
markets; Undertow supplies market-liquidity context. The China dataset route
currently reports restricted or unavailable evidence; it is not counted as
usable China data. Results are not collapsed into one score.
The product does not execute trades or make lending decisions.

## Evaluate now

- [API client kit](../api/): twelve bounded requests for seven datasets,
  Postman, Bruno, OpenAPI/Insomnia and HTTP-client imports.
- [Research toolkit](../tools/): complete captures for Python, notebooks,
  OpenBB, Excel/Power Query and research agents.
- Hosted REST: `https://api.seiche.info/openbb`.
- Hosted MCP: `https://api.seiche.info/openbb/mcp`.
- [Release identity](https://api.seiche.info/openbb/api/v1/release) and
  [current source status](https://api.seiche.info/openbb/api/v1/sources).
- [FDC3 reference application](../integrations/fdc3/evidence-inspector/).
- [Source, tests and release history](https://github.com/beepboop2025/financial-evidence-skills).
- [Dated source review](source-review-2026-10-07.json): nine source routes,
  source-reported clocks and states, content hashes, and unresolved rights.

The 7 October client run retrieved all nine source routes successfully.
The money-market table returned 19 rows with pagination; its upstream atlas
still reported `PARTIAL`. Those rows are not a claim of 19 fully covered,
fresh markets. A successful transport check does not resolve source gaps.
The source-health response did not establish redistribution approval for
any route. This dated inventory is an evaluation aid, not a rights clearance.

Free public research access does not grant resale of underlying third-party
data. A source-by-source rights review must precede a distribution agreement.
The code license, API response, and external-data permissions are distinct.

## Platform-specific proposals

| Platform | Proposed evaluation | Gate to wider distribution |
| --- | --- | --- |
| Bloomberg App Portal / BQuant | Test the read-only HTML research workflow or portable notebook with an entitled development sponsor; evaluate source-linked context beside an analyst's existing workflow. | Current developer admission, entitled environment, native identity/workflow testing and Bloomberg QA. No native Bloomberg test has been completed. |
| LSEG Workspace / partner network | Evaluate a content or solution partnership for cited funding and covered-bank evidence. Start with the public API and a bounded analyst task. | LSEG determines the supported integration route and commercial/content terms. Historical Eikon App Studio instructions are not assumed to apply to Workspace. |
| FactSet Marketplace | Review a sample schema, source-specific rights matrix and client-import workflow for an external-data or solution listing. | Provider screening, suitable delivery contract and vendor approval. |
| Nasdaq Data Link | Assess whether specific lawful derived research datasets add useful coverage for an identified customer need. | Dataset differentiation, provider diligence, rights and delivery agreement. A wrapper over public sources alone is not the proposed data advantage. |
| Reuters Connect | Consider only original research/content whose rights support licensing and whose format fits the editorial marketplace. | Separate editorial/content partner review. This is not a financial-terminal application listing route. |
| Snowflake / Databricks / AWS Data Exchange | Evaluate schema-preserving delivery of an explicitly approved dataset, with sample data and update cadence. | Destination artifact, provider account, costs and rights approval. No dataset has been uploaded or licensed through these channels by this brief. |

## A proposed 14-day analyst evaluation

These are evaluation targets, not achieved customer counts.

1. Recruit ten consenting analysts across three organizations. Record a chosen
   task, onboarding channel and permission to follow up; keep identities private.
2. On day one, have each analyst produce one source-cited result in an existing
   tool without the operator doing the task for them. Record completion and
   elapsed time, including errors and abandoned attempts.
3. On a later day, observe a second useful task. On day seven, measure retained
   use within the original eligible cohort. Keep all verification, crawler and
   operator traffic outside the external-user count.
4. Ask which workflow they would keep using, what evidence is missing, and
   whether they will sponsor an integration or a paid pilot. A stated interest,
   signed pilot agreement and received payment are separate milestones.
5. Present task completion, repeat use, retention, source failures, data rights,
   response times and a reproducible capture to the platform reviewer. Report
   numerator, denominator, time window and unknowns for every rate.

Proposed success threshold: at least seven of ten analysts finish a task,
five return for a second useful task, and two organizations request continued
evaluation. These thresholds are internal decision criteria, not platform
requirements or a guarantee of approval.

## What a platform reviewer still needs

Named support contacts and commitments; a source-by-source redistribution
matrix; the selected dataset's actual observation cadence and missingness;
security and privacy review; a firm-approved native integration test; and
evidence of useful independent demand. We do not claim an SLA, SOC 2 report,
full-market coverage, real-time exchange entitlements or verified paid traction.

## Official route references

- [Bloomberg App Portal developer journey](https://assets.bbhub.io/professional/sites/10/App-Portal-Overview-for-Developers.pdf), a 2022 document: confirm the current admission process with Bloomberg.
- [LSEG partnerships](https://www.lseg.com/en/about-us/business-partnerships-marketplace/partners-portal) and [financial-data contributions](https://www.lseg.com/en/data-analytics/market-data/contribute-financial-data).
- [FactSet provider screening and delivery overview](https://go.factset.com/hubfs/Website/Resources%20Section/Brochures/benefits-of-becoming-an-open-factset-marketplace-partner-brochure.pdf), historical brochure: confirm current requirements.
- [Nasdaq alternative-data partnership](https://www.nasdaq.com/products/data/alternative).
- [Reuters Connect marketplace](https://www.reutersconnect.com/about-us).

No vendor inquiry, contract, financial commitment or endorsement is implied by
this public brief. [Contact and support](../support/).
