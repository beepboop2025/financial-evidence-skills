# Office marketplace publisher pack

The public office desk and file formats are already distribution routes. This
directory adds deployable Google Editor add-on source and concrete listing
materials. Publication is a separate state requiring a native application test,
publisher configuration and platform review. See [status.json](status.json).

| Channel | Package / listing material | Remaining platform step |
| --- | --- | --- |
| Google Workspace Marketplace | [Editor add-on](google/README.md), [source ZIP](google/google-editor-addon.zip), [listing](google/listing.json) | Native add-on test, standard Cloud project and consent/SDK configuration, public review |
| Microsoft Marketplace, formerly AppSource | [Manifest](../excel/manifest.xml), [listing draft](microsoft-listing.json), [exact reviewer script](microsoft-reviewer.md) | Manifest validation, compatible-host testing, approved Partner Center account, review |
| OpenBB App Marketplace | [Existing application readback](openbb-status.md) | Review owner, fee-waiver decision and supported native Workspace access; do not resubmit |

The source package and listing text do not create publisher accounts, consent to
paid terms, grant OAuth permissions, or submit anything externally. The publisher
can use the prepared materials after the account and runtime gates are verified.
The new add-ons are separate products from copied custom functions, Power Query
queries, or imported workbook files; acceptance of one does not validate another.

## Shared publisher assets

- [Office privacy notice](privacy.html), [service privacy](../../privacy/),
  [terms](../../terms/) and [support](../../support/).
- Company and support identity: LIQUILENS PRIVATE LIMITED;
  `mrinal@liquilens.in`. Confirm the account's verified publisher name matches.
- Brand artwork is adapted from the existing Financial Evidence Inspector icon;
  [asset inventory](assets/README.md) records its provenance and sizes.
- Store screenshots must show the actual add-on inside the advertised host.
  Take them in a blank validation workbook with public research only. Do not
  substitute an illustration or a browser desk screenshot for native execution.

Current official instructions: [Google listing fields](https://developers.google.com/workspace/marketplace/create-listing),
[Microsoft submission checklist](https://learn.microsoft.com/en-us/partner-center/marketplace-offers/checklist),
[OpenBB Marketplace](https://openbb.co/solutions/marketplace/).
