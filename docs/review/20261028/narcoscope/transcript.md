# NarcoScope service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Evidence overview

Use NarcoScope to summarize its public evidence coverage and key limitations for a research brief.

Tools: `get_overview`

Expected interpretation: Retrieve the overview, preserve dates and coverage limits, and distinguish evidence availability from validated conclusions.

Captured 2026-10-28T14:35:45.419111+00:00 — `get_overview({})`

## 2. India atlas context

Use NarcoScope's atlas to inspect organized_crime evidence for IND, limited to 10 records.

Tools: `get_atlas`

Expected interpretation: Request domain organized_crime, iso3 IND and limit 10. Cite sources and avoid treating administrative records as proof of guilt or market size.

Captured 2026-10-28T14:37:19.711134+00:00 — `get_atlas({"domain": "organized_crime", "iso3": "IND", "limit": 10})`

## 3. Dataset provenance

Inspect NarcoScope's global-drugs catalog, limited to four entries, and explain units and publication restrictions.

Tools: `get_market_catalog`

Expected interpretation: Request dataset global-drugs and limit 4. Preserve dataset identifiers, hashes when supplied, source clocks, units and rights.

Captured 2026-10-28T14:37:20.032103+00:00 — `get_market_catalog({"dataset": "global-drugs", "limit": 4})`

## 4. Bounded market observations

Find one permitted indicator in NarcoScope's global-drugs catalog, then retrieve at most 20 observations for that exact indicator.

Tools: `get_market_catalog, query_market_observations`

Expected interpretation: Discover an exact indicator before querying. Retain source dates, units and restrictions; if observations are denied or absent, report that state without reconstruction.

Captured 2026-10-28T14:37:20.032103+00:00 — `get_market_catalog({"dataset": "global-drugs", "limit": 4})`

Captured 2026-10-28T14:41:11.360339+00:00 — `query_market_observations({"dataset": "global-drugs", "indicator": "statcan-13100820-monthly-load", "geo": "CAN-CITY-edmonton-alberta", "category": "Benzoylecgonine", "limit": 20})`

## 5. Published research story

Show at most five NarcoScope newsroom items, then summarize one returned story's machine brief with sources and dates.

Tools: `get_newsroom, get_story`

Expected interpretation: Discover the exact returned slug, request artifact machine-brief, cite sources and distinguish reported evidence from interpretation.

Captured 2026-10-28T14:35:46.225453+00:00 — `get_newsroom({"limit": 5})`

Captured 2026-10-28T14:37:20.320771+00:00 — `get_story({"slug": "china-linked-precursor-incidents-official-record"})`
