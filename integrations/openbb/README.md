# Financial Evidence for OpenBB

Use Seiche, LiquiLens, Undertow and Palimpsest from one OpenBB research desk.
The Workspace release adds seven datasets, nine Workspace widgets, seven dashboard
tabs, eight SDK-backed MCP tools, two research prompts and a typed REST API.

Workspace is independently versioned as **workspace-1.2.0**, with the exact source
commit exposed at `/api/v1/release`. The published **v0.1.5 artifacts and public
three-tool MCP endpoint retain their existing contract**. A hosted custom backend
is separate from acceptance in OpenBB's directory.

The hosted production backend is **https://api.seiche.info/openbb**. Add that
URL as a custom backend in OpenBB Workspace. Its MCP endpoint is
`https://api.seiche.info/openbb/mcp`; interactive documentation is at
`https://api.seiche.info/openbb/docs`. Check the release and source status before
relying on any current deployment.

## Start the Workspace backend

In a clean Python 3.10+ environment, from this checkout:

```bash
python -m pip install '.[workspace]'
financial-evidence-api
```

In OpenBB Workspace, add a **custom backend** with URL
`http://127.0.0.1:6900`. Select **Financial Evidence Research Desk** under My Apps.
The backend serves `/widgets.json`, `/apps.json` and `/mcp` from the same process.
No financial-data account or API key is required. OpenBB itself may require an
account. If the browser is on a different machine, use a reachable HTTPS backend
origin instead of that browser's own loopback address.

The app has USD Funding Review, Funding & Capital, Benchmark History, Bank Research, Market
Liquidity, China Coverage and Source Audit tabs. The history widget initially
charts US-USD; keep one entity selected when comparing a series over time.
Other widgets present tables, keeping units, dates, availability and limitations
next to the observations. Tables can be exported from Workspace.

USD Funding Review reads one immutable scheduled capture containing nine required
observations and consistency checks. Inspect `review_asof`, `review_scope`,
`latest_per_instrument` and each row's `newer_observation_available` before
interpreting `ready`: this is a dated common SOFR-IORB review, not the latest
individual print of every instrument. These fields remain in saved CSV exports.
`/api/v1/funding-review` provides its capture
age, exceptions and source hashes; `/api/v1/funding-review.csv` exports its rows
for spreadsheets and SQL. If capture storage is missing or overdue, the review
reports unavailable/stale and CSV returns 503. A captured review with data issues
retains the issues rather than silently substituting an older passing review.

## Python / notebooks

