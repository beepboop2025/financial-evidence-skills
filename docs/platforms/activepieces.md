# Activepieces

Build source-cited research workflows with the Financial Evidence native piece
candidate. Its two actions list the public dataset catalog and retrieve a bounded
evidence page with source dates, units and coverage diagnostics.

Public API access needs no credentials. Choose bank risk, money markets,
money-market history, capital markets, market liquidity, China publication
coverage or source health. The piece keeps the full response instead of extracting
values without their evidence context.

[Source and build instructions](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/activepieces)
· [upstream contribution packet](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/activepieces/UPSTREAM.md)

Start with 25 rows and offset 0. Stop pagination when `next_offset` is null and
place an explicit limit on any workflow loop. Keep `sources`, `diagnostics`,
observation `as_of`, `availability` and `rights_status` with downstream output.
Missing values remain missing. A transport success does not establish freshness,
creditworthiness or an investment conclusion.

The source candidate passed TypeScript compilation, five regression tests and
bounded live action reads using Activepieces SDK 0.32.0 on Node 25.6.0. The
[dated validation receipt](activepieces-verification-20261015.json) includes
source hashes, observed clocks and package contents. Other Node versions, native
editor installation, npm publication and upstream acceptance remain unproven.
The piece does not execute trades or send alerts by itself.

Activepieces accepts reviewed native contributions through its
[official contribution process](https://www.activepieces.com/docs/build-pieces/sharing-pieces/contribute).
