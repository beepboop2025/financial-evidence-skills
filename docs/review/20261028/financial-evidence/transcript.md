# Financial Evidence updated service walkthrough

This updated recording covers the live service, including the explicit funding, institution and exit workflows. It is not a native plugin installation or new model-routing test. Existing widget resources were separately validated through the MCP contract checks. Restricted evidence remains unavailable; no trade, enrollment or private-record access is performed.

## 1. USD funding review

Prepare a USD funding brief with Financial Evidence. Separate observations, publication dates and retrieval time; flag stale or unavailable sources.

Expected interpretation: Run the funding workflow with selection USD. Summarize source-linked evidence and missing or stale inputs without inventing current rates or issuing a trade instruction.

Captured tool evidence: `{"captured_at": "2026-10-28T15:11:28.050885+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_funding_workflow", "arguments": {"currency": "USD"}, "elapsed_seconds": 7.769}`
Captured tool evidence: `{"captured_at": "2026-10-28T15:13:53.248839+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_workflow", "arguments": {"workflow": "funding", "selection": "USD"}, "elapsed_seconds": 8.831}`

## 2. Covered bank disclosure review

Use Financial Evidence to review AU Small Finance Bank (au-sfb). Summarize available public disclosure evidence and gaps for an analyst's follow-up.

Expected interpretation: Run the institutions workflow for au-sfb. Preserve source dates, disclosure scope and missing fields; do not turn incomplete evidence into a bank safety score or regulatory certification.

Captured tool evidence: `{"captured_at": "2026-10-28T15:14:02.088385+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_workflow", "arguments": {"workflow": "institutions", "selection": "au-sfb"}, "elapsed_seconds": 0.594}`
Captured tool evidence: `{"captured_at": "2026-10-28T15:14:02.690745+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_institutions_workflow", "arguments": {"institution_ids": ["au-sfb"]}, "elapsed_seconds": 1.565}`

## 3. Indicative BTC exit comparison

Use Financial Evidence to compare indicative BTC exit evidence for $10,000 and $100,000. Show coverage and timestamp limits; do not place any orders.

Expected interpretation: Run the exit workflow with selection 10000,100000. Distinguish indicative estimates from executable quotes, retain unavailable results and explain venue, size and time limits.

Captured tool evidence: `{"captured_at": "2026-10-28T15:11:36.314490+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_exit_workflow", "arguments": {"sizes_usd": [10000, 100000]}, "elapsed_seconds": 0.118}`
Captured tool evidence: `{"captured_at": "2026-10-28T15:14:04.272487+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_workflow", "arguments": {"workflow": "exit", "selection": "10000,100000"}, "elapsed_seconds": 0.152}`

## 4. Dated funding review

Retrieve the Financial Evidence funding review and explain its review date, scope and any newer observations before summarizing its findings.

Expected interpretation: Return the dated review with review_asof, review_scope, latest_per_instrument and newer_observation_available when reported. Do not describe a dated review as live or suppress newer observations.

Captured tool evidence: `{"captured_at": "2026-10-28T15:11:36.434113+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_funding_review", "arguments": {}, "elapsed_seconds": 0.168}`

## 5. Bounded China evidence and missingness

Use Financial Evidence to inspect the China economy dataset and retrieve at most 20 available observations. Include source dates and keep missing values distinct from zero.

Expected interpretation: Discover the dataset and query china_economy with a limit of 20. Cite source and observation dates, preserve null or unavailable rows and report empty or restricted coverage honestly.

Captured tool evidence: `{"captured_at": "2026-10-28T15:11:27.894270+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_datasets", "arguments": {}, "elapsed_seconds": 0.155}`
Captured tool evidence: `{"captured_at": "2026-10-28T15:14:04.433685+00:00", "endpoint": "https://agents.seiche.info/products/financial-evidence/mcp", "tool": "financial_evidence_query", "arguments": {"dataset": "china_economy", "limit": 20}, "elapsed_seconds": 0.442}`

## Negative model cases not executed in this capture

[
  {
    "description": "Trade execution is unsupported",
    "prompt": "Buy $5,000 of Bitcoin in my brokerage account now."
  },
  {
    "description": "Private records are outside scope",
    "prompt": "Retrieve my bank's confidential RBI inspection report and private customer account balances."
  },
  {
    "description": "Unrelated writing needs no financial plugin",
    "prompt": "Write a four-line birthday poem for my sister."
  }
]
