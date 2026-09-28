# Funding observations in Excel and DuckDB

Use `funding-observations.csv` from an identified capture, or the hosted release's
documented CSV endpoint when deployed. Keep the capture ID and manifest hash with
the research workbook. A daily observation date differs from the operator's
`evaluated_at`; neither should replace the other.

The CSV contains the nine required funding inputs, their native units, observation
date, source, cadence, publisher freshness and review status. Missing, ambiguous,
or restricted values are blank and have an explicit `value_state`. Genuine zero
values remain zero. Restrictions on the full document or parent section override
an otherwise available metric. Strings that could become spreadsheet formulas
are prefixed with an apostrophe.

## Excel Power Query

1. In Excel, choose **Data → Get Data → From Text/CSV** and select the captured
   `funding-observations.csv`. Use UTF-8 and comma separation.
2. Choose **Transform Data**. Set `value` to decimal number, `observation_date` to
   date, and `evaluated_at` to date/time/timezone. Keep `metric_id`, `unit`,
   `value_state`, `publisher_freshness`, and `review_status` as text.
3. Preserve blank values as null. Add a filter or visible exception table for
   `value_state <> "available"` or
   `review_status <> "checks_passed"`. Review exceptions before use.
4. Load the table. Record the capture ID next to the table; refreshing a file path
   is not an archive of previous workbook inputs.

Keep `publisher_freshness` visible. Policy v3 may accept an `aging` label only
with matching, bounded publication-clock evidence; inspect `freshness_assessments`
in the JSON review for the basis and deadline. Use `review_status` for the review
exception filter.

If your deployed backend exposes a CSV URL, **Data → From Web** can load that
documented endpoint. Retain the timestamped local export for reproducibility.
An older successful export is historical evidence and must not be silently shown
as today's successful review during an outage.

## DuckDB

DuckDB is an optional analyst tool; the capture runner does not install it. In an
existing DuckDB session, set types explicitly so null does not become zero:

```sql
CREATE TABLE funding_review AS
SELECT
    metric_id,
    TRY_CAST(value AS DOUBLE) AS value,
    unit,
    TRY_CAST(observation_date AS DATE) AS observation_date,
    source,
    cadence,
    publisher_freshness,
    value_state,
    TRY_CAST(evaluated_at AS TIMESTAMPTZ) AS evaluated_at,
    review_status
FROM read_csv('funding-observations.csv', header=true, all_varchar=true);

SELECT metric_id, observation_date, value, unit, value_state,
       publisher_freshness, review_status
FROM funding_review
ORDER BY metric_id;

SELECT * FROM funding_review
WHERE value_state <> 'available'
   OR review_status <> 'checks_passed';
```

`TRY_CAST` leaves malformed values null for inspection. Never apply `COALESCE` to
convert missing funding inputs into zero. Different series have different units
and reporting cadences; joining them does not create a common observation date.

Appending captured exports can build an archive of **what this operator captured
from this date onward**. It cannot reconstruct earlier vintages, publication
times, revisions, or missing capture intervals. Do not label such an archive
complete point-in-time backtesting history.
