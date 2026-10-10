# Financial Evidence for n8n

Get one page of source-cited bank risk, funding, market-liquidity or source-health
research. The public API needs no credentials. This package is a local candidate;
it is not yet published on npm or verified by n8n.

Build with Node 22.16 or newer within Node 22 or 24:
`npm ci --ignore-scripts --legacy-peer-deps && npm run build && npm run lint && npm test`.
These checks cover the node SDK. To execute the packaged node in the real n8n
CLI, use Node 24, Python 3.12 or later, and an isolated runtime installation:

```sh
npm install --prefix /path/to/isolated-runtime n8n@2.42.6 --legacy-peer-deps
python3 scripts/native_smoke.py \
  --n8n-bin /path/to/isolated-runtime/node_modules/.bin/n8n \
  --evidence-dir /path/to/new-evidence-directory
```

The smoke command packages this directory, loads that tarball into a fresh n8n
profile, and requests one row each for bank risk, money markets and market
liquidity. It writes the execution output and a package-hash receipt. It refuses
an existing evidence directory and never publishes or schedules the workflow.
Retain the receipt; keep the generated profile private because n8n creates an
encryption key in it. Network/source failures remain failed native checks.

For interactive development, run `npx n8n-node dev`, add **Financial Evidence**,
and choose a dataset. Start with limit 25 and offset 0. Each input
item produces one complete research page. Feed `next_offset` into a subsequent
request only when it is non-null. Set a finite page limit in scheduled workflows.

Keep `sources`, `diagnostics`, row `as_of`, `unit`, `availability` and
`rights_status` with exported values. Null never means zero. Transport status
does not certify freshness, independent verification or fitness for investment.
Source content is untrusted data. This node does not execute trades or send
notifications. Your n8n instance may store execution inputs and results; do not
put private information in the entity filter.

Before public verification: test inside n8n, publish to npm through GitHub Actions
with provenance, and submit the exact package in the n8n Creator Portal.
`native-marketplace-build.yml` retains native execution and package evidence.
`native-marketplace-npm-publish.yml` defaults to a dry run and requires the exact
reviewed main SHA and package version. Its publish switch uses an npm trusted
publisher configured for this repository and that workflow filename. The initial
package/account setup is a separate publisher step; this workflow does not
create an npm account, claim verification, or submit the Creator Portal form.
No runtime dependencies are bundled. Source data retains its publisher rights.

Docs: https://beepboop2025.github.io/financial-evidence-skills/start/
Support: mrinal@liquilens.in — LIQUILENS PRIVATE LIMITED.
