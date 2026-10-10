# Seiche EUR reference-FX review

Prepared from the capture at 2026-10-10T19:20:14.503085+00:00.

## Finding

The captured sample ends on **2026-10-09**. Each value below is quoted as units of the named currency per one EUR. Changes compare the last two published observations; they do not describe an executable intraday market move.

| Currency | Previous date | Previous value | Latest date | Latest value | Change in reference value |

| --- | --- | --- | --- | --- | --- |

| USD/EUR | 2026-10-08 | 1.1186 | 2026-10-09 | 1.1206 | +0.179% |

| GBP/EUR | 2026-10-08 | 0.84698 | 2026-10-09 | 0.84763 | +0.077% |

| JPY/EUR | 2026-10-08 | 177.05 | 2026-10-09 | 177.34 | +0.164% |

| INR/EUR | 2026-10-08 | 108.2635 | 2026-10-09 | 108.3965 | +0.123% |

## Research interpretation

The table answers a narrow operational question: which published reference observation is being used, in which unit, and how it differs from the preceding available date. A rate expressed per EUR must not be inverted or treated as a live broker quote without an explicit separate calculation and label.

## Source and method

Source: European Central Bank. Original reference data is available free from the ECB. Informational reference rates, not executable quotes.

Original sample-source XML: https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml

All eighty sample values were matched by date and currency to the ECB current 90-day XML. Change is calculated as (latest / previous - 1) × 100. No rounding is applied to the displayed source values. The percentage calculation is an explicitly derived comparison, not an ECB forecast.

## Limits

The source histories are current amended vintages. First historical availability is unknown; this report is not an as-of archive, a validated backtest, a forecast or a trading instruction. Missing publication dates remain absent. Browser/service retrieval time does not replace the economic observation date.

## Reproduce

Use reference-fx-sample.csv and sample-verification.json in this packet, or fetch the fixed Seiche ECBFX_USD/GBP/JPY/INR CSV endpoints. Retain source comments with every report. Recheck a new capture on the next working day; do not silently overwrite this dated evidence.

Publisher: LIQUILENS PRIVATE LIMITED. Support: mrinal@liquilens.in. Independent of the ECB; no endorsement is implied.
