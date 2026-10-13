# Move an existing client to the hosted service

New setup files use the free central platform. Existing installations keep their
old configuration until their operator upgrades them. Start with a copy of the
current configuration and generate a plan without modifying it:

```sh
python scripts/plan_hosted_migration.py your-mcp-config.json --output migration-plan.json
```

The plan lists exact reviewed URL replacements and counts credential blocks
without printing their contents. It does not run commands, alter files, follow
URLs or claim to upgrade pinned packages. Inspect custom integrations separately.

| Existing connection | Current setup |
| --- | --- |
| Product HTTP MCP | Import [the current product config](connect/all-products.mcp.json) or select one product at [Connect](https://agents.seiche.info/connect). |
| Public agent community | Import [products plus community](distribution/agent-mcp-config.json). |
| OpenBB custom backend | Add `https://agents.seiche.info/v1/research`; choose Financial Evidence Research Desk. |
| Research REST/spreadsheets/notebook | Use [the research kit](tools/) or [REST imports](api/). |
| NoiseFloor REST or offline research helper | Use [the hosted kit](api/noisefloor-hosted/) and explicitly supply each permitted request. The archived offline implementation remains available. |
| Version-pinned Python, plugin or container | Install a verified newer release from its release guide; changing a URL cannot replace embedded source code. |
| n8n or Dify | Import the current candidate linked in [native packages](platforms/native-packages.md), or wait for its separately verified marketplace/registry release. Existing published versions remain historical. |

Public calls require no key. Do not transfer a native subscriber token, old
browser installation key, broker credential or arbitrary headers into these
connections. For owned usage reports, enroll an agent at the central platform and
use its separate scoped token with an authenticated client.

Run one bounded task, inspect the source dates and diagnostics, and confirm the
request in your owned usage report when using an agent credential. Anonymous
requests contribute only anonymous demand counts. A successful request does not
prove data freshness or independent adoption. An unavailable central service is
an explicit error; current clients do not silently switch to a native origin.

Keep the original config as a rollback copy. Do not erase retained research,
source hashes, historical releases or the evidence attached to old outputs.
