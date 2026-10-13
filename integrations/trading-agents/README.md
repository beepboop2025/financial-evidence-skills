# Finance agent starter

The starter gives agent operators direct named product tools, a funding/China
review, optional exact local captures, and explicitly enrolled learning. The
central pilot is live at [agents.seiche.info](https://agents.seiche.info).
Public product tools work anonymously, without enrollment or a token. Agent
messaging and optional learning require their own provisioned permissions.

Install the repository with `python -m pip install -e '.[workspace]'`, then:

```sh
python -m financial_evidence.trading.cli catalog
python -m financial_evidence.trading.cli --platform-url https://agents.seiche.info mcp-config
python -m financial_evidence.trading.cli --platform-url https://agents.seiche.info review --mode test
```

This explicit central setup is recommended for new pilot integrations. With no
platform URL argument or `SEICHE_AGENT_PLATFORM_URL` environment variable, the
existing direct product endpoints remain the default; no configuration is
silently rerouted. To identify calls with a provisioned agent, optionally inject
`SEICHE_NETWORK_TOKEN` through the operator's secret environment. The CLI reads
it without printing or embedding it:

```sh
python -m financial_evidence.trading.cli --platform-url https://agents.seiche.info review --mode shadow
```

The configuration command emits product stdio bridges that preserve native
read-only tool schemas and read an optional inherited token without embedding it
in JSON. For private agent messaging, obtain a provisioned agent token, inject it
as `SEICHE_NETWORK_TOKEN`, then start the network's stdio MCP bridge:

```sh
python -m financial_evidence.trading.network --endpoint https://agents.seiche.info
```

The bridge uses REST endpoints; it never requires the server's database or signing
keys. The learning service at `https://agents.seiche.info/learning` requires a
separate enrollment and learning credential. Core public tools remain free and
independent of optional training.

Inspect [public source status](https://agents.seiche.info/v1/data-status) for
transport availability and scoped `fresh`, `stale`, `restricted` or `unknown`
source states. Check `monitor_current` and each source's reasons and rights before
use. An available pilot route does not establish that all products are healthy,
that a source is eligible for trading, or that large production workloads have
been validated.

Read the [full setup and SDK guide](../../docs/start/trading-agents.md) for exact
local/remote optional measurement examples, secret handling, cache semantics,
private receipt references and network permissions. Read the
[learning contract](../../docs/start/learning.md) before enrolling a participant.

`funding-china-policy.json` is a **JSON Schema for an operator-selected policy**,
not a pre-approved trading policy. Complete the actual series, units, source
calendar, rights review, task horizon and independent funding/China age policies.
The starter deliberately reports `input_eligibility: not_evaluated` until the
operator normalizes observations and applies those policies. Calendar and unit
review cannot be replaced by generic HTTP health checks.

For a reviewed dataset exported by the learning store:

```sh
python integrations/trading-agents/evaluate.py dataset.json --store "$FINANCIAL_LEARNING_STORE" --entity US-USD --output experiment.json
```

The original store rechecks expiry/withdrawal before evaluation. Results preserve
domain-only baselines and usage comparisons where data exists. Insufficient data
remains an explicit result; synthetic test fixtures do not establish forecast
performance or production adoption.
