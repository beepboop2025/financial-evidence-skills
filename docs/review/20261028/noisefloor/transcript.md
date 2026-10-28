# NoiseFloor service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Synthetic A/B comparison

Use NoiseFloor to compare synthetic A/B results: group A has 40 successes out of 100, group B has 55 out of 100. Explain uncertainty.

Tools: `ab_test`

Expected interpretation: Use the declared synthetic counts with the advertised schema and explain effect, uncertainty and test assumptions; do not claim causality from this example.

Captured 2026-10-28T14:35:41.774433+00:00 — `ab_test({"a_successes": 40, "a_total": 100, "b_successes": 55, "b_total": 100})`

## 2. Synthetic change check

Use NoiseFloor to check whether this synthetic chronological series changed: [10,11,9,10,12,10,9,11,20].

Tools: `did_it_change`

Expected interpretation: Use the supplied values without adding observations. Report change evidence and sample limitations without declaring a structural change certain.

Captured 2026-10-28T14:35:41.877266+00:00 — `did_it_change({"values": [10, 11, 9, 10, 12, 10, 9, 11, 20]})`

## 3. Synthetic forecast interval

Use NoiseFloor to forecast the next value of this synthetic series with nominal coverage 0.8: [10,11,10,12,11,13,12,13,14,13,15].

Tools: `forecast_next`

Expected interpretation: Use the supplied values and nominal 0.8. Explain the returned interval, assumptions and any insufficiency rather than promising realized coverage.

Captured 2026-10-28T14:35:42.058653+00:00 — `forecast_next({"values": [10, 11, 10, 12, 11, 13, 12, 13, 14, 13, 15], "nominal": 0.8})`

## 4. Sampling-size sensitivity

Use NoiseFloor to inspect whether this synthetic series could reflect sampling variation. Values: [10,11,10,12,11,13,12,13,14,20]; sample sizes: [100,110,100,120,110,130,120,130,140,200].

Tools: `real_or_sampling`

Expected interpretation: Use both aligned arrays as supplied, retain warnings and distinguish sampling evidence from a causal explanation.

Captured 2026-10-28T14:35:42.141944+00:00 — `real_or_sampling({"values": [10, 11, 10, 12, 11, 13, 12, 13, 14, 20], "sample_sizes": [100, 110, 100, 120, 110, 130, 120, 130, 140, 200]})`

## 5. Chronological forecast scoring

Use NoiseFloor to score forecasts on this synthetic chronological series: [10,11,10,12,11,13,12,13,14,13,15,14,16,15,17,16,18,17,19,18,20].

Tools: `score_forecasts`

Expected interpretation: Use the 21 supplied observations with chronological evaluation, explain baselines and sample limitations, and do not claim future investment performance.

Captured 2026-10-28T14:35:42.337781+00:00 — `score_forecasts({"values": [10, 11, 10, 12, 11, 13, 12, 13, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18, 20]})`
