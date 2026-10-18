# Measure useful office adoption

Use one analyst's recurring funding review or exact institution watchlist to
evaluate the [Office & Linux kit](../office/). A successful workbook import is
compatibility evidence. A useful result requires the reviewer to complete their
own task with source dates and coverage gaps intact. A useful return requires
another confirmed task on a different UTC date.

## Existing collection boundaries

The current office clients use anonymous hosted research. Operational requests
are not people, independent organizations, workbook openings or completed tasks.
They do not enroll users or attach legacy `fe_` installation credentials. The
server's older `application_usage.py` and `workspace_usage.py` reports describe
retained installation records, not office adoption. Calling those reports can
also prune their database; use approved read-only collection when auditing.

The [learning ledger](../start/learning.md) remains an explicit, separate option
for an operator who has chosen its measurement purpose. Seiche task participation
also requires its own current owner grant. Neither permission is inferred from
downloading a workbook or running a public query. Do not enable either to make a
pilot scorecard look populated. This scorecard sends nothing to either service.

## Run a small private pilot

1. Use a consenting analyst or organization with a real recurring task. Record
   the chosen purpose, allowed evidence, retention period, withdrawal process and
   the reviewer's permission in private storage. Keep participants who declined
   measurement fully able to use the product.
2. Have the participant use their chosen client and their own task. Retain only
   the agreed redacted result, exact kit/source version, source dates and gaps,
   and their confirmation of whether the task was completed. A source refusal
   can be valuable feedback, but does not become a useful completion here.
3. Review independence separately. Assign an opaque alias after checking whether
   the participant is an analyst or organization and deduplicating existing
   aliases. Never use a name, email, account ID or credential as the alias. An
   organization with multiple installations gets one organization alias.
4. On their next natural review occasion, record a new task reference and date.
   Do not schedule requests or fabricate another task to produce retention.
5. Keep the CSV and supporting evidence private. Run the local scorecard below.
   Share an aggregate only with the permission required by the pilot agreement.
   Delete or redact source records when consent is withdrawn or retention ends.

Copy the [empty CSV template](pilot-template.csv) outside the repository. Do not
commit participant records or supporting evidence. The template contains no
invented participants. Populate the exact header as follows:

| Field | Rule |
| --- | --- |
| `participant_alias`, `task_reference` | Opaque lowercase labels, 1–48 characters, letters/numbers/underscore/hyphen. Reuse a task reference only for an identical retry. |
| `participant_type` | `analyst` or `organization`; keep these denominators separate. |
| `client` | `google_sheets`, `excel`, `libreoffice`, `onlyoffice`, `collabora`, `nextcloud`, `jupyter`, `openbb`, `linux_cli`, or `other`. |
| `workflow` | `funding`, `institutions`, `liquidity`, or `mixed`. |
| `occurred_at_utc` | Actual completion time as `YYYY-MM-DDTHH:MM:SSZ`. |
| Five boolean columns | Literal `true` or `false`. `operator_test` includes tests, demos, employee use and synthetic runs. |
| `consent_sha256` | SHA-256 of the retained permission record. Permission must cover the stored evidence and purpose. |
| `independence_review_sha256` | SHA-256 of the private reviewed independent-ownership record. |
| `evidence_sha256` | SHA-256 of the private task record containing the reviewer's completion confirmation and cited output reference. A download hash alone is insufficient. |
| Duration columns | Optional paired minutes for the normal manual process and this actual review. Keep empty when unknown; zero is a real observation. |

The program checks digest syntax and requires these references. It does not
authenticate the evidence or establish independence from a hash. The private
pilot owner remains responsible for those reviews and alias deduplication.

From a checkout, using Python 3.10+ and no dependencies:

```sh
python3 scripts/office_adoption.py /private/pilot.csv \
  --through 2026-10-17 --window-days 90 > /private/office-scorecard.json
```

`--through` is the last completed UTC date (yesterday by default). Today's
partial date is rejected. The command performs no network requests or remote
writes, does not enroll anyone, and emits no aliases or task references.

## Interpret the scorecard

- Counts cover reviewed local pilot records, not all users. A blank template
  produces zero observed pilot records and leaves overall active people and
  paying customers unknown.
- Consent, independent review, completed task, accepted source scope and all
  three evidence references are required. Synthetic/operator tasks are excluded.
  Any `consent_recorded=false` row suppresses that alias across the input; also
  remove the private rows as the participant's withdrawal agreement requires.
- Identical retries are deduplicated. A conflicting record for the same
  participant/task is rejected. Multiple same-day tasks do not create a return.
- D7/D30 use an exact UTC date after the first retained qualifying task. A rate
  stays null until an eligible completed observation window exists. Retain the
  permitted earlier history so the first retained date is not mistaken for
  lifetime activation. These exact-day metrics differ from the learning ledger's
  days 7–13 and 30–36 windows; do not combine them.
- Client and workflow totals overlap. Their participant counts are not additive.
  Paired time savings are reviewer reported, can be negative, and are absent if
  either duration is missing. They are not independently measured productivity.

The initial decision is whether analysts return for useful work in their normal
client. Marketplace acceptance, downloads, HTTP success, paid conversion and
independent adoption remain different evidence states.
