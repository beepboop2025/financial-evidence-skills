# MyQuant App Discovery service walkthrough

The product skill and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. NoiseFloor examples use synthetic inputs; all other values retain their service-provided dates and restrictions.

## 1. Offline reading discovery

Inspect MyQuant's published offline-reading capabilities and limits without checking or changing my device.

Tools: `list_capabilities`

Expected interpretation: Explain returned features and boundaries. Do not claim that content is downloaded or available on the user's device.

Captured 2026-10-28T14:35:43.187076+00:00 — `list_capabilities({})`

## 2. Topic controls

What topic controls does MyQuant document, and which actions would still require me to use the app?

Tools: `list_capabilities`

Expected interpretation: Describe documented controls and distinguish feature discovery from reading or changing preferences.

Captured 2026-10-28T14:35:43.187076+00:00 — `list_capabilities({})`

## 3. Briefing and feed validation

Read MyQuant's capability metadata and explain its briefing and feed-validation features and stated limits.

Tools: `list_capabilities`

Expected interpretation: Summarize documented features without claiming to fetch a briefing, validate a particular feed or inspect on-device content.

Captured 2026-10-28T14:35:43.187076+00:00 — `list_capabilities({})`

## 4. Integration surface discovery

Identify MyQuant's documented public API and MCP surfaces and product boundaries for a possible integration.

Tools: `list_capabilities`

Expected interpretation: Report supported surfaces and limits from metadata. Do not infer installation availability or access to private app state.

Captured 2026-10-28T14:35:43.187076+00:00 — `list_capabilities({})`

## 5. Compatibility heartbeat

Check MyQuant's non-sensitive API and MCP compatibility heartbeat and summarize its status.

Tools: `get_health`

Expected interpretation: Report returned compatibility metadata. Do not equate endpoint response with installed-app health, feed freshness or device access.

Captured 2026-10-28T14:35:43.396996+00:00 — `get_health({})`
