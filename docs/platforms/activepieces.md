# Activepieces

Build source-cited research workflows with the Financial Evidence native piece
package, version 0.1.0. Its two actions list the public dataset catalog and retrieve a bounded
evidence page with source dates, units and coverage diagnostics.

Public API access needs no credentials. Choose bank risk, money markets,
money-market history, capital markets, market liquidity, China publication
coverage or source health. The piece keeps the full response instead of extracting
values without their evidence context.

[Published npm package](https://www.npmjs.com/package/@moomoo202020/piece-financial-evidence/v/0.1.0)
· [publication receipt](activepieces-publication-20261015.json)
· [download the qualified archive](downloads/moomoo202020-piece-financial-evidence-0.1.0.tgz)
· [native qualification receipt](activepieces-native-20261015.json)
· [checksums](SHA256SUMS)

The archive installed in the official Activepieces 0.92.3 community host, pinned
by image digest. Its native worker executed both actions successfully: seven
dataset descriptions and one money-market evidence row with its source and
diagnostics. The tested observation was dated 13 October and marked `AGING`;
successful execution does not make that observation fresh.

For an instance that permits independently maintained pieces, open Settings,
My Pieces, Install Piece and select the npm package
`@moomoo202020/piece-financial-evidence`, version `0.1.0`. See the
[official independent package instructions](https://www.activepieces.com/docs/build-pieces/sharing-pieces/community).
For a separate Node environment, the exact package is available with:

```sh
npm install @moomoo202020/piece-financial-evidence@0.1.0
```

An anonymous npm installation loaded both registered actions. The registry
archive matches the native-tested bytes and its registry signature was verified.
This publication has no OIDC provenance attestation; the retained native receipt
provides its separate source-commit and CI-run binding.

Archive evaluation requires an isolated self-hosted development instance with
archive installation available under its edition and plan. The qualification used the host's normal
installation and editor step-test APIs; browser interactions and cloud-account
installation are not verified. For a reproducible check, follow the
[source and build instructions](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/activepieces)
and run `scripts/native_smoke.py` with Docker. Native flows created by that check
are disposable drafts, with no published schedule.

Start with 25 rows and offset 0. Stop pagination when `next_offset` is null and
place an explicit limit on any workflow loop. Keep `sources`, `diagnostics`,
observation `as_of`, `availability` and `rights_status` with downstream output.
Missing values remain missing. A transport success does not establish freshness,
creditworthiness or an investment conclusion.

The package build and five regression tests passed on Node 22 using Activepieces
SDK 0.32.0. The earlier [SDK validation receipt](activepieces-verification-20261015.json)
records the previous source candidate on Node 25.6.0; it is distinct from the
archive identified in the native receipt. The piece does not execute trades or
send alerts by itself.

The package is independently published under its authenticated maintainer's
`@moomoo202020` scope. Activepieces currently pauses unsolicited external pull requests under its
[contribution policy](https://github.com/activepieces/activepieces/blob/main/CONTRIBUTING.md).
See the
[publication instructions](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/activepieces/UPSTREAM.md).
No marketplace acceptance, independent-user adoption or source-data resale
rights are claimed by this qualification.
