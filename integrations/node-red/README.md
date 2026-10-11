# Financial Evidence for Node-RED

Three manual, read-only research previews using only Node-RED's core nodes:

- USD money-market observations from Seiche.
- Filing evidence for `au-sfb`, one currently covered institution, from LiquiLens.
- Indicative BTC market-liquidity research measures from Undertow.

[Open the setup guide](https://beepboop2025.github.io/financial-evidence-skills/automations/node-red/) or import [`financial-evidence.flow.json`](financial-evidence.flow.json) through **Menu → Import**. Deploy, click one task's Inject button, then open the Debug sidebar and expand the evidence preview. Deploying alone makes no request.

No credentials, additional nodes or model are required. The imported flow has no timers, sends, writes or trading actions. Public usage limits and your own Node-RED hosting costs apply.

## Scope and configuration

Double-click an Inject node to edit its JSON payload. Keep `dataset` to `money_markets`, `bank_risk` or `market_liquidity`; `entity` is a substring filter of at most 100 characters. `limit` is 1–200 (default 25). Each click retrieves **one page** from the fixed HTTPS query endpoint. There are no automatic retries or pagination. A 20-second timeout applies; redirects are disabled. The response receives a 2 MiB size check after the HTTP node has buffered it.

`synthetic: false` is for actual research. Use `true` for operator/CI verification, which sends `X-Liquilens-Traffic-Class: synthetic`; verification runs must not be counted as independent adoption.

The output keeps the **entire original table** in `payload.table`, including row units, dates, source URLs, content hashes, rights, nulls, diagnostics and source-reported states. The wrapper separates `pagination_complete`, `transport_complete` and `source_partial_reported`. A source can report `PARTIAL` even when retrieval is complete. The wrapper never declares evidence verified or assigns financial authority.

Empty coverage and unavailable values remain empty/null. A malformed response, inconsistent pagination, missing provenance or unexpected numeric unavailable value goes to the failure Debug node. Network failures also have a readable failure branch. For a full bounded export, use the [Python capture guide](https://beepboop2025.github.io/financial-evidence-skills/tools/#python).

These are dated research observations, not credit ratings, executable quotes, forecasts or point-in-time backtests. Bank coverage is limited. Undertow's public measures retain their segment and retrospective-validation limits. Unknown source rights remain unknown. MIT flow code does not grant redistribution rights to upstream data.

## Build and verification

```sh
node integrations/node-red/build_flow.cjs
node integrations/node-red/test_flow.cjs
```

The builder emits identical repository and website JSON downloads. The offline checks exercise malformed input, redirects, HTML, overflow numbers, pagination, lost metadata, partial sources and null preservation.

For native acceptance, install the pinned `node-red@5.0.8` in an isolated directory, then pass its absolute module path and a new evidence directory:

```sh
node integrations/node-red/native_acceptance.cjs \
  /absolute/runtime/node_modules/node-red \
  /absolute/evidence/node-red
```

The harness creates a fresh user directory, binds the admin server to `127.0.0.1` on an automatically assigned port, sets only its test copy to synthetic traffic, invokes all three native Inject endpoints, verifies failure branches and stops its own runtime. It does not modify existing Node-RED installations, user flows or the public download.

On 11 October 2026, native Node-RED 5.0.8 execution passed for all three tasks, two native failure branches and 33 offline checks. See [verification.json](verification.json) for the exact flow hash, observed row counts and scope. Verification traffic is synthetic; no independent adoption is inferred.

The downloadable flow is separate from Node-RED Flow Library inclusion. The library's [submission route](https://flows.nodered.org/add) requires GitHub sign-in; this repository does not claim acceptance.

Official references: [JSON import/export](https://nodered.org/docs/user-guide/editor/workspace/import-export), [core nodes](https://nodered.org/docs/user-guide/nodes), [embedding Node-RED](https://nodered.org/docs/user-guide/runtime/embedding).
