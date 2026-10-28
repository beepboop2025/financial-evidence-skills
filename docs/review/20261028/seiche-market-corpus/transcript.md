# Seiche Market Atlas Corpus service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Corpus discovery

Summarize registered market corpora and evidence classes so I can choose a research source.

Tools: `corpus_catalog`

Expected interpretation: Describe returned registrations and evidence classes. Do not infer observation availability, freshness or redistribution permission.

Captured 2026-10-28T14:35:44.222149+00:00 — `corpus_catalog({})`

## 2. Dataset rights inspection

List up to ten versioned datasets, choose one returned dataset and inspect rights, publication state and product eligibility using its exact ID.

Tools: `list_datasets, inspect_dataset`

Expected interpretation: Use list limit 10, copy exact dataset_id into inspect_dataset and retain restrictions. If no dataset is returned, stop without fabricating an ID.

Captured 2026-10-28T14:35:44.355974+00:00 — `list_datasets({"limit": 10})`

Captured 2026-10-28T14:38:19.120231+00:00 — `inspect_dataset({"dataset_id": "bis-ws_cbpol_csv_flat"})`

## 3. Normalized market coverage

Show normalized Seiche money-market coverage and identify exact market and source-adapter partitions for bounded queries.

Tools: `seiche_markets`

Expected interpretation: Report returned coverage and exact identifiers. Distinguish source-adapter IDs from publisher labels and retain gaps or restrictions.

Captured 2026-10-28T14:38:20.262922+00:00 — `seiche_markets({})`

## 4. Permitted bounded observations

Discover a Seiche market and exact source-adapter partition, then request no more than twenty permitted canonical observations. Preserve source clocks, units and restrictions.

Tools: `seiche_markets, seiche_observations`

Expected interpretation: Copy market and source identifiers from discovery and use limit 20. Respect redistribution validation; report denial or missing coverage without reconstructing withheld values.

Captured 2026-10-28T14:38:20.262922+00:00 — `seiche_markets({})`

Captured 2026-10-28T14:41:12.124347+00:00 — `seiche_observations({"market": "EA-EUR", "source": "ecb_benchmark", "limit": 20})`

## 5. Corpus service health

Check the corpus service's reported health and explain unavailable storage or service state separately from dataset freshness and licensing.

Tools: `corpus_health`

Expected interpretation: Report health state and limitations. A healthy service does not establish current data, complete coverage or redistribution authorization.

Captured 2026-10-28T14:38:19.242883+00:00 — `corpus_health({})`
