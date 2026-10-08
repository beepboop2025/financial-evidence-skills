# Execution integration for financial AI agents

Publisher: LIQUILENS PRIVATE LIMITED. Updated 8 October 2026.

Use the [browser walkthrough](execution.html) to explore order identity, a
timeout and reconciliation without credentials. All of its data and fills are
synthetic. For broker integration, use the separate Carrier source below.
The Financial Evidence package and public research MCP remain read-only.

## Install the reviewed source

The execution components currently ship from an exact source commit, not the
Financial Evidence wheel or a new PyPI release. Requires Python 3.11–3.14 and uv.

```sh
git clone https://github.com/beepboop2025/liquilens-evidence-carrier.git
cd liquilens-evidence-carrier
git checkout --detach aebba668c55079b27b46c7584b3f0743c201a84f
uv sync --project integrations/trading-copilot --locked
```

Review this commit before enabling any tool. Keep local state in a private,
durable directory outside the agent's filesystem access. Do not put broker keys,
host tokens, HMAC keys, private requests or account records into prompts or Git.

## Paper account

Initialize a disabled host with generated read/execution tokens:

```sh
uv run --project integrations/trading-copilot --locked liquilens-agent-host init \
  --state-dir /absolute/private/paper-state
```

Provision your own paper account ID and paper credentials in the generated
owner-only files. Follow the [complete host guide](https://github.com/beepboop2025/liquilens-evidence-carrier/blob/aebba668c55079b27b46c7584b3f0743c201a84f/integrations/trading-copilot/AGENT-HOST.md)
for identity, network isolation, activation, recovery and supported limits.
The default profile is exactly **$1,000 BTC/USD market IOC**. It requires the
relevant product evidence and account checks before submission.

Check the local setup without contacting the broker or changing any files:

```sh
uv run --project integrations/trading-copilot --locked liquilens-agent-host doctor \
  --state-dir /absolute/private/paper-state
```

The report identifies missing configuration, credentials, token scopes and
private-file requirements without printing secrets. Exit code 2 means local
setup has blockers. Passing local checks does not establish current source
eligibility, an authorized account or execution readiness.

```sh
uv run --project integrations/trading-copilot --locked liquilens-agent-host serve \
  --state-dir /absolute/private/paper-state --port 8766
```

In another terminal:

```sh
uv run --project integrations/trading-copilot --locked liquilens-agent capabilities \
  --token-file /absolute/private/paper-state/agent-read.token
uv run --project integrations/trading-copilot --locked liquilens-agent assess \
  --token-file /absolute/private/paper-state/agent-read.token \
  --intent-id my-first-research-decision --side buy --notional-usd 1000
```

Save the intent before assessment and its assessment ID before any submission.
An assessment may be unavailable or held. It does not submit an order.
The execution token, operator enablement and all source/account checks are
separate requirements. Never use a new intent to retry an uncertain order.

**Dated source check, 8 October 2026 at 03:29 UTC:** the standard paper profile
was unavailable. Undertow returned `rights_manifest_not_approved`; the
LiquiLens CP-rollover observation dated September 30 exceeded the profile's
eight-day age limit. Seiche's selected funding inputs were available.
This is a dated observation, not a permanent readiness claim. Reassess current
sources in your installation. Do not mark missing rights approved or increase
an age limit solely to make an order pass.

## Embed in an AI platform

REST works with any customer runtime. The private MCP bridge supports clients
that can launch a stdio server. Merge this entry into your existing MCP config,
replacing both absolute paths:

```json
{
  "mcpServers": {
    "liquilens-paper": {
      "command": "uv",
      "args": [
        "run", "--project", "/absolute/checkout/integrations/trading-copilot",
        "--locked", "liquilens-agent-mcp", "--token-file",
        "/absolute/private/paper-state/agent-read.token"
      ]
    }
  }
}
```

The default catalog exposes `paper_capabilities`, `assess_paper_order` and
`paper_order_status`. An operator can add `--allow-submit` and provision the
execution token to expose `submit_paper_order` and `reconcile_paper_order`.
This does not enable the host or bypass its policy. Use the same exact IDs for
status and reconciliation. STOP blocks new submissions; an acknowledgment is
not a fill. The host owns broker/HMAC credentials and the durable journal.

Connect public [research MCPs](CONNECT.md) separately for source discovery.
Their tool permissions do not authorize the private execution service.
For LangGraph, CrewAI and custom runtimes, use your runtime's MCP client or
the authenticated REST methods in the complete host guide. No accepted upstream
plugin, framework endorsement or production customer is implied.

## Customer-owned live connector

The separate live connector is an **integration candidate**, tested with HTTP
broker doubles. No real live-account activation or fill is claimed. It supports
Alpaca limit orders, explicit symbol/size scope, cash/exposure/daily-loss limits,
durable single-attempt submission, cancellation requests and reconciliation.

```sh
uv run --project integrations/trading-copilot --locked liquilens-live init \
  --state-dir /absolute/private/live-state
uv run --project integrations/trading-copilot --locked liquilens-live capabilities \
  --state-dir /absolute/private/live-state
uv run --project integrations/trading-copilot --locked liquilens-live doctor \
  --state-dir /absolute/private/live-state
```

These commands contact no broker. Initialization leaves live execution off
and all credentials blank. The [live connector contract](https://github.com/beepboop2025/liquilens-evidence-carrier/blob/aebba668c55079b27b46c7584b3f0743c201a84f/integrations/trading-copilot/LIVE-CONNECTOR.md)
specifies customer authorization, dedicated account ownership, trusted issuer
binding, entitled execution-grade inputs and the verified broker-preview
reference needed before a live order. Its local preflight does not create that
preview. Paper receipts, public research data and simulator results cannot
authorize live orders. There is no public managed live execution endpoint.

The offline doctor checks local configuration and explains the outstanding
qualification requirements. It always reports `live_ready=false`; neither
nonempty credentials nor a local activation flag prove live eligibility.
Alpaca's documented Broker API estimation endpoint is indicative and excludes
crypto and limit orders, so it cannot supply the preview required by this
Trading API limit-order connector. [Broker estimation scope](https://docs.alpaca.markets/us/reference/get-v1-trading-accounts-account_id-orders-estimation).

Local recovery remains available when credentials are removed:

```sh
uv run --project integrations/trading-copilot --locked liquilens-live orders \
  --state-dir /absolute/private/live-state --unresolved-only
uv run --project integrations/trading-copilot --locked liquilens-live status \
  --state-dir /absolute/private/live-state --request-hash <saved-hash>
```

These read an existing private journal without a broker connection. They report
the last observed outcome; they cannot confirm a new fill or cancellation.
The `export` operation emits a bounded page of sanitized journal metadata.
Keep any exported account/order records private. This export is not a full
database backup; use the connector's documented recovery procedure.

## Start without an existing broker account

The [browser simulator](execution.html) is usable immediately with synthetic
balances and quotes. It requires no broker account and places no broker orders.

For a dedicated paper account, follow [Alpaca paper signup](https://app.alpaca.markets/signup)
and complete the account-owner verification prompts and required MFA. Signup
and MFA create a paper account; live-account applications are separate.
Generate **paper** keys in the paper dashboard and provision them directly into
the private installation described in the host guide. Never paste credentials
into an agent prompt or a public issue. [Official signup requirements](https://alpaca.markets/learn/live-trading-account-non-us),
[paper account API](https://docs.alpaca.markets/us/docs/paper-trading).

Account setup alone does not admit source evidence. The default product-evidence
profile also requires current observations and the applicable data permissions.
Its doctor explains local blockers; an execution assessment must still pass the
source and account checks at the time of the request.

Platforms connecting existing customers through OAuth need their own approved
Alpaca Connect application and explicit paper-environment authorization. This
source integration does not provide a shared approved OAuth application or a
managed credential service. [App registration and review](https://docs.alpaca.markets/us/docs/registering-your-app).

## Evaluate a recurring workflow

Start with one task and measure: integration time, first useful evidence result,
source refusals, independently observed paper outcomes and return use on another
day. Browser walkthroughs, our tests, downloads and anonymous requests are not
verified customers. [Measurement definitions](../start/measurement.md).

For an integration pilot, contact [mrinal@liquilens.in](mailto:mrinal@liquilens.in)
with your runtime, broker, instrument scope and recurring task. Do not send keys
or confidential account data. Pricing and a paid mandate are separate agreements;
running these public examples creates neither.
