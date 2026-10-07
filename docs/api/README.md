# Financial Evidence API kit

Connect LiquiLens bank evidence, Seiche funding and capital markets, Undertow
market liquidity, and China economic context through one public research API.
Operator: **LIQUILENS PRIVATE LIMITED**. Public reads require no API key.

1. Import `financial-evidence.postman_collection.json` into Postman, or open
   the `bruno` folder in Bruno. Insomnia can import `openapi.json`. JetBrains
   HTTP Client and VS Code REST Client can open `financial-evidence.http`.
2. Run **Release identity**, **Dataset coverage**, then **Source status and
   clocks**. The API version is independent of the CLI package version.
3. Run one table request. Each example requests at most five rows. Preserve
   `sources`, `diagnostics`, observation dates, units, rights and null values.
4. If `next_offset` is non-null, the response is a page, not a complete dataset.
   For complete captures with hash-consistent pagination, use the
   [research kit](https://beepboop2025.github.io/financial-evidence-skills/tools/).
5. A passing collection checks response shape and evidence boundaries. It does
   not establish fresh sources, redistribution permission or financial suitability.
   Check the actual source clocks and status; missing or held values stay null.

The twelve examples cover seven datasets and five discovery/review requests.
They do not create accounts, subscribe users, send messages or execute trades.
Requests go directly to `https://api.seiche.info/openbb`. No intermediary or
marketplace key is embedded. Never add a personal key to a public collection.

For operator verification, set `traffic_class=synthetic`. This label helps
identify tests; it is not a verified identity or an attribution system.
Bruno: `bru run --env-var traffic_class=synthetic`.
Newman: `newman run financial-evidence.postman_collection.json --env-var traffic_class=synthetic`.
No polling, monitors or scheduled collection runs are enabled by importing.

The OpenAPI file preserves the observed service contract, with an absolute
public server URL and discovery metadata. Its original retrieval time and hash
are in `x-source-observation`; they describe the API schema, not data freshness.
`manifest.json` records every import asset's SHA-256. Rebuild with
`python3 scripts/build_api_kit.py` from the repository root.

The MIT code license does not replace source-specific data rights.

For direct product tools, use the [financial-agent connection guide](https://beepboop2025.github.io/financial-evidence-skills/agents/CONNECT.md)
and its [machine-readable catalog](https://beepboop2025.github.io/financial-evidence-skills/agents/connections.json).
Start with LiquiLens coverage, Seiche source health and Undertow access scope.
The included **Agent research review** request returns a bounded three-product
research view. Bring missing or stale evidence to human attention before
interpreting changed values; this order does not approve financial actions.

[Terms](https://beepboop2025.github.io/financial-evidence-skills/terms/) ·
[Privacy](https://beepboop2025.github.io/financial-evidence-skills/privacy/) ·
[Support](https://beepboop2025.github.io/financial-evidence-skills/support/)
