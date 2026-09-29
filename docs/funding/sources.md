# Source attribution and transformations

Updated 29 September 2026. Publisher terms remain attached to the data; the
repository's MIT software license does not grant new rights to those data.
This page describes this nine-input original-publisher packet, not every source
in the wider LiquiLens family.

## Federal Reserve Bank of New York

Copyright 2026 Federal Reserve Bank of New York. Content from the New York Fed
subject to the [Terms of Use](https://www.newyorkfed.org/privacy/termsofuse).
SOFR, EFFR and operation results are subject to those Terms of Use. The New York
Fed is not responsible for publication of these data by Liquidity Lab, does not
sanction or endorse this republication, and has no liability for your use.
Liquidity Lab is not affiliated with the New York Fed. The SOFR terms also
address DTCC Solutions LLC data used by the publisher; no ownership of that
underlying data is claimed here.

We retrieve rate and overnight operation results from the original Markets API.
Rate values, the SOFR 99th percentile and SOFR volume retain source precision.
Accepted overnight operation amounts are converted from USD to USD billions.
Morning and afternoon standing-repo results are summed only when both results
are present. A zero is published only when the original result is exactly zero.
These transformations, selections and crosschecks are Liquidity Lab's work.
Keep publisher attribution, notices, links and applicable permissions when
reusing these data; do not imply publisher endorsement.

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
