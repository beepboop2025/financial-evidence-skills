# Financial Evidence Runtime

Run repeatable research workflows across LiquiLens, Seiche and Undertow from a
Python application, a terminal or an MCP client. Each run has a fixed policy,
bounded source reads, a durable receipt and an offline replay path.

The runtime is included in **Financial Evidence 0.1.7**. Its runtime contract
version is 1.0.0, separate from the package version. The [release record](../../docs/releases/0.1.7.json)
retains artifact and independent consumer verification.

## Install and prove the installation

Use a local disk and Python 3.10 or newer. These commands are for macOS/Linux.
Choose an isolated environment and a private state directory. On the development
Mac, use the mounted SSD workspace for both.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'https://github.com/beepboop2025/financial-evidence-skills/releases/download/v0.1.7/financial_evidence-0.1.7-py3-none-any.whl'
.venv/bin/financial-evidence-runtime catalog
```

For the private stdio MCP server, install the optional dependencies in the same
environment:

```sh
.venv/bin/python -m pip install 'financial-evidence[workspace] @ https://github.com/beepboop2025/financial-evidence-skills/releases/download/v0.1.7/financial_evidence-0.1.7-py3-none-any.whl'
```

Checksums, build attestations and the source archive are attached to the
[GitHub release](https://github.com/beepboop2025/financial-evidence-skills/releases/tag/v0.1.7).
The core CLI has no package dependencies. Homebrew includes the core runtime
CLI; optional runtime MCP dependencies use the isolated Python installation.

To reproduce offline acceptance, check out tag `v0.1.7` in a separate source
directory and invoke its `integrations/agent-runtime/offline_acceptance.py`
using the installed environment's Python interpreter, with
`--output /ABSOLUTE/NEW/acceptance`. It uses synthetic observations, denies the
client's network access paths and retains a receipt, backup, restored database
and JSON report. PASS establishes local behavior; it says nothing about current
market data, trading returns or outside users.

## Register and run a workflow

```sh
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state init --traffic-class internal
.venv/bin/financial-evidence-runtime presets --id funding-watch > funding-watch.json
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state register funding-watch.json
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state run funding-watch --key morning-2026-10-08
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state metrics
```

The state directory is created with mode 0700 and the database with mode 0600.
An existing publicly accessible directory is refused. Keep the state directory
outside a served website, shared repository or synchronized network drive.

Run returns a `run_id`. Reuse the same key when a client times out: the runtime
returns the original attempt. It does not automatically repeat an interrupted
attempt. A new key requests a new run, still subject to cooldown and budgets.
CLI keys and MCP keys have different namespaces; use one interface consistently
for retries of the same request. Python callers control their own namespace.

Edit `parameters.entity` to focus the query and review the requirements before
registration. Configuration is immutable after registration. To change a policy,
register a new workflow ID and pause the old one. These presets are research
examples, not statements of a product's publication cadence:

| Preset | Product/data | Maximum observation age | Default cadence |
|---|---|---|---|
| `funding-watch` | Seiche money markets | 4 days | 15 minutes; 96 attempts/UTC day |
| `bank-evidence` | LiquiLens bank evidence | 180 days | 15 minutes; 96 attempts/UTC day |
| `liquidity-watch` | Undertow market liquidity | 1 day | 15 minutes; 96 attempts/UTC day |
| `source-watch` | Existing family source metadata | No numeric age assessment | 15 minutes; 96 attempts/UTC day |

The numeric presets require numeric rows, units, established source-reported
rights and a complete page. Broad queries can legitimately be blocked by missing
or restricted rows or a second page. Narrow the research question; investigate
the reasons before changing a policy. `source-watch` permits metadata-only rows;
a complete run there establishes a metadata check, not market-data freshness.

`review` can also be registered with `parameters: {"bank": "", "limit": 10}`.
It retains separate funding, bank and liquidity sections. It does not combine
different units and observation dates into an investment score.

## Connect an MCP client

Use the client's existing stdio MCP configuration surface:

```json
{
  "mcpServers": {
    "financial-research-runtime": {
      "command": "/ABSOLUTE/financial-evidence-skills/.venv/bin/financial-evidence-runtime-mcp",
      "args": ["--root", "/ABSOLUTE/PRIVATE/state"]
    }
  }
}
```

The server exposes six tools: `financial_runtime_catalog`,
`financial_runtime_jobs`, `financial_runtime_run`, `financial_runtime_replay`,
`financial_runtime_events` and `financial_runtime_metrics`. The owner registers
workflows through the CLI. The agent can request only those registered jobs,
under their fixed limits. Registration, policy changes and outcome
acknowledgements are not agent tools.

The run tool writes a local record and is annotated accordingly. Catalog,
replay and diagnostics tools are read-only. Tool annotations describe behavior;
the database and validation code enforce the limits. This interface is private
stdio and has no hosted endpoint, public login or remote administration surface.

Example prompt: "List the registered workflows. Run funding-watch with key
research-2026-10-08-001. Report its assessment reasons and source observation
dates. Keep missing data explicit. Save the run ID for replay."

## Use Python or an external scheduler

```python
from financial_evidence.runtime.engine import Runtime
from financial_evidence.runtime.store import Store

