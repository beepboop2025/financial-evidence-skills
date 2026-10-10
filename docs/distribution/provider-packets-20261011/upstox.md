# Upstox — read-only MCP research companion

Prepared 11 October 2026 IST. State: **companion instructions ready oauth required**. No new application, agreement or message was sent by this preparation work.

## Proposed recurring use

A user who already has Upstox connects its official read-only MCP to their own assistant and separately adds Financial Evidence. The assistant uses only the user-selected institution names or symbols to gather research; brokerage account data stays in the user's chosen client.

## Entry and prepared fields

Official entry: https://upstox.com/developer/api-documentation/mcp-integration/

- Official Upstox MCP: https://mcp.upstox.com/mcp.
- Financial Evidence MCP: https://api.seiche.info/openbb/mcp.
- Client configuration example: upstox-companion.mcp.json.
- Use the official upstox-mcp connector. The separate upstox-skill package can execute trades and is not part of this research workflow.
- Daily Upstox OAuth renewal remains user-controlled.

Ready-to-use prompt:

> Inspect the currently exposed tool schemas. Use only read operations. For the institutions I explicitly select, retrieve the minimum account context necessary from Upstox, then query Financial Evidence using public institution names or identifiers only. Do not send holdings quantities, balances, profile data or account identifiers to Financial Evidence. Keep broker prices separate from dated public research. Verify entity identity and coverage before joining evidence. Preserve sources, observation dates, units, stale and unavailable states. Save a concise evidence note for my review. Do not place, modify or cancel orders, change account settings, or install execution skills.

Publisher: **LIQUILENS PRIVATE LIMITED**. Brand: **LiquiLens**. Contact: **mrinal@liquilens.in**. Website: https://liquilens.in/.

Public demonstration: https://beepboop2025.github.io/financial-evidence-skills/start/.
Research MCP: https://api.seiche.info/openbb/mcp.
[Privacy](https://beepboop2025.github.io/financial-evidence-skills/privacy/) · [Terms](https://beepboop2025.github.io/financial-evidence-skills/terms/) · [Support](https://beepboop2025.github.io/financial-evidence-skills/support/).

The downloadable sample is limited to four ECB EUR reference-FX series. Broader LiquiLens institution and Undertow liquidity tools are separate source-bound research services. No dataset sample grants rights over unrelated sources. Customer counts, revenue, certifications, SLA commitments and named reference clients are not established by this packet.

## Remaining gate

Consenting account holder, supported AI client, OAuth and a native useful-task transcript. No actual Upstox login, account read or combined native session was performed. Two valid MCP endpoint URLs do not establish a native platform partnership or customer adoption.

Official current documentation states the MCP reads holdings, orders, positions, mutual funds, funds and profile and cannot place trades. Verify tool schemas again before use because capability sets can change. This route avoids creating an unnecessary broker API app for a read-only research task.

## Evaluation assets

[Dataset factsheet](dataset-factsheet.md) · [80-row CSV sample](reference-fx-sample.csv) · [JSON sample](reference-fx-sample.json) · [Sample verification](sample-verification.json) · [Reference-FX review](sample-report-fx.md) · [Coverage and vintage review](sample-report-coverage.md).

A useful first evaluation is one dated note retained by an independent analyst. A second-day return and the analyst's assessment of usefulness are tracked separately from a successful request or an accepted listing.

## Official requirements checked

- https://upstox.com/developer/api-documentation/mcp-integration/
- https://upstox.com/developer/api-documentation/agent-quickstart/
