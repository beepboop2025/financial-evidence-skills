# Financial Evidence for Excel — certification notes

Package: [manifest.xml](../excel/manifest.xml). ID:
`acdb8bb2-280d-4c73-aadc-bbd4e1427bf0`, version `1.0.0.0`.
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
2. Open **Financial Evidence** from the installed/sideloaded add-in. The host
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

The publisher's own acceptance copy can add `?operator=1` to its source URL so
verification calls are labelled synthetic. Keep that test-only manifest separate
from the submitted production manifest. No separate analytics call or learning
enrollment occurs. Do not describe certification tests as independent adoption.

## Submission evidence still required

Record the validated manifest hash, hosted release identity, each tested Excel
build/platform, runtime results, keyboard acceptance and a real host screenshot.
Excel web acceptance alone does not establish Windows, Mac or mobile acceptance.
Use the actual Partner Center account to verify publisher identity and program
enrollment. The source files and this checklist are not account approval or
Microsoft Marketplace acceptance. The copied Power Query route has its own
native execution test and is not the Office.js add-in.
