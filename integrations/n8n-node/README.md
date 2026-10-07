# Financial Evidence for n8n

Get one page of source-cited bank risk, funding, market-liquidity or source-health
research. The public API needs no credentials. This package is a local candidate;
it is not yet published on npm or verified by n8n.

Build with Node 22.16 or newer within Node 22 or 24:
`npm ci --ignore-scripts --legacy-peer-deps && npm run build && npm run lint && npm test`.
These checks do not start the development server or its native VM. Install the
full development dependencies with lifecycle scripts enabled before native testing.
In a local n8n development environment run `npx n8n-node dev`, add **Financial
Evidence**, and choose a dataset. Start with limit 25 and offset 0. Each input
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
No runtime dependencies are bundled. Source data retains its publisher rights.

Docs: https://beepboop2025.github.io/financial-evidence-skills/start/
Support: mrinal@liquilens.in — LIQUILENS PRIVATE LIMITED.
