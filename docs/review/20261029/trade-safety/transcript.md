# LiquiLens Trade Safety 0.2.3 service walkthrough

One live trade_safety_capabilities call is reused across five review cases. No assessment was executed.

Direct public MCP calls only. Product-skill routing and negative model-routing cases are review expectations, not newly executed model tests. No trading, enrollment, collection, private-record access or execution was performed. Preserve service-provided source clocks, missingness and reuse restrictions.

## 1. Sandbox authority

Read Trade Safety's capabilities and explain exactly what authority its read-only sandbox has and lacks.

Expected interpretation: Describe returned authority limits and preserve the absence of broker, execution and custody authority. Do not run an assessment.

Captured 2026-10-28T19:19:49.020091+00:00 - `trade_safety_capabilities({})`

## 2. Fixed source discovery

Inspect Trade Safety's fixed public sources and explain their documented roles and conditional source use.

Expected interpretation: Report documented roles and conditions only. Do not claim that source evidence was fetched, is fresh or clears a trade.

Captured 2026-10-28T19:19:49.020091+00:00 - `trade_safety_capabilities({})`

## 3. Assessment preparation

Before I provide trade details, inspect the published sandbox capabilities for request and policy prerequisites. Identify undocumented requirements.

Expected interpretation: Summarize documented prerequisites and unknowns. Do not invent nested request or policy fields, supply missing financial inputs or invoke assess_trade_safety.

Captured 2026-10-28T19:19:49.020091+00:00 - `trade_safety_capabilities({})`

## 4. Receipt interpretation

Use Trade Safety's capability metadata to explain documented sandbox receipt boundaries and whether a receipt authorizes an order.

Expected interpretation: Explain documented receipt semantics and missing details. A sandbox receipt grants no order authority.

Captured 2026-10-28T19:19:49.020091+00:00 - `trade_safety_capabilities({})`

## 5. Integration boundaries

Inspect Trade Safety's capabilities and separate available public research functions from broker integration and execution functions.

Expected interpretation: Classify functions according to documented boundaries. Do not imply broker connectivity, make an assessment or generate an execution-ready instruction.

Captured 2026-10-28T19:19:49.020091+00:00 - `trade_safety_capabilities({})`
