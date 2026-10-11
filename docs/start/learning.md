# Optional financial-agent measurement and learning

This package implements the Finance stage's separate participation ledger. It is
not enabled by importing Financial Evidence, using a public tool, or running an
existing runtime job. Those paths retain their existing collection contract.
Participating operators explicitly install a local sink or configure a remote
learning endpoint and an enrolled credential. Core evidence tools remain usable
without participation.

The service can run on the same centrally operated platform as the product
gateway and Seiche Agent Network. A shared host does not merge permissions: the
learning database, network credentials and private product records remain
separate. A gateway access token is not a learning credential or permission to
train models. The named products remain the sources of their data.

## Four separately selected purposes

| Purpose | Admits | Does not admit |
| --- | --- | --- |
| `measurement` | Bounded tool/task status, duration, cache state, permitted usefulness and cost reports | Prompts, raw tool arguments, IPs, portfolios, private decision features, training |
| `private_evidence` | Selected numeric features, exact receipt references and linked later outcomes within one tenant | Shared research or commercial training |
| `research_training` | Potential admission to a reviewed research dataset | Automatic admission, commercial use |
| `commercial_training` | Potential admission to a separately reviewed commercial-model dataset | Automatic admission or commercial release of a model |

Enrollment records the chosen purposes, policy version, grant time, expiry and
retention. Training choices require private-evidence permission. Every training
pair also needs local operator review of all exact source scopes and a reviewed
outcome. A request cannot mark itself training eligible, verify its own outcome,
or certify that its sender is an institution. A publisher or employer may impose
restrictions beyond a contributor's permission.

In particular, Palimpsest source access is not a blanket training grant. Existing
SAFE, CFETS/ChinaMoney and context-only restrictions must be reconciled against
the exact series and intended use before a local reviewer supplies an admission
record. Unknown, denied and context-only scopes are rejected by admission. The
reviewer's rights reference must point to actual supporting evidence; the
software cannot establish legal rights from an identifier alone.

## Local use

`LearningStore` uses a separate owner-only directory (0700) and SQLite file
(0600). It rejects linked/nonprivate database files. Credentials are random and
only their hashes are stored. The original enrollment response contains the
credential once; the CLI writes it to a new 0600 file rather than printing it.

```python
import time
from financial_evidence.learning import LearningStore

# Select an existing approved SSD/private-server location. No network traffic.
store = LearningStore("/approved/private/learning-state")
enrollment = store.enroll(
    purposes=["measurement"],
    policy_version="finance-measurement-v1",
    expires_at=time.time() + 30 * 86400,
    retention_days=30,
)
credential = enrollment["credential"]  # keep in the operator's secret storage

store.record_tool(credential, {
    "id": "attempt-opaque-001",  # reuse only when retrying this exact event
    "product": "seiche", "tool": "money_markets",
    "task": "funding_review", "occurred_at": time.time(),
    "duration_ms": 48, "status": "success", "mode": "shadow",
    "cached": False,
})
```

Pass `lambda event: store.record_tool(credential, event)` as an explicitly
selected measurement sink in an integration. Do not install global tracing hooks.
Delivery failure must remain visible in the integration's diagnostics and must
not be represented as successful receipt. The public data call itself does not
need to fail when optional measurement fails.

Tool events require `id`, `product`, `tool`, `task`, `occurred_at`, `duration_ms`,
`status`, and `mode`. UTC times are Unix seconds. Status is one of `success`,
`error`, `refused`, `stale`. Mode is `unknown`, `test`, `backtest`, `shadow`, `paper`,
or `operator_reported_production`; the last is an operator statement, not
independent confirmation of a trade or production institution. Optional fields
are `cached`, `useful`, `cost_usd`, `source_age_seconds`, `logical_workflow_id`,
`client_version`, `model_version`, `config_version` and `available_tools`.
Identifiers are bounded labels; versions and task labels must not encode private
text. Each payload is capped at 64 KiB. The same id/content returns the original
receipt; reusing an id with changed content fails. Use separate attempt ids for
actual retries and a common logical workflow id where permitted. Old activity
predating measurement enrollment cannot be backfilled.

