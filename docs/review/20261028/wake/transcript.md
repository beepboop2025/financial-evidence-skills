# Wake service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Attributed AI-model usage

Read Wake's available AI-model usage evidence. Summarize what is measured, who supplied it and the observation dates.

Tools: `wake_economy_now`

Expected interpretation: Report attributed observations and their clocks; distinguish measurement coverage from total market adoption and retain unavailable fields.

Captured 2026-10-28T14:35:41.867680+00:00 — `wake_economy_now({})`

## 2. Retail reference periods

Use Wake to explain the available U.S. retail e-commerce context. Separate its reference period from retrieval time.

Tools: `wake_economy_now`

Expected interpretation: Preserve units, source attribution and reference periods. Do not describe dated aggregate observations as live transactions.

Captured 2026-10-28T14:35:41.867680+00:00 — `wake_economy_now({})`

## 3. Aggregate eligibility

Inspect Wake's published contributor thresholds and permission requirements for institutional aggregates.

Tools: `wake_dataset_policy`

Expected interpretation: Explain returned thresholds and permission conditions without claiming that the user or their data already qualifies.

Captured 2026-10-28T14:35:41.951993+00:00 — `wake_dataset_policy({})`

## 4. Collection contract discovery

Read Wake's signed opt-in event contract and explain what a contributor must authorize. Do not enroll me or send events.

Tools: `wake_collection_contract`

Expected interpretation: Describe the returned contract and its limits. Reading it grants no consent, source authority or resale rights.

Captured 2026-10-28T14:35:42.046304+00:00 — `wake_collection_contract({})`

## 5. Contribution preparation

Compare Wake's dataset policy with its collection contract and list documented prerequisites for a proposed institutional contribution.

Tools: `wake_dataset_policy, wake_collection_contract`

Expected interpretation: Connect documented policy and contract requirements, identify unanswered questions, and make no enrollment or compliance claim.

Captured 2026-10-28T14:35:41.951993+00:00 — `wake_dataset_policy({})`

Captured 2026-10-28T14:35:42.046304+00:00 — `wake_collection_contract({})`
