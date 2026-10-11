# OpenBB Marketplace application — 11 October 2026

The official **Become a Marketplace Partner** form received one application
for **Financial Evidence Research Desk by LiquiLens**, selecting both
**Application** and **MCP Server**, at 11:08 UTC on 11 October 2026.
The application names Seiche, LiquiLens and Undertow as contributing products
and asks whether the operator prefers separate entries. Palimpsest is
described only as metadata coverage.

**Status: submitted; Marketplace approval and public listing pending.**
This is one application, not three approved product listings.

## Official route and receipt

- Entry: [OpenBB App Marketplace](https://openbb.co/solutions/marketplace/),
  **Become a Partner**.
- Form: [Become a Marketplace Partner](https://app.formbricks.com/s/cms3erjhmnwz901shu03176vk).
- On completion, the form displayed: “Thank you for your interest in the
  OpenBB App Marketplace” and “Our team will reach out to you soon.”
- The final form update returned HTTP 200, a response identifier, and
  `quotaFull=false`; the submitted request contained `finished=true` and the
  full offering, audience and waiver condition.
- Private submission bodies, response identifier, screenshot and mailbox
  readbacks are retained in the operator's SSD evidence archive. This public
  record includes no mailbox bodies or form-response identifiers.

Receipt snapshot SHA-256:
`3a96bf7913b753ab962c12e0859c6d129097ae03fa4bcdf46e09bea0e6f10491`.

The form publishes an annual listing fee of **USD 1,000** and says it may
waive the first-year fee for selected offerings. The application explicitly
requests that waiver and makes participation conditional on it. It does not
authorize a paid listing, invoicing or automatic renewal. The waiver has
**not** been granted; later-year terms require a separate decision.

## Existing work preserved

The application reuses the public backend and current installation guide:

- Backend: <https://api.seiche.info/openbb>
- App manifest: <https://api.seiche.info/openbb/apps.json>
- Widgets: <https://api.seiche.info/openbb/widgets.json>
- MCP: <https://api.seiche.info/openbb/mcp>
- [Source and setup](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/openbb)

Existing Awesome OpenBB submissions remain open and unmerged in an archived
repository: [Evidence Carrier #11](https://github.com/OpenBB-finance/awesome-openbb/pull/11),
[Financial Evidence #12](https://github.com/OpenBB-finance/awesome-openbb/pull/12),
and [Seiche #13](https://github.com/OpenBB-finance/awesome-openbb/pull/13).
The official Marketplace intake is a distinct route; it does not change the
status of those PRs.

The prior OpenBQ enquiry was rejected by its published recipient group.
The existing FINOS routing request was found in the company mailbox, with
no reply observed during this check. Searches of the company mailbox and
two existing Gmail accounts found no Marketplace acceptance or reviewer
response. These are bounded mailbox observations, not proof of recipient
delivery. Neither earlier message was resent.

OpenBB's current website describes the [OpenBQ transition](https://openbb.co/).
The submitted application asks for the current Marketplace review owner and
references the previous outreach so it can be reconciled.

At 11:10 UTC, opening `https://pro.openbb.co/login` redirected to
[BQ Workspace — Coming Soon](https://workspace.brightquery.com/). The successor
page offers early access and a custom-integration contact, rather than a
Workspace login. No early-access registration or additional email was sent.
The hosted native acceptance check remains blocked through that route. The
official site-linked form receipt does not prove that Marketplace onboarding
continues unchanged during this transition.

## Fresh backend verification

At 11:05 UTC, the current repository's HTTP/MCP verifier passed against
<https://api.seiche.info/openbb>, checking the expected reported source commit:

| Check | Observed result |
| --- | --- |
| Release | `workspace-1.3.0+4802a9b3bfb9` |
| Reported source | `4802a9b3bfb9d652199f25bf52852cb1e5db1cb3` |
| Identity scope | Operator-supplied build revision |
| Dataset requests | Seven bounded queries; all transport-complete |
| App manifests | One app; all referenced widgets resolve |
| Widgets | Nine |
| MCP | Initialization, nine read-only tool declarations, and a query passed |
| Traffic class | Operator verification; synthetic |

Verification report SHA-256:
`63aa63a90b4304075ef3777041ceb82390879567480fca5edc6f20303b1dda4c`.

The inherited checkout's verifier expected eight MCP tools; the live service
now reports nine. The check was rerun successfully using the current repository
verifier. The initial mismatch was not treated as a passed check.

These checks establish HTTP/MCP behavior and consistent declared identity.
They do not establish native Workspace rendering, a data licence, independent
model validation, institutional certification or customer adoption. Restricted
and unavailable data retain their published limitations.

## Remaining operator decisions

1. Identify the current Marketplace reviewer and confirm the fee waiver.
2. Obtain a supported Workspace access route and complete a native walkthrough
   if required by the reviewer.
3. Agree on one Research Desk entry or separate product entries without
   implying unrestricted redistribution of third-party data.
4. Independently verify the public listing URL before changing the ledger
   from `submitted` to `live`.

Reconcile the retained completed-form receipt before any further submission.