Current repository source supports OpenBB V4 (`openbb-core` 1.6.13) and V5
(`openbb-core` 2.0.1), with generated-query checks in CI for Python 3.10 and
3.13. The published v0.1.6 wheel retains its original V4-only dependency range.
Use a fresh environment for V5, as the [OpenBB migration guide](https://docs.openbb.co/odp/python/migration-from-v4)
requires. From a current clone of this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[openbb,workspace]' 'openbb-core==2.0.1'
openbb-build
```

For a clean V4 environment, substitute `openbb-core==1.6.13`. Record the checkout
commit when installing source. The [portable research kit](https://beepboop2025.github.io/financial-evidence-skills/tools/)
also works without installing OpenBB and follows pagination for complete captures.

```python
from openbb import obb

catalog = obb.financial_evidence.datasets().to_df()
result = obb.financial_evidence.query(dataset="money_markets")
rates = result.to_df()
print(rates[["entity_id", "metric", "value", "unit", "as_of", "availability"]])
print(result.extra["financial_evidence"]["sources"])

history = obb.financial_evidence.query(
    dataset="money_market_history", entity="US-USD",
    start_date="2026-09-01", end_date="2026-09-28", limit=2000,
)
print(history.to_df())

# Exact name/ID substring, not a ticker resolver or unsupported-issuer lookup.
banks = obb.financial_evidence.query(dataset="bank_risk", entity="ESAF")
print(banks.extra["financial_evidence"]["total_rows"])
```

`routes()` and `fetch()` retain their existing interfaces. New query results use
typed rows and retain pagination and source diagnostics in `extra.financial_evidence`.
OpenBB reserves `extra.metadata` for its own command execution details.
An empty entity match is not a statement about that institution's risk.
For an empty result, inspect `results` and metadata before calling `to_df()`;
OpenBB raises when there are no rows to convert.

## Datasets

| Dataset | Published content | Main boundary |
| --- | --- | --- |
| `money_markets` | One row per declared benchmark | Native units and source availability; cross-currency rate levels are not stress rankings |
| `money_market_history` | Published benchmark history | Original cadence, explicit gaps; current history, not an as-published vintage archive |
| `capital_markets` | VIX and high-yield OAS observations | Each value's own observation clock |
| `bank_risk` | Covered-bank monitoring scores and model probabilities | Corpus research, not credit ratings or validated forecasts; construction-PIT limitations remain attached |
| `market_liquidity` | Public Undertow measure percentiles | Restricted percentiles stay null; source replay limitations remain attached |
| `china_economy` | Palimpsest publication status and NBS series catalog | Metadata only; no restricted economic values |
| `source_health` | All six source routes, hashes, reported clocks and errors | Transport status is not freshness, eligibility, rights approval or Carrier verification |

Use `/api/v1/datasets` or `datasets()` to discover supported filters. The
default limit is 200 rows; the maximum is 2,000. Follow `next_offset` until null.
Source content hashes identify the documents used by each page. If those hashes
change between pages, restart the query rather than mixing snapshots.
Date filters are inclusive and apply to observation dates. Undated metadata is
excluded by date filters. Transport failures remain in `diagnostics` even if
the entity filter removes their placeholder rows.

## REST and MCP

```bash
curl 'http://127.0.0.1:6900/api/v1/query?dataset=money_markets&entity=USD'
curl 'http://127.0.0.1:6900/api/v1/sources'
```

Interactive API documentation is at `/docs`; the typed specification is at
`/openapi.json`. Add `http://127.0.0.1:6900/mcp` as a Streamable HTTP MCP server
in OpenBB, or connect it from the app's MCP entry. It exposes:

- `financial_evidence_datasets`: offline catalog and coverage.
- `financial_evidence_funding_review`: latest archived funding review, exceptions and capture age.
- `financial_evidence_query`: filtered, paginated, cited table rows.
- `financial_evidence_sources`: source health and provenance audit.
- `financial_evidence_route`: offline routing to fixed public sources.
- `financial_evidence_packet`: original bounded documents when table detail is insufficient.

All tools declare read-only, non-destructive behavior. The query tools advertise
structured output schemas. Dataset and scope resources plus funding and bank
review prompts support repeatable research. For stdio clients, run
`financial-evidence-workspace-mcp` from this same environment. The original
dependency-free `financial-evidence-mcp` keeps its three-tool compatibility contract.

## Hosting and verification

```bash
financial-evidence-api --host 0.0.0.0 --port 6900 \
  --public-base-url https://evidence.example.org
```

Terminate HTTPS at your reverse proxy. `FINANCIAL_EVIDENCE_BASE_URL` is the
environment equivalent of `--public-base-url`. `FINANCIAL_EVIDENCE_ALLOWED_ORIGINS`
accepts additional comma-separated, explicit browser origins; OpenBB's
`https://pro.openbb.co` and `https://my.openbb.co` are already included. Wildcards
and credentialed origins are rejected. The server has host and MCP origin checks.
Apply deployment-specific rate and connection limits at the proxy for a public
service. It is a public read-only backend and has no built-in user authentication.

A safe path prefix such as `/openbb` is supported; configure the proxy to strip
it before forwarding. The checked-in [Caddy fragment](Caddyfile.fragment) includes
a 64 KiB request limit and delegates origin checks to the application. Uvicorn
limits concurrent connections to 64; the service template bounds container CPU,
memory and processes. These limits do not create per-organization entitlements.

Set `FINANCIAL_EVIDENCE_REVIEW_DIR` to the read-only mounted review archive. The
[capture service and timer](../funding-review/OPERATIONS.md) must write that archive
under the same dedicated UID as its container reader. Capture ownership does
not grant the API write access to the archive.

The cache stores at most six fixed sources in process memory, with four network
workers and one in-flight request per source. Successful responses cache for 60
seconds, failures for five. Cached retrieval time and source dates never advance.
An expired success is not served after a refresh failure. The money-market atlas has a 4 MiB response limit; other sources keep a 1 MiB
response cap and a ten-second socket timeout; the timeout is not an absolute
whole-response deadline. Each server process has its own cache.

Use the separate container recipe from the repository root:

```bash
docker build -f integrations/openbb/Dockerfile --build-arg SOURCE_COMMIT="$(git rev-parse HEAD)" -t financial-evidence-workspace .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  -p 127.0.0.1:6900:6900 financial-evidence-workspace
python scripts/verify_openbb_workspace.py --url http://127.0.0.1:6900
```

The verifier identifies its traffic as operator verification and checks all
dataset endpoints, manifests, initialization and MCP query output. Its requests
are not adoption evidence. `/healthz` checks the backend process only; inspect
`/api/v1/sources` for upstream transport and publisher metadata.

The implementation follows OpenBB's [custom backend contract](https://docs.openbb.co/workspace/developers/data-integration),
[widget specification](https://docs.openbb.co/workspace/developers/json-specs/widgets-json-reference)
and [app specification](https://docs.openbb.co/workspace/developers/json-specs/apps-json-reference).
Read the [semantic contract](../../SEMANTIC_CONTRACT.md) for evidence boundaries.

## Browser research and optional measurement

The [Research Desk](https://beepboop2025.github.io/financial-evidence-skills/start/) uses the same typed query endpoint without installation. The GitHub Pages origin is explicitly allowed; arbitrary browser origins remain blocked. Optional, revocable measurement uses `/api/v1/applications` and a separate private usage mount. See [measurement scope, storage, limits and the private scorecard](../../docs/start/measurement.md). Install the workspace usage expiry service/timer alongside the API only when this measurement mount is enabled.

## Guided workflows

`GET /api/v1/workflow?workflow=funding|institutions|exit&selection=...` returns
`financial-evidence.workflow-result.v1` with the original product response, a
source link and content hash. Defaults are USD, au-sfb/bajaj-finance, and
10,000/100,000 USD BTC sells. Select up to five institutions or four sizes.
The route uses fixed upstream endpoints, a 1 MiB response bound for direct
product calls, no redirects and no forwarded caller credentials. Existing
funding source caching and bounds remain in place.

The browser desk can save a local summary baseline and export the full JSON.
Optional workflow measurement uses the existing revocable installation key;
prepared responses are not completed tasks, independent people or paid users.
