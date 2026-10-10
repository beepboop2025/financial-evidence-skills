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
NoiseFloor's public card was still marked Unvalidated and displayed version
0.1.2, while native discovery returned 0.4.0 and ten tools. The other cards'
public metadata has not been fully revalidated in this pass.

## Account steps

The publisher CLI has no existing credentials. Its login requests LobeHub
profile, email and persistent sign-in (`offline_access`). This new grant awaits
owner approval. GitHub ownership access, if requested next, needs its displayed
scope reviewed separately. Do not create a machine identity or publish duplicate
cards to work around account ownership.

After authorized sign-in and GitHub ownership verification, inspect
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
