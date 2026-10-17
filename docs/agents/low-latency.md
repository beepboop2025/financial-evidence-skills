# Reliable agent data delivery

The published clients provide persistent MCP sessions, compact source-status snapshots,
bounded SSE clients, latency diagnostics, and a synthetic feed recovery pilot.
The hosted context stream reports source metadata. It does not publish live
prices, establish source redistribution permission, or authorize an order.

## Install and verify

Use a dedicated Python 3.10+ environment. Install or upgrade the published
package for persistent clients, complete-event timeouts and initial-reset
validation:

```sh
python3 -m pip install --upgrade 'financial-evidence[workspace]'
financial-evidence-trading doctor
financial-evidence-trading latency --samples 3
financial-evidence-trading context
financial-evidence-trading context --events --limit 1
financial-evidence-trading source-access
financial-evidence-trading feed-pilot
```

For JavaScript AI SDK tools, install
`@moomoo202020/financial-evidence-ai-sdk@0.1.2`; see the
[verified npm setup](../platforms/ai-sdk.md). The Python client bounds the wait for a
complete event even when partial bytes or comments arrive. Python and JavaScript
streams require an initial reset before a keepalive. These clients retain no
trade-execution authority.

`latency` labels requests synthetic, ignores ambient credentials, makes no
retries, and stops each product's probe after its first failure. The first call
includes session establishment and MCP schema discovery. Repeat calls reuse
the session; local response caching is disabled, but upstream caches may apply.
Reports retain hashes and timing rather than returned data. Small samples do
not report p95/p99 or certify an SLA. Record the calling region and workload
alongside a result before making a performance comparison.

`source-access` exits successfully when the catalog was inspected; its permission
states still decide availability. `feed-pilot` returns nonzero on a failed
synthetic acceptance check. Neither command connects to a venue or buys data.

## Persistent product reads

```python
from financial_evidence.trading.client import ProductClient

async def research():
    async with ProductClient(mode="test") as client:
        first = await client.call("undertow", "liquidity_tiers", {})
        again = await client.call("undertow", "liquidity_tiers", {})
        return first["timing"], again["timing"]
```

Use the appropriate declared mode for actual work; test traffic remains separate
from external usage. One client owns its sessions and credential identity.
Cancellation invalidates an in-flight session. Failed calls are not replayed;
a later explicit call may establish a new session. See
[lifecycle and limits](persistent-client.md). Existing one-shot calls remain
compatible; the local stdio bridge retains its separate bounded transport.

## Compact snapshots and updates

The public contract is
<https://agents.seiche.info/v1/context/contract>. The snapshot and SSE endpoints
are `/v1/context/snapshot` and `/v1/context/events`. A background reader prepares
snapshots from the existing scheduled freshness report. Requests do not trigger
an upstream market-data fetch.

```python
from contextlib import aclosing
from financial_evidence.trading.context import ContextClient

async def source_status():
    async with ContextClient() as client:
        snapshot = await client.snapshot()
        async with aclosing(client.events()) as stream:
            async for event in stream:
                if event["event"] in {"reset", "snapshot"}:
                    return snapshot, event["data"]
```

For Node 22+ or a modern fetch runtime, download [context-client.mjs](context-client.mjs):

```javascript
import {contextSnapshot, contextEvents} from './context-client.mjs';
const snapshot = await contextSnapshot();
for await (const event of contextEvents({timeoutMs: 30000})) {
  if (event.event === 'reset') { console.log(event.data); break; }
}
```

Both clients check monitor expiry on receipt and preserve the original clocks.
Recheck `valid_until` while holding a snapshot; receipt-time validation cannot
keep a previously obtained result current forever. A heartbeat establishes
transport liveness only. `current` means the monitor is recent, not that every
source is fresh or admitted for trading. Source rows retain their own cadence,
coverage, restrictions, and missingness. A daily rate is never a tick quote.

Each connection begins with a full `reset`. IDs are `stream_id:sequence`; a new
process has a new stream ID. Reconnect always returns latest state and explicitly
reports `replay_complete=false`. Slow consumers may receive a coalesced reset,
not all intervening updates. There is no market-event replay guarantee.
Snapshots are capped at 16 KiB, sessions at 300 seconds, writes at 5 seconds,
and subscribers at 64 per process. The JavaScript client's default total
deadline is 30 seconds; reconnect explicitly with bounded backoff. Python event
reads use the configured idle timeout and a separate monotonic deadline for each
complete event. Partial bytes and comment frames do not renew that deadline;
processing time in the consuming application does not consume the next read's
budget. Both clients reject keepalives before the initial reset. The CLI
additionally bounds the whole run. A timeout closes the stream; reconnecting is
explicit and never replays an order or grants source permissions.

## Source access and the feed pilot

Read the [source qualification and procurement packet](source-access.md) before
connecting a feed. It includes current restrictions, missing permissions and
unsent provider inquiries. The [machine-readable catalog](source-access-contracts.json)
keeps connection, internal research, AI inference, redistribution, trading, and
training permissions separate. None of the external source contracts currently
grants the proposed production AI-feed use.

The replay pilot exercises source timestamps, heartbeat versus quote freshness,
sequence gaps, restart quarantine, rights expiry, and a reviewed policy reload.
Its values and clocks are invented fixtures. Production adapters still require
verified permissions, authenticated source lineage, venue/instrument units,
sequence semantics, persistence/replay qualification, and observed capacity.

## Operating and proving the service

The server's private operator metrics separate synthetic and unknown traffic.
An optional five-minute systemd observer stores bounded delivery measurements
and independently rechecks monitor validity. A successful HTTP read is recorded
separately from fresh source availability. Inspect natural timer recurrence and
the actual source timestamps; one manual success is not sustained reliability.

Proposed targets remain unverified: same-region compact reads p95<100ms,
our event ingestion-to-publication p99<50ms, and 99.9% monthly API availability.
These require a declared load, controlled regional probes, sufficient samples,
and a complete observation window. The context metadata stream does not
implement or establish the live-feed event-latency target.

The next acceptance stage is a narrow authorized feed and independent pilot
operators. Measure returning integrations, useful tasks, errors, stale-input
rejections and paid continuation. [Pilot scorecard](pilot-scorecard.md).
Private outcomes remain separately consented; calls and downloads are not trades.
