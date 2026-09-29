# Use a verified funding packet

Open the [public review](./) and choose **Save evidence packet** or **Download
CSV**. The browser checks SHA-256 hashes before preparing either download. Keep
the JSON packet alongside a CSV workbook: it contains the manifest, exact JSON
and CSV text, source notices, dates and exceptions.

For automation with Python 3.10 or newer:

```sh
python3 download_packet.py --output ./funding-review-001
```

Download [the client](download_packet.py) first and inspect it. It needs no
installed packages or account and sends no usage events. Use a new output path
for each run. Exit 0 means the acquired dated review passed its required checks;
exit 1 means it needs attention; exit 2 means acquisition or verification failed.

## Excel

Choose Data → From Text/CSV → `observations.csv`. Keep `metric_id`, `unit`,
`observation_date`, `source`, `value_state`, `review_status`, `review_asof`,
`canonical_latest_asof` and `newer_observation_available` beside the values.
Rates are percent; liquidity amounts and SOFR volume are USD billions. Reserve
balances are a weekly average; TGA is the opening balance. Do not convert an
unavailable cell into zero or describe every input as current because a download
succeeded.

## DuckDB

```sql
SELECT metric_id, value, unit, observation_date, value_state,
       review_status, canonical_latest_asof, newer_observation_available
FROM read_csv('funding-review-001/observations.csv', header = true)
ORDER BY metric_id;
```

## History and repeat reviews

The page's **Known by (UTC)** control filters the forward archive by first
verification time. Compare two packets or open the later selected packet to
inspect and download it. Historical packets are labelled historical. Their
observation dates do not imply that this service knew those values before its
archive began.

The API offers `/latest`, `/history?as_of=...`, `/compare?before=...&after=...`
and `/packets/{packet_id}/{manifest.json|review.json|observations.csv}` under
`https://api.seiche.info/funding-evidence`. Use packet IDs returned by the API;
verify JSON and CSV against the manifest before reuse. A hash verifies integrity,
not a publisher signature.

[Dataset contract](contract.json) · [Source rights](sources.md) ·
[Evaluation checklist](pilot.md)
