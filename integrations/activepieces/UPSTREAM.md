# Activepieces contribution packet

Status: prepared source candidate; no upstream PR or npm publication performed.

Proposed PR title: **feat(financial-evidence): add public research catalog and evidence page actions**

## Proposed description

Adds two credential-free Financial Evidence actions for finding public research
datasets and retrieving a bounded page of financial observations. Each query
keeps its source citations, native units, observation clocks, unavailable values,
rights fields and coverage diagnostics in the returned page. This supports
research workflows without trade execution or private financial inputs.

The adapter fixes its HTTPS host and paths, rejects redirects, limits selectors
and page sizes, and propagates upstream failures. It performs no background work
or automatic pagination. Tests cover the real SDK action registration, complete
response preservation, invalid input rejection, schema drift and failure behavior.

## Upstream placement and review

1. Check the current upstream tree and open PRs for duplicate Financial Evidence
   work before opening a contribution.
2. Generate a community piece in the current Activepieces checkout and copy
   `src/` under `packages/pieces/community/financial-evidence/src/`. Use that
   checkout's generated package/build files and shared dependency versions; this
   standalone package pins the currently published SDK for reproducible checks.
3. Add the project logo under the upstream asset process; the candidate uses the
   existing public repository logo. Confirm that upstream accepts the URL or
   supply its requested CDN asset before publication.
4. Add `financial-evidence` to `AP_DEV_PIECES` and run the actual flow-builder
   actions. Capture editor installation and execution evidence. SDK invocation
   alone does not establish this check.
5. Run upstream formatting, build and applicable piece checks. Review the
   declared minimum release against the upstream SDK. Prepare one PR; maintainers
   review and merge it before upstream package availability.

An independent npm publication is a different distribution route. Do not infer
ownership of the `@liquilens` npm scope from this package name, and do not claim
an upstream `@activepieces` package before maintainer publication.

## Official references

- [Piece definition](https://www.activepieces.com/docs/build-pieces/building-pieces/piece-definition)
- [Action SDK and editor testing](https://www.activepieces.com/docs/build-pieces/building-pieces/create-action)
- [Contribution and publication flow](https://www.activepieces.com/docs/build-pieces/sharing-pieces/contribute)
- [Standalone community package route](https://www.activepieces.com/docs/build-pieces/sharing-pieces/community)
