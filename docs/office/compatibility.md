# Office and Linux compatibility

Reviewed 28 October 2026. Windows add-in evidence updated; other host results retain their recorded dates. Use the path that matches the task and application.
The [setup guide](setup.md) gives installation and refresh instructions; the
[native acceptance record](native-acceptance.md) states what has actually run.

| Tool or path | Available workflow | Acceptance state |
| --- | --- | --- |
| Linux browser | Refresh funding/watchlists and download local review files | Published browser workflow verified; no automatic polling. |
| LibreOffice Calc | Open ODS or XLSX snapshots | Native Linux import and all-cell checks passed for both formats in LibreOffice 24.2.7. |
| Excel for the web | Open and save/download XLSX snapshots | Native UI roundtrip passed: all 260 fixture cells preserved. |
| Excel desktop | Open XLSX snapshots or save add-in-created workbooks | Windows add-in workbook save and independent readback passed on 28 October; arbitrary snapshot import and Mac desktop acceptance remain unrecorded. |
| Microsoft Power Query engine | Execute the three shipped funding/watchlist queries | Native Windows engine passed 22 assertion groups plus a failing control. HTTP responses were synthetic fixtures. |
| Excel / Power BI Power Query interface | Create queries and manually refresh the hosted service | Native UI/live HTTP refresh pending. Availability depends on the application's edition and account. |
| Excel Office add-in | Research task pane creates six new review sheets | Windows version 1.0.1.0 operator test passed ribbon launch, refresh and two insertions: 634 inserted cells checked across 12 review sheets, plus original markers. Earlier Excel web version 1.0.0.0 test checked 894 cells across 18 tabs. Mac/mobile, complete keyboard acceptance, unchanged production-manifest runtime and marketplace approval remain pending. |
| Google Sheets custom functions | Refresh funding or exact institution watchlists from cells | Pasteable script available. This is separate from the new Editor add-on. |
| Google Sheets bound Apps Script sidebar | Research sidebar creates six new review sheets | Native live capture/repeat verified; 317 capture cells and earlier review tabs preserved. |
| Google Sheets Editor add-on test deployment | Open the add-on through the Extensions menu and create a review | Installed-state (`AuthMode.NONE`) capture passed: all 317 capture cells, 650 earlier review cells and existing analysis markers preserved. Enabled-state (`AuthMode.LIMITED`) menu/sidebar also passed; marketplace approval remains separate. |
| ONLYOFFICE 10.0.0.1 | XLSX import, browser edit and save | Native route passed with all 260 cells preserved, including the expected edit. Use XLSX; ODS-to-XLSX export remains unsupported in the tested server. |
| Collabora CODE 26.04.5.1.1 / Nextcloud 35.0.2 with Office 12.0.1 | Open ODS or XLSX in a self-hosted browser workspace | Native conversion preserved all 260 cells in both formats; byte-exact WebDAV roundtrip and actual browser opening with all six tabs passed. Browser edit/save was not exercised. |
| Linux terminal / Node.js | Export ODS, XLSX, CSV, HTML and evidence JSON | Dependency-free command available; each run creates a new local directory. |
| Word, Google Docs, Writer | Import the HTML brief or copy cited tables | Portable document route; no native document add-in claimed. |
| PowerPoint, Google Slides, Impress | Copy cited tables from a review workbook | Manual presentation route; no automatic refresh integration claimed. |
| R, DuckDB, SQLite, DBeaver | Import the CSV tables | Portable data route; retain the accompanying status and evidence files. |
| OpenBB, notebooks, automation and API/MCP clients | Existing product integrations | Follow the [platform guides](../platforms/); each route has its own verification and provider requirements. |

The office projections cover Seiche funding, LiquiLens institution watchlists,
optional Undertow market liquidity and Palimpsest publication-coverage metadata.
Other family products remain accessible through their existing API/MCP routes;
their availability is not a claim of a new native office projection.

The [institution product/platform matrix](../distribution/institution-product-platforms.md)
maps broader research workflows to their existing clients. The Excel pane itself
accepts only funding currencies and institution selections.

Excel and Google marketplace acceptance, native add-in installation, file
compatibility and independent repeat adoption remain separate evidence states.
The [local pilot scorecard](../office-adoption/README.md) measures consenting
reviewers' useful tasks without adding covert identifiers or remote enrollment.

The [machine-readable route inventory](compatibility.json) and this table should
be updated together when a new native result is accepted. Source coverage,
dates, limitations and rights still apply in every client.
