# Seiche reference-FX coverage and vintage review

Prepared from the capture at 2026-10-10T19:20:14.503085+00:00.

## Finding

The evaluation sample contains four currencies and twenty published observations per currency. All eighty values matched the ECB source in this capture. This validates the selected sample and its transformation; it does not validate complete history, scheduled recurrence or independent adoption.

| Series | Retained-history rows | First retained date | Last retained date | Checked sample |

| --- | --- | --- | --- | --- |

| ECBFX_USD | 7111 | 1999-01-04 | 2026-10-09 | 20/20 |

| ECBFX_GBP | 7111 | 1999-01-04 | 2026-10-09 | 20/20 |

| ECBFX_JPY | 7111 | 1999-01-04 | 2026-10-09 | 20/20 |

| ECBFX_INR | 4551 | 2009-01-02 | 2026-10-09 | 20/20 |

## Why the clocks matter

observation_date identifies the reference date; source_retrieved_at records Seiche collection; sample_captured_at records this evaluator capture. first_available_at is null because the original historical release time has not been reconstructed. These clocks cannot be substituted for each other.

## Missingness and revisions

Non-publication days remain absent. A missing observation is not zero and is not forward-filled. A current upstream revision can change a historical row. A model claiming historical knowledge must use an independently verified vintage archive; this sample does not provide one.

## Dataset acceptance decision

The sample is suitable for schema, attribution, unit and current-observation evaluation. Native warehouse sharing, uptime/SLA, full-history parity and point-in-time backtest suitability remain unverified. The next useful check is a second working-day capture and a real analyst review.

## Source and rights

Source: European Central Bank. Original reference data is available free from the ECB. Informational reference rates, not executable quotes.

ECB policy: https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html

Seiche transforms ECB XML values into dated CSV/JSON rows. Values are not interpolated, inverted or economically adjusted. Preserve the free-source notice wherever accessed and before any payment. This scope covers only the four specified numerical reference series.

Publisher: LIQUILENS PRIVATE LIMITED. Support: mrinal@liquilens.in. Independent of the ECB; no endorsement is implied.
