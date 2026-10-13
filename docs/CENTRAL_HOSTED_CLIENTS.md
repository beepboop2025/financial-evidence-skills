# Central hosted clients

Current-source clients request public data through `https://agents.seiche.info`.
An unavailable gateway remains an explicit failure; clients do not silently use
native origins, stale local data or an anonymous retry after an auth rejection.
Public access remains free and needs no account. An optional workspace credential
attributes ordinary requests to owned usage reports.

## Connections

`ProductClient`, `financial-evidence-trading` and `financial-evidence-product-mcp`
default to `/products/{product}/mcp`. The catalog contains seven core products
plus Riptide research, MyQuant Editorial, MyQuant App metadata, the read-only
Trade Safety sandbox and the Financial Evidence research wrapper. MyQuant App
discovery does not expose on-device reading state. Sandbox checks do not execute
orders. Wrapper requests and nested source requests are nonadditive measurements.

An explicit custom platform URL or injected test transport remains supported.
Credentials go only to the configured platform, never into generated configs,
receipts or native source URLs. Redirects are rejected.

The legacy CLI/MCP, both standalone skill helpers, `EvidenceService`, framework
tools, OpenBB extension and research runtime fetch eight fixed datasets at
`/v1/data/{dataset_id}`. The gateway selects the reviewed upstream; no arbitrary
URL is accepted. `Source.url`, source adapters, original bytes, hashes and source
clocks keep their original meaning. `resolved_url` identifies the actual central
transport. Packet, CLI, stdio MCP and standalone helper reads default to a
4 MiB per-source allowance so the money-market atlas fits. An explicitly smaller
`max_bytes`/`--max-bytes` allowance remains a hard limit; oversized responses
remain unavailable. `EvidenceService` defaults to zero success/error cache time: sequential
reads request the service again. Concurrent in-flight requests and repeated source
references within one packet still share a fetch. Explicit local cache durations
remain available; cache hits are not server requests or unique completed tasks. Local projections and cached receipts do not become new source facts.

Institution and exit workflows use the reviewed
`liquilens.institution_watchlist` and `undertow.exit_check` routes with bounded
selectors. Python, Excel and Google Sheets research downloads use
`/v1/research/api/v1/query`; agent queries/reviews and workflow requests have
separate bounded endpoints. The browser research desk, guided workflows and
package-free workflow starter use those same hosted routes. Legacy browser
installation keys are never forwarded; explicit deletion remains at their issuer.
The standalone LangChain toolkit uses the hosted
catalog and these agent routes; current Node-RED, n8n, Dify and Zapier sources use
the same central query route. Generated task workflows use product MCP routes.
Unsupported operations are not generic proxies.

## Measurement

The hosted service counts fixed product/tool/dataset demand, request outcomes,
traffic classes and coarse timing. Private prompts, arbitrary selector values,
query text, credentials and response bodies are not demand dimensions. A request
is neither an independent user nor a successful trade. Tests are labeled
synthetic. A metadata lookup is not a data-engine interaction.

Optional learning and task sharing remain separate, explicitly enabled systems.
`measurement=False` disables the optional SDK learning sink; it does not claim
that a hosted service receives no ordinary request. Optional sink failure cannot
turn usable data into a failed call. Local cache hits are distinguishable from
server requests, and offline replay makes no network request.

## Distribution and limits

Current editor/plugin configs and `docs/connect/all-products.mcp.json` use hosted
MCP. The research kit includes the updated Python, spreadsheet and notebook
clients. The notebook verifies exact helper bytes before execution; the complete
kit supplies those bytes alongside it. A standalone notebook needs the matching
helper to have been published at its configured source URL.

Historical package tags, previously installed configurations, downloaded data
and independently operated open-source copies do not change automatically.
They remain outside central coverage until their operators upgrade. Native
product services retain their own deployment authorities and source contracts;
this client release does not turn the central service into universal visibility.

## Current native surfaces still outside central coverage

These are explicit exceptions in current public instructions, in addition to
immutable older releases. This migration does not claim whole-fleet coverage.

- **OpenBB Workspace custom backend:** `https://api.seiche.info/openbb`, still
  linked by `docs/tools/index.html`, `docs/tools/setup.md` and
  `integrations/openbb/README.md`. Its UI contract uses `GET /`, `/widgets.json`,
  `/apps.json`, `/guide`, `/thumbnail.svg`, `/docs`, `/openapi.json` and `/healthz`
  without query parameters. Widget definitions use `GET /api/v1/query` with
  dataset, entity, start_date, end_date, limit and offset, and
  `GET /api/v1/funding-review` without parameters. Those two research reads have
  central equivalents, but the custom-backend UI still resolves its relative
  widget URLs against the native base. `/api/v1/funding-review.csv` is a native
  CSV export with no parameters; the central JSON gateway does not proxy it.
  Source: `src/financial_evidence/workspace.py` and `workspace_config.py`.
- **NoiseFloor REST client kit 0.4.0:** `docs/api/noisefloor/` is a versioned,
  source-hash-bound bundle advertised by the current site. Its Postman, Bruno
  and HTTP examples still call `POST https://api.seiche.info/noisefloor/v1/spectral/assess`
  and `/v1/research/dyson`, with JSON bodies and no query parameters. Spectral
  input contains at most 32 series of at most 2,048 observations each, `as_of`
  and bounded window/step policy. Dyson input contains dimension 2–16, steps
  1–100, dt 0.000001–1 and a 32-bit unsigned seed. Its included schema also
  describes `POST /v1/market/assess`, `POST /v1/narrative/triage`, and
  `GET /v1/capabilities` and `/healthz`. These numeric/text input contracts need
  their own reviewed POST gateway and retention boundaries before migration;
  the original kit and manifest have not been silently rewritten. Current
  NoiseFloor MCP connections already use `/products/noisefloor/mcp`.
- **Legacy browser deletion:** only explicit
  `DELETE https://api.seiche.info/openbb/api/v1/applications/current` uses a
  saved legacy `fe_` key, sent exclusively to its original issuer. New desk
  research does not enroll or forward that key.

Native backend responses can still contain native documentation, resource or
source links as returned provenance. The central proxy does not rewrite source
identity or claim that every link is an independently observed central request.
