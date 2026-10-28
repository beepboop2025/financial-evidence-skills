# LiquiLens service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Discover institution coverage

Use LiquiLens to find the public research coverage for AU Small Finance Bank before reviewing it.

Tools: `institution_research_coverage`

Expected interpretation: Discover covered institutions and use returned identifiers. Report available disclosures and gaps without inventing coverage or private records.

Captured 2026-10-28T14:35:42.333293+00:00 — `institution_research_coverage({"q": "AU", "limit": 10})`

## 2. Asset-quality review

Find AU Small Finance Bank in LiquiLens and review its available asset-quality evidence, citing disclosure dates and limitations.

Tools: `institution_research_coverage, bank_asset_quality_review`

Expected interpretation: Discover the exact slug before requesting the asset-quality review. Preserve missing, stale and non-comparable fields and avoid declaring the institution safe or compliant.

Captured 2026-10-28T14:35:42.333293+00:00 — `institution_research_coverage({"q": "AU", "limit": 10})`

Captured 2026-10-28T14:35:42.710245+00:00 — `bank_asset_quality_review({"slug": "au-sfb"})`

## 3. Cited institution review packet

Find AU Small Finance Bank in LiquiLens and retrieve its cited institution review packet. Preserve source dates and unresolved coverage gaps.

Tools: `institution_research_coverage, institution_review_packet`

Expected interpretation: Discover the exact returned institution slug or full name, then supply it as institution to institution_review_packet. Report no exact match if needed; preserve stale or dark gaps and do not interpret a content hash as attestation or publication-time proof.

Captured 2026-10-28T14:35:42.333293+00:00 — `institution_research_coverage({"q": "AU", "limit": 10})`

Captured 2026-10-28T14:35:43.061619+00:00 — `institution_review_packet({"institution": "au-sfb"})`

## 4. RBI supervisory evidence

Summarize the public RBI supervisory tape in LiquiLens for a bank-risk research note.

Tools: `rbi_supervisory_tape`

Expected interpretation: Retrieve the supervisory tape with dates and citations; distinguish published supervisory events from an analyst's interpretation and avoid private inspection claims.

Captured 2026-10-28T14:35:43.395231+00:00 — `rbi_supervisory_tape({})`

## 5. Official NBFC register discovery

Use LiquiLens to search the RBI NBFC register for HFC-classified institutions, limited to 10 rows.

Tools: `universe_search`

Expected interpretation: Use classification HFC and limit 10. Preserve official institution identifiers and register dates; registration does not establish financial-evidence coverage, creditworthiness or regulatory approval.

Captured 2026-10-28T14:35:43.710529+00:00 — `universe_search({"classification": "HFC", "limit": 10})`
