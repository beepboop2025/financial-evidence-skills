# Financial Evidence for Excel — certification notes

Package: [manifest.xml](../excel/manifest.xml). ID:
`acdb8bb2-280d-4c73-aadc-bbd4e1427bf0`, version `1.0.2.0`.
Host: Workbook. Requirement: ExcelApi 1.1. Permission: ReadWriteDocument.
Publisher and manifest ProviderName: LIQUILENS PRIVATE LIMITED.

The task pane is hosted at
`https://beepboop2025.github.io/financial-evidence-skills/office/excel/taskpane.html`.
Confirm these exact bytes are published before beginning host acceptance. Use
[Microsoft's supported sideload procedure](https://learn.microsoft.com/en-us/office/dev/add-ins/testing/sideload-office-add-ins-for-testing)
for the host under review. A tenant policy can prevent sideloading; that outcome
is an access gate, not a passed or failed runtime test.

## First-use test

1. Open a blank workbook with `Keep my analysis` and `42` in an existing sheet.
2. On Excel's **Home** ribbon, find the **Financial Evidence** group and select
   **Open research review**. Confirm the button has a readable label and tooltip
   and can be reached using the host's keyboard navigation. On a host that does
   not apply the command override, open the installed add-in through its add-in
   menu. Opening the pane must not refresh research or insert sheets. The host
   status should say it is connected to Excel. Insertion must remain disabled
   if the host or the declared API requirement is unavailable.
3. Enter `USD,EUR` in **Funding currencies** and `au-sfb,unknown-bank` in
   **Institution watchlist**. Select **Refresh research**.
4. Inspect the visible capture timestamp, row counts and scope. No Financial
   Evidence account, key or purchase is required. Public source values may
   change and can be delayed, partial or unavailable; fixed values are not
   expected. A capture should preserve the source's dates and limitations.
5. Select **Insert new review sheets**. Confirm six new `FE …` sheets appear,
   containing the capture's Funding, Institutions, Gaps, Other data, Status and
   Read me tables. `unknown-bank` must remain explicitly uncovered. Confirm the
   original `Keep my analysis` and `42` cells remain unchanged.
6. Select **Download original evidence** and inspect its original responses,
   selected requests, source clocks and capture time. Save it with the workbook.
7. Select **Insert new review sheets** again. The add-in must either create a
   distinct new capture group or report a safe collision; it must not overwrite
   existing sheets. Refresh again to obtain new data on a later review.
8. Change an input without refreshing. The previous capture must become
   unavailable for insertion. Try empty inputs, six currencies and malformed
   slugs; errors should be visible. All failed requests must not become a
   successful insertable capture; a partial result must retain failed statuses.
9. Complete the keyboard, focus, narrow-pane and privacy checks in
   [the common reviewer script](reviewer-tests.md).

## Data and permissions

The task pane sends only entered currencies/slugs to the public research gateway.
It does not send cells, sheet names, Microsoft identity or credentials. The
ReadWriteDocument permission is used to check worksheet names for collisions
and create new review sheets. It does not read or update existing cells.
See [the exact Excel privacy notice](../excel/privacy.html).

The publisher's own acceptance copy can add `?operator=1` to both its base
`SourceLocation` and the `Review.TaskpaneUrl` resource so verification calls
from either launch path are labelled synthetic. Keep that test-only manifest separate
from the submitted production manifest. No separate analytics call or learning
enrollment occurs. Do not describe certification tests as independent adoption.

## Recorded acceptance and remaining submission evidence

The [28 October Windows receipt](../excel/native-acceptance-windows-20261028.json)
records version `1.0.1.0` operator-manifest validation and deployment, native
ribbon label/tooltip launch, manual refresh, two six-sheet insertions and all
634 inserted cells checked against the original JSON. The original analysis
markers survived. [Actual host screenshot](assets/native-excel-windows-20261028.png).
The host was Microsoft 365 Apps for business Version 2609, Build 20430.20180.
The deployment was removed after testing. The earlier
[18 October web receipt](../excel/native-acceptance.json) remains separate and
covers version `1.0.0.0`.

Forward Tab, visible focus and Return-to-refresh passed on Windows. Reverse Tab,
full ribbon keyboard traversal, the native all-requests-failed network case,
Mac/mobile and a new web run are still unqualified. The production manifest's
validation is separate from installation through the test-only operator manifest.
Retest those gates and record host/build, release hashes and results before
extending supported-host claims. The screenshot is the original 2932×1404
capture; check the active Partner Center form's dimensions before upload.
Use the actual Partner Center account to verify publisher identity and program
enrollment. The source files and this checklist are not account approval or
Microsoft Marketplace acceptance. The copied Power Query route has its own
native execution test and is not the Office.js add-in.

## Institutional positioning and product scope

This listing contains the supported Seiche funding and LiquiLens institution
review workflow. It supports source review and evidence export; it does not
connect private bank systems, read existing workbook cells, grant access to a
vendor subscription, or approve a regulatory decision. RBI asset-quality tools
and the broader product family have separate API/MCP routes in the
[institution product/platform matrix](../../distribution/institution-product-platforms.md).
Do not add unimplemented product commands to this listing or create duplicate
Microsoft submissions to represent those routes. The existing publisher plugins
are separate distribution packages; they do not establish official directory
approval or private institutional controls.

## Verification identity

Generate synthetic verification manifests with `scripts/build_excel_office_addin.py --operator-manifest /path/to/verification.xml`. The generated manifest has its own app ID and verification display name; never reuse the production app identity for an operator URL. Version 1.0.2.0 advances the production configuration past the earlier shared test identity. Historical 1.0.1.0 operator acceptance does not establish native acceptance of 1.0.2.0.
