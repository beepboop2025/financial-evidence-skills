# USD funding review checks

This source utility compares captured Seiche evidence before a research review.
It detects missing required observations, changed units, old or future clocks,
explicit publication restrictions, and disagreement about SOFR across the USD
desk, global atlas and source-health surface.

It does not produce a funding-risk score or certify the service for institutional
use. A passing result covers the checks in `usd-funding-review-checks.v2` only.

## Inputs and reproducible use

Capture these public surfaces close together, retaining each original response
and acquisition time. Label operator probes as synthetic in your own usage
measurement. Do not replace source clocks with the time of capture.

| Local input | Public source | Required shape |
|---|---|---|
| `desk.json` | `https://api.seiche.info/mcp`, tool `money_market_context`, arguments `{"section":"all"}` | Decoded tool payload, schema `seiche.money-market-desk.v1`; not the outer JSON-RPC envelope |
| `atlas.json` | `https://api.seiche.info/api/v2/money-markets` | Original JSON object |
| `health.json` | `https://api.seiche.info/api/health` | Original JSON object |

From this repository, with Python 3.10 or newer:

```bash
python scripts/check_funding_review.py \
  --desk desk.json --atlas atlas.json --health health.json \
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

## Policy v2

Required inputs are SOFR, EFFR, IORB, SOFR P99 and volume, reserves, TGA, ON RRP
and SRF use. Every required value must have its expected native unit and cadence,
a source label, an observation date and publisher-reported `fresh` state. A real
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
