# Use the same approved research connections across clients

`financial-evidence connect` prepares usable MCP configuration files for an institution's approved public-research workspace. Select products once and generate either or both supported formats: `mcpServers` for compatible remote MCP clients and `servers` for VS Code.

Generation is offline and uses the existing Financial Evidence product catalog. It does not sign in, install a server, fetch research, upload private data, or connect a vendor subscription. Importing a generated configuration later enables the client to contact the listed hosted endpoints.

## Version availability

This command is part of the **0.1.16 source candidate**. The last verified public
release is 0.1.15, which does not include `connect`. Until 0.1.16 publication and
consumer verification are recorded, use a reviewed candidate checkout in an
isolated environment; do not assume an unpinned PyPI install includes it.

From that checkout on macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/financial-evidence --version
```

The version should report `0.1.16`. Use the installed environment's
`financial-evidence` executable for the commands below. See the
[candidate release notes](../releases/0.1.16-candidate.md) for publication gates.

## Start with the existing products

```sh
financial-evidence connect --catalog
```

This lists the same 14 product routes used by the shipped product client, including LiquiLens, Seiche, Undertow, Palimpsest, NoiseFloor, Financial Evidence Workspace and Source Data Research Workspace. The catalog is a route declaration, not a live health check, freshness verdict or claim that each product supports the same operations. Clients may require their own account, subscription and approval of remote servers.

## Create a connection profile

Generate a template locally, or inspect [the demonstration profile](https://github.com/beepboop2025/financial-evidence-skills/blob/main/examples/institution-connection-profile.json):

```sh
financial-evidence connect --example > institution.json
```

The generated template starts with `hosted_queries_approved: false` and cannot produce a connection package until you record actual approval. Its example approval reference is **not** authorization. Replace the identifiers, approval reference and retention period with your institution's choices, and set hosted approval to true only after approval has been obtained. Include only product IDs returned by `connect --catalog` and only the client formats you intend to use.

The [profile schema](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/institution-connection-profile.schema.json) documents approved-profile fields. The CLI additionally validates known routes, destination identity equality and subscription expiry. Approval references and dataset IDs are identifiers, not passwords, API keys, customer records or document contents.

```sh
# Preview the exact package as JSON; no files or network requests are created.
financial-evidence connect --profile institution.json

# The parent directory must exist. The target directory must be new.
financial-evidence connect --profile institution.json --output bank-a-research-connections
```

The output directory contains:

| File | Purpose |
| --- | --- |
| `mcp.json` | Selected remote servers under `mcpServers`, if requested |
| `vscode.json` | The same selection under `servers`, if requested |
| `profile.json` | Declared institution approval, destinations, evidence policy and subscription inventory |
| `connection-receipt.json` | Selected routes, UTC generation time, profile/config hashes and explicit qualification limits |
| `README.md` | Import instructions and the public-data boundary |

On POSIX systems the directory is created with mode `0700` and files with `0600`. Existing files, directories and symlinks are refused. This command never merges into or overwrites a client's existing settings. If a write fails after the directory is created, review that incomplete directory and use a new destination for the next attempt.

## Import into an approved workspace

For a remote MCP client using `mcpServers`, merge the named server entries from `mcp.json` through that client's documented configuration flow. For VS Code, merge the `servers` entries into the approved workspace's `.vscode/mcp.json`. Review the client trust prompt before connecting. Do not replace unrelated configuration or distribute an institution's profile to a different institution.

Use `financial-evidence start` to choose an existing task and inspect its scope. For example, this separate, explicit command fetches public USD research and saves the original result, a brief and a receipt:

```sh
financial-evidence review funding --selection USD --output reviews
```

Moving the selected connections between supported clients preserves their product IDs and URLs. Moving research between tools also requires retaining original evidence, source URLs, observation/publication/retrieval dates, native units, missingness, rights and revisions. A chart or summary alone is not an equivalent evidence handoff.

## Existing subscriptions and private institutional silos

An optional external-subscription entry records a provider identifier, entitlement reference, approved dataset IDs and an inclusive expiry date. Its rights must be declared `confirmed_internal_research`, its connection status must remain `not_connected`, and its expiry must not be before the current UTC date. Unknown, expired or ambiguous permissions block generation. These are checked declarations; the generator does not independently verify a contract.

No third-party endpoint, credentials or subscription data is included in the generated client configurations. Use each vendor's official customer-approved connector and separately confirm allowed users, datasets, export, derived-data, redistribution and retention terms. An existing paid subscription does not automatically authorize another client or a hosted AI service to use its data.

The current package deliberately accepts only `public_research_only` queries with explicit hosted egress approval. It rejects private-data profiles, unknown routes, destinations for another institution/workspace, missing source-rights review and cross-institution sharing. Those checks govern **configuration generation only**. Once imported, a plain MCP configuration cannot filter subsequent arguments or enforce institutional policy.

Private silo integration therefore still needs separately qualified customer infrastructure: authenticated user and workload identities, tenant and dataset access enforcement, approved vendor connections, data-location/egress policy, audit records, retention/deletion, and export/exit controls. This feature does not implement those controls or claim RBI, US, EU or UK compliance. The declared retention period is a requirement for the institution to enforce, not an automated deletion schedule or legal recommendation.

Check the rights and diagnostics on every result. Restricted, unknown, stale or missing evidence stays explicit; a working connection does not turn it into permission, a current observation, a credit rating or execution authority.
