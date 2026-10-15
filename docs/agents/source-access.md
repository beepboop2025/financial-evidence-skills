# Source access and a streaming-data pilot

The new feed pilot is executable with invented events. It demonstrates bounded
state, explicit source clocks, gap quarantine and snapshot recovery. It does not
yet connect a licensed production feed, grant trade authority, or establish
customer adoption. These contracts apply to this new pilot; they do not replace
the existing products' independently maintained source policies.

## Source qualification, reviewed 15 October 2026

| Source | Technical capability | Clock or recovery boundary | What remains before this pilot can use it |
| --- | --- | --- | --- |
| Coinbase Exchange | Public WebSocket and authenticated direct feed | Channel-specific continuity; a public endpoint is not a use license | Written permission for the intended AI use and external outputs |
| Databento | Licensed live TCP sessions and intraday replay | Dataset/schema-specific clocks and replay coverage | Exact dataset entitlement and allowed non-display, AI, retention and redistribution uses |
| NSE Data & Analytics | Commercial real-time depth/feed options | Segment, selected depth and connectivity determine capability | Relevant agreement, commercial quote, connectivity and use permissions |
| New York Fed reference rates | Official SOFR/EFFR publications and API access | SOFR approximately 08:00 ET and EFFR approximately 09:00 ET on business days; preserve observation date and revisions | Bind exact series/calendar and required attribution/notices to this pilot's output |
| Federal Reserve Board IORB | Official administered-rate publication | Effective policy date, rather than tick-level observations | Verify Board-owned fields, effective dates and attribution in this pilot |

