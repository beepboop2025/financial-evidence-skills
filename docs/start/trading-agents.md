# Financial-agent product inputs

The Finance starter calls Seiche, LiquiLens, Undertow, Palimpsest, NoiseFloor and
NarcoScope by name through their reviewed read-only tools. It supports their
direct endpoints and a configured central product gateway. Financial Evidence
provides optional local decision captures and a separate learning ledger; it is
not a mandatory replacement for the named product interfaces.

This is implementation and operator setup documentation. The new central agent
network/learning stack is not represented here as a publicly deployed service,
a broker integration or a validated trading strategy. Existing free product
features remain usable without learning enrollment or training contributions.

## Install and inspect

From this repository, use a Python environment on approved development storage:

```sh
python -m pip install -e '.[workspace]'
python -m financial_evidence.trading.cli catalog
python -m financial_evidence.trading.cli mcp-config
python -m financial_evidence.trading.cli review --mode test
```

`catalog` reports each named product and its first tool. `mcp-config` generates
editable MCP entries for an agent host; the host/operator decides which tools to
enable and use. It does not modify another agent's configuration automatically.
`review` requests two Seiche funding inputs plus Palimpsest's catalog and economic
observations. Failures remain visible per input. Its result explicitly says
`input_eligibility: not_evaluated`: transport success is not a freshness, rights
or trading-quality decision.

The default review mode is `test`. The CLI also supports `shadow`, `paper` and
`unknown`; the Python SDK additionally accepts `backtest` and
`operator_reported_production`. Selecting production mode is an operator report,
not evidence that a trade occurred. Test traffic is labelled synthetic to product
transports. This adapter does not place orders, access a brokerage account or
grant execution authority.

To use a provisioned central gateway, have the operator's secret manager inject
`SEICHE_NETWORK_TOKEN` into the process environment, and configure
`SEICHE_AGENT_PLATFORM_URL` to the reviewed deployment's HTTPS base URL. Then:

```sh
python -m financial_evidence.trading.cli --platform-url "$SEICHE_AGENT_PLATFORM_URL" review --mode shadow
python -m financial_evidence.trading.cli --platform-url "$SEICHE_AGENT_PLATFORM_URL" mcp-config
```

The token is read from the environment and never written into a generated
configuration, receipt or source file. Central product routes are
`/products/{product}/mcp`; the operator's gateway credential authorizes those
routes. Direct public product endpoints retain their own access rules. The
learning credential described below is separate.

For a central platform, `mcp-config` emits local stdio entries invoking
`financial-evidence-product-mcp --product PRODUCT --platform-url URL`. Install the
package in an environment available to the agent host, and let the host inherit
`SEICHE_NETWORK_TOKEN` from its configured secret environment. This adapter passes
the token to the gateway without copying it into the JSON. It discovers and
preserves the native tool schemas for the reviewed read-only subset. A host that
does not inherit the configured environment needs its own documented secret
injection mechanism. With no platform URL, the generated entries use the direct
public HTTP MCP endpoints.

## Use the Python SDK directly

```python
import asyncio
from financial_evidence.trading import ProductClient

async def review():
    client = ProductClient(mode="shadow", timeout=30, cache_seconds=0)
    result = await client.call(
        "seiche", "funding_stress_now", {}, task="funding_review"
    )
    return result

receipt = asyncio.run(review())
```

`ProductClient` restricts calls to the product's reviewed read-only tool allowlist.
It bounds input/output sizes, deadline and cache entries; redirects are not
followed. Cached results retain their original capture time. A cache hit is useful
local reuse, not another server request. Operators select cache duration and
apply observation-age checks independently.

The constructor accepts `platform_url` and `credential` when the central gateway
is desired. Supply these from the environment, not literals or URL credentials:

```python
import os
client = ProductClient(
    platform_url=os.environ["SEICHE_AGENT_PLATFORM_URL"],
    credential=os.environ["SEICHE_NETWORK_TOKEN"],
    mode="shadow",
)
```

## Select source-specific inputs before a trading evaluation

The [policy schema](../../integrations/trading-agents/funding-china-policy.json)
requires a concrete task/horizon, exact product-qualified series and separate
funding/China policies. It deliberately contains no invented live series ids or
unreviewed maximum ages. Select identifiers from the actual returned catalog and
observations, confirm units and source rights, and review their publication
calendars before approving a policy.

Each `Observation` records product, series, period, value/unit, source URL,
observation/publication/availability/capture times, revision, rights, quality and
context-only state. Map actual product records to these fields explicitly; an
HTTP retrieval timestamp is not a missing publication timestamp. Missing values,
unknown clocks, restricted rights and unavailable series remain unavailable.

Use a separate `InputPolicy` for each cadence rather than applying one stale-data
threshold to daily funding and monthly or quarterly China releases:

```python
from financial_evidence.trading import InputPolicy, assess

def assess_selected_group(observations, selected, decision_at):
    policy = InputPolicy(
        required_series=tuple(selected["required_series"]),
        max_observation_age_seconds=selected["max_observation_age_seconds"],
        allow_estimates=selected["allow_estimates"],
        require_captured_by_decision=True,
    )
    return assess(observations, policy, decision_at)
```

