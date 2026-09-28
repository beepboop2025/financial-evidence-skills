# USD funding review checks

This source utility compares captured Seiche evidence before a research review.
It detects missing required observations, changed units, old or future clocks,
explicit publication restrictions, and disagreement about SOFR across the USD
desk, global atlas and source-health surface.

It does not produce a funding-risk score or certify the service for institutional
use. A passing result covers the checks in `usd-funding-review-checks.v3` only.

## Inputs and reproducible use

Capture these public surfaces close together, retaining each original response
and acquisition time. Label operator probes as synthetic in your own usage
measurement. Do not replace source clocks with the time of capture.

| Local input | Public source | Required shape |
|---|---|---|
| `desk.json` | `https://api.seiche.info/mcp`, tool `money_market_context`, arguments `{"section":"all"}` | Decoded tool payload, schema `seiche.money-market-desk.v1`; not the outer JSON-RPC envelope |
| `atlas.json` | `https://api.seiche.info/api/v2/money-markets` | Original JSON object |
| `health.json` | `https://api.seiche.info/api/health` | Original JSON object |
| `desk-history.json` | `https://api.seiche.info/api/money-markets` | Full USD desk snapshot with dated charts; must match the MCP snapshot and observations |

From this repository, with Python 3.10 or newer:

```bash
python scripts/check_funding_review.py \
  --desk desk.json --atlas atlas.json --health health.json \
  --desk-history desk-history.json \
  --evaluated-at 2026-09-28T19:17:16Z > review.json
```

Supply the actual review timestamp explicitly. Reusing the historical example
timestamp is appropriate only when reproducing a historical captured review.
The script uses no network, credentials, scheduler, or external notification.
Files are bounded to 2 MiB each. The output hashes the exact local input bytes.

| Exit | Meaning |
|---|---|
| 0 | These bounded checks passed. |
| 1 | Review needs attention; inspect `issues`. |
| 2 | Input or policy argument could not be evaluated. |

## Policy v3

Required inputs are SOFR, EFFR, IORB, SOFR P99 and volume, reserves, TGA, ON RRP
and SRF use. Every required value must have its expected native unit and cadence,
a source label, an observation date and an accepted freshness assessment. A real
zero remains valid. Missing or malformed values never become zero.

Snapshot age defaults to 900 seconds, independently of observation age. This is
an operator-selected acceptance threshold, not an advertised service SLA. A
snapshot more than 300 seconds into the future requires attention. Daily and
weekly observations additionally have calendar-day backstops of four and ten
days. These backstops do not implement the NY Fed or other official publication
calendars. For TGA, a complete `treasury-dts-next-business-day-v1` publication
schedule can explain a longer interval over holidays: the expected observation
date must be covered, its latest due time cannot be in the future, and the count
of missed publication opportunities must be zero. Invalid or missed schedules
require attention. This recognizes Seiche's Treasury schedule; it does not
independently certify all publishers' calendars or create a contractual SLA.

Policy v3 reconciles SOFR, EFFR, SOFR P99 and SOFR volume with their own atlas
instruments. Dates and values must match, including the explicit USD-million to
USD-billion volume conversion. Each row must be available, unrestricted and
reported FRESH with zero missed releases. Its next publication deadline must
exactly match the independently reviewed 2026 NY Fed calendar and remain ahead
of evaluation. This can explain an `aging` desk label through midnight or a
holiday; it cannot excuse `stale`, `unknown`, a mismatched distribution, or a
missed release. The original label is preserved in CSV and in the report's
`freshness_assessments`, alongside the accepted basis and deadline.

The reviewed calendar follows the [NY Fed holiday schedule](https://www.newyorkfed.org/aboutthefed/holiday_schedule)
and [reference-rate publication methodology](https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates),
including distinct SOFR closures on [April 3](https://www.newyorkfed.org/markets/opolicy/operating_policy_260312a)
and [July 3](https://www.newyorkfed.org/markets/opolicy/operating_policy_260618a),
2026, when EFFR continues. It accepts only 2026 observation dates, with a limited
January 2027 calculation bridge. Review and version the calendar before accepting
2027 observations. A source-calendar disagreement remains an exception; this
consumer does not repair or silently replace the upstream calendar. IORB, ON RRP
and SRF have no such exception based on an inferred deadline. Original captures
must be replayed with their original policy and calendar fingerprints.

The USD desk intentionally clips inputs to its latest common SOFR-IORB date.
The review therefore exports `review_asof`, `review_scope`, and
`latest_per_instrument=false` on every CSV row as well as in REST/MCP. A ready
common-horizon review establishes the stated dated assessment; individual
instruments may already have newer observations. `canonical_latest_asof` and
`newer_observation_available` retain reported atlas/health dates, with unknown
values left explicit. They do not supply or infer a newer numeric value.

For this explicit scope, IORB, ON RRP and SRF may retain an `aging` label only
when their own dated values match the corresponding history points, the full
REST and MCP snapshots agree, the common SOFR-IORB history intersection is
current, and the SOFR/EFFR publication clocks pass. No older-than-horizon,
restricted, stale or unknown observation is excused. Missing charts or ambiguous
history require attention. The REST history is an additional fixed public GET;
the scheduled capture still uses one upstream MCP funding-tool call.

SOFR is compared between the desk policy ladder, desk secured distribution, and
atlas US-USD benchmark. Different observation dates require attention; values
are compared only when observation dates and units agree. The source-health SOFR
date must also agree. A positive count of missed publication opportunities cannot
be overridden by a publisher's `FRESH` label. Weekly reserves and daily TGA are
not forced onto the same date.

The report retains publisher coverage as context; high overall coverage never
excuses a missing required input. Retired or auxiliary health series do not make
an otherwise complete USD review fail merely because they are old.

## Observed acceptance failure

At 2026-09-28 19:17 UTC, a captured live run required attention for three reasons:

- The required TGA input was reported `aging`.
- The atlas US-USD benchmark reported two missed publication opportunities.
- Atlas SOFR was dated September 24, while both desk SOFR observations were dated
  September 25.

The utility exposes this discrepancy; it does not repair the upstream collector,
choose a substitute source, or rewrite an old observation. A new capture may
produce a different result. This single probe establishes neither uptime nor
external customer adoption.
