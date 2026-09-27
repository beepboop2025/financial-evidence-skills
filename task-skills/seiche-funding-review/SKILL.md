---
name: seiche-funding-review
description: Review dollar funding conditions, repo and reserve context with Seiche's published evidence. Use for a morning funding check or money-market research question.
---

Use the Seiche MCP connection at `https://api.seiche.info/mcp`. The public endpoint needs no account or API key. If it is unavailable, report the connection failure instead of reconstructing a current reading from memory.

Start with `funding_stress_now` and `{}`. Preserve the source's regime, generated time, data-quality counts and individual observation dates. A newly generated board does not make its underlying daily or weekly observations current. Keep counterevidence and historical-validation limits with the conclusion. If the user needs the repo/reserves mechanism, discover the current schema for `money_market_context` and call it with the relevant supported inputs.

Answer the user's funding question with the source-reported reading, what evidence is old or missing, and links to the underlying evidence when provided. Do not turn this context into an instruction to trade or infer any institution's creditworthiness from the system-wide reading.

Starter question: “What does the current dollar-funding board say, and which underlying observations are old or missing?”

[Browser demo](https://liquilens.in/start/?task=funding) · [Source and setup](https://seiche.info/developers/)
