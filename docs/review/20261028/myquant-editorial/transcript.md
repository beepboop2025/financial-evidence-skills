# MyQuant Editorial service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Recent stories

Retrieve five recent MyQuant archive stories and summarize their evidence, publication dates and limitations.

Tools: `latest_stories`

Expected interpretation: Use limit 5, preserve source and evidence clocks, and report unavailable feeds explicitly rather than inventing stories.

Captured 2026-10-28T14:35:43.013311+00:00 — `latest_stories({"limit": 5})`

## 2. Plain-text search

Search the MyQuant archive for 'dollar funding' and show up to five matching stories with source links.

Tools: `search_stories`

Expected interpretation: Use query dollar funding and limit 5. Explain empty results without inventing matches or treating text matching as semantic ranking.

Captured 2026-10-28T14:35:43.596317+00:00 — `search_stories({"query": "dollar funding", "limit": 5})`

## 3. Exact story retrieval

List the newest available MyQuant story, then retrieve it using the exact returned story ID and summarize its evidence limits.

Tools: `latest_stories, get_story`

Expected interpretation: Discover the ID with limit 1 and copy it exactly into get_story. If no story is returned, stop and report the gap.

Captured 2026-10-28T14:35:43.013311+00:00 — `latest_stories({"limit": 5})`

Captured 2026-10-28T14:37:21.082599+00:00 — `get_story({"id": "liquilens-undertow:2026-10-28"})`

## 4. Archive capabilities

Inspect MyQuant Editorial's supported content tools, API routes and content limits before I build an archive-reading workflow.

Tools: `list_capabilities`

Expected interpretation: Describe returned capabilities and distribution boundaries; do not claim this discovery call retrieved stories.

Captured 2026-10-28T14:35:43.817007+00:00 — `list_capabilities({})`

## 5. Connection compatibility

Check MyQuant Editorial's API and MCP compatibility metadata and report its deployed source identity if available.

Tools: `get_health`

Expected interpretation: Report returned versions, checked_at and source identity when present. Endpoint compatibility is separate from feed freshness.

Captured 2026-10-28T14:35:44.119052+00:00 — `get_health({})`
