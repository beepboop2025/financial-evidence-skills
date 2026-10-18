# Office and Linux compatibility

Reviewed 18 October 2026. Use the path that matches the task and application.
The [setup guide](setup.md) gives installation and refresh instructions; the
[native acceptance record](native-acceptance.md) states what has actually run.

| Tool or path | Available workflow | Acceptance state |
| --- | --- | --- |
| Linux browser | Refresh funding/watchlists and download local review files | Published browser workflow verified; no automatic polling. |
| LibreOffice Calc | Open ODS or XLSX snapshots | Native Linux import and all-cell checks passed for both formats in LibreOffice 24.2.7. |
| Excel for the web | Open and save/download XLSX snapshots | Native UI roundtrip passed: all 260 fixture cells preserved. |
| Excel desktop | Open XLSX snapshots | File format provided; desktop application acceptance not recorded here. |
| Microsoft Power Query engine | Execute the three shipped funding/watchlist queries | Native Windows engine passed 22 assertion groups plus a failing control. HTTP responses were synthetic fixtures. |
| Excel / Power BI Power Query interface | Create queries and manually refresh the hosted service | Native UI/live HTTP refresh pending. Availability depends on the application's edition and account. |
| Excel Office add-in | Research task pane creates six new review sheets | Implementation and isolated tests available; native add-in host execution pending. |
| Google Sheets custom functions | Refresh funding or exact institution watchlists from cells | Pasteable script available. This is separate from the new Editor add-on. |
| Google Sheets Editor add-on | Research sidebar creates six new review sheets | Source package and isolated tests available; native host execution awaits permission. No marketplace approval claimed. |
| ONLYOFFICE | XLSX snapshots | Native acceptance closeout pending. Use XLSX; ODS-to-XLSX conversion remains unsupported in the tested server. |
| Collabora Online / Nextcloud Office | Open review files in a self-hosted browser workspace | Native conversion and complete browser/save acceptance are tracked separately; final integration closeout pending. |
| Linux terminal / Node.js | Export ODS, XLSX, CSV, HTML and evidence JSON | Dependency-free command available; each run creates a new local directory. |
| Word, Google Docs, Writer | Import the HTML brief or copy cited tables | Portable document route; no native document add-in claimed. |
| PowerPoint, Google Slides, Impress | Copy cited tables from a review workbook | Manual presentation route; no automatic refresh integration claimed. |
| R, DuckDB, SQLite, DBeaver | Import the CSV tables | Portable data route; retain the accompanying status and evidence files. |
| OpenBB, notebooks, automation and API/MCP clients | Existing product integrations | Follow the [platform guides](../platforms/); each route has its own verification and provider requirements. |

The office projections cover Seiche funding, LiquiLens institution watchlists,
optional Undertow market liquidity and Palimpsest publication-coverage metadata.
Other family products remain accessible through their existing API/MCP routes;
their availability is not a claim of a new native office projection.

Excel and Google marketplace acceptance, native add-in installation, file
compatibility and independent repeat adoption remain separate evidence states.
The [local pilot scorecard](../office-adoption/README.md) measures consenting
reviewers' useful tasks without adding covert identifiers or remote enrollment.

The [machine-readable route inventory](compatibility.json) and this table should
be updated together when a new native result is accepted. Source coverage,
dates, limitations and rights still apply in every client.
