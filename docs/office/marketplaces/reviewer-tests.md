# Native reviewer acceptance script

Use a blank workbook and public test selections. Label verification requests
synthetic wherever the package offers its publisher-test option. This script is
also suitable as certification notes; attach actual results, versions and screenshots.

## Common review

1. Keep an existing sheet with `Keep my analysis` and `42`. Open the add-in.
   Confirm no research request is made before a user clicks the refresh action.
2. Request `USD,EUR` and `au-sfb,unknown-bank`. No Financial Evidence account,
   API key, payment, external subscription or test credential is needed.
3. Inspect Funding, Institutions, Gaps and Status. Compare one result with its
   cited public source. Do not expect a fixed current number: upstream releases
   and source states change. Unknown institutions must stay `not_covered`.
4. Download original evidence JSON. Confirm it includes the selected requests,
   original responses, retrieval time and source clocks. A returned request is
   not proof of freshness, complete coverage or independent evidence validation.
5. Make a second capture. Confirm it has a distinct identity and leaves earlier
   results and the user's existing analysis untouched.
6. Test invalid selections and failed requests. Errors must be visible; old
   values must not silently be relabelled as new. Check spreadsheet cells for
   unexpected formulas, automatic schedules or unsolicited network calls.
7. Use the keyboard to reach all controls; confirm visible focus and readable
   error/status updates at narrow width. Check privacy, terms and help links.
8. Close the add-in. Confirm it creates no background job, automatic sharing or
   optional learning enrollment. Removal should not erase saved research tabs.

## Google-specific

Follow [the add-on's exact development/test steps](google/README.md). Test
installation and enabled-document states, menu opening, the sidebar, permissions
and repeated insertion. The manifest declares three scopes: current spreadsheet,
external requests and container UI. The console's final consent must agree.
Record immutable Apps Script version and standard Cloud project privately.

## Microsoft-specific

Use [the exact Excel certification notes](microsoft-reviewer.md) for the current
manifest ID, requirement set and button sequence: **Refresh research**, then
**Insert new review sheets**, with **Download original evidence** for the JSON.

Load the final manifest using the host's supported sideload/test route. Confirm
the manifest's `ProviderName` matches the approved publisher. Record the actual
Excel host build, operating system and API requirement set. Test every supported
platform required by that declaration; a mocked Office.js API does not replace
native Excel execution. Office web testing establishes only that tested web host,
not Mac, Windows or mobile acceptance. Power Query testing is a separate route.

Use the final package's exact button names in the submitted notes. Do not attach
these generic notes unchanged if the final runtime has a different workflow.
Provide a screenshot of the native task pane and its inserted evidence tables.
See [Microsoft reviewer information](https://learn.microsoft.com/en-us/partner-center/marketplace-offers/submit-to-appsource-via-partner-center).

## OpenBB-specific

Use the existing backend `https://api.seiche.info/openbb`, `apps.json` and
`widgets.json` from the submitted application. Confirm the widget catalogue
renders, parameter changes return the expected dataset and source/coverage states
remain visible. A successful REST or MCP check is not this native walkthrough.
The October 2026 public login still redirects to the successor waitlist; retain
that blocker unless a supported native session or reviewer route is available.
