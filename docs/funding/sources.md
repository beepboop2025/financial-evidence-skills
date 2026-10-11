# Source attribution and transformations

Updated 11 October 2026 (publisher identity and notice wording). Publisher terms remain attached to the data; the
repository's MIT software license does not grant new rights to those data.
This page describes this nine-input original-publisher packet, not every source
in the wider LiquiLens family.

## Federal Reserve Bank of New York

© 2026 Federal Reserve Bank of New York. Content from the New York Fed subject
to the Terms of Use at newyorkfed.org.

The SOFR and EFFR reference-rate data, including SOFR percentile and volume data,
is subject to the Terms of Use posted at newyorkfed.org. The New York Fed is not
responsible for publication of the SOFR and EFFR reference-rate data by
LIQUILENS PRIVATE LIMITED, does not sanction or endorse any particular
republication, and has no liability for your use.

LIQUILENS PRIVATE LIMITED is not affiliated with the New York Fed. The New York
Fed does not sanction, endorse, or recommend any products or services offered
by LIQUILENS PRIVATE LIMITED.

The publisher's SOFR/BGCR notice follows; this packet uses SOFR, not BGCR:

The Secured Overnight Financing Rate (SOFR) Data and Broad General Collateral
Rate (BGCR) Data are calculated using data provided under a license granted to
the New York Fed by DTCC Solutions LLC (“Solutions”), an affiliate of The
Depository Trust & Clearing Corporation. Solutions, its affiliates, and third
parties from which they obtained data have no liability for the content of this
material.

These notices follow the Conditions and Reference Rates sections of the
[Terms of Use](https://www.newyorkfed.org/privacy/termsofuse), checked 11 October
2026. No ownership of underlying transaction data is claimed. Preserve the same
source permissions, conditions and restrictions when redistributing the data.
Original sources are available without charge: [Secured Overnight Financing
Rate Data](https://www.newyorkfed.org/markets/reference-rates/sofr),
[Effective Federal Funds Rate](https://www.newyorkfed.org/markets/reference-rates/effr)
and [Markets API](https://markets.newyorkfed.org/static/docs/markets-api.html).

We retrieve rate and overnight operation results from the original Markets API.
Rate values, the SOFR 99th percentile and SOFR volume retain source precision.
Accepted overnight operation amounts are converted from USD to USD billions.
Morning and afternoon standing-repo results are summed only when both results
are present. A zero is published only when the original result is exactly zero.
These transformations, selections and crosschecks are the work of
LIQUILENS PRIVATE LIMITED (LiquiLens / Seiche).
Keep publisher attribution, notices, links and applicable permissions when
reusing these data; do not imply publisher endorsement.

Retained historical packets may carry an earlier source-notice summary naming
Liquidity Lab. Their observation values, edition times and archived hashes have
not been rewritten. Accompany republication with the current notices above and
the dated caption supplied for the edition.

## Federal Reserve Board

IORB comes from the Board's PRATES daily RESBM_N.D series. Reserve balances come
from the weekly-average column of H.4.1, not its Wednesday-level column. We
convert USD millions to USD billions without display rounding. See the
[Board's copyright and disclaimer](https://www.federalreserve.gov/disclaimer.htm).
Board publication does not imply endorsement of this service.

## US Treasury

The Daily Treasury Statement operating-cash-balance dataset supplies the
Treasury General Account **opening** balance. We select the exact account type
and observation date and convert USD millions to USD billions. See
[Fiscal Data](https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/operating-cash-balance)
and its [about and data policy information](https://fiscaldata.treasury.gov/about-us/).
The value is not a closing balance or an intraday cash estimate.

## Acquisition and review boundaries

Each packet includes the original source URLs, response hashes, retrieval
clocks and field lineage. The pinned Workspace review supplies a reference
horizon and release/readiness metadata. Original-publisher values are fetched
independently and compared with that reference within its two-decimal display
precision. For example, USD 1 million of repo usage stays USD 0.001 billion
in the packet even if the reference screen displays 0.00. Missing source values
are never replaced with a reference value or with zero. FRED-derived reference
bodies are not retained in this new archive.

Packets align SOFR and IORB to a common horizon. Every input retains its own
observation date and a flag when the acquired publisher document contains a
newer date. Retrieval time is not publication time. The service's forward
archive begins at first verification; it does not reconstruct pre-launch
knowledge or claim complete publisher revision histories.

[Dataset contract](contract.json) · [Public funding review](./)
