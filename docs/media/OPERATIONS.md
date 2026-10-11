# Reviewed Media Desk cadence

This is an operator procedure, not a publication schedule or a claim that new
editions already exist. The current dated editions remain historical. RSS reports
published editions and recorded corrections; it does not fetch live observations,
publish automatically, or notify people who downloaded a chart.

## Review queue and ownership

Assign an editor and a second reviewer for each proposed release. On working days,
review the funding queue after the relevant publishers' releases, and check for
missed releases, holidays, missing fields and corrections. Review issuer packets
when a relevant filing is available. This is a suggested internal cadence, not an
external turnaround guarantee. Record a skipped release and its reason rather
than refreshing a date on old evidence.

The daily `research-tools` and `funding-reliability` workflows observe service
contracts and availability. They are not editorial review or publication jobs.
An HTTP success or recent retrieval timestamp does not establish source freshness.

For each candidate, retain a local review record with its owner, reviewer, proposed
edition ID, question, source URLs, observation periods, publisher/retrieval times,
capture hashes, missing fields, rights check, calculation check and disposition
(`hold`, `reviewed`, or `published` with release and public verification evidence).
Do not put contact details or private reviewer notes in the public catalog.

## A new edition

1. Agree one bounded finding. Retrieve and retain source evidence; check source
   completeness, dates, units, attribution and permitted reuse independently.
   A failed source or rights gate leaves the candidate on hold.
2. Create a new dated edition directory and reviewed `brief.json`; retain old
   edition URLs, data and hashes. The two initial brief builders have fixed edition
   identifiers and retained inputs. Adapt and review a builder for a new edition;
   do not rerun it as if it supplied a fresh daily publication.
3. Keep observation dates, first publication time and retrieval time separate.
   Include downloads, source URLs, coverage and limitations. Check the chart,
   caption and accessible text against the exact retained numerical extract.
4. Run the catalog builder and relevant tests below. Inspect the resulting page,
   downloads, feed and catalog locally, then use the repository's normal reviewed
   release process. Building files alone does not publish them.
5. After deployment, verify the canonical page, download bytes/hashes, catalog and
   RSS against the reviewed release. Record publication evidence separately from
   any later newsroom citation, repeat use, pilot or commercial outcome.

## A correction or confirmed publisher revision

First distinguish an error in our work (`correction`) from an independently
confirmed change by the original publisher (`source_revision`). A new observation,
reporting period or later retrieval alone is neither; use a new edition where
appropriate. The generator does not establish the truth of a correction.

Add a dated visible notice to the affected edition explaining the field or claim,
before/after values, reason, source evidence and any replacement download. Preserve
the original edition's `published_at`, observation periods and identifiable data
and hashes. Update that edition's generator too, so rebuilding cannot erase its
notice. Choose an HTML `id` for the notice.

Then append a record to `docs/media/corrections.json`. The following is a **schema
example only**; do not publish this invented event:

```json
{
  "id": "2026-10-12-dollar-funding-unit-1",
  "edition_id": "2026-10-11-dollar-funding",
  "kind": "correction",
  "published_at": "2026-10-12T10:00:00Z",
  "summary": "Explain the actual reviewed change, affected value and reason here.",
  "notice_anchor": "correction-unit-1"
}
```

- `id` is globally unique and permanent. IDs and anchors use lowercase letters,
  digits and single hyphens. Never reuse an ID for a later event.
- `edition_id` must identify a retained published edition. `notice_anchor` must
  already exist on its HTML page; a reviewer checks that its content is the dated
  notice described by the record.
- `kind` is `correction` or `source_revision`; the latter requires publisher
  revision evidence. `summary` is nonempty plain text.
- `published_at` is the event's first publication timestamp, with a timezone. It
  cannot predate the edition. Keep this timestamp and ID stable across rebuilds.
  Update the log's ISO `updated_at` date to at least the UTC date of the latest
  event. This is a review date, not an observation-freshness claim.

The builder validates every record before writing its generated outputs. It adds
the event to `catalog.json`, creates a visible `corrections.html#<id>` entry and a
separate RSS item with that URL as its GUID. Edition GUIDs and first publication
dates remain unchanged. The affected edition link includes the notice anchor.
RSS entries use `edition`, `correction` or `source_revision` categories and are
ordered by their publication timestamps. With an empty log, no correction events
are invented. The public log must not contain private intake or unverified reports.

Keep prior correction records. If a published correction needs a further material
correction, append a new event and explain the relationship in both notices; editing
an old GUID alone may not produce a new notification in a reader.

## Build, check and publish deliberately

From the repository root:

```sh
python3 scripts/build_media_catalog.py
python3 -m unittest discover -s tests -p 'test_media_catalog.py' -v
python3 -m unittest discover -s tests -p 'test_*media_brief.py' -v
```

The catalog builder reads local metadata and writes `docs/media/index.html`,
`catalog.json`, `feed.xml` and `corrections.html`. It fetches nothing and publishes
nothing. Run the reuse-page builder/tests too when that page or its assets change.
Review generated diffs before release: preserve previews, reuse navigation, source
notices, dated caveats and original edition timestamps. A publication update must
ship the affected edition notice, reviewed log and generated outputs together.

Check the deployed correction anchor and feed event after release. If publication
verification fails, retain the reviewed local work and record the failure without
claiming subscriber delivery. RSS reader refresh timing is outside our control;
email follow-up, CMS import and Datawrapper publication are separate actions.
