# Reuse a product connection

Use one client context for a bounded agent job. It retains a separate MCP session
for each exact hosted product endpoint, saving repeated initialization:

```python
import asyncio
from financial_evidence.trading import ProductClient

async def main():
    async with ProductClient(mode="test", timeout=15) as client:
        first = await client.call("seiche", "data_health")
        second = await client.call("seiche", "data_health")
        print(first["timing"], second["timing"])

asyncio.run(main())
```

`mode="test"` marks diagnostic traffic synthetic. It does not create a verified
user, trade, or adoption event. Supply a credential explicitly only for an
authorized integration; anonymous access stays anonymous. Session pools are
never shared between clients, principals, or event loops.

Outside a context, `ProductClient.call()` retains its existing one-shot behavior.
`await client.aclose()` explicitly closes owned sessions; a closed client cannot
be reused. Injected custom transport callables retain their four-argument API and
remain owned by the caller.

Calls to one endpoint are serialized. Different endpoints can proceed
concurrently. Defaults allow 14 sessions and 16 queued requests per session;
`max_sessions` (1–14) and `max_pending` (1–128) can lower those limits. Capacity
exhaustion raises `MCPCapacityError` locally. A request's timeout includes queue
waiting and initialization. An active cancellation or session failure invalidates
that session and fails its queued work with `MCPTransportError`. Cancelling a
queued request does not interrupt the active request. No failed request is
automatically replayed. A subsequent explicit request can establish a new
session. There is no fallback to a native origin. Default HTTP transport rejects
redirects and compressed responses and bounds each response stream to 2 MiB.
Remote session termination has a five-second cleanup deadline, enforced in the
session's owning task.

Each receipt's `timing` reports local monotonic `duration_ms`, excluding optional
measurement delivery. Default transport calls also report `initialization_ms`,
`tool_ms`, `queue_ms`, and `session_reused`. These are client measurements, not
exchange latency or source age. The initial call includes initialization; reused
sessions report zero initialization time. Cache hits have no transport timing.
Source payloads, their hashes, and original cached `captured_at` stay unchanged.
The returned data still requires source-specific freshness and rights policies;
reusing a connection never grants execution authority.
