# Evaluate LiquiLens in a recurring research task

LIQUILENS PRIVATE LIMITED provides public financial-evidence tools for agent
builders, research platforms and trading research teams. Start with one useful
task, inspect its coverage, and repeat it using your existing tools. Public
research reads need no account or data API key. Platform accounts and subscriber
services have their own requirements.

Reviewed 15 October 2026. [Machine-readable evaluation paths](evaluation.json).

## Choose a task

| Team | Start here | Useful output | Connect through |
| --- | --- | --- | --- |
| AI agents and workflow builders | [USD funding review](../connect/?task=funding) | A cited observation with original dates, units and missingness | [MCP, REST, editors and native adapters](../platforms/) |
| Financial platforms, treasury and bank-risk teams | [Covered-institution review](../connect/?task=institutions) | Available disclosures and a queue of evidence gaps | [API client kit](../api/), [Python, notebooks and spreadsheets](../tools/) |
| Trading and quantitative research teams | [Indicative BTC liquidity review](../connect/?task=exit) | Supported sizes, venues, observation clocks and limits | [Research workflow guide](../agents/WORKFLOWS.md) and source-preserving exports |

Seiche supplies funding context, LiquiLens supplies covered-institution evidence,
and Undertow supplies indicative liquidity research. Their meanings and sources
remain separate. Start with one product when that is sufficient for your task.
The [dataset catalog](https://agents.seiche.info/v1/research/api/v1/datasets)
describes the wider research views, including China publication coverage and
source health. A catalog entry is not a claim of complete market coverage.

## Run and retain a first result

1. Open the task and inspect its current source status and coverage. Keep a
   missing, unavailable, restricted or stale result explicit.
2. Choose your client from the connection page. Run the bounded example before
   adding a schedule or pagination loop.
3. Retain the result together with its source URLs, observation dates, native
   units, diagnostics and the [deployed identity](https://agents.seiche.info/v1/research/api/v1/release).
4. Record whether it helped your own task and how long setup took. Report a
   reproducible integration problem with private details removed.
5. Repeat on a different day. Distinguish revised data, unchanged source data and
   a failed refresh; a new response timestamp does not renew an observation.

## Evaluate production fit

Before adopting a recurring integration, agree the exact dataset and entities,
publication cadence, allowable source age, outage behavior, quotas, support
expectations and permitted downstream use. Check
[source status](https://agents.seiche.info/v1/research/api/v1/sources) and
[the API contract](../api/openapi.json). Test how your workflow handles missing
data and service errors before increasing traffic.

The open adapter software is MIT licensed. Upstream data keeps its own rights;
redistribution and derived-data use require source-specific review. Public
availability does not grant unrestricted resale rights or a production SLA.
Research outputs do not authorize orders, provide executable quotes, guarantee
fills or establish a credit rating. The separately documented paper/execution
candidate is outside these public research evaluations.

## Measure the evaluation

Use the existing [14-day pilot scorecard](../agents/pilot-scorecard.md). With
participant consent, record first useful completion, return use on another day,
setup time, coverage blockers and the decision to continue. Count independent
organizations separately from their installations and from individuals.

Downloads, page views, anonymous calls, CI and operator checks are separate
operational measurements. Verified customer and repeat-use counts remain
unknown until supported by participant records. The scorecard's targets are
planning targets, not measured traction.

[Discuss a scoped evaluation](../support/) · [Pricing](../pricing.md) ·
[Integration and marketplace status](../marketplaces.json) · [Privacy](../privacy/)
