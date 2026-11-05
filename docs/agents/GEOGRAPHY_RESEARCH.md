# Geography research with LiquiLens

Use the reviewed `lending_geography` read tool to inspect district observations
and documented cooperative-bank geography. The request goes through the same
configured Financial Evidence product gateway as other LiquiLens read calls.
It does not grant credit, valuation, trading or training authority.

```python
import asyncio
from financial_evidence.trading import ProductClient

async def review():
    async with ProductClient() as client:
        receipt = await client.call(
            "liquilens", "lending_geography",
            {"id": "in-dist-rajasthan-jaipur", "offset": 0},
            task="geography_research",
        )
        return receipt

receipt = asyncio.run(review())
```

The client needs its existing MCP transport dependencies. Use the already
configured platform endpoint and credentials; this tool does not introduce an
additional account or send queries to arbitrary source URLs. Optional learning
remains off by default.

Accepted IDs start with `in-dist-`, `in-state-`, `in-dccb-` or `in-stcb-`.
Only `id` and an optional integer `offset` between 0 and 1000 are accepted.
Discover district IDs and inspect the same observations in the
[public geography workspace](https://liquilens.in/banking/geography/).
For a state or bank, follow the response's `next_offset` only when present;
each response contains a bounded district page. Retain the page scope and total
when exporting or summarising a result.

Keep each source's observation date, licence, coverage and missingness. The
response generation date does not make older soil-moisture or vegetation
observations current. `null` is unavailable, not zero. A bank's documented area
of operation is not a measurement of its lending share. District observations
and dated NASA GIBS imagery use independent sources and dates; image comparison
alone does not quantify land-use change.

For reproducible handoffs, share a geography URL with `evidence`, `offset`,
`before`, `after` and `view` parameters, or use the workspace's source-complete
brief export. The [land and planning companion](https://liquilens.in/banking/real-assets/)
keeps asking prices, recorded transactions, government guidance values and
planning records distinct. Satellite views do not establish legal boundaries,
property title, permitted development, market value or creditworthiness.

The native MCP bridge exposes this tool only when upstream discovery advertises
it. It preserves the upstream schema and result instead of fabricating a local
answer when service or coverage is unavailable.
