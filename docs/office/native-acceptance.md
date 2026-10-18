# Native office acceptance

This page records completed native checks and their limits. A working import,
query, marketplace listing and independent analyst adoption are different results.

## Excel for the web — XLSX import and roundtrip passed

On 18 October 2026, Excel for the web opened the synthetic review workbook and
saved/downloaded it through its native interface. All **260 expected cells**
matched after the roundtrip. The exact uploaded file, expected-cell fixture and
downloaded workbook are bound by SHA-256:

```text
f23f3516d89b51784f171958928d514dd4e904e837066301ac30df1cbd857bd0  uploaded-review.xlsx
a97fbdad2d3f44cc6212dcf832afe221ba4ff937cdfee06314315a6a0e599154  expected-cells.json
bceffc5130f48b67648a6a2b852d6edf54286a274a81861d8cbc4013703fb2fb  excel-roundtrip.xlsx
```

The [fixture generator](https://github.com/beepboop2025/financial-evidence-skills/blob/b6266ce063d2b1c37ff4a47fb710ab8f72b3b495/scripts/create_office_fixtures.cjs)
and [cell verifier](https://github.com/beepboop2025/financial-evidence-skills/blob/b6266ce063d2b1c37ff4a47fb710ab8f72b3b495/scripts/office_native/verify_cells.py)
define the synthetic acceptance contract, including original source text,
Unicode, booleans, zero, negative values, missing values and source gaps.
The host was Excel for the web; its internal build number was not exposed in
the recorded receipt. Account identifiers and private workbook URLs are not
published.

This proves the **XLSX snapshot import/save path**. The tested account exposed
the Queries pane but no Get Data or New Query entry, so Excel-hosted Power Query
creation/refresh was not completed. The [Office add-in](excel/README.md) has
separate native acceptance recorded below.

## Excel Office add-in — web capture and repeated insertion passed

On 18 October 2026, the published Office.js task pane connected inside Excel for
the web. A live capture at `09:58:46.619Z` requested USD/EUR funding and the exact
institution selections `au-sfb,unknown-bank`: three requests, zero failures.
The same capture was inserted twice, creating two separate sets of six sheets.
The downloaded workbook matched all **894 checked cells**: 317 cells in each
insertion and all 260 original fixture cells, across 18 tabs. Each insertion
preserved 277 strings, 9 numbers, 6 booleans and 25 blanks. No formula cells or
external workbook links were present.

The test used the public HTML/JavaScript from
[`fe3894e`](https://github.com/beepboop2025/financial-evidence-skills/commit/fe3894e5654f304d03cbc0e50bc811857368943f),
verified after [Pages deployment](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/39117298512).
The privately sideloaded manifest changed only `SourceLocation` by adding
`?operator=1`, which activates existing synthetic verification attribution.
This verifies the published runtime through that test manifest. The unchanged
production manifest separately passed `office-addin-manifest` **3.0.1**
production validation; its runtime installation was not the tested route.

```text
5692bcd3b9e14c39a0108198db2bb321c7b7738bfdde5accca3bb6ddd2ff3f77  officejs-repeat-roundtrip.xlsx
8c8504e57863c6a136be8dce7a0c0622572e4fbc467a7ca34706d8bf806cdb87  officejs-capture.json
170530e4b99e72bf7985f383bbdb9101838711721c3585243db8038d4f955a77  production-manifest.xml
f007988160d6595106cb06782651bc481e9684887d1bde90a205182bcd533b82  operator-test-manifest.xml
```

A six-currency selection produced the expected validation error and removed the
old preview and insert controls. Request counts for that invalid action were
not independently measured. The live capture contained no formula-like strings;
the original fixture's one such string stayed inert. Desktop hosts, marketplace
approval and independent adoption remain unverified. See the
[public receipt](excel/native-acceptance.json) and
[manifest validation record](marketplaces/microsoft-manifest-validation.json).

## LibreOffice Calc on Linux — ODS and XLSX passed

The [native Linux check](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/39115197306/job/117639720098)
passed on source `f85cc8c15a21e219aaa9ce019b1498b94fbe4446` using Ubuntu 24.04 and
LibreOffice **24.2.7** (`4:24.2.7-0ubuntu0.24.04.7`). LibreOffice converted both
generated ODS and XLSX files, and every expected cell matched after conversion.
The retained `linux-office-acceptance` artifact includes the receipt and fixtures.

The same job also checks the original files with independent readers, archive
integrity and absence of unexpected formulas or external workbook links. These
are native file-compatibility checks; they do not make the snapshots live queries.

## ONLYOFFICE — XLSX import, edit and save passed

The [native ONLYOFFICE run](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/39115847600)
passed using Document Server **10.0.0.1**. It verified native XLSX import,
browser document readiness, an actual keyboard edit and the save callback.
All 260 expected cells matched both the imported and saved workbook, including
the deliberately changed cell in the saved expectation.

The run tested branch source `27a42b5be121126635bf49f454fcdc0ac00dd33c` through
GitHub's merge checkout `840e207bfc1a3bc1e48c34368e8047b43f4fdb2e`; both have the
same source tree. The `office-native-onlyoffice` artifact retains the native
receipt, workbook exports and browser evidence.

```text
ca17889f10b11141cc6441836aebdd2835cf3e1b49681b2fd6e155c94b7850b3  onlyoffice/documentserver image digest
f23f3516d89b51784f171958928d514dd4e904e837066301ac30df1cbd857bd0  input-review.xlsx
b6d303c074c4495858924b5b6c1428664ff26fd3414e911ec1a5378ceac2e807  saved-review.xlsx
```

ODS browser readiness also passed, but **ODS-to-XLSX export remains unsupported**
in this tested server: exported number-format metadata was rejected by the
independent reader. Use XLSX for the supported ONLYOFFICE import/edit/save path.
This isolated server verification is not certification of every customer host.

## Collabora and Nextcloud Office — ODS and XLSX import and browser opening passed

The [native integration run](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/39115847600)
tested Collabora CODE **26.04.5.1.1**, Nextcloud **35.0.2** and its
richdocuments Office app **12.0.1**. Collabora converted both ODS and XLSX through
its native engine, preserving all **260 expected cells** in each. Both files
survived a byte-exact Nextcloud WebDAV upload/download roundtrip.

The actual Nextcloud Office browser opened both documents through WOPI. The
Collabora iframe displayed all six expected sheet tabs, and the native
spreadsheet status confirmed the same six sheets. **Editing and saving through
Nextcloud Office were not exercised.** A vendor welcome overlay remained in
the screenshots; the document and sheet tabs had loaded behind it.

The source and merge checkout are the same as the ONLYOFFICE run above. The
`office-native-nextcloud-collabora` artifact contains the receipt, fixtures,
converted files and browser evidence. Pinned image digests and input files are:

```text
bb8f3c9c5c9016045f25fccb5f0649be94469ebc7c7cc379f3576e470cccf33d  collabora/code image digest
a588aa5353703b44106a6129adaaf7bf22521b7a4754f9f529b3228d6aa390c5  nextcloud image digest
0639ab0e3413142a76334af20ca88cba0a351a11c9c07effa0f1eb7f05941f2c  richdocuments-v12.0.1.tar.gz
c69774eb06435343f01774647aa9da4f403911edf4effc44014207a3cacdf457  input-review.ods
f23f3516d89b51784f171958928d514dd4e904e837066301ac30df1cbd857bd0  input-review.xlsx
```

This verifies the isolated server versions and import/open routes listed here.
It does not establish compatibility with every customer's Nextcloud setup.

## Google Sheets Editor add-on test deployment — installed and enabled states passed

On 18 October 2026, the research sidebar ran inside real Google Sheets through
both a bound Apps Script project and an **Editor add-on test deployment**. The
Editor test used the installed state (`AuthMode.NONE`, enabled state false),
opened the sidebar through the Extensions menu, and completed a new capture at
`09:34:05.410Z`. All three selected live requests returned with zero failures.
The explicit synthetic verification option was selected.

A second Editor test deployment used the enabled-in-current-document state
(`AuthMode.LIMITED`). Its Extensions menu opened the research sidebar
successfully. That check verified the menu/sidebar lifecycle without repeating
the product requests; the complete capture below belongs to the installed-state
test.

The downloaded workbook was compared with the exact capture JSON: **all 317
cells matched**, including 277 strings, 9 numbers, 6 booleans and 25 blanks.
The earlier first capture also still matched all 317 cells of its original JSON.
All **650 existing cells in the 14 earlier review tabs** matched their prior
workbook export. The separately entered analysis markers—text in A1 and numeric
42 in B1—were confirmed before the run and survived unchanged. The run added six
new review tabs, for 21 total, with no formula cells or external workbook links.

```text
c03ef2b56471ca9d5d0cecd9673dc6b59410ec3ff775c156d5c98939038d3d45  editor-capture.json
b1326a9a2b2ea1aa278b10640443a646cb6fc631f19b6f53b8caa13f2aaec306  editor-roundtrip.xlsx
58bd3044f6a3d0de896039dbea672668c4e3c4b9b1f1926ceda527da77eea270  first-capture.json
359721baa093ccd1294845e015c3911b17e86d83e600a9ce0d3ed32e46f30d4d  prior-sidebar-roundtrip.xlsx
```

Two earlier bound-sidebar captures at `09:30:04.269Z` and `09:30:28.212Z` each
returned three requests with zero failures and created separate six-tab sets.
An invalid six-currency selection was rejected without adding tabs. Two partial
Read me tabs from earlier failed attempts remained visible for recovery.
The second capture was not compared with its full JSON because that download
was blocked; its workbook cells were subsequently verified unchanged after the
third capture. These captures contained no formula-like source strings, so
native execution does not extend the isolated escaping test coverage.

The final sidebar revision also passed a native validation/retry check. A
six-currency selection displayed the expected error with focus on Close;
Escape dismissed it and restored focus to Create review. A valid retry at
`09:40:48.368Z` created six new tabs with three requests and zero failures,
with synthetic verification selected. This was a UI check; its cells were not
included in the full JSON comparisons above.

This verifies the **bound sidebar, installed-state Editor live capture,
enabled-state Editor menu/sidebar, typed cells, repeat behavior and preservation
of existing analysis**. Google Workspace Marketplace approval remains separate.
Account identifiers and private Google file URLs are
omitted. The [sidebar source](https://github.com/beepboop2025/financial-evidence-skills/blob/f85cc8c15a21e219aaa9ce019b1498b94fbe4446/docs/office/marketplaces/google/Code.gs)
and [setup instructions](marketplaces/google/README.md) remain public.

## Microsoft Power Query engine — passed

On 18 October 2026, the [Windows acceptance workflow](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/39114203632)
passed against source commit `b6266ce063d2b1c37ff4a47fb710ab8f72b3b495`.

| Component | Verified version or scope |
| --- | --- |
| Runtime platform | GitHub-hosted `windows-2022` runner |
| Microsoft SDK package | `Microsoft.PowerQuery.SdkTools` 2.155.2, pinned SHA-512 checked before extraction |
| PQTest application | 2.155.2.0 |
| Microsoft Mashup Engine | 2.155.504.0 |
| Shipped expressions | `FinancialEvidenceRows.pq`, `FinancialEvidenceFunding.pq`, `FinancialEvidenceWatchlist.pq` |
| Results | 22 assertion groups passed; separate deliberately incorrect numeric assertion rejected |
| Transport | Only `Web.Contents` replaced with deterministic synthetic fixture responses |

The harness embeds the actual shipped query expressions unchanged. Microsoft's
engine executes their data validation and table transformations. The successful
result is checked in the engine's evaluated output, and the failing control must
produce the precise expected error. A process exit code of zero alone is
insufficient: the engine can use it when a query test fails.

The checks cover:

- Positive, zero, negative and null numeric values, literal formula-like source
  text, source URLs and original observation/retrieval dates.
- Funding currency normalization, deduplication and bounds; distinct zero/missing
  states; restricted values withheld while their restriction remains visible.
- Exact institution coverage, explicit uncovered selections, zero versus missing
  metrics, source gaps, warnings and evidence limits.
- Rejection of malformed schemas, wrong dataset/selection identity, incomplete
  transport, unresolved pagination, incorrect row counts, duplicate/omitted
  institutions and unexpected financial authority.

The artifact named `power-query-native` contains the generated queries, engine
outputs, version record and acceptance receipt. Both actual Windows checkout
hashes and LF-normalized source hashes are retained. The latter match the
published query source:

```text
9009772b17e128897068a1acea895563cd15f7ae18381fa5253d54adbde9e9f0  FinancialEvidenceRows.pq
08df13f125330f2d54e41d01f4bbfa5e73e084f5c7a3de0b94d4e071efb257f3  FinancialEvidenceFunding.pq
0f568da06fdd04ac424d0fd5832aba222b8f04c43bf23998d0136910ae756a2b  FinancialEvidenceWatchlist.pq
```

This verifies **Microsoft Power Query runtime behavior with controlled HTTP
fixtures**. It does not establish Excel UI refresh, live network authentication,
an add-in marketplace approval or independent usage. The Excel file import
described above is a different path; it does not execute these queries.

The [test harness](https://github.com/beepboop2025/financial-evidence-skills/tree/main/scripts/power_query_native)
and [workflow](https://github.com/beepboop2025/financial-evidence-skills/blob/main/.github/workflows/power-query-native.yml)
make the check repeatable. Microsoft's [PQTest commands](https://learn.microsoft.com/en-us/power-query/sdk-tools/pqtest-commands-options)
describe the engine interface used here.

## Other office paths

The [compatibility table](compatibility.md) separates completed acceptance from
available formats and pending host checks. Excel desktop add-in execution,
Excel-hosted Power Query refresh and marketplace review remain separate from
the completed web add-in, query-engine, Google Editor and workbook checks. Nextcloud Office
editing/saving and the unsupported ONLYOFFICE ODS export are not covered by the
successful import/open results.
