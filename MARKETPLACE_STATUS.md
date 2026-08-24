# Third-party marketplace status

This ledger records third-party discovery and marketplace work for Financial
Evidence v0.1.4. It deliberately separates an independently verified public
listing from a submission, an automatic-indexing prerequisite, and a packet
that is technically ready but still needs an account-owned action.

The machine-readable source of truth is
[`docs/marketplaces.json`](docs/marketplaces.json). Its `checked_at` timestamp
is the observation clock; external operators may change state after that time.

## Public now

- Official MCP Registry v0.1.4 is active with both the public Streamable HTTP
  endpoint and the versioned OCI package.
- The public Homebrew tap installs and tests Financial Evidence v0.1.4.
- skills.sh serves the Agent Skill.
- Glama serves both the registry-ingested connector and repository listing, but
  its repository evaluation is incomplete until a Glama release exposes the
  three tools.

## Submitted for independent review

- Docker MCP Catalog: [PR #4765](https://github.com/docker/mcp-registry/pull/4765)
- Awesome MCP Servers: [PR #12771](https://github.com/punkpeye/awesome-mcp-servers/pull/12771)
- Awesome GitHub Copilot: [PR #2785](https://github.com/github/awesome-copilot/pull/2785)
- FINOS FDC3 App Directory: [PR #40](https://github.com/finos-labs/FDC3-App-Directory/pull/40)
- Awesome OpenBB: [PR #12](https://github.com/OpenBB-finance/awesome-openbb/pull/12)

An open or mergeable pull request is not an accepted listing. The operator's
review and merge remain authoritative.

## Ready for account-owned action

OpenAI, Claude, Smithery, StackShare, SaaSHub, and AlternativeTo require an
authenticated publisher or owner portal. Their public assets are ready, but no
submission, approval, listing, or publication is claimed until the operator
returns a receipt. Cline additionally requires a real Cline install test before
its submission attestation can be checked honestly.

## Held by policy or channel fit

- Gemini CLI gallery discovery is automatic; repository prerequisites are met,
  but no observed gallery listing is claimed.
- PulseMCP is temporarily closed to submissions.
- Zenodo and Hugging Face require destination-specific citation or demo assets;
  a promotional mirror would not be a valid submission.
- MCP.so charges USD 39. It remains unpurchased because no exact spend was
  authorized.

## Refresh rules

1. Re-resolve the public URL or operator API before changing an entry to
   `live`.
2. Record the exact submission or review URL for every `submitted` entry.
3. Never infer acceptance from mergeability, a passing syntax check, or a badge.
4. Stop before any checkout unless the exact amount and action were separately
   authorized.
5. Publish the signed version tag and verify every release asset before merging
   documentation that marks those versioned URLs public.
