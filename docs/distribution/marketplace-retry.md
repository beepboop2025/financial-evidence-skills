# Marketplace retries — 7 October 2026

This follow-up records five new product/company submissions across three
platforms. LiquiLens now has a public G2 profile, with a category correction
still required. G2 explicitly approved Seiche and Undertow; their public
visibility remains unverified.

| Platform | Product or company | Verified result | Remaining acceptance |
| --- | --- | --- | --- |
| [G2](https://www.g2.com/products/liquilens/reviews) | LiquiLens | Public profile claimed under LIQUILENS PRIVATE LIMITED; free Public research tier visible at $0; correction case 00642455 received | G2 category decision and logo enrichment |
| G2 | Seiche | The submission page says **Profile Approved!** | Public profile propagation and category assignment |
| G2 | Undertow | The submission page says **Profile Approved!** | Public profile propagation and category assignment |
| API.market | Seiche Reference FX API | PRO **$5/month**, 10,000-call hard cap; **4/4 Playground tests passed**; resubmitted, **In Review, 3 / 3 complete** | Operator approval and public catalog acceptance |
| Datarade | LIQUILENS PRIVATE LIMITED | **Email confirmed** and **application is now under review** | Provider qualification and any later commercial onboarding |

G2's optional Capterra, GetApp and Software Advice cross-publication was
authorized and selected for all three products. G2 says those placements
remain subject to verification. They are not three additional accepted
platforms. LiquiLens's free administrator claim is complete. No customer-review
invitations were sent.
LiquiLens returned a page-rendering error after submission, so it was not
resubmitted. Its public profile subsequently appeared in search, and the
[company catalog](https://www.g2.com/sellers/liquilens-private-limited) shows
the submitted financial-research description. The owner approved the separate
free Master Service Agreement and supplied the title Founder / CEO. The product
page verifies administrator access and Claimed status. The claim was submitted
once; its confirmation-page error was reconciled against the actual profile.
Seiche's record URL still returned 404 at 17:45 UTC and its public search did not
expose an exact Seiche listing. The company catalog showed only LiquiLens
when checked after that.

## LiquiLens correction and pricing follow-through

The My.G2 pricing editor independently confirmed the saved **Free Version**
setting after the interrupted session resumed. Free Trial is unchecked. The
description covers public bank/NBFC/MFI research views and documented public
read-only REST/MCP routes, with no API key required for those routes. Coverage,
source observation dates and access limits remain explicit. No paid package
was created. A **Public research** tier has now been saved, and the
[buyer-facing pricing page](https://www.g2.com/products/liquilens/pricing)
displays **Free / $0** with the same public-access boundaries. The pricing route
was checked in the signed-in administrator browser; anonymous retrieval through
the search tool was unavailable. Category and logo work remain open.

G2's support portal received **case 00642455** on 7 October. Its confirmation
lists three separate requests: remove Survey, assess Financial Data APIs, and
assess Financial Research. The supporting evidence explicitly discloses that
LiquiLens does not provide a real-time market-news feed; G2 must determine the
appropriate category against its inclusion criteria. The case is **New** in
the **Intake Queue**. Its displayed 14 October resolution estimate is not a
guarantee. The profile remains `listed_incomplete` while classification and
logo enrichment remain open. The receipt is retained privately, with its hash
in [receipt summaries](receipt-summaries.json).

## API.market product scope

The free seller organization has one submitted product. API.market requested
a paid plan because buyers receive the **Free** plan as a **seven-day trial**
with **1,000 calls**. The owner approved and saved **PRO at $5/month**, with
**10,000 calls/month**, a **hard limit**, **no overage calls** and **one request
per second**. Both plans include the same four fixed GET routes:

- `/api/series/ECBFX_USD.csv`
- `/api/series/ECBFX_GBP.csv`
- `/api/series/ECBFX_JPY.csv`
- `/api/series/ECBFX_INR.csv`

The source is `https://api.seiche.info`. The product description retains ECB
source attribution, the free-original-data notice, modification details and
the boundary between reference rates and executable quotes. The
[source-rights review](apyhub-reference-fx-rights.md) also applies to this
same bounded set of routes. The operator's standardized documentation was
preserved, with the plan terms and explicit ECB free-source notice added before
subscription. Fresh upstream checks matched the ECB's 7 October observations
for all four currencies.

All four requests then returned **HTTP 200 CSV** in **API Playground**, with the
correct series, source credit, free-data notice and 7 October observation date.
These were owner verification calls on the **no-charge Free Trial**, not paid
subscriptions or independent adoption. The retained browser response excerpts
do not establish full-history byte parity through the gateway.

The existing product was resubmitted once after those checks. API.market shows
**In Review** and **3/3 complete**. The signed-in seller preview now renders the
description, plans and Playground at
[the store route](https://api.market/store/liquilens/seiche-reference-fx).
Operator approval and unrestricted public catalog acceptance remain pending.
The separate ApyHub FX submission remains intact.

## Other routes retried

| Destination | Result and next step |
| --- | --- |
| Zenodo | Automatic GitHub release preservation is enabled for `beepboop2025/financial-evidence-skills`. Its release list is still empty. Verify a DOI after the next genuine release; no new version was created solely to trigger archiving. The existing Seiche DOI is a different product. |
| StackShare | The current **List a Tool** form works. LiquiLens metadata is prepared, but the site's imported SVG was rejected: **Image must be JPEG, PNG, or WebP**. Attach the prepared PNG, then submit. No accepted submission exists. |
| AlternativeTo | Signed-in account still has an unverified email; app submission remains disabled. Complete the verification email. |
| SaaSHub | Undertow retry still requires approval of an earlier submission. Preserve the received LiquiLens and Seiche applications. |
| Product Hunt | ResearchDesk draft remains prepared; thumbnail/gallery upload and launch configuration remain. |
| Dev Hunt | ResearchDesk draft has its public URL, repository, description, free pricing, API/MCP/Open Source categories and factual maker comment. Required logo/screenshots and launch-date selection remain. |
| APILayer | Signed-in provider FAQ points to an application without exposing a usable supplier form in the inspected navigation. Confirm the operator-supported route. |
| APITracker | No provider submission form was found; the beta waitlist is a consumer signup. No contact email was sent. |
| Demyst | The earlier data-provider path returns 404; a replacement application route was not established. |
| Zyla | Provider route remains blocked by Cloudflare. |
| [PulseMCP](https://www.pulsemcp.com/submit) | Rechecked: new server/client submissions and listing edits are still paused. The operator directs publishers to the Official MCP Registry, where Financial Evidence is already published. The separate use-case submission page is also closed. |

Chrome's local-file upload error persisted after the owner reported enabling
access. The prepared forms and assets are retained for manual attachment.
SourceForge remains owned by the concurrent session; its submission was not
duplicated. AWS remains excluded. Paid placements remain unpurchased.

## Evidence and follow-up

[Receipt summaries](receipt-summaries.json) retain hashes of the exact browser
receipts. The [product ledger](../marketplaces.json) separates received,
approved-awaiting-public-verification and live states. Private evidence holds
the account forms and screenshots; personal contact fields are not published
here.

Next, resolve the G2 links supplied by the operator, monitor API.market and
Datarade review decisions, and finish the existing verification/upload gates.
No received application should be replayed. The
[Hugging Face demo and integration candidates](non-amazon-follow-through.md)
remain available. These results expand distribution; independent completed
research tasks, returning people and paid adoption still require measurement.
