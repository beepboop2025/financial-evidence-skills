# Undertow service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Indicative BTC size comparison

Use Undertow to compare indicative BTC exits for $10,000 and $100,000. Include venue coverage and timestamp limits; do not trade.

Tools: `crypto_exit_check`

Expected interpretation: Request sizes_usd [10000,100000], preserve unavailable estimates and distinguish indicative exit evidence from executable quotes.

Captured 2026-10-28T14:35:41.875187+00:00 — `crypto_exit_check({"sizes_usd": [10000, 100000]})`

## 2. Liquidity tiers

Show Undertow's liquidity tiers and explain their coverage and evidence limits.

Tools: `liquidity_tiers`

Expected interpretation: Retrieve the published tiers with definitions, dates and source scope; do not convert tiers into a guarantee of execution.

Captured 2026-10-28T14:35:41.970685+00:00 — `liquidity_tiers({})`

## 3. Depth episodes

Use Undertow to summarize depth episodes for a liquidity research note.

Tools: `depth_episodes`

Expected interpretation: Return bounded available episodes and source timestamps, flag missing coverage and avoid representing historical episodes as current depth.

Captured 2026-10-28T14:35:42.145187+00:00 — `depth_episodes({})`

## 4. Venue concentration

Review Undertow's venue concentration evidence and list risks an analyst should investigate.

Tools: `venue_concentration`

Expected interpretation: Report the observed venue coverage and concentration measures with units, dates and limitations; do not infer unsupported private positions.

Captured 2026-10-28T14:35:42.307707+00:00 — `venue_concentration({})`

## 5. Venue price reconciliation

Use Undertow to reconcile public venue-price evidence and flag unresolved differences.

Tools: `venue_price_reconciliation`

Expected interpretation: Keep venue timestamps and units distinct, preserve discrepancies and unavailable prices, and avoid creating a consolidated executable quote.

Captured 2026-10-28T14:35:42.470655+00:00 — `venue_price_reconciliation({})`
