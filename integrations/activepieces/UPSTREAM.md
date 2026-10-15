# Activepieces publication routes

Status checked 15 October 2026: independent package candidate. Activepieces has
temporarily paused unsolicited pull requests from outside its organization.
Do not open a new upstream PR while that policy applies. The project explicitly
supports publishing independently maintained pieces outside its repository.

The [current contribution policy](https://github.com/activepieces/activepieces/blob/main/CONTRIBUTING.md)
takes precedence over the older contribution walkthrough linked below.

## Independent package

Build with Node 22 and run the SDK tests. For native qualification, run:

```sh
python3 scripts/native_smoke.py --evidence-dir /path/to/verification-evidence
```

This requires Docker and uses the official Activepieces 0.92.3 image pinned by
digest. It installs the packed archive in a disposable instance and tests both
actions through the native worker using the editor's step-test API. It removes
that instance afterward. This is distinct from browser interaction and npm
registry installation; see the generated receipt for actual results.

Before npm publication, authenticate with the intended publisher account and
verify its ownership of the `@liquilens` scope. Publish only the exact qualified
tarball. Read back the registry version and tarball and compare their SHA-256
with the native receipt before recording publication. No credentials belong in
the source, artifact, workflow logs or public receipt.

The public npm route is installed through Activepieces Settings, My Pieces,
Install Piece, using the exact package name and version. Packed archive upload
depends on the instance edition and plan; do not assume that a cloud account
permits it. No paid plan or upstream acceptance is included in this candidate.

## Future upstream contribution, only if reopened or invited

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
