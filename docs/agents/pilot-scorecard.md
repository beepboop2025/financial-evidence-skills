# A 14-day AI integration pilot

Use one recurring financial task to establish whether the integration is useful.
The public [research tools](./) work without a data API key. The
[execution walkthrough](execution.html) demonstrates the order lifecycle with
synthetic prices. Paper-broker activation depends on eligible sources; a source
refusal is a measurable integration result, not an executed order.

## Pick one workflow

| Team | First task | Evidence of useful completion |
| --- | --- | --- |
| Quant-agent developer | Add funding, covered-bank or liquidity context to a research step | Developer retains a cited result with source dates and explains how it informed the task |
| Trading-platform builder | Connect the private paper host through REST or MCP | Their own paper account is assessed; when eligible, an order is submitted once and reconciled |
| Financial AI infrastructure team | Embed exact-intent and timeout handling in an existing runtime | Their runtime preserves request identity and refuses a duplicate or unavailable assessment |

Do not require all three product datasets for a task that needs only one. Never
relax source rights, freshness or account controls to make a pilot pass.

## Record these checkpoints privately

| Checkpoint | When | What to retain |
| --- | --- | --- |
| First independent use | Day 0–2 | Consenting organization alias, integration source version, workflow, elapsed setup time and outcome |
| First useful result | Day 0–3 | Customer confirmation and a redacted cited result or paper reconciliation receipt |
| Second distinct task | Day 2–7 | A separate dated task, its outcome and the reason they returned |
| Day-seven use | Day 7–10 | Customer-confirmed use on another day, unresolved blockers and support time |
| Continuation decision | Day 10–14 | Continue, change or stop; willingness to pay and the concrete feature or reliability requirement |

Keep customer account IDs, credentials, balances, order contents and trading
strategies out of public issue trackers and analytics. Collect only the pilot
records the participant agrees to share. Delete them when no longer needed.

Suggested private CSV columns:

```text
organization_alias,consent_recorded,workflow,source_version,first_independent_use_at,first_useful_result_at,second_task_at,day_seven_use_at,setup_minutes,blocker_code,continuation_decision,payment_verified
```

## Initial targets, not traction claims

For the first cohort, aim for five independent activated organizations, three
returning organizations and one agreed paid continuation. These are proposed
targets. Actual results are currently unverified and must remain unknown until
supported by customer records. A paid continuation is only a paying customer
after payment is independently reconciled.

Report conversion with both numerator and denominator. Measure activation from
consenting independent evaluators, and retention from organizations that have
had enough time to reach the checkpoint. Record product, workflow and first
discovery source separately so the team can prioritize the useful route.

Do not count CI, operator checks, page fetches, bots, package downloads, local
simulation runs or a successful HTTP response as activated customers. The
browser execution walkthrough collects no usage analytics. The research desk's
[optional installation measurement](../start/measurement.md) also does not
identify verified people or organizations.

## Handle blockers and improve the next attempt

- Setup fails: keep the exact version and redacted error, fix the smallest
  reproducible integration problem, then repeat that user's task.
- Source unavailable: report its original date, rights state and reason;
  retain the refusal and continue any independently useful research task.
- Broker response uncertain: reconcile the original client order ID. Never
  generate a fresh intent to escape the uncertainty.
- No return use: ask which recurring task was missing before adding features.
- Useful repeat use: agree scope and support expectations before proposing a
  paid plan. Do not invent an advertised price or platform certification.

Start an evaluation through [support](../support/) or the
[integration pilot contact](execution.html). Do not send credentials.
