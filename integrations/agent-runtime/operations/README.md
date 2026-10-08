# Operate a private research installation

Runtime Operations 1.0.3 operates the separately published Financial Evidence
0.1.7 runtime. It adds service supervision, a private console, capacity and
schedule monitoring, persistent incident transitions, encrypted offsite backup
and verified restoration. Source eligibility and external adoption remain
separate from infrastructure health. No research result grants trading authority.

The supported deployment is one Linux/systemd host, a dedicated runtime account,
a local persistent filesystem and an **existing encrypted Restic repository**.
The console listens only on `127.0.0.1:8768`. Package installation alone starts
no service. This is an individually operated installation, not a hosted tenant
service or public administration API.

Version 1.0.3 schedules backups on UTC quarter-hours with persistent catch-up,
so service-manager reloads cannot rearm a startup backup delay. It verifies upgrades using the prior applied unit hashes, including
legacy monitor units that 1.0.1 did not recognize. It also adds recovery after host-local receipt loss and retained-row source
diagnostics. Use a published 1.0.3 archive for these commands; the 1.0.0 archive
remains available as the earlier release and does not include them.

## Bind and install

Download Runtime Operations 1.0.3 from the [1.0.3 release](https://github.com/beepboop2025/financial-evidence-skills/releases/tag/runtime-ops-v1.0.3),
including the archive, `source.json` and `SHA256SUMS`. The
[verification record](../../../docs/releases/runtime-ops-1.0.3.json) pins the
signed source and the archive digest. On Linux, verify the downloaded bytes and
their build provenance before extracting them into a new administrator-owned
release directory. Use the exact source commit from the published verification record:

```sh
sha256sum --check SHA256SUMS
gh attestation verify financial-evidence-runtime-ops-1.0.3.tar \
  --repo beepboop2025/financial-evidence-skills \
  --signer-workflow beepboop2025/financial-evidence-skills/.github/workflows/runtime-ops-release.yml \
  --source-digest EXPECTED_SOURCE_COMMIT \
  --source-ref refs/tags/runtime-ops-v1.0.3
```

The archive contains one `financial-evidence-runtime-ops-1.0.3` directory.
The `/opt/runtime-ops` paths below stand for its verified installation path.
Keep the immutable release files and the verification record with your plan.

Install the [verified runtime wheel](https://github.com/beepboop2025/financial-evidence-skills/releases/tag/v0.1.7)
in an isolated environment, initialize private research state and register your
workflows using the [runtime guide](../README.md). `runtime-release.json` pins
the package, wheel, release source and installed Python implementation hash.
The operations helpers refuse a different implementation.

Keep the runtime environment and these operations files in root-owned immutable
directories. Research state belongs to the dedicated runtime account. Operations
state must be a separate mode-0700 directory under root-owned, non-writable
ancestry: it contains private diagnostics and temporary plaintext restore files.
The parent directories must already exist on the intended persistent volume.

As the host administrator, adapt these paths to your installation:

```sh
install -d -m 700 /etc/financial-evidence-runtime-ops
/opt/financial-evidence-runtime/current/.venv/bin/python /opt/runtime-ops/configure.py \
  --root /data/research/state --state /data/runtime-operations \
  --repository-id EXACT_64_CHARACTER_RESTIC_REPOSITORY_ID \
  --output /etc/financial-evidence-runtime-ops/config.json

# Render the concrete plan without changing services.
/opt/financial-evidence-runtime/current/.venv/bin/python /opt/runtime-ops/install.py \
  --config /etc/financial-evidence-runtime-ops/config.json \
  --runtime-python /opt/financial-evidence-runtime/current/.venv/bin/python \
  --credentials /etc/financial-evidence/existing-restic.env \
  --runtime-user financial-research --output /data/runtime-operations/plan
```

After checking the plan, run the same installer with a **new** output directory
and `--apply`. When upgrading an existing installation, also pass
`--previous-plan /absolute/path/to/prior-applied/plan.json` in both invocations.
The prior plan must be applied, private and bound to the same installation. Every
existing unit must match its recorded hash; missing, modified or symlinked units
are refused. Keep the prior plan independently with the recovery configuration.

The installer verifies the runtime account, implementation and workflow
inventory, checks the native systemd units, retains prior owned unit files and
refuses to interrupt an active research or backup process. Retain its plan with
the deployment receipt. Paths containing spaces or systemd substitutions are
refused by this installer.

The root-private environment file supplies existing Restic repository/password
settings and backend credentials. It is referenced, never copied or printed.
The cache is placed in the private operations directory. Do not put credentials
in a repo, page, MCP configuration or health report. Production backup never
initializes a repository and never deletes, prunes or unlocks remote snapshots.

## What stays running

| Component | Behavior |
| --- | --- |
| Research scheduler | One bounded tick per minute; each workflow keeps its own cadence and keys |
| Offsite backup | UTC quarter-hours; persistent catch-up after a missed calendar slot |
| Restore verification | Every accepted backup restores its exact snapshot and verifies the complete journal |
| Monitor | Every minute; reports expire after 180 seconds |
| Private console | Read-only loopback HTTP, refreshing every 20 seconds |

A fresh installation waits for the next UTC quarter-hour (or a persistent
missed-run catch-up) for its first backup. Monitoring correctly reports a missing
verified backup until that succeeds. Upgrades retain existing verified recovery
proof. An immediate catch-up is not steady recurrence; observe later calendar
slots. There is no startup-relative backup trigger to rearm on daemon reloads.

The backup target recovery point is one interval plus transfer time during
healthy operation; it is not a contractual SLA. Backups older than one hour,
missed scheduler heartbeats, overdue workflows, interrupted claims, failed
services and insufficient disk reserve produce critical health. Journal capacity
warns at 80% and is critical at its cap. Operator stops and paused workflows stay
visible. Broad source queries can be blocked while operations are healthy.

```sh
systemctl status financial-evidence-runtime.timer financial-evidence-runtime-backup.timer
systemctl status financial-evidence-runtime-monitor.timer financial-evidence-runtime-dashboard.service
/opt/financial-evidence-runtime/current/.venv/bin/python /opt/runtime-ops/ops.py \
  --config /etc/financial-evidence-runtime-ops/config.json status

# On your workstation, using existing SSH access:
ssh -N -L 127.0.0.1:8768:127.0.0.1:8768 YOUR_HOST
# Open http://127.0.0.1:8768/
```

`/status.json` returns HTTP 503 when monitoring is critical or stale. `/metrics`
provides Prometheus text with monitor time, next-due times and backup age. There
are no CORS grants or mutation endpoints. Source strings are inserted as text,
never HTML. A public proxy needs a separate authentication boundary.

Private state holds `health.json`, `metrics.prom`, `incidents.jsonl`, `backup.json`
and immutable backup `receipts/`. Incidents record openings and resolutions; an
unchanged source block does not produce a new incident every minute. These tools
do not send email, Telegram, customer messages or webhooks. Existing operator
monitoring can poll the private endpoint over authenticated access.

## Recover without repeating work

Each verified backup receipt pins an exact encrypted snapshot and manifest.
Never select an unqualified `latest` snapshot from a shared repository. See the
[Restic restore contract](https://restic.readthedocs.io/en/stable/050_restore.html)
for snapshot selection. This implementation additionally verifies the complete
file inventory, receipt hashes, workflows, retry keys and event cursor.

Supply the same existing Restic environment through your service manager or
credential loader. Do not print its contents.

```sh
/opt/financial-evidence-runtime/current/.venv/bin/python /opt/runtime-ops/ops.py \
  --config /etc/financial-evidence-runtime-ops/config.json restore \
  --receipt /data/runtime-operations/receipts/EXACT_OPERATION_ID.json \
  --target /data/private-recovery/new-state
```

The target must not exist and its parent must be private. Recovery verifies the
original snapshot before creating a **stopped** copy. It preserves retry keys and
source dates, performs no source fetch and enables no service. The original host
remains active until an operator stops it, changes the selected root and ownership,
and explicitly resumes the recovered copy. Never run both copies simultaneously.

An interrupted upload retains `active-backup.json` and its staging directory.
The next attempt checks only for that uniquely tagged accepted snapshot; it
never blindly repeats the upload. Uncertain acceptance remains blocked for
operator reconciliation. An accepted upload can repeat its read-only restore
after a verification failure. A crash after committing a verified receipt finishes
local cleanup without another upload. A preparation failure before an intent
exists retains its directory for inspection: move only a verified pre-upload
orphan out of `pending/` before resuming.

## Recover after loss of host-local receipts

Retain the operations configuration and repository credentials independently of
the runtime host. The configuration pins the installation, exact runtime,
workflow hashes and encrypted repository. It contains no password. You can adapt
its filesystem paths for a replacement host while retaining those identities.
The research and operations directories may both be absent for this recovery.

Using the pinned runtime, the operations release and your existing repository
credentials, list candidate snapshots:

```sh
/opt/financial-evidence-runtime/current/.venv/bin/python /opt/runtime-ops/ops.py \
  --config /etc/financial-evidence-runtime-ops/config.json recovery-candidates
```

A listing proves only that a tagged snapshot exists. It does not establish that
the old host verified it. Choose an **exact 64-character snapshot ID**, then use
a new target under an administrator-owned private parent:

```sh
/opt/financial-evidence-runtime/current/.venv/bin/python /opt/runtime-ops/ops.py \
  --config /etc/financial-evidence-runtime-ops/config.json restore-snapshot \
  --snapshot EXACT_64_CHARACTER_SNAPSHOT_ID --target /data/private-recovery/new-state
```

`latest`, abbreviated IDs, wrong installations, changed runtime/workflow hashes,
unexpected payload files and corrupt journals are refused. The helper reads the
authenticated repository manifest, restores the exact snapshot and validates all
receipts, keys and cursors. Only then does it publish a stopped database and a
`reconstructed-receipt.json` in the new directory. An interrupted stop transaction
cannot publish a live copy. The reconstructed receipt records **newly observed
restore verification**; the prior host's verification remains unknown.

This path creates no backup snapshot and deletes or prunes none. Restic retains
its normal repository locking behavior. It does not need the original journal or
host-local backup receipts, does not alter source state, and does not enable a
scheduler. Keep the original stopped before explicitly resuming a replacement.

## Diagnose a source block

The private console shows the original receipt time, per-reason affected-row
counts, representative source field pointers and concrete remediation guidance.
It uses the runtime's own assessment logic at the **original capture time**.
Current monitor time never becomes a newer source-observation date.

```sh
/opt/financial-evidence-runtime/current/.venv/bin/python /opt/runtime-ops/ops.py \
  --config /etc/financial-evidence-runtime-ops/config.json diagnose --job bank-evidence
```

Omit `--job` to inspect all registered jobs. This command performs no financial
source fetch and changes no policy. `/diagnostics.json` exposes the bounded
read-only result privately; a stale or unavailable report returns HTTP 503.
Examples are representative, with full row counts and omitted reason labels
reported explicitly. Consult the original receipt for the entire result.

Unknown rights require an upstream rights statement or review. Missing and
withheld values stay missing. Stale observations require newer eligible data;
fresh retrieval does not repair them. A partial page needs a narrower explicit
question or bounded full-page inspection. Register a new workflow ID for a
changed research question, then review the new operations inventory; do not
silently relax the original policy to obtain a green status.

## Capacity and updates

The runtime's 10,000-attempt / 64 MiB receipt allowance remains enforced. Nothing
automatically resets its journal or deduplication history. Operations require
1 GiB free and refuse more than 10,000 backup receipts or a 1 MiB incident ledger.
Temporary staging is removed only after verified completion. Old backup files
and remote snapshots remain retained. Review warnings and archive verified
evidence before a cap. A new installation has a new key namespace and does not
deduplicate across the old installation.

A full restore every 15 minutes can consume several GiB of network reads per day
at the journal's maximum size. Monitor actual capacity and bandwidth before
increasing limits or adding installations. A hosted service would need shared
acquisition, tenant isolation, a queue and a reviewed retention policy.

Policies and workflows remain immutable. Register a new ID, pause the old one,
then review and generate operations configuration in a new file. Unreviewed
inventory drift is refused. Package/operations updates require new source
identities and recovery acceptance; do not edit an installed release in place.

## Reproduce acceptance

With the runtime installed and Restic available:

```sh
python -m unittest discover -s tests -p test_runtime_operations.py -v
python tests/integration_runtime_operations.py --output /ABSOLUTE/NEW/acceptance
```

The integration test creates an isolated encrypted **synthetic** repository,
verifies two snapshots with the actual Restic binary, checks stopped recovery
and same-key deduplication, and performs a full repository integrity check. It also hides both original
state directories and restores by exact snapshot without a host-local receipt.
Linux also validates all seven systemd units. No source request or broker order
is made. Production acceptance separately checks the actual offsite repository,
private HTTP readback, stopped recovery, preserved retry keys and two natural
scheduled backup cycles separated by a complete 15-minute interval.