`selected` is one completed, reviewed group from the policy schema. The required
series use `seiche:actual_series_id` or `palimpsest:actual_series_id`; the suffix
must match a real observation, not those illustrative words. Check its unit
against `selected["units"]` before assessment. The SDK checks clocks, source age,
rights, missing values and quality; it does not automatically interpret every
market calendar. Holidays, combined release periods and revisions require the
reviewed source-specific policy. `input_eligible` means these configured checks
passed, not that an order is suitable or profitable.

Palimpsest's existing private/permission-required SAFE data, restricted
CFETS/ChinaMoney values and context-only series remain constrained. A shared
gateway cannot expand their publication or training rights. Institution-owned
licensed feeds, including Bloomberg where licensed, should be combined inside
the institution's authorised environment under their own entitlements.

## Capture exact decision evidence

`review --capture-dir /approved/private/receipts` writes selected returned receipts
only when the operator chooses local capture. The directory must be owner-only;
files are immutable and content-addressed with mode 0600. Capturing permitted
product results is separate from sending them to the learning service.

```python
from financial_evidence.trading.journal import save_receipt

saved = save_receipt("/approved/private/receipts", receipt)
reference = {key: saved[key] for key in ("kind", "product", "receipt_id", "sha256")}
```

Use `reference` in an explicitly enrolled private decision record. Do not send
the local `path` or extra capture metadata as an evidence reference. A hash binds
the captured bytes; it does not prove issuer identity, source truth or a trusted
historical timestamp. The existing runtime's v1 bundles remain unchanged.

## Optional measurement, separately enrolled

The default is off, even if a sink was supplied. To enable a local ledger, first
enroll the operator for the actual purposes and policy version. This example
chooses only measurement and sends no network traffic:

```python
import os
import time
from financial_evidence.learning import LearningStore

store = LearningStore(os.environ["FINANCIAL_LEARNING_STORE"])
enrollment = store.enroll(
    purposes=["measurement"], policy_version="finance-measurement-v1",
    expires_at=time.time() + 30 * 86400, retention_days=30,
)
credential = enrollment["credential"]
client = ProductClient(
    mode="shadow", measurement=True,
    event_sink=lambda event: store.record_tool(credential, event),
)
```

For an explicitly provisioned remote learning service, inject the endpoint and
separate learning credential through the operator's secret environment:

```python
from financial_evidence.learning.client import RemoteLearningClient

learning = RemoteLearningClient(
    os.environ["FINANCIAL_LEARNING_ENDPOINT"],
    os.environ["FINANCIAL_LEARNING_CREDENTIAL"],
)
client = ProductClient(
    mode="shadow", measurement=True, event_sink=learning.record_tool,
    platform_url=os.environ["SEICHE_AGENT_PLATFORM_URL"],
    credential=os.environ["SEICHE_NETWORK_TOKEN"],
)
```

When using this learning ledger, the task allowlist is exactly `money_markets`,
`funding_review`, `liquidity`, `institution_evidence`, `china_macro`, `research`,
`other`. The starter uses `funding_review`; the SDK default is `other`. A custom
task label outside this list is rejected by the learning sink. No prompts, raw
arguments, returned payloads, portfolios, IPs or private model reasoning enter
the tool event. Metadata includes status, duration, cache state and explicit usage
mode. Optional sink failures increase `client.measurement_failures` while the
free product call remains usable; inspect this counter to detect collection gaps.

Measurement does not enroll the operator for private decision storage, research
training or commercial training. See [the complete learning contract](learning.md)
for selected numeric features, independent outcomes, local source-rights review,
retention, withdrawal, baseline evaluation and dataset/model lineage. The initial
model experiment may correctly report `insufficient_data`; traffic volume is not
a substitute for reviewed outcome pairs.

## Connect agents to the Seiche network

The network client uses a provisioned agent token to contact the hosted network's
REST API. It needs no server SQLite file, server signing key or institutional
owner credential. With the same approved platform environment:

```sh
python -m financial_evidence.trading.network --endpoint "$SEICHE_AGENT_PLATFORM_URL"
```

This starts a local stdio MCP adapter for the operator's agent host. The exposed
tools cover identity, opted-in directory, contacts/invitations, private room
creation/acceptance, inbox, messages, receipt acknowledgements and task state.
Agents must accept contacts and room membership before exchanging messages.
Incoming content remains untrusted evidence; a message or receipt acknowledgement
never authorizes a trade or disclosure. Private messages do not enter shared
training by default.

The service implementation is maintained separately in the Seiche repository at
`services/agent-network`, on the development branch
`feat/stage-one-agent-network-20261011`. Its intended
[branch source location](https://github.com/beepboop2025/seiche/tree/feat/stage-one-agent-network-20261011/services/agent-network)
may require that branch to be published; this document does not claim the branch
has merged to main or that a production endpoint is available. Operators should
use its reviewed deployment/operations instructions and provision credentials
before distributing a central configuration.
