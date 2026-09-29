# Public funding packet operations

This service adds a public research workflow around the pinned Workspace 1.0.1
release. The Workspace and Seiche production images are unchanged. Its packet
values are independently acquired from original publishers. FRED-derived
Workspace values are compared transiently, never copied into this new archive.
Publisher responses and field lineage are retained with their own hashes. New
packet manifests separately bind the generator commit and four source-module
hashes; `source_commit` remains the pinned reference release. Initial manifests
without producer fields remain linked through their activation receipt, not
retroactively rewritten.

The USD funding dataset contract is `docs/funding/contract.json`. The web client
and standard-library Python client verify the packet JSON/CSV hashes before
preparing a download. The archive begins when this service first verifies a
packet. It does not turn historical observation dates into earlier knowledge.

## Runtime and schedules

- `financial-evidence-packets.service`: container on loopback port 6910,
  non-root, read-only filesystem, restricted resources, archive mounted read-only.
  The separate usage mount contains optional consented counters only.
- `financial-evidence-packet-capture.path`: watches the source review's atomically
  replaced `current.json` and starts the existing capture service after each
  completed observation, including failed observations and bounded rechecks.
  systemd serializes this with timer starts. Changes while capture is running
  may coalesce; the reconciliation timer below catches those missed updates.
  Enable this path unit on the source host.
  The packet's original source clock and 1200-second limit remain unchanged.
- `financial-evidence-packet-reconcile.timer`: every minute, compare the completed
  source capture identity with the archive's latest hash-verified attempt. Start
  the existing serialized capture service only when they differ. This check
  reads local references and makes no source requests when nothing has changed.
  It also retries a notification that arrived while capture was running. The
  regular fifteen-minute capture remains responsible for retrying a failed
  attempt against the same source identity.
- `financial-evidence-packet-capture.timer`: fallback at :08/:23/:38/:53 UTC, up to 20
  seconds jitter, plus an initial attempt one minute after activation. Fetches the existing review and matching CSV, then seven
  bounded original-publisher documents. A failed source or mismatch records an
  unsuccessful attempt; `/latest` never falls back to an earlier success.
- `financial-evidence-packet-backup.timer`: hourly at :12 UTC with up to 30
  seconds jitter, plus an initial backup two minutes after activation. Uses the existing encrypted repository under a separate tag,
  restores the exact new snapshot and verifies every file. Usage identifiers
  and the HMAC key are excluded. No deletion or repository initialization occurs.
- `financial-evidence-usage-expiry.timer`: daily at midnight UTC. Purges consented
  counters even without new visitor traffic; includes only the last 30 UTC dates.
- GitHub `funding-reliability.yml`: external samples at :07/:22/:37/:52 UTC.
  Each run inherits only this workflow's previous main-branch artifact and
  publishes a new cumulative ledger with 90-day retention. Failed samples are
  retained. Missing artifact history restarts the available baseline explicitly.
  GitHub scheduling can be delayed; missed slots are not counted as successes.

First deployment and any manual invocation must be recorded separately from a
subsequent automatic run. To manually test capture, run the image's archive
command with `--trigger manual`, not the scheduled systemd command.

## Read current evidence

The versioned `/v1/funding/latest` and `/v1/funding/changes` routes validate live
freshness before conditional responses. `/widgets.json` and `/apps.json` expose
the same contract as an optional OpenBB backend. Anonymous reads remain open;
application enrollment is explicit measurement consent, with no quota upgrade.

Application storage shares the private usage mount and is excluded from evidence
backups. The existing daily usage-expiry service purges both independent usage
datasets: browser events retain 30 UTC dates; application completions retain 90.
Application credentials and first-use dates expire after 180 inactive days.
Read the server report with the installed image's
`python -m financial_evidence.application_usage report --directory /data/usage`.
Use only a container with that private mount; do not expose the report publicly.

New credentials are unverified. Local `application_usage classify` supports
`--application ID --classification internal|unverified|external_verified`.
External verification also requires `--evidence /private/review.json` containing
the matching `application_id`, `independent_operator: true` and a reviewed
`basis`. Only its hash is stored, and classification applies to future responses.
Never classify owner-operated tests as independent applications. D7/D30 return
rates remain null when no completed eligible observation window exists.

The shared Caddy funding route must allow the API's Cache-Control response
header through: normal routes send no-store; conditional routes send private,
no-cache, must-revalidate. Keep the request-body limit and loopback binding.

```sh
systemctl list-timers 'financial-evidence-packet-*'
systemctl status financial-evidence-packets.service
cat /var/lib/financial-evidence-institutional/backup/status.json
curl --fail https://api.seiche.info/funding-evidence/latest
curl --fail https://api.seiche.info/funding-evidence/reliability
```

Source lives at `/opt/financial-evidence-institutional/current`. The immutable
image is selected in `/etc/financial-evidence/institutional.env`. Do not print
environment files from the offsite service: they contain storage credentials.

The archive is `/var/lib/financial-evidence-institutional/archive`. Its public
packets, attempt receipts and original-publisher blobs are append-only. An
as-of query returns packets first verified before that UTC cutoff and the most
recent known acquisition outcome, including failure. A capture's source date,
first archive time and current request time remain separate.

## Incidents and recovery

Mrinal owns the public support contact (mrinal@liquilens.in). GitHub marks an
unavailable or unready sample as a failed run and retains its artifact; actual
notification delivery depends on the owner's GitHub notification settings.
No email, Slack or Telegram alert destination is silently enrolled.

Inspect `/latest`, the latest capture journal, and the external workflow when
a review fails. Distinguish publisher delay, mismatched evidence, service failure
and an absent observation. Preserve the failure receipt. Never edit a captured
date/value, suppress a source restriction, or mark an older success current.

For restoration, use a separate directory and restore the **exact snapshot ID**
from the packet backup receipt; verify its complete inventory before use. The
backup receipt's `inventory_sha256` binds the sorted filename/hash map. Capture
a new live packet before describing a restored service as current. The packet
API can restart against the same archive without modifying packet files.

Rollback the packet service by stopping only its API and capture/backup/usage-expiry timers,
restoring the preceding immutable image and the exact saved Caddy configuration,
validating Caddy and reloading. Preserve archive and usage state; do not alter
the existing Workspace, source collectors or their backups.

## Usage and retention

The owner can run the image's `python -m financial_evidence.institutional usage
--directory /data/usage` command with the usage directory mounted. It reports
consented browser downloads, anonymous visitors and visitors active on three
distinct days in fourteen. It cannot determine fund identity, analyst task
completion, willingness to pay or time saved. Those require a consenting pilot
and the private scorecard. Public operator tests use `?operator=1`; they send no
usage events. Server ingestion also excludes explicitly marked operator events.

Only an HMAC of a random browser ID, UTC day, packet ID and the fixed event name
is retained. No IP, user-agent, referrer, free text, name or portfolio enters the
application database. The proxy retains its separate existing delivery logs.
Deduplicate visitor/day/packet events, enforce bounded event counts, honor
explicit deletion and expire application events after 30 days. These optional
counters are excluded from immutable evidence backups.

## Acceptance still requiring real time or participation

Thirty days of scheduled observations must actually elapse. No fund has been
inferred from operator probes or anonymous events. A buyer's access, warehouse,
legal and support requirements must be agreed before offering a private or
licensed service. Publication calendars and publisher formats need maintenance;
the existing review's 2026 calendar must be reviewed before its year boundary.