## Explicit remote ingestion

Install the repository's `workspace` optional dependencies. Start the dedicated
service, behind the platform's HTTPS proxy:

```sh
python -m financial_evidence.learning --store /approved/private/learning-state serve --host 127.0.0.1 --port 8091
```

The factory is `financial_evidence.learning.api.create_app(store)`.
`RemoteLearningClient(endpoint, credential)` in
`financial_evidence.learning.client` exposes `record_tool(event)`,
`record_decision(decision)`, `record_outcome(outcome)`, `describe()`, `report()`,
`withdraw(purposes=..., delete=...)`, and `delete()`. Construction sends nothing.
The client requires HTTPS except on loopback, refuses redirects, bounds response
size/time, and raises `LearningDeliveryError` on unconfirmed delivery. It does not
silently retry or forward a bearer credential to a redirect destination.

| Route | Access |
| --- | --- |
| `GET /health` | Service status only; no participant counts |
| `POST /v1/events` | Own tenant; active measurement permission |
| `POST /v1/decisions`, `POST /v1/outcomes` | Own tenant; active private-evidence permission |
| `GET /v1/me`, `GET /v1/report` | Own permission state and bounded private report |
| `POST /v1/withdraw` | Revoke selected purposes; optional associated-record deletion |
| `DELETE /v1/me` | Delete own enrollment and private records |

All `/v1` routes require the separately enrolled bearer credential. There are no
HTTP enrollment, source review, institution verification, cross-tenant reporting
or dataset-export routes. JSON body limits and a per-credential 600-request/minute
process allowance apply; each tenant's retained record cap is 100,000. Multiple
workers need the platform edge's shared rate limit. The private SQLite service
is single-host infrastructure, not an unbounded multi-region collector.

Run enrollment and review through the local CLI. For example, `enroll` takes
repeated `--purpose`, `--policy-version`, `--expires-at` (epoch), `--retention-days`
and `--output` for the new credential file. Ingestion commands `event`, `decision`
and `outcome` take `--input` JSON and `--credential-file`. Help lists all arguments:

```sh
python -m financial_evidence.learning --store /approved/private/learning-state --help
python -m financial_evidence.learning --store /approved/private/learning-state enroll --help
```

## Frozen decisions and independent outcomes

A decision is an immutable record with `id`, `decided_at`, `target`, `entity`,
`horizon_seconds`, `mode`, `evidence_refs`, `data_features` and `usage_features`.
The default target is `funding_next_release_change`, measured in
`percentage_points`: one explicitly identified funding series at its next
observed release. This is not an order, recommended position or profit forecast.
Local operators can register immutable versioned targets with explicit units.

Every numeric feature contains `value`, `observed_at`, `available_at`, `source`
and `revision`; observation and availability must precede the decision. Up to 32
features per class and 16 exact evidence references are allowed. References are:

```json
{"kind":"runtime","run_id":"00000000000000000000000000000000","sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
```

or `{kind: "product", product: "seiche", receipt_id: "...", sha256: "..."}`.
These schemas pin a reference to bytes; they do not authenticate an issuer or
independently verify a source. Existing runtime bundles retain their own
`verify_bundle` integrity checks. Decision references never grant order authority.

An outcome requires `id`, `decision_id`, `value`, `unit`, `observed_at`,
`available_at`, `source`, `revision`. Receipt time is added by the service. The
unit must match the target and the observation must follow its horizon. One
immutable outcome is accepted per decision. New revisions need a new versioned
decision/outcome pair. Submission is always `operator_reported`; local
`review-outcome` records an independent review reference before it becomes
`reviewer_verified`.

Local `admit` then requires the tenant, decision, specific training purpose,
reviewer, rights reference, expiry, and a JSON mapping of **every** feature and
outcome source to that purpose. The admission binds the exact decision/outcome
digest. A private outcome, a successful call or a verified organization alone
does not create training admission.

