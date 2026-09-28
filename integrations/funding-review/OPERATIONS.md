# Repeatable USD funding reviews

`scripts/capture_funding_review.py` captures the public Seiche USD desk, global
money-market atlas and source health in one bounded run. It calls the existing
offline checker, saves an export for Excel and DuckDB, and optionally checks the
hosted Workspace backend's liveness and exact release identity.

The runner uses Python 3.10+ standard-library modules on Linux or macOS. It labels
requests as synthetic operator traffic. It sends no alerts or other messages.

## Capture and inspect

Run from a checkout of this repository. On the development Mac, verify the SSD
with `ssd-workspace status` first and put output beneath `SSDWorkspace/evidence`.

```bash
python3 scripts/capture_funding_review.py \
  --output-dir /var/lib/financial-evidence/funding-review \
  --backend-url https://api.seiche.info/openbb \
  --expected-release workspace-1.0.1+REPLACE_WITH_TESTED_COMMIT_PREFIX
```

Use the release identity recorded in the deployment receipt. Omitting
`--expected-release` records the observed identity without asserting a match.
Omitting `--backend-url` captures only the source surfaces. Local backend testing
may use `http://127.0.0.1:8000`; remote backends must use HTTPS. Credentials, query
parameters, unsafe path segments and redirects are rejected.

The JSON printed to stdout identifies the new capture directory and result.

| Exit | Meaning |
|---|---|
| `0` | Sources and requested backend are available; the bounded data checks and requested release identity pass. |
| `1` | Services responded, but data needs attention or the release identity differs. |
| `2` | A required capture, payload, input, or local filesystem operation failed. |

The five source requests are MCP initialization, initialized notification, the
`money_market_context` tool with `section=all`, `/api/v2/money-markets`, and
`/api/health`, all at the fixed origin `https://api.seiche.info`. A configured
backend adds `/healthz` and `/api/v1/release`. MCP session headers are used in
memory and are not retained. No source values or dates are repaired.

## Evidence layout and failure behavior

Every attempt creates a new timestamp-and-random-ID directory:

```text
funding-review/
  current.json
  captures/<UTC timestamp>-<random ID>/
    mcp-initialize.response
    mcp-initialized.response
    funding-desk.response
    atlas.response
    health.response
    backend-health.response       # when requested
    backend-release.response      # when requested
    desk.json                     # decoded valid desk payload
    review.json
    funding-observations.csv       # when the source payload is evaluable
    manifest.json                 # written last; complete attempt receipt
  replays/<UTC timestamp>-<random ID>/
    ...
```

Response files retain the original HTTP response **body** bytes, including error
bodies. They are not raw TLS/HTTP wire recordings. The manifest retains SHA-256,
byte count, HTTP status, acquisition start/end, measured request latency, and
transport errors. Over-limit or interrupted responses retain a bounded prefix
marked `complete=false`; that prefix is never accepted as complete evidence.

Each new artifact is opened exclusively, so rerunning cannot overwrite previous
evidence. A failed capture still gets its own receipt. `current.json` is replaced
atomically under a process lock and contains:

- `latest`: the newest completed attempt, including failures;
- `last_available`: the latest attempt where all requested services and payloads
  were available;
- `last_ready`: the latest attempt where bounded review and identity checks passed;
- `measurement`: counts and latency of completed operator probes.

Every reference has a relative `capture` path, `capture_id`, original evaluation
time, manifest hash, and compact status. A failure updates `latest` and preserves
the earlier successful references. Consumers must inspect `latest`; displaying
`last_ready` as current would conceal an outage. A killed run can leave a partial
directory without `manifest.json`; it does not update current state. A filesystem
failure may leave a complete manifest while current remains unchanged; that
receipt remains available for manual diagnosis.

Retained capture directories are immutable by runner convention, not signed or
write-once storage. Restrict filesystem writers and back them up if stronger
evidence retention is needed. Raw captures remain operator-only; the public API
can expose the compact summary and rights-filtered CSV through a read-only mount.

## Deterministic replay

Replay first requires the original checker policy ID and SHA-256 fingerprints of
the checker, capture tool and publication-policy implementation to match the
currently running source. A mismatch returns `policy_version_mismatch` and asks
the operator to use the original release. It never silently recalculates an older
review under a changed policy. It then checks every retained response against the
manifest's byte count and hash and uses the original `evaluated_at` and snapshot-age policy. It makes no network
requests, writes a fresh directory under `replays/`, and leaves `current.json`
unchanged. Replaying changed or incomplete evidence does not turn it into a pass.

```bash
python3 scripts/capture_funding_review.py \
  --output-dir /var/lib/financial-evidence/funding-review \
  --replay /var/lib/financial-evidence/funding-review/captures/CAPTURE_ID
```

Compare `review.json` and `funding-observations.csv`: unchanged captures and code
produce identical review/export bytes. Preserve the exact source commit alongside
deployment receipts so a later checker revision does not masquerade as the same
policy implementation. Replay shows the historical captured review; it does not
assert that those observations are fresh today.

## Availability, readiness, and measurement

Availability means the requested calls succeeded and the required payloads were
parseable. Data readiness is independently `checks_passed`, `attention_required`,
or `not_evaluated`. A backend outage still allows a successful source review to be
recorded. Release mismatch is separate from both HTTP availability and data age.

`measurement.sampled_availability_pct` is the share of completed operator samples
that were available. `ready_probes` is tracked separately. Neither is continuous
uptime or a contractual SLA. A stopped timer produces no samples: always inspect
`latest_probe_at`, timer status, and the elapsed window, including deployment and
maintenance gaps. Counters describe this output directory from its first probe;
use a new output directory when changing which services the policy covers.

