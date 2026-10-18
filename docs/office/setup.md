# Financial Evidence in office and Linux tools

[Open the office desk](https://beepboop2025.github.io/financial-evidence-skills/office/)
or [download the complete kit](office-kit.zip).

Start with a funding comparison and covered-institution watchlist. Refresh when
your next review is due. Public reads need no account or API key. The desk sends
only your selected currencies, institution slugs and datasets to the public
service; it does not read or upload a workbook.

Seiche supplies published funding benchmarks and capital-market observations.
LiquiLens supplies covered-institution evidence and gaps. Optional tables expose
Undertow market-liquidity research and Palimpsest publication coverage. Palimpsest
metadata does not imply access to restricted economic values. For the wider
family, use the [product-specific API and MCP catalog](../connect/).

## Browser: the quickest first result

1. Enter currencies such as `USD,EUR,INR` and exact institution slugs such as
   `au-sfb,bajaj-finance` in the office desk.
2. Select **Refresh research**. Each request gets a status row, including failures.
3. Download **Excel workbook** (`review.xlsx`) or **LibreOffice workbook**
   (`review.ods`) and **Full evidence JSON** (`evidence.json`).
4. Inspect Funding, Institutions, Gaps and Status before using the result. Add your
   calculations in your own workbook or a separate sheet.
5. Repeat the same selection on your next review. Save each export under a new
   dated name so previous observations remain available.

Files contain typed values, sources, dates and coverage states. No macros,
background refresh or external workbook links are installed. A returned request
is not a freshness judgment. The Status sheet retains source-reported states and
clocks, diagnostics and page scope. Optional dataset previews stop at 200 rows and
show `next_offset`; use the [research client](../tools/research_client.py) for a
complete bounded capture. Funding uses the existing 100-row workflow endpoint.

## Google Sheets

The new script provides two custom functions. It can coexist with the older
`FINANCIAL_EVIDENCE` dataset-page function.

1. Open a blank Sheet, then **Extensions → Apps Script**.
2. Paste the complete [FinancialEvidenceOffice.gs](FinancialEvidenceOffice.gs),
   save, and return to the Sheet. Do not run a custom function in the script editor.
3. Put the number `1` in `B1`. Enter `USD`, `EUR`, `INR` in `A2:A4`.
4. Enter `=FINANCIAL_FUNDING(A2:A4,$B$1)` in `D2`. Leave columns D through AB and
   the rows below empty for the 25-column result.
5. On another tab, enter institution slugs in `A2:A6`, a plain refresh number in
   `B1`, and `=FINANCIAL_WATCHLIST(A2:A6,$B$1)` in `D2`. Leave D through T and the
   rows below empty for its 17-column result.
6. Change B1 to request another review. Do not use `NOW()` or `RAND()` as the
   refresh dependency. Some locales use semicolons between formula arguments.

The funding function accepts up to five distinct currencies and batches their
requests. The watchlist makes one request for up to five distinct exact slugs.
Blank range cells are ignored. Unknown slugs appear as `not_covered`; the script
does not replace them with similar names. Both functions include request status;
the watchlist also includes individual coverage gaps.

Google limits custom functions to 30 seconds. A slow service can produce a Sheets
timeout; narrow the selection or retry manually. Sheet recalculation can request
data again. There are no time triggers or retries. Only supplied selections leave
the sheet; the refresh cell and other workbook cells are never sent. Formula-like
source text is escaped and missing or explicitly withheld numbers stay blank.

This is a copyable Apps Script, not a Google Workspace Marketplace add-on.
Contract tests are separate from Google-hosted execution, which remains pending.
[Google's custom-function rules](https://developers.google.com/apps-script/guides/sheets/functions).

## Excel and Power BI

**Any edition that can import XLSX:** open the downloaded workbook. In Excel on
the web, upload it through your own OneDrive or workbook picker. Repeat the browser
export for a fresh snapshot. The snapshot does not refresh itself.

**Power Query editions with Web access:** create blank queries and use Advanced
Editor. Choose Anonymous authentication for `https://agents.seiche.info`.

1. Paste [FinancialEvidenceRows.pq](FinancialEvidenceRows.pq) and name the query
   `FinancialEvidenceRows`.
2. Paste [FinancialEvidenceFunding.pq](FinancialEvidenceFunding.pq) into a second
   query named `FinancialEvidenceFunding`.
3. Paste [FinancialEvidenceWatchlist.pq](FinancialEvidenceWatchlist.pq) into a third
   query named `FinancialEvidenceWatchlist`.
4. Invoke these expressions in new blank queries and load their tables:

```powerquery
FinancialEvidenceFunding({"USD", "EUR", "INR"})
FinancialEvidenceWatchlist({"au-sfb", "bajaj-finance"})
```

Use Data → Refresh All for a later review. Funding fails explicitly if a source
cannot supply a complete capture; it does not carry old values forward as new.
The watchlist keeps gaps, warnings and category coverage as JSON columns.
Power Query availability, supported sources, credentials and refresh differ by
Excel version and tenant. Native Excel/Power BI execution of these two new
queries remains unverified. Power BI Desktop is not a Linux desktop application.
Use the browser/CSV route on Linux where Power Query is unavailable.
[Microsoft's Web connector documentation](https://learn.microsoft.com/en-us/power-query/connectors/web/web).

## LibreOffice Calc

Download ODS and open it in Calc on Linux, macOS or Windows. It is a native
OpenDocument workbook, not an extension. Sources and gaps are separate sheets.
Numeric zero remains zero; unavailable values remain empty numeric cells with a
separate `value_state`. There are no embedded formulas or automatic web requests.

For an existing workbook, use Sheet → Insert Sheet from File to import the
needed CSV, or open the CSV and copy its table. Use UTF-8 and comma as the
separator, with double-quote as text delimiter. Keep dates and identifiers as
text and disable formula evaluation during CSV import. For repeat work, generate
a new capture and import the new table into your own workbook. Do not overwrite
the file containing your analysis with an exported snapshot.

## Linux command line

Extract the kit into a directory you own. Requires Node 20 or later; the client
uses only Node built-ins. No `npm install` is needed.

```sh
node refresh.mjs --currencies USD,EUR,INR \
  --institutions au-sfb,bajaj-finance \
  --output ./review-2026-10-18

node refresh.mjs --datasets market_liquidity,china_economy \
  --output ./wider-review-2026-10-18
```

Output must be a new directory. It contains `review.ods`, `review.xlsx`, six CSV
tables, `brief.html`, `evidence.json` and `receipt.json` with file hashes. The
command exits 2 when any request failed, while retaining successful rows and
explicit failures. Exit 0 means requests returned valid contracts, not that all
data is current or complete. For operator checks add `--verification`; such
requests are marked synthetic and are not external adoption.

You can call this from an existing local scheduler if you choose. The kit itself
creates no timers, services, automatic uploads or messages. Use a new dated output
directory for each invocation and check both the exit code and Status.

## Other office tools

- **ONLYOFFICE Desktop Editors or Docs:** open/import `review.xlsx`.
- **Collabora Online / Nextcloud Office:** upload `review.ods` or `review.xlsx`
  using your own account and supported editor.
- **Google Drive / OneDrive / Nextcloud:** store the workbook and `evidence.json`
  together. Storage is not a live data connector.
- **Google Sheets:** File → Import the XLSX snapshot if Apps Script is unavailable.

These are file-access routes, not published extensions. Native execution in
each vendor's current application is not implied. See [compatibility states](compatibility.json).

## Documents and presentations

Open `brief.html` locally for a source-linked review. Word and LibreOffice Writer
can import HTML; Google Docs users can copy the required tables from the local
brief or workbook. Keep the observation date, unit, source and availability
columns when copying. For Slides, PowerPoint and Impress, paste the same cited
tables. No native Docs, Word, Slides or PowerPoint add-on is claimed.

## SQL, R and BI

Keep the Status table and original JSON next to any imported values.

```sql
-- DuckDB: preserve missing values and text dates during initial inspection.
SELECT selection, metric, value, value_state, unit, as_of, source_url
FROM read_csv('funding.csv', header=true, all_varchar=true);
```

```r
funding <- read.csv("funding.csv", colClasses = "character",
                    check.names = FALSE, na.strings = "")
```

SQLite and DBeaver can import CSV with an explicit schema. Metabase and Superset
can query tables imported into a supported database; this kit does not install
a native BI driver or create a database. Do not infer that CSV import means a
marketplace connector is available.

For Python, Jupyter and Google Colab, reuse the
[research notebook and bounded client](../tools/). For OpenBB use the
[existing extension and custom backend](../tools/#openbb). For n8n, Node-RED,
Activepieces and agent clients, use the [integration directory](../platforms/).

## Verification and distribution

The implementation and tests distinguish generated-file checks, actual office
application acceptance and third-party marketplace review. Local request probes
are labelled synthetic. Availability is not evidence of independent use.

Google Workspace Marketplace and Microsoft AppSource publication require their
own packaging, account configuration and review; no listing is claimed by this
kit. The existing OpenBB application is already tracked separately.