## Evaluation and lineage

`export --purpose research_training --target funding_next_release_change --output
dataset.json` selects only live permissions, unexpired records, reviewed outcomes
and admitted source scopes. An optional `--as-of` enforces source availability,
service receipt and review timing. Test, backtest and unknown-mode records are
excluded from this shared evaluation path. The private internal manifest links
each row to its permission, admission and source records; exported features omit
tenant credentials and source record ids. Exported rows remain potentially
sensitive and are written to a new 0600 file.

```sh
python -m financial_evidence.learning --store /approved/private/learning-state evaluate --input dataset.json --entity US-USD --output experiment.json
```

The standalone `integrations/trading-agents/evaluate.py` supports the same
evaluation and requires `--store` to recheck current withdrawal/expiry. Both
supported commands refuse revoked or altered snapshots. A pure Python
`evaluation.evaluate(dataset)` function performs deterministic numeric evaluation
only; an external caller must use `store.validate_snapshot(dataset)` first.

The experiment uses a fixed 70/30 chronological split, training-only feature
scaling and fixed ridge regularization. It compares zero change, the training
mean, domain-data-only features and, where available, data plus usage. Training
labels whose horizons or receipt/availability overlap the test period are
purged. Decisions first recorded after the outcome became available are excluded.
Multiple agents or cloned requests pointing to the same source's release
observation count as one label; the earliest decision is retained deterministically.
The default minimums are 30 training and 10 held-out pairs. Mixed entities or
horizons require separate experiments. Without usage features, the domain
baseline still runs with `evaluated_baseline_only` and
`usage_uplift: not_evaluable`. Without enough reviewed data, the result is
`insufficient_data`; synthetic test fixtures never substitute for actual data.

All metrics and predictions are retained even when usage features fail to help.
A single historical holdout does not authorize commercial release or establish
future performance, representative preferences, causality or trading profit.
Registering an experiment artifact with `--model-id` records the snapshot/model
digest lineage; it does not deploy the model.

## Withdrawal, retention and operating reports

`withdraw` revokes the selected purpose immediately. Withdrawing private evidence
also withdraws both training purposes. `--delete-records` deletes associated
stored content; deleting the tenant revokes its credential and removes all its
private records. Past exports cannot be recalled automatically and already
trained weights are not instantly unlearned. Affected snapshots are invalidated
and registered models are marked `needs_review`. The operator must reconcile
export copies, backups and retraining/deletion work. Minimal snapshot/model
lineage is retained without record contents for this purpose.

Records expire at the earlier of permission expiry or their bounded 1–365-day
retention. Reads/writes run expiry checks, and the explicitly hosted service runs
expiry at startup and hourly in the background without incoming traffic. For a
local-only store, schedule the `expire` command at least daily. SQLite secure deletion is
enabled, but this is not encryption at rest or guaranteed erasure from SSD
snapshots/backups. Use protected volumes, isolated service ownership, encrypted
backups and an explicit backup deletion procedure for institutional deployment.
No learning database should enter public artifacts or an evidence-publication
backup. Keep this private service's operational security logs separate from
model datasets and preserve applicable independently required retention.

Reports include per-tool requests, mode classification, failures/refusals/stale
results, cache hits, latency, cost coverage and linked/reviewer-verified outcome
denominators. Costs are operator-reported; missing cost remains unknown. Cost per
useful workflow is reported only when all measured shadow/paper/production-scope
requests have cost observations. Tests, backtests and unknown traffic are shown
separately and excluded from that denominator.

Retention cohorts use the first retained confirmed-useful completion per tenant.
D7 return means another useful completion in days 7–13 and is evaluated only
after day 14; D30 uses days 30–36 after day 37. Reports include numerator,
eligible denominator and window. These are retained, instrumented workspace
cohorts, not all customers or verified people. Organisation verification is a
separate local onboarding action; verified workspace counts do not deduplicate
multiple workspaces belonging to the same institution. IPs, tool calls, keys and
downloads are never promoted to institution or trading-adoption counts.
