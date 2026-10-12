# Connect free tools and contribute an authorised source

Start at https://agents.seiche.info/connect. Free public MCP tools do not require
an account, a task-sharing grant or permission to train on your data.

The [combined configuration](agent-mcp-config.json) includes seven product tools
and the public community. Choose the connections your workflow needs. The
community connection accepts no credentials and only reads owner-published data.

## Finance and trading operators

Use Seiche for funding context, LiquiLens for institution evidence and Undertow
for market-liquidity research. Keep source dates and missing inputs attached.
An optional workspace can share coarse task and outcome categories after its
owner enables the current participation contract. These reports are
self-reported; they do not establish trade execution or performance.

For price-arbitrage research, distinguish a quoted price gap from an executable
opportunity. A useful source contribution includes quote time, venue, product,
currency, size, fees and what remains unknown. Keep paper and live outcomes
separate. The free tools do not place orders.

## Shopping and service-commerce operators

Wake accepts events from a specifically enrolled source. Review the
[current event schema](https://agents.seiche.info/commerce/v1/schema) and
[public release policy](https://agents.seiche.info/commerce/v1/public/policy).
An agent workspace key is not a commerce source credential.

Before enrollment, prepare a source brief with:

- The organisation and source system you control, plus the exact permitted use.
- One domain: physical goods or digital services; evaluate them separately.
- The event types you can attest: quote, checkout, fulfillment, settlement,
  cancellation or refund. Observer, merchant and payment authorities differ.
- Source-local opaque agent/journey identifiers and the evidence supporting
  their attribution. Public wallet activity alone does not establish an AI buyer.
- Retention, expiry, withdrawal and independent collection, training and
  aggregate-resale permissions. Keep personal details, prompts, passwords and
  payment credentials out of contributed payloads.

Send the brief through the existing [company contact](../support/). The operator
reviews the source and assigns its scoped signing capability. A pending brief
does not enroll a contributor. Do not transmit data before that review.

The hosted ingestion endpoint is
`https://agents.seiche.info/commerce/v1/events`. The existing SDK signs the exact
request body and uses an immutable event ID with its durable outbox. Source
secrets stay in the contributor's backend. Retries reuse the event body and ID;
they never replay a purchase.

The current institutional export gate requires at least 20 agents and three
independently reviewed contributors, with no contributor exceeding 50% of a
closed weekly cohort. A contributor needs a reviewed aggregate-resale grant.
Collection or training consent alone cannot satisfy that requirement.

## What the discovery monitor records

The [daily observation workflow](https://github.com/beepboop2025/financial-evidence-skills/actions/workflows/agent-distribution.yml)
checks the curated source directory, public listing pages and bounded public
GitHub/MCP searches. Reports include source URLs, dates, hashes, unavailable
sources and comparison limits. Reports are retained for 30 days; the next run
compares with the previous successfully produced report where observations are
compatible. External failures stay visible and do not establish disappearance.

Project metadata is an acquisition lead. It is not a deployed agent, a consenting
contributor, a purchase record or adoption evidence. Global coverage remains
unknown. The monitor never changes marketplace states automatically.
