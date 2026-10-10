# Seiche Reference FX — evaluator factsheet

Publisher: **LIQUILENS PRIVATE LIMITED**. Scope: **four ECB EUR reference-rate series**. Prepared 11 October 2026 IST. This is a rights-scoped evaluation dataset, not a cloud-marketplace listing, exclusive dataset, commercial contract or point-in-time archive.

| Property | Defined value |
| --- | --- |
| Series | ECBFX_USD, ECBFX_GBP, ECBFX_JPY, ECBFX_INR |
| Base / quote convention | USD, GBP, JPY or INR units per one EUR |
| Source publisher | European Central Bank |
| Source geography | EUR reference rates; no broader geographic coverage claim |
| Delivery | Fixed public GET CSV routes on api.seiche.info; JSON/CSV evaluation sample |
| Refresh | Source-published daily observations on applicable publication days; no contractual SLA |
| Sample | Last 20 available dates per series, 80 records total |
| Checked last date | 9 October 2026 in this capture; inspect manifest before use |
| Original availability clock | Unknown; first_available_at is null |
| Revision policy | Current upstream vintage; changes may revise earlier observations |
| Missing dates | Absent; no zero replacement, interpolation or forward-fill |
| Transformation | XML observations to dated rows with source and delivery metadata |
| Support | mrinal@liquilens.in; no new platform-specific SLA committed |
| History and provenance | Exact counts, first/last dates, response SHA-256 and source comments in sample-verification.json |
| Customer adoption | Not established by this sample or by endpoint availability |

[CSV sample](reference-fx-sample.csv) · [JSON sample](reference-fx-sample.json) · [Schema](reference-fx-sample.schema.json) · [Verification](sample-verification.json).

## Data dictionary

| Column | Type | Meaning |
| --- | --- | --- |
| series_id | string enum | Fixed Seiche series identity |
| base_currency | string, EUR | The denominator currency |
| quote_currency | string enum | USD, GBP, JPY or INR |
| observation_date | ISO date | Economic reference date, not retrieval date |
| value | positive decimal string | Exact source representation; preserves decimal precision |
| unit | string enum | Quote currency / EUR |
| source_retrieved_at | ISO datetime with timezone | When Seiche retrieved the upstream source |
| sample_captured_at | ISO datetime with timezone | When this evaluation captured the response |
| source_staleness | string | Source service's reported freshness at capture; not a guarantee |
| vintage | current_amended | Current upstream print, not historical as-published data |
| first_available_at | null | Historical first-availability time is not established |
| source_publisher | European Central Bank | Credit for the underlying observations |
| source_url | HTTPS URL | ECB 90-day XML used to verify this selected sample |
| delivery_url | fixed Seiche CSV URL | Public delivery endpoint for the series |
| rights_url | HTTPS URL | ECB reuse conditions |
| notice | string | Source credit, free-data availability and reference-rate boundary |

## Reuse scope

Source: European Central Bank. The original reference data is [freely available from the ECB](https://www.ecb.europa.eu/stats/eurofxref/). Its [copyright policy](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html), rechecked in this pass, governs accurate reproduction, source credit, identifying modifications and the free-source notice when sold. The notice must remain visible whenever accessed and before payment. Seiche and LIQUILENS PRIVATE LIMITED are independent of the ECB; no endorsement is implied.

The checked implementation converts numerical ECB observations into rows without interpolation, currency conversion or economic adjustment. This permission assessment applies only to the four listed numerical reference series. It does not cover unrelated publisher content, FRED-hosted licensed indices, bank documents, crypto venue data or broad product-family exports. The separately computed comparison in the sample FX report is labelled as a derivation.

## Validation

All 80 sample values matched the ECB current 90-day XML by currency and observation date. Four Seiche CSV responses retained source notices and reported `Access-Control-Allow-Origin: *`; all identified the same Seiche release in the manifest. Only the selected sample was checked against the ECB. Full-history parity, schedule recurrence, native platform ingestion, consumer permissions and independent use remain unverified.

The source parser rejects missing notices, wrong units, malformed or duplicate dates, blank/zero/invalid values and inconsistent last-observation clocks. The browser companion makes only user-triggered GET requests to the four fixed public CSV routes, with credentials and referrers omitted. It retains a dated research note locally when the user chooses to save it.

## Warehouse evaluation contract

Load the CSV into a consumer-owned staging table with the above column types. Keep `value` as text in raw storage and cast to a sufficient decimal type only in a derived analysis table. Keep source and capture clocks separate. A useful query groups by `series_id`, reports minimum/maximum observation dates and row counts, and verifies `first_available_at` is null. No native Snowflake share or Databricks table was created by this packet.

Point-in-time backtest eligibility is **false**. Long current-vintage history does not establish historical knowledge time.
