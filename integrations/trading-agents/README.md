# Finance agent starter

The starter gives agent operators direct named product tools, a funding/China
review, optional exact local captures, and explicitly enrolled learning. The new
central gateway and Seiche Agent Network require an operator deployment; this
directory does not imply they are already live.

Install the repository with `python -m pip install -e '.[workspace]'`, then:

```sh
python -m financial_evidence.trading.cli catalog
python -m financial_evidence.trading.cli mcp-config
python -m financial_evidence.trading.cli review --mode test
```

For a reviewed central deployment, inject `SEICHE_AGENT_PLATFORM_URL` and
`SEICHE_NETWORK_TOKEN` through the operator's environment. The CLI reads the
credential without printing it:

```sh
python -m financial_evidence.trading.cli --platform-url "$SEICHE_AGENT_PLATFORM_URL" review --mode shadow
python -m financial_evidence.trading.cli --platform-url "$SEICHE_AGENT_PLATFORM_URL" mcp-config
python -m financial_evidence.trading.network --endpoint "$SEICHE_AGENT_PLATFORM_URL"
```

The configuration command emits product stdio bridges that preserve native
read-only tool schemas and read the inherited token without embedding it in
JSON. The last command is a stdio MCP bridge to the hosted Seiche network. It uses an
agent token and REST endpoints; it never requires the server's database or
signing keys. Core public tools remain free and independent of optional training.

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