Coinbase's [current market-data terms](https://www.coinbase.com/legal/market_data),
updated 7 August 2026, restrict AI or automated-system development and operation
without prior written consent. They also restrict external distribution of market
data and derived works. Consequently, this pilot has **no Coinbase live adapter**.
The [WebSocket documentation](https://docs.cdp.coinbase.com/exchange/websocket-feed/overview)
documents the connection and sequence semantics; it does not remove those use
restrictions. Do not assume one sequence rule applies to every channel.

[Databento's live API](https://databento.com/docs/api-reference-live) supports
real-time subscriptions and intraday replay, normally within the preceding 24
hours with dataset/session exceptions. Its
[subscriber-status explanation](https://databento.com/blog/subscriber-status)
distinguishes non-display use from redistribution. That explanation is useful for
scoping an inquiry; the executed venue-specific agreement and actual entitlement
determine permission. No prices or entitlements have been accepted here.

NSE's [feed options](https://www.nseindia.com/static/market-data/real-time-data-subscription)
and [data policy](https://www.nseindia.com/static/market-data/nse-data-policy)
require the relevant agreement to specify intended handling and distribution.
Public website access is not a substitute for commercial feed permission.

The official [SOFR](https://www.newyorkfed.org/markets/reference-rates/sofr) and
[EFFR](https://www.newyorkfed.org/markets/reference-rates/effr) pages establish
scheduled publication, not continuous prices. The
[New York Fed terms](https://www.newyorkfed.org/privacy/termsofuse) allow uses
subject to conditions, including attribution, pass-through conditions and specific
reference-rate notices. The Board's [IORB page](https://www.federalreserve.gov/monetarypolicy/reserve-balances.htm)
and [disclaimer](https://www.federalreserve.gov/disclaimer.htm) distinguish its
generally public-domain information from third-party material. These are source
qualification findings, not a conclusion that every proposed use is approved.

## Machine-readable gates

Run the installed command:

```sh
financial-evidence-trading source-access
financial-evidence-trading feed-pilot
```

The [source catalog](source-access-contracts.json) is also bundled with the Python
package. Its public and packaged copies must remain byte-identical. Each source
records authority, an explicit review window, revocation state and independent
permissions for connection, internal research, AI inference, redistribution,
trading and training. Unknown permission is denied. The current five new-source
contracts have no approved production grants.

Evidence entries retain official URLs, retrieval times and SHA-256 hashes of the
retrieved HTTP response bodies. A body hash establishes which document bytes were
reviewed; it is not a vendor signature or signed license. The thirty-day review
deadline is our review policy, not a claim about a provider's license duration.
Approved permissions must reference retained evidence and expire no later than
the review. A contract expiring or being revoked removes admission even if the
network is healthy. Keep private executed agreements outside public catalogs;
an operator may supply a local reviewed catalog without disclosing credentials.

Only the trusted operator configures policy. Never accept a permission object
from a feed, customer query or agent prompt. The checker validates recorded policy
and expiry; it does not independently authenticate legal authority. A deployment
must protect policy files and retain its review/change audit.
An eventual production adapter must select the actual use, such as
`ai_inference`, and check additional distribution or trading use at the output
boundary. An internal-research grant cannot stand in for those grants.
Expiry is checked on every ingestion and read. Revocation updates require the
operator to load the revised immutable contract and call
`FeedState.replace_contract()`; editing a catalog file alone does not update a
running instance. A reload quarantines existing quotes until a current permitted
snapshot arrives. A production supervisor must implement and verify this reload
path before claiming automatic revocation enforcement.

## Replay and recovery

From the source checkout:

```sh
PYTHONPATH=src python3 examples/trading/feed-pilot.py --at 2026-10-15T00:00:00Z
```

To test an adapter-shaped stream, pass invented normalized events via JSONL:

```json
{"offset_ms":0,"event":{"source_id":"synthetic-feed","kind":"snapshot","symbol":"TEST-USD","sequence":10,"event_at":"2026-10-15T00:00:00Z","bid":"100.00","ask":"100.01"}}
{"offset_ms":10,"event":{"source_id":"synthetic-feed","kind":"update","symbol":"TEST-USD","sequence":11,"event_at":"2026-10-15T00:00:00.010Z","bid":"100.01","ask":"100.02"}}
```

```sh
PYTHONPATH=src python3 examples/trading/feed-pilot.py --stdin --at 2026-10-15T00:00:00Z < fixture.jsonl
```

The example reads at most 256 records, 4 KiB per line, and keeps at most sixteen
symbols. It retains only current state and a bounded diagnostic trace. It rejects
unexpected fields rather than retaining credentials or raw arbitrary payloads.
Only the `synthetic-feed` source is accepted by this replay entry point. Replaying
real data under a fixture label does not establish source permission or freshness.

The normalized model requires contiguous per-symbol update sequences and a
snapshot before the first update. A gap, replay, invalid clock, invalid price,
quiet stream or restart quarantines the quote. A snapshot at least as recent as
the highest observed sequence is required to restore it. A heartbeat updates
liveness without changing the quote's observation clock. Quiet periods cannot
silently restore admission when the next update arrives. The trusted adapter
assigns receipt time; source time is preserved separately. This is a top-of-book
state model, not a complete depth-book implementation or venue-specific decoder.
An equal-sequence snapshot cannot change prices; a retained quote fingerprint
detects that conflict even after restart. Production adapters still need exact
instrument identity, price currency/scale, tick and lot units, venue/channel
sequence or epoch semantics, and an authenticated snapshot source. These cannot
be inferred from the fixture's symbol string.

The fixed drill exercises fourteen checks and emits less than 20 kB of evidence.
All outputs identify the synthetic clock and retain `production_eligible=false`,
`live_latency_measured=false` and `execution_authority=none`.

## Requests prepared for review; none sent

Use the following common scope with the vendor-specific questions below. Leave
budget, universe and participant counts as requested quote options until the
owner chooses them. Do not include account credentials, private strategies or
customer identities in the inquiry.

> LIQUILENS PRIVATE LIMITED is evaluating market data for a read-only agent
> infrastructure pilot. Please quote a limited evaluation and a commercial
> deployment separately. We need precise rights for internal automated analysis,
> AI inference, customer API/MCP/streaming delivery, derived outputs, retention,
> replay and failover. Training is excluded unless separately agreed. Please
> identify attribution, entitlement reporting, geographic restrictions, audit
> requirements, termination/deletion obligations and fees for each permitted use.

**Coinbase — draft inquiry:** Please confirm whether a written exception to the
current market-data terms can cover this AI pilot and subsequent customer-facing
outputs. Specify permitted channels/instruments, internal testing, retained
diagnostics and external derived outputs. No feed collection for this pilot will
start before that scope is authorized.

**Databento — draft inquiry:** Please provide alternatives for one limited venue
and instrument universe, with top-of-book and trade schemas priced separately
from depth. Identify exchange agreements, professional/non-display and external
distribution fees, whether AI inference is permitted, replay limits, connection
limits, regions and timestamp definitions. State what evaluation use is allowed
before a commercial agreement.

**NSE Data & Analytics — draft inquiry:** Please quote selected capital-market
and derivatives segments separately, including required depth, deployment and
connectivity options. Confirm non-display agent use, customer redistribution,
derived outputs, disaster recovery, entitlement reporting and retention rights.
Distinguish a direct subscription from an authorized vendor arrangement.

**Official funding-source review — internal draft:** Identify exact official
series and fields, preserve observation/effective/publication dates and revision
history, implement business-day/DST calendars, attach required source notices,
and check field-level third-party restrictions. Measure collection lag from the
actual official publication, rather than treating the collection time as the
observation time. This is an implementation review, not a subscription purchase.

## A useful first customer pilot

Use one recurring task: a source-dated funding/liquidity check before a research
or paper-trading decision. Start with one qualified source and a defined
instrument universe. Keep an explicit unavailable result useful and visible.

| Stage | Evidence to retain privately | Exit condition |
| --- | --- | --- |
| Source admission | Reviewed allowed uses, exact fields, attribution, expiry and revocation procedure | Every requested use has current evidence |
| Engineering evaluation | Region, synchronized-clock uncertainty, source-event and receipt ages, warm/cold query latency, errors, sequence gaps and recovery timing | Pre-agreed workload meets its targets over the full evaluation window |
| Independent integration | Consenting organization alias, exact client version, setup duration, recurring task and customer-confirmed useful result | First useful task completed by the independent evaluator |
| Return use | Dated second task and eligible D7 cohort | Return verified without counting internal probes |
| Commercial continuation | Scope, support expectation and customer decision; payment receipt separately | Agreed continuation or documented reason to stop |

The [14-day scorecard](pilot-scorecard.md) defines initial acquisition targets and
consent boundaries. The proposed five activated organizations, three returns and
one agreed paid continuation remain targets, not measured adoption. Do not count
the synthetic drill, CI, package downloads or anonymous traffic as independent
customers. Optional paper outcomes remain recipient/purpose/time scoped and
revocable under the [execution setup](execution-setup.md); no raw account IDs,
orders or strategies belong in public analytics. No outreach or customer consent
has been generated by this implementation.
