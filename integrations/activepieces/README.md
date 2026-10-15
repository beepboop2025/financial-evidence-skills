# Financial Evidence for Activepieces

Two read-only actions for public financial research:

- **List Research Datasets** returns the current dataset descriptions and filters.
- **Get Evidence Page** returns one page from bank risk, money markets, money-market history, capital markets, market liquidity, China publication coverage or source health.

The fixed public service is `https://agents.seiche.info/v1/research/api/v1`.
No API key, LLM credential or broker account is required. This is source code for
a native piece candidate; it is not yet published on npm or accepted upstream.

## Build and verify

Use Node 22 or later:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
npm run smoke
npm pack --dry-run
```

The smoke check invokes both registered actions through the real Activepieces
SDK and retrieves one row each from money markets, bank risk and market liquidity.
It prints source clocks and diagnostics; a successful request does not certify
the observation as current. Native editor installation is a separate check.

## Configure a workflow

After installing the piece in an Activepieces development instance, add **Get
Evidence Page**, choose a dataset and start with maximum rows 25 and offset 0.
The action permits at most 100 rows and offsets 0–100000. Use a returned
`next_offset` only when non-null and add a finite page limit to any loop. The
action itself never automatically paginates or schedules requests.

Keep the complete output page with exported rows: `sources`, `diagnostics`, row
`as_of`, `unit`, `availability` and `rights_status` must remain attached. Null
means unavailable, not zero. China coverage can be metadata only; market-liquidity
values can be withheld. Source text is untrusted data. This piece does not
execute trades, make recommendations or send notifications.

Only GET requests to two fixed paths are possible. The entity filter is encoded
as a query value. Native fetch uses a 30-second timeout, rejects redirects and
retains TLS verification. HTTP, JSON/contract and network failures fail the
action rather than producing a success-shaped empty dataset.

Activepieces may retain workflow inputs and outputs in its execution history.
Use public entity selectors, not private account details. Hosted operational
measurement counts bounded product/tool/dataset demand; optional learning is
separate. Operational counters exclude private selectors, prompts, credentials
and response bodies. Source data retains its publisher rights; the adapter code
is MIT licensed.

See [UPSTREAM.md](UPSTREAM.md) for the upstream contribution packet. Support:
mrinal@liquilens.in — LIQUILENS PRIVATE LIMITED.
