# n8n first-publication operator procedure

This is a prepared procedure, not a publication receipt. The candidate is
`n8n-nodes-financial-evidence@0.1.0`, authored by LIQUILENS PRIVATE LIMITED.
Keep npm publication, n8n verification and independent adoption as separate
states. Signing in to npm does not complete any of them.

The reviewed download is
[`n8n-nodes-financial-evidence-0.1.0.tgz`](https://beepboop2025.github.io/financial-evidence-skills/platforms/downloads/n8n-nodes-financial-evidence-0.1.0.tgz),
4,445 bytes, SHA-256
`9d2fa6ba3950c41a68e025ea6f5c57922697c0b311ef6d77ce52412267b392ae`.
Its native n8n 2.42.6 execution passed in
[run 38080327701](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/38080327701).
The original tarball remains unchanged. Exact comparison found that its README
matches current package source: both have SHA-256
`4f360e31bd4284f56f5ce487ff21d2e8b487b4a8935b83eab66a6e05cf571dd5`.
The staging workflow rebuilds the runtime, requires every shipped file including
README and metadata to match the current build, records both README hashes, and
executes the existing tarball in a fresh native profile. Repacking is unnecessary
and would not prove identity with the previously tested archive. The unchanged
package README's older reference to a `publish` switch is superseded by this
procedure and the workflow's `mode` input. Any future package README change must
be treated as a new candidate, not silently substituted in this release.

## Why a first-package bootstrap is necessary

[npm trusted publishers](https://docs.npmjs.com/cli/v11/commands/npm-trust/)
require an existing package, write access and account 2FA. The recommended
bootstrap uses the existing signed-in local session only to stage this exact
archive. **For a new name, npm creates a publicly available `0.0.0-stage`
placeholder.** The actual staged `0.1.0` content remains unavailable to the
public until a maintainer approves it. This is an external registry change and
must be understood before starting; it is not a live product release.
[Official staged-publishing behavior](https://docs.npmjs.com/staged-publishing/).

There are two possible first-release routes:

| Route | Credential/grant | Consequence |
| --- | --- | --- |
| Recommended: local stage bootstrap, then package-specific OIDC | Existing isolated npm session stays local; only the named GitHub workflow can stage this one package | Public placeholder first; human approval remains separate; no npm token copied into GitHub |
| First CI release using a granular token | New token and GitHub secret; a nonexistent unscoped name cannot yet be selected as an existing package | Broader initial package permission may be needed; adds a stored secret and an account decision |

The alternative is documented by
[n8n's publishing instructions](https://docs.n8n.io/connect/create-nodes/deploy-your-node/submit-community-nodes)
and [npm's granular-token options](https://docs.npmjs.com/creating-and-viewing-access-tokens/).
It is not implemented here. Do not copy a login/session token into GitHub, create
a bypass-2FA token, or fall back to direct local publication.

## Account steps, after review

1. Confirm the local isolated npm session is the intended publisher and that
   account 2FA is enabled. Recheck that the package name has not been claimed.
   Keep the default npm configuration untouched. Use Node 24 and npm 11.21.0
   (staging requires npm 11.15+); any local CLI installation belongs in the
   task's SSD artifact directory.
2. With the placeholder effect approved, stage the reviewed tarball locally
   using that isolated user configuration and `--access public --tag latest
   --ignore-scripts`. Retain its stage ID. This bootstrap has **no GitHub
   provenance**: do not approve it as the actual release.
3. On the package settings page, add this exact trusted publisher:

   | Setting | Value |
   | --- | --- |
   | Provider | GitHub Actions |
   | Repository owner | `beepboop2025` |
   | Repository | `financial-evidence-skills` |
   | Workflow filename | `native-marketplace-npm-publish.yml` |
   | GitHub environment | Leave empty; this workflow does not declare one |
   | `npm stage publish` | Allow |
   | Direct `npm publish` | Do not allow |
   | Dist-tag management | Do not allow |

   This is a package-specific staging grant, not approval of a release.
   [npm's OIDC setup and command permissions](https://docs.npmjs.com/trusted-publishers/)
   explain the trust boundary. The prepared workflow uses GitHub-hosted
   runners, `contents: read`, and `id-token: write` only for its staging job.
   It contains no npm secret or direct-publication fallback.
4. Reject the local bootstrap stage through npm with the required human 2FA.
   Staged and published versions share a version index, so the original stage
   must be removed before CI can stage `0.1.0` again. Verify the placeholder,
   ownership and publisher grant remain as expected before continuing.
   [npm stage commands](https://docs.npmjs.com/cli/v11/commands/npm-stage/)
   document rejection and re-staging; do not automatically retry a failed or
   ambiguous mutation.

## CI candidate and human release approval

Use the merged, reviewed main commit and the hash above as workflow inputs.
`expected_sha` must equal the run's main commit, `expected_version` is `0.1.0`,
and `expected_archive_sha256` must equal the reviewed archive hash. The modes are:

| Mode | Result |
| --- | --- |
| `dry-run` (default) | Source/archive checks, unit tests, native n8n execution and npm staging dry run; no registry mutation or OIDC publishing permission |
| `stage` | The same checks, then OIDC staging with provenance; uploads the npm stage result; awaits a separate human approval |
| `verify-published` | The same candidate checks, plus anonymous registry identity, SHA-512 integrity, byte equality and provenance-metadata readback after approval |

Run `dry-run` first and retain its `archive-check.json` and `receipt.json`.
After the exact package trust is configured, run `stage`. Newly configured npm
publishers have a limited initial-use window, so configure the grant only when
the reviewed candidate is ready. Review the stage ID, package/version, tarball
hash and GitHub provenance from the successful run. The npm account holder
then approves that stage separately in npm with 2FA. Never approve the earlier
local bootstrap stage.

After approval, run `verify-published`, inspect the linked provenance subject
and workflow identity, and install the exact registry version in an isolated
consumer to verify its n8n metadata. Only then record npm publication. Submit
that version to the [n8n Creator Portal](https://creators.n8n.io/nodes) for its
separate review; [n8n requires GitHub Actions provenance for verified nodes](https://docs.n8n.io/connect/create-nodes/deploy-your-node/submit-community-nodes).
Neither staging nor a successful registry readback proves n8n acceptance or
independent customer use.