Every response is limited to 2 MiB plus one sentinel byte. Default socket/read
timeout is 15 seconds, configurable from 1 to 30. Reads check elapsed time between
single socket operations, so a slow body can take approximately twice the timeout.
There are no retries. The service template also limits total runtime and memory.
This intentionally provides one recorded observation per scheduled attempt.

The checker retains publisher freshness and missed-publication claims and adds
calendar-day age backstops. Policy v3 recognizes a bounded Treasury DTS publisher
schedule: its latest due time must be 16:00 New York time and no older than four
days plus one hour, its expected observation must precede that due date by one
to four days, and its source URL must match the documented Treasury page. This
may extend TGA's observation-age limit to eight days; it never removes the limit.
These are consistency bounds, not an independent official-source publication
calendar or a funding-risk recommendation. See [the checker's policy](README.md).

Policy v3 also checks four exact NY Fed instruments against an independently
reviewed 2026 publication calendar. Its original bytes are included in every
capture's `publication_calendar_sha256`; replay requires the same calendar.
The bounded calendar must be reviewed and versioned before accepting 2027
observations. Atlas/calendar disagreements remain visible exceptions. Preserve
the raw publisher freshness label and inspect `freshness_assessments` for the
accepted basis; do not treat a future deadline alone as proof of freshness.

## Scheduled operation

A configured live Workspace requires the captured backend's complete release
identity to match its current runtime. After an upgrade, an older matched capture
is exposed as `runtime_release_identity=mismatch`, is not ready, and has no CSV
download until a new matching capture arrives. The original capture is unchanged.
The Python reader's explicit `enforce_runtime_release=False` option is reserved
for historical/offline inspection and reports `not_checked`; HTTP/MCP clients
cannot request this override.

The [oneshot service](financial-evidence-funding-review.service) and
[15-minute timer](financial-evidence-funding-review.timer) are templates. They are
not activated by installing the Python package. Install them only as part of the
reviewed deployment, after the intended user, checkout and storage exist.

The service defaults to `/opt/financial-evidence-workspace/current`, user
`financial-evidence`, and `/var/lib/financial-evidence/funding-review`. Set the
deployed source path and expected release in a unit override. The API process must
read as the same UID (capture directories are private), or receive an explicitly
configured read-only mount with appropriate host permissions. Do not make the raw
capture directory a general public static directory.

```bash
sudo systemctl daemon-reload
sudo systemctl start financial-evidence-funding-review.service
sudo systemctl status financial-evidence-funding-review.service --no-pager
sudo systemctl enable --now financial-evidence-funding-review.timer
systemctl list-timers financial-evidence-funding-review.timer --no-pager
journalctl -u financial-evidence-funding-review.service -n 30 --no-pager
```

Check that `current.json` advances, the observed release matches the receipt,
and the timer schedules its next run. Exit `1` is an expected review-exception
outcome, so the service treats it as a completed observation. Exit `2` marks a
service failure; the journal and retained receipt explain the cause. The timer
does not send notifications or attempt repairs.

Storage grows with retained evidence and is deliberately not auto-pruned. Measure
actual capture size, provision capacity, and archive verified older directories
through the deployment's backup policy. Deleting history to make a probe appear
healthy destroys the record. No captured history is advertised as complete
point-in-time coverage or as evidence of external investment-team adoption.

## Hosted review reader

The backend's `FINANCIAL_EVIDENCE_REVIEW_DIR` points to a read-only view of this
archive. The shared `financial_evidence.funding_archive` reader returns the latest
review to REST, Workspace and MCP consumers. It verifies the current summary's
manifest hash and the manifest's review/CSV hashes, rejects symbolic links and
path traversal, and bounds files to 128 KiB. Local paths and raw response bodies
are not included in its public result. Manifest/input hashes, fixed source URLs
and the filtered observed backend release identity remain available for audit.

An unconfigured, malformed or missing archive returns an explicit unavailable
result with an empty `results` array. A valid but older-than-20-minute capture
returns its historical rows marked `review_status=stale_capture` and `ready=false`;
its CSV download is unavailable. Release identity mismatches mark each row
`review_status=release_identity_mismatch` and also withhold the CSV. A failed latest attempt never silently falls
back to `last_ready`. A fresh `attention_required` review can still be inspected
and exported with its exception status intact. `read_export()` returns summary
and optional CSV from the same verified capture, so HTTP metadata cannot race
with a separate archive read. The public summary includes the checker `policy_id`.

## Verified backup to another machine

`scripts/backup_funding_review.py --output-dir /path/on/backup/storage` reads an
SSH inventory of completed captures, pulls only their listed files with rsync,
and verifies every manifest and artifact hash before advancing the backup's
`current.json`. The default SSH alias is `liquilens-hetzner`; credentials stay in
SSH configuration. Existing backup files are never replaced or deleted: changed
upstream evidence fails verification. Failed and attention-required captures are
backed up as evidence, along with successful ones. Partial uncommitted captures
are excluded. Each successful pull leaves a dated `backup-receipts/` record.

Schedule this on an independent machine with the existing SSH authorization.
On this Mac, run through `ssd-workspace run` with output on the mounted SSD.
A login LaunchAgent runs only while that Mac and SSD are available; its schedule
is not an always-on offsite guarantee. Inspect receipt age rather than assuming a
scheduled backup completed. Restore into a separate directory, replay with the
original source release, and compare review/CSV bytes before using restored data.
Do not restore a historical `current.json` over the live server to conceal an
outage. The backup pull itself does not claim that a restore drill passed.
