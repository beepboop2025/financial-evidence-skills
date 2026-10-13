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
Trade Safety sandbox, Financial Evidence research wrapper, source-data explorer
and Seiche Market Atlas corpus wrapper. The fourteen products keep explicit
reviewed tool allowlists. MyQuant App
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

## Current hosted surface migration

OpenBB Workspace now uses `https://agents.seiche.info/v1/research` as its custom
backend. Its root, widget/app manifests, guide, thumbnail, API docs, OpenAPI,
health, reviewed research reads and funding CSV export use the same central
namespace. Public MCP remains `/products/financial-evidence/mcp`.

The [current hosted NoiseFloor kit](api/noisefloor-hosted/) uses
`https://agents.seiche.info/v1/noisefloor` for capabilities, schema and the four
reviewed research POST operations. Input is explicitly selected by the caller.
Operation demand excludes request bodies, arbitrary selector text and credentials.
The [verified 0.4.0 archive](api/noisefloor/) retains its original bytes and
local implementation; it is not silently relabeled as a current hosted release.

See [the migration guide](HOSTED_MIGRATION.md) to review an older JSON config
before replacing connections. Published old packages do not update themselves.
Legacy browser deletion still sends its saved `fe_` key only to its original
issuer; new desk research does not forward that key.

Native response source links remain provenance. A source link is not a claim
that every subsequent request is observed by this platform.

The source-data browser and bounded reads use `/v1/source-data/`; banking
coverage, individual filing histories and monitoring use `/v1/banking/`.
Five admitted economy series use `/v1/economy/series/`; corpus coverage uses
`/v1/corpus/v1/catalog`. Public source-data and corpus MCPs are distinct products
at `/products/research-data/mcp` and `/products/seiche-market-corpus/mcp`.
Their source schemas and rights restrictions are preserved. Wider native API
documents remain publisher references, not central transport guarantees.
