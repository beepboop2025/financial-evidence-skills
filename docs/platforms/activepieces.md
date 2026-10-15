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
· [native npm-installation receipt](activepieces-registry-20261015.json)
· [worker byte-attestation receipt](activepieces-worker-attestation-20261015.json)
· [checksums](SHA256SUMS)

The archive installed in the official Activepieces 0.92.3 community host, pinned
by image digest. Its native worker executed both actions successfully: seven
dataset descriptions and one money-market evidence row with its source and
diagnostics. The tested observation was dated 13 October and marked `AGING`;
successful execution does not make that observation fresh.

A separate fresh host installed version 0.1.0 directly from npm through the
native registry-install API and executed both actions successfully. The host
reported package type `REGISTRY`. The anonymous public archive matched the
previous publication's SHA-256, SHA-512 integrity and size before installation.
The [CI run](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/38727761856)
records both installation paths; that earlier run did not attest worker files.

A later qualification of both installation modes verified all 14 packaged files
and the five JavaScript modules compiled for each action against the reviewed
published archive. The [worker attestation receipt](activepieces-worker-attestation-20261015.json)
retains actual runtime paths, file hashes and source/CI identities. Dependency
bytes, image build provenance and browser interaction remain unverified.

On a self-hosted instance that permits independently maintained pieces, sign in
as a platform administrator. In Activepieces 0.92.3, open **Platform → Catalogue
→ Pieces → Install Piece**, choose **NPM Registry**, and enter
`@moomoo202020/piece-financial-evidence`, version `0.1.0`. The route is
`/platform/pieces`; older documentation calls it **Settings → My Pieces**.
These navigation labels were checked against the
[0.92.3 frontend source](https://github.com/activepieces/activepieces/blob/0.92.3/packages/web/src/app/components/sidebar/platform/index.tsx#L95),
and browser interaction remains unverified. See the
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

Use `--installation registry --evidence-dir PATH` to repeat the npm installation
check. It targets the version in the retained publication receipt. The default
`--installation archive` checks the local candidate build, which can differ from
the published version. Keep their receipts separate when developing an update.

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
