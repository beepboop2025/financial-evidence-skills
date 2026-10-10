# Existing LobeHub listing corrections

Prepared on 10 October 2026 with the official `@lobehub/market-cli 0.0.41`.
These are update declarations for seven existing listings. None has been
published or claimed by this preparation step.

| Existing identifier | Observed version | Discovered tools | Connection |
| --- | --- | ---: | --- |
| beepboop2025-liquilens-mcp | 1.8.1 | 24 | Public Streamable HTTP |
| beepboop2025-seiche | 0.16.2 | 16 | Public Streamable HTTP |
| beepboop2025-undertow-mcp | 1.13.0 | 16 | Public Streamable HTTP |
| beepboop2025-palimpsest | 1.9.3 | 7 | Public Streamable HTTP |
| beepboop2025-riptide-mcp | 1.3.0 | 7 | Public Streamable HTTP |
| beepboop2025-noisefloor | 0.4.0 | 10 | Public Streamable HTTP |
| beepboop2025-liquilens-evidence-carrier | 0.20.1 | 4 | Local MCP bundle |

The CLI performed MCP initialization and discovery. That proves a protocol
connection and the observed public inventory, not an end-user chat workflow,
publisher verification, directory acceptance or independent adoption.
Undertow advertises eight additional subscriber tools through its access-status
tool; subscriber access was not tested and those tools are not in this public
manifest.

Evidence Carrier was inspected from the public v0.20.1 MCP bundle against an
empty evidence directory. Its SHA-256 matched the repository server manifest:
`09b25571f61f4ba2bd5e1c367a580355a6e08eccf0d1c34bdde0bbd460be0ed6`.
No private document was opened or uploaded. Its listing must retain the local
bundle installation and user-selected evidence-root requirement; it has no
hosted endpoint.

[Inventory and per-file hashes](index.json) identify the prepared declarations.
All seven public cards were rechecked on 10 October. Each still showed
Unvalidated. Their displayed versions were LiquiLens 1.0.0, Seiche 1.0.0,
Undertow 1.9.0, Palimpsest 1.0.0, Riptide 1.3.0, NoiseFloor 0.1.2 and
Evidence Carrier 0.19.0. These directory versions are separate from the native
versions in the table above. NoiseFloor's score was 45/100, with 2/4 required
items recorded by LobeHub.

The public Refresh Metadata control was tried once each for NoiseFloor,
LiquiLens and Seiche. No success confirmation was observed, and no changed
public metadata was verified. These attempts are not recorded as accepted
publisher updates. [Current correction receipt](../g2-lobehub-repair-20261010.json).

NoiseFloor also has the documented ownership badge on its public README after
[PR 6](https://github.com/beepboop2025/noisefloor/pull/6) merged. LobeHub's
Check Claim Status dialog showed Start Check disabled, so this did not submit
or complete a claim. The badge route was not extended to the other repositories.

## Account steps

Owner-approved publisher CLI login is complete, including LobeHub profile,
email and persistent sign-in (`offline_access`). The owner also approved the
separate GitHub grant for `gist`, `read:org`, `read:user`, `repo`, `user:email`
and `workflow`.

The GitHub authorization button remained disabled while organization access
loaded, including after reload and a fresh official CLI request. The CLI still
reported GitHub disconnected and an empty owned-plugin list. This is a
provider-interface blocker, not a request for another owner approval. No card
has been claimed or updated, and no restriction was bypassed. Retain the seven
prepared declarations until the official ownership flow becomes available.

An owner-approved support request covering all seven cards was sent to
[support@lobehub.com](https://lobehub.com/contact) at 09:19 UTC on 10 October.
Sent-folder readback confirms the send; delivery and a provider response remain
unverified. See the [current correction report](../g2-lobehub-repair-20261010.md).

The [publisher follow-through receipt](../publisher-completion-20261010.json)
tracks this later account state separately from the initial preparation.

Once the official GitHub ownership flow completes, inspect
`lhm plugin list --output json`. For each existing identifier, claim it only
if necessary and then use its corresponding prepared directory:

```sh
npx -y @lobehub/market-cli@0.0.41 plugin claim beepboop2025-noisefloor
npx -y @lobehub/market-cli@0.0.41 plugin update --dir docs/distribution/lobehub-updates/beepboop2025-noisefloor
```

Repeat the update for the remaining identifiers only after ownership is
confirmed. Retain the update receipt and re-read each public card. The directory
validation label remains unverified until LobeHub changes it; native discovery
alone does not justify replacing that label in the distribution ledger.
