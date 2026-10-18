# Financial Evidence for Excel

Refresh source-linked funding and covered-institution evidence, inspect the
capture, and insert six new review sheets without overwriting existing analysis.
The public service needs no Financial Evidence account, API key or payment.

This is an Office.js task-pane add-in, separate from the downloadable XLSX
snapshots and Power Query queries. The source package is available for native
testing and supported sideloading. Microsoft Marketplace approval and runtime
acceptance on every compatible Excel host are separate checks; do not infer
them from this package.

## Install a development copy

Download [financial-evidence-excel.zip](financial-evidence-excel.zip) and inspect
`SHA256SUMS`. The included `excel/manifest.xml` points to the hosted HTTPS task
pane; the package includes the corresponding source and shared evidence parser.
It does not run a local server, install a desktop service, or grant permissions.

For Excel on the web, open a workbook, select **Home → Add-ins → More Settings**,
then **Upload My Add-in** and choose `excel/manifest.xml`. The exact navigation
can vary by host or tenant. If upload is unavailable, follow your administrator's
supported deployment policy; the browser desk remains a file-download route.
[Microsoft's web sideload instructions](https://learn.microsoft.com/en-us/office/dev/add-ins/testing/sideload-office-add-ins-for-testing).

For Excel on Mac, use [Microsoft's Mac sideload procedure](https://learn.microsoft.com/en-us/office/dev/add-ins/testing/sideload-an-office-add-in-on-mac).
For production organizational use, follow Microsoft's supported deployment route
for that tenant. Linux users use Excel on the web where their account permits
it, or the existing LibreOffice/browser export route; this package does not
provide a native Linux Excel application.

Manifest version `1.0.1.0` adds **Home → Financial Evidence → Open research review**
on hosts that support add-in commands. The button opens the same task pane; it
does not refresh research or insert sheets. Hosts that do not apply the command
override retain the manifest's task-pane launch location. The 16- and 20-pixel
ribbon icons are renders of the unchanged publisher SVG at
`../marketplaces/assets/icon.svg`.

## Use

1. Select **Open research review** in the **Financial Evidence** group on Excel's
   **Home** ribbon, or open the installed add-in through the host's add-in menu.
   The task pane should report
   **Connected to Excel** before insertion is available.
2. Enter up to five currency codes and up to five exact institution slugs.
   Defaults are `USD,EUR,INR` and `au-sfb,bajaj-finance`. Leave either field empty
   to skip it. Unknown slugs are explicitly uncovered, not fuzzy replacements.
3. Select **Refresh research**, then inspect capture time, row counts and scope.
4. Select **Insert new review sheets**. Six distinct `FE …` sheets contain
   Read me, Funding, Institutions, Gaps, Other data and Status.
5. Select **Download original evidence** to retain the original JSON responses
   beside your workbook. Review source clocks and gaps before using values.
6. Refresh again when the next review is due. Each insertion uses new sheet
   names. The add-in never edits existing analysis or schedules background work.

Changing an input invalidates the pending capture. Missing/withheld values remain
blank, zero remains numeric zero, and source text is inserted as text. A failed
request remains visible in Status alongside any successful results. If all
requests fail, insertion is disabled. An interrupted insertion can leave partial
new sheets; inspect those sheets before retrying. Nothing is deleted automatically.

Requests are limited to 30 seconds each, three at a time. The insertion adapter
bounds the capture to six sheets, 20,000 cells and a 2 MiB serialized write plan.
For larger captures use the office desk's downloadable files. Funding uses the
existing bounded public workflow; results may be delayed, partial or unavailable.
Funding levels across currencies are not stress rankings and institution states
are evidence-review states, not credit ratings.

## Permissions and data

`ReadWriteDocument` lets the adapter inspect worksheet names to avoid collisions
and create new review sheets. It does not read existing cell values, send workbook
contents, use Microsoft identity, or acquire an access token. Only the selected
currencies and slugs leave the task pane in ordinary public research requests.
See [privacy](https://beepboop2025.github.io/financial-evidence-skills/office/excel/privacy.html), [service terms](https://beepboop2025.github.io/financial-evidence-skills/terms/) and
[support](https://beepboop2025.github.io/financial-evidence-skills/support/).

The manifest targets Workbook with ExcelApi 1.1. A compatible API declaration is
not evidence that all corresponding hosts were tested. See the exact
[reviewer test script](https://beepboop2025.github.io/financial-evidence-skills/office/marketplaces/microsoft-reviewer.md) and
[release states](https://beepboop2025.github.io/financial-evidence-skills/office/marketplaces/status.json). Publisher verification can use a
separate test-only manifest whose task-pane URL ends with `?operator=1` to mark
requests synthetic. Apply that query flag to both the base `SourceLocation`
and the `Review.TaskpaneUrl` resource so fallback and ribbon launches remain
synthetic. Keep test manifests distinct from the submitted release. The existing
native acceptance receipt covers the earlier `1.0.0.0` operator manifest; it does
not establish native acceptance of this version's ribbon command.

## Rebuild from the repository

```sh
python3 scripts/build_excel_office_addin.py
python3 scripts/build_excel_office_addin.py --check
```

The archive keeps the `office-core.js` / `excel/` directory relationship needed
by the hosted code. Rehosting requires updating the manifest's HTTPS URLs and
checking the research gateway's allowed-origin policy; merely unpacking the ZIP
does not authorize a new web origin. The MIT licence covers client code, not
unrestricted redistribution of every upstream source.
