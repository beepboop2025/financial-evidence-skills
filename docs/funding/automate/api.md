# Funding automation API v1

Base URL: `https://api.seiche.info/funding-evidence`. No account is required.
Review [source terms](../sources.md) before redistribution.

| GET route | Response |
| --- | --- |
| `/v1/funding/latest` | `financial-evidence.funding.v1`, nine `observations`, packet identity, horizon, source/archival clocks, artifact hashes and relative download links |
| `/v1/funding/changes?since=PACKET_ID&until=EXPECTED_LATEST_ID` | `financial-evidence.funding-changes.v1`, before/after identities and captured differences; optional `until` keeps a client transaction consistent |
| `/v1/funding/history?as_of=UTC_TIMESTAMP` | Forward coverage, up to 96 observed packets, total count and explicit truncation |
| `/packets/PACKET_ID/manifest.json` | Immutable manifest and SHA-256 hashes for JSON and CSV |
| `/packets/PACKET_ID/review.json` | Original-publisher review with dates, sources and readiness at capture |
| `/packets/PACKET_ID/observations.csv` | Matching nine-row dataset |

```sh
curl --fail --max-time 20 https://api.seiche.info/funding-evidence/v1/funding/latest
```

Rates use `%`; balances and operations use `$B`. The common SOFR/IORB review
horizon and per-instrument dates remain separate. Zero is a value, not a missing
marker. Preserve full precision: an SRF amount can be nonzero below 0.01 billion.
Archive time is first verification in this forward archive, not earlier knowledge.

Latest and changes include a strong `ETag`. Send it as `If-None-Match` on the
same route to avoid downloading unchanged content. Credentials, live readiness,
source clocks and artifact hashes are checked **before** returning 304. Reuse
only a verified local copy with the matching validator. `X-Evidence-Checked-At`
reports the new check. Responses require revalidation and are private to the
client cache. The downloadable job advances its cursor only after all artifacts
verify and retains the prior cursor on failure.

| Status | Meaning and handling |
| --- | --- |
| 200 | Validated response; verify packet hashes before advancing a cursor |
| 304 | Same representation with freshness rechecked; reuse verified local bytes |
| 400 / 422 | Invalid or missing fields; correct the request |
| 401 | Invalid, erased or expired optional key; do not silently drop authentication |
| 404 | Starting packet absent from this forward archive; retain cursor and inspect coverage |
| 409 | Latest changed during comparison; retry the transaction at most three times |
| 429 | Enrollment allowance reached; honor `Retry-After` |
| 503 | Latest evidence or identity storage unavailable; keep prior files and report unavailable |

The client uses 20-second request timeouts, at most three attempts for
429/502/503/504 or transport failures, and a maximum 20-second retry wait. Three
transaction attempts bound concurrent changes. Redirects and responses larger
than 256 KiB are rejected. A daily research job should normally run once daily.
Public concurrency is bounded; no capacity or SLA is sold by this API. Later
success does not erase failed capture history. Changes are captured differences,
not confirmed publisher revisions or complete historical publisher vintages.

## Optional application identity

Enrollment explicitly opts into measurement. `POST /v1/applications` with
`Content-Type: application/json` and exactly `{"measurement_consent": true}`
returns `application_id` and a Bearer `token` once. Store it in a mode-600 file
without displaying or committing it:

```sh
python3 daily_job.py --state ./funding-state --token-file /private/path/funding.key
```

API callers send `Authorization: Bearer TOKEN`. Keys are never accepted in a URL.
Enrollment is bounded to 100 currently retained registrations per UTC day and
10,000 retained applications. Keyed reads have the same public capacity;
higher quotas and commercial terms are not enabled.

`DELETE /v1/applications/current` with the key revokes it and removes the
installation and linked completions/cohorts. Anonymous aggregate counts remain.
Only a SHA-256 digest of the high-entropy token is stored. The database stores
no IP, user agent, referrer, personal name, employer or free text. Infrastructure
delivery logs are separate.

The service counts server-prepared 200 data responses and separate 304 responses.
An app/UTC-day/packet/class combination counts once across latest and changes.
This cannot prove client receipt, useful research, organizations or downstream
users. Anonymous requests are aggregate counts only. Keys are `unverified` by
default. External ownership requires a separate local review; past events are
not retroactively relabeled. `X-Traffic-Class: synthetic` and `X-Operator-Probe`
exclude tests; the job supports `--operator`.

Completions/aggregates retain 90 UTC dates, capped at 50,000 unique completions
per date and bounded aggregate counters. Missing telemetry or saturation is not
established nonuse. Keys expire after 180 days without accepted use. D7/D30 rates
use completed UTC return dates and eligible cohorts; incomplete windows have no
rate. Browser consent counters remain a separate 30-day dataset.

Conditional requests follow [HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-none-match).
