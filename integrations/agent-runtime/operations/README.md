# Operate a private research installation

Runtime Operations 1.0.0 operates the separately published Financial Evidence
0.1.7 runtime. It adds service supervision, a private console, capacity and
schedule monitoring, persistent incident transitions, encrypted offsite backup
and verified restoration. Source eligibility and external adoption remain
separate from infrastructure health. No research result grants trading authority.

The supported deployment is one Linux/systemd host, a dedicated runtime account,
a local persistent filesystem and an **existing encrypted Restic repository**.
The console listens only on `127.0.0.1:8768`. Package installation alone starts
no service. This is an individually operated installation, not a hosted tenant
service or public administration API.

## Bind and install

Download the [Runtime Operations 1.0.0 release](https://github.com/beepboop2025/financial-evidence-skills/releases/tag/runtime-ops-v1.0.0),
including the archive, `source.json` and `SHA256SUMS`. The
[verification record](../../../docs/releases/runtime-ops-1.0.0.json) pins the
signed source and the archive digest. On Linux, verify the downloaded bytes and
their build provenance before extracting them into a new administrator-owned
release directory:

```sh
sha256sum --check SHA256SUMS
gh attestation verify financial-evidence-runtime-ops-1.0.0.tar \
  --repo beepboop2025/financial-evidence-skills \
  --signer-workflow beepboop2025/financial-evidence-skills/.github/workflows/runtime-ops-release.yml \
  --source-digest e7fa30de7d93d8e32733a7152d19c8b799d80571 \
  --source-ref refs/tags/runtime-ops-v1.0.0
```

The archive contains one `financial-evidence-runtime-ops-1.0.0` directory.
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
and `--apply`. It verifies the runtime account, implementation and workflow
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
| Offsite backup | Startup attempt within 45 seconds, then every 15 minutes from service activation |
| Restore verification | Every accepted backup restores its exact snapshot and verifies the complete journal |
| Monitor | Every minute; reports expire after 180 seconds |
| Private console | Read-only loopback HTTP, refreshing every 20 seconds |

When replacing an existing backup timer, systemd can run an immediate overdue
attempt and another at the 45-second startup deadline. These have distinct
operation IDs and snapshots. Do not count both startup attempts as proof of
15-minute recurrence; observe the next complete interval as well.

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
and same-key deduplication, and performs a full repository integrity check.
Linux also validates all seven systemd units. No source request or broker order
is made. Production acceptance separately checks the actual offsite repository,
private HTTP readback, stopped recovery, preserved retry keys and two natural
scheduled backup cycles separated by a complete 15-minute interval.
