# Execution integration for financial AI agents

Publisher: LIQUILENS PRIVATE LIMITED. Updated 8 October 2026.

Use the [browser walkthrough](execution.html) to explore order identity, a
timeout and reconciliation without credentials. All of its data and fills are
synthetic. For broker integration, use the separate Carrier source below.
The Financial Evidence package and public research MCP remain read-only.

## Evidence walkthrough

The browser workbench contains five authored, synthetic examples. It makes no
requests to a broker or product API and collects no interaction analytics.
The scenario clock is fixed at **8 October 2026, 12:00 UTC**; source observation
and retrieval timestamps are example inputs, not assertions about real data.
Your proposal's separate 60-second expiry uses your browser clock.

| Scenario | Product's role | Illustrated decision |
| --- | --- | --- |
| Eligible illustration | All three product checks satisfy the example policy | Pass for explicit simulated submission |
| Funding pressure | Seiche SOFR/IORB and EFFR/IORB spreads produce 18 bp pressure | Hold under an experimental operator STRAIN rule |
| Stale CP observation | LiquiLens CP rollover is older than eight days, despite a recent retrieval | Unavailable |
| Missing permissions | Undertow venue rights are unknown | Unavailable |
| Expensive SELL liquidation | Undertow hypothetical SELL cost is 38 bp against a 25 bp limit | Limit; no automatic resizing |

These examples illustrate selected rules of `liquilens.paper-funding-exit.v1`.
The funding pressure calculation is `max(SOFR-IORB, abs(EFFR-IORB))`, with
CALM at ≤5 bp, EROSION above 5, STRAIN above 15 and STRESS above 25. STRAIN and
STRESS hold the request. These are experimental operator bands, not Seiche's
full composite, calibrated forecasts or investment recommendations.
Both commercial-paper observation dates must be less than eight days old.
Undertow observations must be less than 300 seconds old, with hypothetical
SELL cost at most 25 bp and venue spread at most 15 bp.

The original BUY or SELL proposal and its hypothetical SELL liquidation have
distinct identities. Exit-cost evidence never becomes an executable BUY quote.
Example permissions are assumed only inside the eligible examples and do not
grant real venue rights. The browser supports illustrative notionals up to
$1,000; the installed paper host has its own fixed $1,000 profile and complete
source/account validators. No browser result is an authenticated Carrier receipt.

Each retained assessment binds the exact side, notional, account sequence and
evidence revision. Changing the scenario invalidates outstanding submissions;
it does not erase history. Journal schema `liquilens.execution-walkthrough.v2`
exports every retained assessment, including refusals, with a detached copy of
its evidence and decision. The export also includes orders, account balances,
STOP state and the current evidence. Invalid form inputs are not assessments.
Timeout reconciliation and repeated submission use the original intent and
never produce a second simulated fill. Export before reloading to retain the
session; this in-memory walkthrough is not durable execution storage.

