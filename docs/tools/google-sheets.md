# Financial Evidence in Google Sheets

Bring a page of cited bank, dollar-funding, money-market or indicative liquidity research into a sheet. The function keeps source dates, units, missing values, rights and retrieval status beside the numbers. It uses the public research endpoint without an API key.

## Set up once

1. Open a blank Google Sheet and choose **Extensions → Apps Script**.
2. Add a script file named `FinancialEvidenceSheets`. Paste the complete contents of [FinancialEvidenceSheets.gs](FinancialEvidenceSheets.gs) and save. Preserve any existing scripts.
3. Back in Sheets, type `1` into **A1** as a manual refresh counter.
4. In **A3**, enter:

   ```text
   =FINANCIAL_EVIDENCE("money_markets","USD",20,0,$A$1)
   ```

Leave the area below A3 through column X empty: the function returns 24 columns, 13 status rows, a header row, then up to 20 evidence rows in this example. Sheets refuses to overwrite occupied cells. In locales using semicolons as formula separators, replace the commas with semicolons.

Change A1 to `2` when you want another request. The counter's value is not sent to the service. Use a manually entered number, text value or checkbox; do not use `NOW()` or `RAND()`. Google requires deterministic arguments and a directly referenced changing cell to trigger recalculation. URL Fetch is supported in custom functions, which have a 30-second execution limit; one request can still time out. [Google custom-function guidance](https://developers.google.com/apps-script/guides/sheets/functions)

## Choose a research table

```text
=FINANCIAL_EVIDENCE("bank_risk","",50,0,$A$1)
=FINANCIAL_EVIDENCE("market_liquidity","",50,0,$A$1)
=FINANCIAL_EVIDENCE("money_markets","US",50,0,$A$1)
```

`entity` is a case-insensitive substring of an entity ID or name. A filter may match no rows; that is not a zero observation. The seven allowed datasets are:

| Dataset | Research use |
| --- | --- |
| `money_markets` | Current published benchmark-rate evidence with native units and rights |
| `money_market_history` | Currently published historical observations; not historical publication vintages |
| `capital_markets` | Published funding and capital-market context |
| `bank_risk` | Covered bank and lender filing evidence; inspect actual coverage |
| `market_liquidity` | Indicative BTC market-liquidity research; not executable quotes |
| `china_economy` | Available China economic evidence with coverage boundaries |
| `source_health` | Source retrieval and reported-state context |

Arguments are `FINANCIAL_EVIDENCE(dataset, entity, limit, offset, refreshCell)`. Defaults are `money_markets`, an empty entity filter, 50 rows and offset 0. `limit` accepts integers from 1 to 200; `offset` accepts 0 to 100000. The refresh argument is optional, but referencing a manual counter makes refreshing clearer. Each invocation performs exactly one request, without scheduled jobs, retries or automatic pagination.

## Read status before using values

The status block appears above every table, even when no rows match:

- **transport_status** describes source retrieval, not evidence quality. A `partial` or `unavailable` response stays visibly labelled; inspect `diagnostics_json` and `source_provenance_json` before interpreting its rows.
- **source_provenance_json** retains source URLs, hashes, reported source states, source clocks and cache metadata. Transport may be `complete` while a source itself reports `PARTIAL`.
- **page_scope**, **page_counts** and **next_offset** make omitted pages visible. To view another page, make a separate call using the reported next offset. Even a final page starting after zero remains labelled a partial dataset page. Separate calls can observe different source snapshots; use [research_client.py](research_client.py) for complete, consistent, multi-page captures.
- **value_state** distinguishes numeric values, including zero, from null values. Explicitly restricted numeric values are blanked defensively and marked `withheld_by_client`; availability and rights fields remain visible. A null or unknown right is not a grant of permission.
- **as_of**, **published_at**, **knowledge_time** and **retrieved_at** preserve their source meanings. `fetched_at_utc` records this request, not the age of an observation.

Text that could be interpreted as a spreadsheet formula is prefixed with an apostrophe. Genuine numeric negatives remain numbers. Unexpected schema, malformed page counts, redirects, non-JSON responses and HTTP failures produce an error rather than substituted data. A blocked spill range or a Google quota/runtime error is handled by Sheets itself; reduce repeated formulas and retry manually after resolving it.

The function sends only the chosen public dataset, entity filter, limit and offset to `api.seiche.info`. Do not put private client information in the entity argument. It does not read other cells, open spreadsheets, store credentials, install triggers or send the refresh counter. It is a copyable script, not a published Google Workspace Marketplace add-on or a Google endorsement. Software licensing does not change underlying source-data rights; retain attribution and check the relevant source terms before sharing or redistributing data.

## Validation status

The JavaScript is tested in Node with mocked Apps Script transport, including bounds, null/zero distinctions, pagination, partial retrieval, explicit restrictions and formula-like source text. A live public response is also parsed through the same rendering path during operator verification. **Google-native installation and execution have not been verified**; this is a provided setup path, not a claim of an installed add-on or independent user adoption.

Run the focused checks from the repository root:

```sh
node --test tests/test_google_sheets.mjs
```

For an optional live parser check that identifies the request as operator verification:

```sh
FINANCIAL_EVIDENCE_LIVE_CHECK=1 node --test tests/test_google_sheets.mjs
```
