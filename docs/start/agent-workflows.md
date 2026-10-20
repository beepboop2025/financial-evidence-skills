# Repeat a financial evidence review in your agent

Run the same funding, institution or BTC exit review again and compare it with
the last successful capture. The main Python package includes a private journal,
explicit usefulness feedback, decision/outcome records and optional delivery
queue. Public research uses the existing central gateway without a key.

Install the published Python package, then run a review. Offline Markdown display
and retained-review comparison require version 0.1.14 or newer:

```sh
python3 -m pip install --upgrade financial-evidence
financial-evidence workflow run funding --selection USD --state ./funding-reviews
financial-evidence workflow report --state ./funding-reviews
financial-evidence workflow history --state ./funding-reviews
```

The base Python package needs no optional dependencies for this workflow. The
private SQLite journal uses POSIX ownership/permissions (Linux or macOS).
Repeat `run` at your next review to get the comparison. The private directory is
created automatically. For installation checks, add `--mode test`; both public
requests are labeled synthetic. Normal usage defaults to `unknown`. Select
`paper`, `shadow` or `operator_reported_production` only when it describes your
application. These are operator labels, not verified trades.

```sh
financial-evidence workflow run institutions --selection au-sfb,bajaj-finance --state ./institution-reviews
financial-evidence workflow run exit --selection 10000,100000 --state ./exit-reviews --format json
```

Each run checks the source monitor, reads bounded research, verifies the Python
evidence digest, rechecks monitor expiry and saves original evidence plus its
comparison. Funding accepts a three-letter currency; institutions accepts up to
five covered slugs; exit accepts up to four sizes up to USD 1,000,000. A valid
selection can still be outside source coverage.

| Status | Application action |
| --- | --- |
| `ready_for_review` | Inspect original dates, missing values, rights and coverage. |
| `blocked_monitor` | Keep the blocked result; obtain a current monitor before another review. |
| `context_unavailable` | Retain the attempt; investigate connection or contract diagnostics. |
| `evidence_unavailable` | Retain the gap; do not turn it into zero or success. |

The CLI exits 0 for a prepared review, 2 for blocked/unavailable evidence and 1
for invalid input or local state. A current monitor can describe stale,
restricted or missing sources. `input_eligibility` stays `not_evaluated` and
`execution_authority` stays `none`. Source text remains untrusted data.

## Put the hook in your application

```python
from financial_evidence.agent_workflow import AgentWorkflow

reviews = AgentWorkflow("./funding-reviews", mode="unknown")
result = reviews.run("funding", "USD")
if result["status"] == "ready_for_review":
    print(result["run_id"], result["comparison"])
    print(result["result"]["evidence"])
```

Your application owns timing and source-eligibility policy. Installation starts
no background job. For LangGraph, the [recurring_review.py adapter](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/trading-agents/recurring_review.py)
returns a synchronous node updating `financial_review`:

```python
# Import review_node from the adapter copied into your application.
graph.add_node("evidence_review", review_node("./funding-reviews"))
```