For actual inputs, inspect [Seiche funding observations](../start/?dataset=money_markets&entity=USD),
the [LiquiLens corporate-funding source](https://api.liquilens.in/api/public-signals/corporate-transmission)
and [Undertow liquidity coverage](../start/?dataset=market_liquidity).

## Install the reviewed source

The execution components currently ship from an exact source commit, not the
Financial Evidence wheel or a new PyPI release. Requires Python 3.11–3.14 and uv.

```sh
git clone https://github.com/beepboop2025/liquilens-evidence-carrier.git
cd liquilens-evidence-carrier
git checkout --detach ee6bdd549e4ac478342e64551f755f5a6389e36a
uv sync --project integrations/trading-copilot --locked
```

Review this commit before enabling any tool. Keep local state in a private,
durable directory outside the agent's filesystem access. Do not put broker keys,
host tokens, HMAC keys, private requests or account records into prompts or Git.

## Observe the current product evidence

After installing the reviewed Carrier source, collect a current, independent
report for Seiche funding context, LiquiLens commercial-paper observations and
Undertow hypothetical exit context:

```sh
uv run --project integrations/trading-copilot --locked \
  liquilens-trading-copilot observe --format json
```

Use `--format markdown` for a readable report with the complete JSON included.
The observer contacts the three configured public product endpoints. By default
it loads no operator configuration or broker credentials, contacts no broker
and opens or modifies no trading state. A denied or missing source stays in the
report alongside the other products, with its reason, source clocks, retrieval
clock, source hash and next action. Producer observation dates on rejected rows
remain unadmitted claims; a recent retrieval does not make them eligible.

The report uses a distinct diagnostic identity for a hypothetical **$1,000
BTC/USD SELL** scenario. `source_checks_passed` reports source admission;
`source_policy_checks_passed` additionally checks the selected funding and
exit-cost limits. Neither is order readiness. `ready_for_order`,
`receipt_issued`, `order_authorized`, `order_submitted` and `state_modified`
always remain false. No executable request, receipt or submission is created.
Check each report's evaluation time and source expiry before using it as a
dated diagnostic; it is not a permanent health assertion.

An optional paper-account readback requires explicit private configuration and
credential files:

```sh
uv run --project integrations/trading-copilot --locked \
  liquilens-trading-copilot observe --format json --check-account \
  --config /absolute/private/operator-state/config.json \
  --env-file /absolute/private/operator-state/paper.env
```

This opt-in check uses only fixed-origin GET requests for the paper account,
positions and open orders. It verifies account binding and ACTIVE/USD/block
flags, returning counts and flags without account identifiers, balances or
secrets. Missing credentials affect only the account row. It does not use
receipt-signing authority, write operator state or enable execution. Keep the
input files private and provide them directly, never through a prompt.

For recurring source checks, follow the [source observatory deployment guide](https://github.com/beepboop2025/liquilens-evidence-carrier/blob/ee6bdd549e4ac478342e64551f755f5a6389e36a/integrations/trading-copilot/OBSERVATORY-DEPLOYMENT.md).
It installs a separate observer service and timer with bounded private history.
The timer collects **thirty minutes** after the preceding run completes, with
up to fifteen seconds of jitter: at most 48 scheduled calls per day, leaving
room beneath Undertow's separate 60-call proof and 200-call public-tool limits.
Startup and manual checks also count. Monitoring snapshots do not replace fresh
order-specific evidence or grant order authority.

The scheduled service template requires a dedicated Undertow identity issued by
the source operator. It supplies the private token with systemd `LoadCredential`;
the observer and paper host use separate identities and retain their normal
quotas across token rotation. A service name alone is not registration. For an
operator-issued token, the explicit local command is:

```sh
uv run --project integrations/trading-copilot --locked \
  liquilens-trading-copilot observe --format json \
  --undertow-token-file /absolute/private/source-access.token
```

The token is sent only to the fixed Undertow exit-context route. It is separate
from broker credentials and grants neither venue-data rights nor order authority.
An unreadable or rejected configured token produces an unavailable source;
the client never retries anonymously. The deployment guide covers registration,
private storage and rotation. These instructions describe a private installation,
not a public managed execution endpoint.

A completed capture may still report `source_quota_exhausted` for a validated
MCP quota refusal or `source_clock_in_future` when an upstream clock exceeds
the observer's trusted evaluation clock. Preserve either source as unavailable.
Wait for the provider allowance to reset or change, or verify the conflicting
clocks; do not retry repeatedly or relax eligibility limits to obtain a pass.

## Paper account

**Existing bound paper account:** follow the [same-state host attachment guide](https://github.com/beepboop2025/liquilens-evidence-carrier/blob/ee6bdd549e4ac478342e64551f755f5a6389e36a/integrations/trading-copilot/HOST-ATTACH.md).
The guarded check/prepare/apply flow preserves the existing account, broker/HMAC
credentials, limits, lock and audit history. It adds private agent access without
initializing another account directory. It requires disabled paper configuration,
an inactive prior owner and no execution history; interrupted publication resumes
only from its reviewed manifest. Do not run `init` against an existing account.

The attached unit requires `--require-disabled` at startup. It can serve private
capability and source-assessment requests while refusing trading activation.
Future activation requires a deliberate reviewed unit change as well as every
source/account gate; routine credential renewal cannot remove that requirement.

**New installation:** initialize a disabled host with generated read/execution tokens:

```sh
uv run --project integrations/trading-copilot --locked liquilens-agent-host init \
  --state-dir /absolute/private/paper-state
```

Provision your own paper account ID and paper credentials in the generated
owner-only files. Follow the [complete host guide](https://github.com/beepboop2025/liquilens-evidence-carrier/blob/ee6bdd549e4ac478342e64551f755f5a6389e36a/integrations/trading-copilot/AGENT-HOST.md)
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
  --state-dir /absolute/private/paper-state --port 8766 --require-disabled
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
and all credentials blank. The [live connector contract](https://github.com/beepboop2025/liquilens-evidence-carrier/blob/ee6bdd549e4ac478342e64551f755f5a6389e36a/integrations/trading-copilot/LIVE-CONNECTOR.md)
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
