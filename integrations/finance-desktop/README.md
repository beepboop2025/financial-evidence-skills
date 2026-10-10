# Finance desktop research companion

A small browser panel for the four rights-qualified Seiche ECB reference-FX series. It fetches one selected currency on demand, displays ten recent published observations and saves a note containing exact values, source comments and separate collection clocks.

It works as an independent browser companion beside research or trading software. The current cTrader URL-plugin builder is an additional candidate deployment route, with native building, testing and review still pending. No Bloomberg, LSEG, FactSet, IBKR, MQL5, NinjaTrader, Kite or Upstox native compatibility is claimed by this page.

## Files and local use

Serve this directory with a local static server:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory integrations/finance-desktop
```

Open `http://127.0.0.1:8765/`, select a currency and choose **Fetch reference observations**. The `?currency=INR` parameter preselects one of the four allowed currencies; other query parameters are ignored. The panel requests no brokerage account data and stores no identifier. It does not install a broker SDK or contain account/trading API calls.

The parent platform hub publishes exactly these four files together:

- `index.html`
- `panel.css`
- `panel.mjs`
- `reference-fx.mjs`

Planned public path: `https://beepboop2025.github.io/financial-evidence-skills/platforms/desktop/`. Public deployment/readback must be verified independently; source availability alone does not establish that URL is live.

## Verification

```sh
node --test integrations/finance-desktop/test_reference_fx.mjs
```

Six tests cover exact decimal retention, source allowlisting, missing/zero/invalid-value rejection, corrupt units/clocks/dates, credential-free GETs and explicit access/content-type failures. They verify parser and transport behavior, not native rendering.

`verification.json` records the dated verification scope. A live read was parsed for all four series. Retained sample evidence is outside the repository on the designated SSD, with a public hash manifest and 80-row sample under `docs/distribution/provider-packets-20261011/`.

Rebuild the sample only into chosen new evidence/output directories:

```sh
python3 integrations/finance-desktop/capture_reference_fx.py \
  --output /path/on/SSD/new-sample \
  --evidence /path/on/SSD/new-raw-evidence
```

The capture compares only the last twenty available dates per currency against ECB's current 90-day XML. It does not prove full-history parity or point-in-time eligibility. Review source policy before creating a different data product.

## cTrader candidate

[Current official builder](https://help.ctrader.com/plugins/developers/all-apps/build-a-plugin/) accepts a hosted web URL through Algo → Plugins → Create. The current documentation describes web/mobile/desktop placements and a 300×300 owned logo. Start with a large separate window or Trade Watch tab and the published companion URL. Native account, builder declarations and testing are still required.

The current panel makes no host SDK calls. If the native builder requires SDK initialization, add only the documented minimal handshake after validating the need. Do not copy the official all-operations demo: it includes mutations irrelevant to the research panel. Confirm cross-origin fetches, saved notes, mobile readability, source notices and error behavior in each intended client before claiming native support or publishing a Store product.

## Other routes

The broker-independent panel is immediately useful beside other tools. MQL5 requires an actual compiled MQL product and has external-service/link restrictions; NinjaTrader User App Share requires a native source export. These gates are documented in the platform-specific packets. Upstox has a separate official read-only MCP; its paired research workflow is in `docs/distribution/provider-packets-20261011/upstox.md`.
