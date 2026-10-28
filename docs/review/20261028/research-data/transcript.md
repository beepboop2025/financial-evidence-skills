# Source Data Research Workspace service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Funding workspace overview

Read the Seiche research workspace and summarize coverage, source freshness, gaps and snapshot identifier.

Tools: `research_workspace`

Expected interpretation: Use product seiche; retain independent source clocks, snapshot identity and unavailable evidence without treating response time as observation time.

Captured 2026-10-28T14:35:44.075835+00:00 — `research_workspace({"product": "seiche"})`

## 2. Institution dataset discovery

Discover datasets available for LiquiLens research and explain each dataset's coverage and rights.

Tools: `research_catalog`

Expected interpretation: Use product liquilens, preserve exact dataset IDs and rights, and avoid presenting registry presence as complete financial coverage.

Captured 2026-10-28T14:35:44.301680+00:00 — `research_catalog({"product": "liquilens"})`

## 3. Bounded observation retrieval

Discover a permitted Seiche dataset and metric, then retrieve at most twenty observations using their exact returned IDs. Preserve units, dates, citations and missing values.

Tools: `research_catalog, research_series, research_observations`

Expected interpretation: Use product seiche for discovery, copy exact dataset and series IDs, and set observation limit 20. Stop if no permitted series is available; do not infer historical availability.

Captured 2026-10-28T14:35:44.451448+00:00 — `research_catalog({"product": "seiche"})`

Captured 2026-10-28T14:37:21.647985+00:00 — `research_series({"dataset": "ofr-fnyr", "limit": 10})`

Captured 2026-10-28T14:39:47.608412+00:00 — `research_observations({"dataset": "ofr-fnyr", "series": "FNYR-BGCR-A", "start": "2026-10-01", "limit": 20})`

## 4. Tracked institution coverage

Search existing Indian dossiers for 'AU', return at most ten results and explain financial-evidence gaps and population overlap.

Tools: `research_tracked_institutions`

Expected interpretation: Use scope dossiers, q AU and limit 10. Retain source clocks and gaps; do not treat overlapping populations as a global institution census.

Captured 2026-10-28T14:35:44.541767+00:00 — `research_tracked_institutions({"q": "AU", "limit": 10})`

## 5. Settlement analysis

Read Undertow's descriptive research analysis and explain returned settlement findings, input references and limitations.

Tools: `research_analysis`

Expected interpretation: Use product undertow, cite returned inputs and scope, and preserve withheld or unavailable analysis without causal or execution claims.

Captured 2026-10-28T14:35:44.670174+00:00 — `research_analysis({"product": "undertow"})`
