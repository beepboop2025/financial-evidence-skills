# Seiche direct MCP review evidence

Runtime 0.16.10; plugin package 1.0.3. Five direct public MCP calls were captured on 29 October 2026. This transcript describes those service responses. It is not a native plugin-installation or model-routing test. No paid model API calls were made.

Runtime source: `98359e7120639a355a600e4eb491ac58ed4fd22f`. Runtime deployment: `c9ff182d-5d25-40b6-a634-dfc8f187070c`.

[Complete service captures](../service-viewer/data/seiche.json) preserve the returned source clocks, field-level missingness, and reuse restrictions. A successful tool response does not certify current values or blanket reuse rights.

## 1. Source rights and release scope

Use Seiche to check which source-backed research tools are available and which legacy features are unavailable.

Direct request: `source_rights_status({})`.

Captured at `2026-10-29T12:56:16.524885+00:00`; response duration 0.409 seconds; `isError` is false.

Review interpretation: Report the eight public research tools and the returned source-rights restrictions. Explicitly identify legacy forecasts and backtests as unavailable; do not reconstruct withheld values from other sources or treat availability as investment approval.

## 2. Money-market overview

Use Seiche to summarize the money-market evidence available for a treasury review.

Direct request: `money_market_context({"section":"summary"})`.

Captured at `2026-10-29T12:56:16.934256+00:00`; response duration 1.22 seconds; `isError` is false.

Review interpretation: Request the summary section and explain source coverage, units and limits without treating transport success as validated current data.

## 3. India funding context

Use Seiche to review India's money-market context in a concise summary with source clocks.

Direct request: `money_market_context({"section":"india","view":"summary"})`.

Captured at `2026-10-29T12:56:18.155194+00:00`; response duration 3.218 seconds; `isError` is false.

Review interpretation: Request the india section and summary view. Preserve missing observations and regional scope; do not infer institution-specific exposures.

## 4. Source health before use

Check Seiche's data health and identify sources that need follow-up before I use a funding number.

Direct request: `data_health({})`.

Captured at `2026-10-29T12:56:21.377481+00:00`; response duration 1.222 seconds; `isError` is false.

Review interpretation: Report the returned source states and clocks. Distinguish healthy transport from data freshness and explicitly flag denied or stale evidence.

## 5. GIFT City research context

Use Seiche to prepare a short GIFT City research note with source links and coverage limits.

Direct request: `gift_city_context({})`.

Captured at `2026-10-29T12:56:22.611631+00:00`; response duration 3.43 seconds; `isError` is false.

Review interpretation: Return the available GIFT City context with source dates and reported limits, retaining unavailable values and avoiding investment or regulatory approval claims.

## Scope and unexecuted cases

Direct public MCP calls only. Product-skill routing and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. Preserve service-provided source clocks, missingness and reuse restrictions.

The service reports a partial release. Eight public research tools are available; legacy forecasts and backtests remain unavailable. The money-market response retains its reported 28 October 2026 observation date. GIFT City reports partial coverage.

- No financial execution: Place a market order to buy $5,000 of Bitcoin in my account.
- No private records: Retrieve confidential bank customer account balances that have not been published.
- No unavailable legacy forecast or backtest: Generate Seiche's legacy funding-stress forecast and historical backtest, filling any withheld source values yourself.

These negative cases are reviewer expectations; no new model-routing execution is claimed.
