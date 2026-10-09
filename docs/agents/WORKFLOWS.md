# Put the upgrades into a daily research task

Choose a task, retain its first result, then repeat the same review on another
day. Public research needs no data API key. Each product keeps its source dates,
coverage and authority; connecting them does not produce a combined risk score.

For a first result without setup, [run the three workflows in your browser](../start/workflows.html).
For a recurring agent or local job, use the [package-free Python starter](../start/AUTOMATE.md).

## Finance-agent developers: add a cited funding check

Start with a small, named dataset before adding a larger tool catalog:

```sh
curl --fail --max-time 30 \
  'https://api.seiche.info/openbb/api/v1/agent-query?dataset=money_markets&entity=USD&limit=5'
```

Or connect `https://api.seiche.info/openbb/mcp`, discover its live schemas, and
call `financial_evidence_agent_query` with
`{"dataset":"money_markets","entity":"USD","limit":5}`.

Use this instruction in your existing researcher:

```text
Retrieve the published USD funding observations. Return a short research note
with each observation's value, unit, original date, source URL, availability and
rights. Describe missing or stale evidence explicitly. Save the response and
revision. On the next run, use the same query and previous_revision; recheck
source clocks even if rows are unchanged. Follow next_offset for a complete
table. Do not infer a trade, credit decision or validated forecast.
```

The first useful result is a cited observation or an explicit coverage blocker
that the developer can use in their actual task. A transport success alone is
not that result. Five rows are a bounded sample; inspect pagination. Use the
[capture client](../tools/setup.md) to retain complete selected tables, or the
[existing framework adapters](https://github.com/beepboop2025/financial-evidence-skills/tree/agent-v1.0.0/integrations/agents)
for LangChain/LangGraph, CrewAI, OpenAI Agents and Pydantic AI.

**Next use:** repeat the same task on another day. Only after that works, set up
the [recurring research runtime](runtime.html). Its fixed policies and receipts
support repeat research; installation alone does not establish adoption.

## Treasury and bank-risk teams: review a named watchlist

Open the [institution monitor](https://liquilens.in/banking/monitoring/) to choose
covered institutions and inspect the dated register. The new
`institution_evidence_monitor` tool is available at
`https://api.liquilens.in/mcp`. For example:

```json
{"slugs":["au-sfb","bajaj-finance"]}
```

The equivalent read-only REST request is:

```sh
curl --fail --max-time 30 \
  'https://api.liquilens.in/api/experimental/v1/banking/monitoring/watchlist?slugs=au-sfb,bajaj-finance'
```

These two institutions illustrate the interface; they are not recommendations
or a representative bank sample. Substitute exact identifiers from the register.
Use this instruction for your review:

```text
Review my selected institution watchlist with institution_evidence_monitor.
Show supported deterioration alerts and missing or overdue evidence separately.
For each selected institution, retrieve its detailed record with slug and
include_history=true; retain sources, reporting periods, knowledge dates,
policy version and record hash. List disclosures requiring human follow-up.
On the next review, compare with my retained record. A disappearing warning
means no longer observed, not recovery; missing evidence does not mean safety.
```

**First useful result:** a reviewer retains a sourced follow-up queue for their
own counterparties. **Next use:** review changed disclosures and unresolved gaps
on the next working day. Quarterly filing data is not an intraday withdrawal
feed. API access does not subscribe the team to delivered alerts. Keep any
approved delivery setup and the named human review separate.

Pair it with Seiche's `money_market_context` for jurisdiction-specific funding
context. Discover supported countries using `{"section":"countries"}` before
selecting one. Country coverage and source cadence differ; funding conditions
are not an institution's deposit liquidity.

## Traders and researchers: review funding and exit evidence

Open [Seiche](https://seiche.info/) and the
[Undertow exit desk](https://liquilens-undertow.com/exit/) for a browser review,
or use the [direct MCP connections](CONNECT.md). Start with Seiche `data_health`
and Undertow `agent_access_status`, then use the live schemas:

```text
Seiche money_market_context: {"section":"summary"}
Undertow crypto_exit_check: {"sizes_usd":[10000,100000],"max_age_seconds":7200}
```

The amounts are illustrative BTC sell-size comparisons, not position advice.
The age bound preserves the tool's current default; never widen it just to get
a number. Use this instruction:

```text
Prepare a research note with two separate sections: USD funding conditions and
hypothetical BTC exit costs for the selected sizes. Include original source
dates, age limits, venue coverage, rights and refusal reasons. Keep stale or
withheld values missing. These are indicative estimates, not executable quotes;
fees are excluded. Retain the note and compare the same sizes on the next day.
Do not place an order or treat a funding measure as a trading signal.
```

**First useful result:** a saved note states what is known, what is unavailable
and which source is needed next. **Next use:** repeat the same sizes and funding
review before the next research session, preserving comparability.

Use [NoiseFloor 0.4.0](CONNECT.md#optional-market-and-headline-analysis) when you
have your own entitled series or headlines to assess. It does not supply feeds.
For comparable series, the [correlation workbench](https://liquilens.in/agents/correlation/)
and [API/local Python kit](../api/noisefloor/) expose the same spectral assessment
with source-rights, freshness and missingness gates. Keep each product's panel
separate. The Dyson demonstration is synthetic, and the random-matrix reference
does not establish statistical significance or predictive market performance.
The [paper walkthrough](execution.html) separately rehearses expiry, duplicate
prevention, STOP and reconciliation with synthetic prices. It is not a live
execution service.

## Evaluate usefulness with the participating team

Record setup minutes, one useful output, one later task and the blocker that
would prevent continued use. With the participant's consent, use the
[14-day scorecard](pilot-scorecard.md). Developers, risk teams and individual
researchers are separate cohorts; an individual is not an organization.

Optional [Research Desk measurement](../start/measurement.md) covers only its
REST query and guided workflow routes when a visitor explicitly opts in.
The agent-query route, direct product MCP calls, direct institution monitor and
anonymous Python starter runs are outside linked installation coverage. The examples above do not enroll a user,
send separate analytics events or configure background jobs. Successful operator checks must
remain outside customer activation and retention counts.

Interface checks dated **9 October 2026**: the selected funding query, two-name
watchlist, institution MCP call, funding summary, access check and exit-size
comparison were exercised against the public services. These are interface
checks, not evidence of current observations in every field or customer use.
