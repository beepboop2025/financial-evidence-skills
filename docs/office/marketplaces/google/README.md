# Financial Evidence Editor add-on for Sheets

This is a deployable source package for a Google Sheets Editor add-on. It adds
an **Open research review** menu and a sidebar that creates fresh review tabs.
It is separate from the already tested copyable custom functions. Marketplace
publication, the new add-on's native menu execution, and OAuth verification are
not established by the source package or its mocked tests.

## Install a development copy

1. Extract `google-editor-addon.zip` and inspect `SHA256SUMS`.
2. Open a new spreadsheet and choose **Extensions → Apps Script**. Use a new
   test spreadsheet so its container script does not replace another project.
3. Replace the default `Code.gs` with the package's complete `Code.gs`.
4. Add an HTML file named `Sidebar` and paste `Sidebar.html`.
5. In Project settings, show the manifest file. Replace `appsscript.json` with
   the package manifest and save. This does not deploy or publish the project.
6. For the bound development copy, run `onOpen` once or reload the spreadsheet.
   Open the new Financial Evidence/research-review menu. Complete the normal
   Google consent only for the three listed scopes if your account permits it.
7. For the actual Editor add-on lifecycle, use **Deploy → Test deployments**,
   choose **Editor add-on**, select a test spreadsheet and test the installed
   and enabled states. Follow [Google's Editor testing instructions](https://developers.google.com/workspace/add-ons/how-tos/testing-editor-addons).

Do not install `Addon.gs` alongside `Code.gs`: the generated Code already includes
it and the shared evidence core. No Node packages, API keys or account creation
are needed by the add-on's public research service.

## Use and reviewer acceptance

1. Put `Keep my analysis` and the number `42` in an existing tab.
2. Open the sidebar. Select **Publisher testing → Mark this refresh as a test**.
   This marks ordinary API requests synthetic without sending a separate event.
3. Request currencies `USD,EUR` and institution slugs `au-sfb,unknown-bank`.
4. Confirm six new `FE …` tabs appear: Read me, Funding, Institutions, Gaps,
   Other data and Status. Funding should retain currency-specific units/dates.
   Institutions must show `unknown-bank` as `not_covered`. Gaps must remain
   visible; blank/withheld numeric values must not become zero.
5. Confirm the Status tab includes each of the three requests, source URL,
   clocks, coverage and any explicit failures. A successful HTTP response does
   not assert current, complete or independently verified evidence.
6. Save the JSON from the sidebar and check it contains original responses.
   It remains a local download; no Drive permission or upload is performed.
7. Refresh again. A second set of tabs should appear; the original capture and
   the `Keep my analysis`/`42` cells must remain unchanged.
8. Enter six currencies, a URL, or an empty selection. Confirm a visible error
   and no new tabs. Close/reopen the sidebar without refreshing and confirm no
   research request occurs. Use keyboard navigation and a narrow display.
9. Record spreadsheet/app version, test deployment/version, timestamp, observed
   results, and screenshot. Never expose a private workbook in a store screenshot.

The new add-on accepts at most five currencies and five exact institution slugs,
makes at most six requests per click, and caps each response at 4 MiB. The
serialized capture is limited to two million characters for the sidebar.
Failures remain explicit. A write failure can leave clearly named partial new
tabs, which the user can inspect and remove manually. The add-on never deletes
tabs and never retries or schedules work automatically.

## Permissions and data handling

| Declared runtime scope | Purpose |
| --- | --- |
| `spreadsheets.currentonly` | Create evidence tabs in the spreadsheet where the add-on is used. Existing cell data is not read. |
| `script.external_request` | Fetch public research for the entered currencies and slugs from the fixed Seiche gateway. |
| `script.container.ui` | Display the review sidebar in the current spreadsheet. |

The runtime manifest requests no Drive, Gmail, contacts, account identity,
background trigger or all-spreadsheets scope. The Marketplace
SDK installation configuration also includes Google's default `userinfo.email` and
`userinfo.profile` scopes. Google's review of the installation/runtime scope alignment remains pending; the add-on code does
not read or transmit Google identity.

Installation does not enroll users in optional measurement, learning or sharing.
Request counters and provider delivery logs still apply as described in the
[Google add-on privacy policy](https://liquilens.in/financial-evidence/privacy/) and [service privacy policy](../../../privacy/).

## Publisher configuration — not yet completed by this package

The publisher must use an existing approved standard Google Cloud project or
explicitly authorize creation/configuration of one. Link the Apps Script project,
enable the Marketplace SDK, and configure OAuth consent for the actual installation
and runtime permissions. Record the script ID, immutable version and test deployment
ID privately; no account IDs belong in this public package. Choose public visibility
intentionally: Google's selection
cannot later be changed. [Publication overview](https://developers.google.com/workspace/add-ons/how-tos/publish-add-on-overview).

Google distinguishes Data Access declarations used for verification, Marketplace
SDK scopes used to authorize installation, and manifest scopes used by the runtime.
Its guidance says these lists must match, with an example where separate add-on
manifests contain subsets of a multi-integration app's combined scopes. That example
does not establish an exception for this single add-on's SDK identity defaults.
[Scope roles and matching requirements](https://developers.google.com/workspace/marketplace/configure-oauth-consent-screen#understand_oauth_scopes).

For this existing project, the proposed review configuration declares all five
observed SDK installation scopes in Data Access: the three runtime scopes above,
plus `userinfo.email` and `userinfo.profile`. The Apps Script manifest retains its
three functional scopes unchanged. This is a proposal for Google's review, not a
resolved scope reconciliation or an approved exception. Confirm the live saved
SDK, Data Access and manifest lists before describing the proposal as configured.
Adding a verification declaration does not itself grant the add-on access to an
account; actual Marketplace consent must still disclose the five installation
permissions. Do not add identity-reading code or runtime identity scopes to invent
a justification for the defaults. The implementation does not retrieve, store or
transmit account email or profile information.

The verification demonstration must show the actual installation consent with all
five requested scopes and any separate runtime authorization flow, in English,
with the correct app name and OAuth client ID visible. Then show the sidebar,
public research retrieval and new-tab insertion that use the three runtime scopes.
Explain that the SDK identity defaults are unused by the implementation; do not
present them as a feature. A bound-script consent demonstration showing only three
scopes does not demonstrate the five-scope Marketplace installation. Provide a
real accessible video link and retain Google's actual review outcome before
claiming reconciliation or approval.
[Consent demonstration requirements](https://support.google.com/cloud/answer/13804565)
and [sensitive-scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification).

The console must confirm publisher domain/branding, support contact and any
scope verification requirement. Google's current OAuth guide also lists Cloud
billing as a prerequisite; verify the actual account requirement before enabling
billing or agreeing to paid terms. No billing action is included here.
[OAuth configuration](https://developers.google.com/workspace/marketplace/configure-oauth-consent-screen).

Use [listing.json](listing.json), the real native screenshots, and the shared
publisher assets. A public install URL is only added after review acceptance and
an independent install/readback. Test deployment success is not public approval.

## Rebuild and verify from the repository

```sh
python3 scripts/build_google_office_addon.py
python3 scripts/build_google_office_addon.py --check
node --test tests/test_google_office_addon.cjs
```

The package includes the repository's MIT licence. Source-data rights, restricted
values and provider terms remain separate from the client-code licence.

## OAuth privacy and domain remediation — 30 October 2026

The Google reviewer requested explicit data access, use, sharing and protection
disclosures and URLs on a verified owned domain. The proposed application URLs are:

- Homepage: https://liquilens.in/financial-evidence/
- Privacy: https://liquilens.in/financial-evidence/privacy/
- Terms: https://liquilens.in/financial-evidence/terms/

The homepage and dedicated policy are maintained in beepboop2025/liquilens-site.
The previous shared Office privacy URL retains the complete Google disclosures
and the separate Excel/custom-function notices, so existing installed sidebars
continue to reach the updated information. New source packages point directly to
the company-domain policy. Runtime behavior and the three manifest scopes remain
unchanged. Existing status records retain their original observation dates.

Before submitting remediation, verify the public page bytes and ownership under
a project owner account; update Google Auth Platform branding and the Marketplace
listing; inspect the live five verification/installation scopes and three runtime
scopes; and reply to the original reviewer thread after submission. Source changes
alone do not establish live script deployment, approval or public installation.