Include `financial_review` in your state schema and connect this node before the
research step consuming it. In async applications, use a worker thread, such as
`await asyncio.to_thread(reviews.run, "funding", "USD")`. Give each application
its own private journal. A scheduler can invoke the CLI; it owns cadence,
exit-status handling and retries.
The adapter is exercised with LangGraph 1.2.16 in CI using its
[documented state-update node contract](https://docs.langchain.com/oss/python/langgraph/graph-api).

## Confirm usefulness and record observed outcomes

A completed read is never automatically marked useful. After inspecting the
saved run, record feedback with its printed ID:

```sh
financial-evidence workflow feedback RUN_ID --useful --state ./funding-reviews
financial-evidence workflow show RUN_ID --state ./funding-reviews
```

Use `--not-useful` for a negative rating. Feedback is immutable and idempotent;
repeating the rating does not inflate the useful-workflow count.

Supply your application's actual numeric decision/outcome records under the
[existing learning contracts](learning.md). A decision includes `id`,
`decided_at`, `target`, `entity`, `horizon_seconds`, `mode`, `data_features` and
`usage_features`; `evidence_refs` is optional on input. The command attaches the
saved review's exact evidence reference. Features must have been observed and
available by the decision time; the decision must follow the run with the same
mode. An outcome includes `id`, `decision_id`, `value`, `unit`, `observed_at`,
`available_at`, `source` and `revision`.

```sh
financial-evidence workflow decision RUN_ID --record decision.json --state ./funding-reviews
financial-evidence workflow outcome --record outcome.json --state ./funding-reviews
```

Only one immutable outcome is accepted per decision, observed after its horizon.
Outcomes remain operator-reported. The existing service separately validates
registered target units and independent review. A delivery receipt or claimed
result does not establish profitability.

## Enable optional contributions explicitly

Local records remain local by default. The public gateway still receives
ordinary operational requests under its existing usage policy. To contribute
learning records, obtain a separate enrollment with the required purposes and
retention terms. Configure `FINANCIAL_LEARNING_CREDENTIAL` through your secret
manager, then explicitly queue:

```sh
financial-evidence workflow run funding --state ./shared-reviews --share-usage
financial-evidence workflow feedback RUN_ID --useful --state ./shared-reviews --share
financial-evidence workflow deliver --state ./shared-reviews
```

`--share-usage` queues bounded product/tool/task, time, duration, mode and version
metadata. It excludes research results, selectors, prompts and credentials.
Decision/outcome records need their own `--share`; share the decision before its
outcome. Later sharing remains subject to the service's permission and
no-backfill checks. Nothing grants training rights automatically.

Only `deliver` sends queued records. Its default destination is
`https://agents.seiche.info/learning`; explicitly selected deployments can use
`--learning-endpoint`. The outbox is bound to an endpoint/credential fingerprint.
Credentials are never stored. Use a new journal for another enrollment.

Retries keep the original ID/digest, honor rate-limit delays and require matching
ingestion receipts. A lease prevents overlapping workers; delivery is at least
once and relies on the service's immutable IDs after crashes. Permission/client
rejections stop retries. An outcome waits for its decision's matching receipt.
`deliver` exits 2 when pending, rejected or expired records need attention;
`report` exposes their counts separately.

```sh
financial-evidence workflow discard-pending --state ./shared-reviews
```

This stops queued delivery and erases queued payloads. It does not withdraw
already accepted remote records; use the enrolled client's `withdraw` or `delete`
operations in the learning guide. An active delivery must finish before discard.
Revoked permission or an operator's choice to stop remains effective.

The journal uses private directories/files (0700/0600), not encryption. Captures
and records expire after 30 days, pending payloads after seven. Cleanup runs when
the journal is used. Capacity is bounded to 1,000 captures and 10,000 typed
records/queued payloads, with 64 MiB for each class. Archive needed research before
the bound is reached. Long-horizon studies should use the existing learning store
with an explicitly chosen retention policy. To remove local history, stop users
of the journal and remove its private directory.

## AI SDK applications

Install the published package with
`npm install @moomoo202020/financial-evidence-ai-sdk@0.1.2 ai@^7.0.141`.

```javascript
import {runFinancialWorkflow, financialEvidenceWorkflowTool} from '@moomoo202020/financial-evidence-ai-sdk';

const review = await runFinancialWorkflow({workflow: 'funding', selection: 'USD'});
console.log(review.status, review.result);
const tools = {financial_evidence_workflow: financialEvidenceWorkflowTool()};
```

Call `runFinancialWorkflow` in application code when the review must happen
regardless of the model's tool choice. Both exports use the fixed gateway,
bounded inputs, a whole-workflow deadline and monitor revalidation. Pass
`{synthetic: true}` for installation tests. The original three-tool factory keeps
its existing contract.

JavaScript preserves the original parsed envelope and provider-reported digest,
explicitly marked unverified: Python and JavaScript serialize numbers
differently. Use the Python workflow for a locally verified provider digest,
durable journal or delivery queue. JavaScript persistence belongs to the caller;
this adapter submits no learning records. No integration promises universal
agent adoption or makes a trade.