runtime = Runtime(Store("/ABSOLUTE/PRIVATE/state"))
attempt = runtime.run("funding-watch", "application:2026-10-08-001")
if attempt.get("run_id"):
    print(runtime.store.run(attempt["run_id"]))
```

The CLI `tick --limit 1` admits at most one due workflow and exits. Schedule it
once a minute using your existing scheduler. The supplied systemd service/timer
templates use journald and default to one execution per tick; edit absolute
paths and the service account before installing them. **No service is installed
or enabled by package installation.** macOS owners can invoke the same one-shot
command from an existing launchd job.

Missed intervals are coalesced into the next eligible run, not replayed as a
burst. Rejected jobs do not consume an execution slot. Admission remains atomic
across separate processes sharing this one local database. Ten runs is the
maximum per tick; with 45-second worker deadlines, a ten-run tick can take over
seven minutes. Start with one run per tick.

## Events, replay and outcomes

```sh
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state events --after 0 --limit 100
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state replay RUN_ID
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state export RUN_ID --output /ABSOLUTE/NEW/receipt.json
.venv/bin/financial-evidence-runtime verify /ABSOLUTE/NEW/receipt.json
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state acknowledge RUN_ID --outcome useful --confirm-local-report
```

Process an event page, then persist `next_cursor` in the consuming application.
On failure, retry the previous cursor and deduplicate by event ID. A finished
event carries run status, result revision, change classification and receipt
hash. Read the receipt for policy reasons and individual source clocks.
`unchanged` retains full rows and means content revision equality; source age
can still cause a later run to be blocked.

Verification checks canonical content integrity, workflow binding and the
configured assessment at the original capture time. It does not authenticate
the issuer or publisher, grant data rights, establish historical vintages or
approve an order. An attacker who controls the local account can rewrite the
database and recompute hashes; this is not a signed audit ledger.

Outcome acknowledgement is an immutable local operator report. It is useful
for improving workflows, but it cannot establish customer identity, retention,
revenue or trading performance. Those metrics remain null in local reports.

## Pause, recover and retain evidence

```sh
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state pause funding-watch
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state stop
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/PRIVATE/state backup --output /ABSOLUTE/NEW/runtime-backup.sqlite
```

Stop gates new research work; in-flight read-only requests may finish. A
worker exceeding 45 seconds is killed and its failure is retained. A lost claim
is marked interrupted on the next attempt for that workflow after 120 seconds.
The original key stays consumed. Inspect the failure before choosing a new key.
To resume admission, run `resume`; to re-enable a paused workflow, run `enable ID`.

Restore into a **new** private directory while its scheduler is stopped:

```sh
mkdir -m 700 /ABSOLUTE/NEW/restored-state
cp /ABSOLUTE/runtime-backup.sqlite /ABSOLUTE/NEW/restored-state/runtime.sqlite
chmod 600 /ABSOLUTE/NEW/restored-state/runtime.sqlite
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/NEW/restored-state metrics
.venv/bin/financial-evidence-runtime --root /ABSOLUTE/NEW/restored-state replay RUN_ID
```

Resume only one copy of an installation. Running the original and restored copy
simultaneously would create two independent schedulers with the same identity.
The backup preserves keys, policies, cursor history and stop state. It is a
local snapshot; arrange encrypted offsite delivery in the existing backup
system separately. Restore to a clock at or after the original journal time.
A backwards clock jump greater than five seconds stops new admissions until
the clock catches up; inspect host clock synchronization, do not edit the DB.

The default cap is 10,000 retained attempts and 64 MiB of receipt payload, plus
SQLite/event overhead. Nothing is silently deleted. On a cap, stop scheduling,
export needed receipts and back up the installation. Archive it before
provisioning a new explicit root; keys are scoped to an installation and do not
deduplicate across a new root. Monitor actual filesystem capacity separately.

See [architecture and scale boundaries](../../docs/infrastructure/ARCHITECTURE.md)
and [adoption measurements](../../docs/infrastructure/ADOPTION.md).

## Verify the paper-host boundary

`paper_host_acceptance.py` uses the real Carrier ASGI service and its synthetic
test rig at commit `aebba668c55079b27b46c7584b3f0743c201a84f`. Its explicit
`--carrier-root` must be a clean checkout of that commit. Install the Carrier
trading-copilot locked test environment, then install this package in the same
environment, as shown in the `agent-runtime` CI workflow. Run:

```sh
python integrations/agent-runtime/paper_host_acceptance.py \
  --carrier-root /ABSOLUTE/PINNED/carrier \
  --output /ABSOLUTE/NEW/paper-host-acceptance
```

The test retains a local research-to-intent link. The host independently acquires
and assesses its evidence; it rejects caller-provided research bundles. Checks
cover read-scope denial, operator stop, stable intents across restarts, stale
research and backup restoration. All network connections are denied and broker
responses are test doubles. A pass proves these integration boundaries, not
live execution, fills, profitability or external adoption.
