# Non-Amazon distribution follow-through — 7 October 2026

The new results below extend the [earlier audit](marketplace-audit.md). They do
not replace its existing receipts or count pending applications as public users.

| Destination | Observed result |
| --- | --- |
| [Hugging Face](https://huggingface.co/spaces/oldmacdonaldhadafarm/financial-evidence-packet-inspector) | Public Static Space. Anonymous source and served-asset checks passed; the live example and Clear controls were exercised. |
| [SaaSHub: LiquiLens](https://www.saashub.com/liquilens/added) | Submission acknowledged; awaiting independent approval. Extended product description and research categories saved. |
| [SaaSHub: Seiche](https://www.saashub.com/seiche/added) | Submission acknowledged; awaiting independent approval. Extended product description and research categories saved. |
| SaaSHub: Undertow | The site requires an approval of an earlier submission before accepting another. No Undertow receipt exists. |

The Space is a useful software demonstration, not a redistributed market-data
archive. Its bundled example is synthetic. A visitor can inspect a local packet
without sending the file to a server. Public source commit:
`4a857f30a6b1d7a30c933a1eb2e62c41efe5d9ea`.
Hugging Face adds a platform identity bootstrap to served HTML; source files,
JavaScript and CSS were checked independently. No paid hardware was enabled.

## Launch and account gates observed

| Destination | Concrete remaining step |
| --- | --- |
| Product Hunt | Draft has name, tagline, description, API topic and first comment. Thumbnail and gallery images still need attachment before launch configuration. |
| Dev Hunt | Draft has public demo URL, repository, description and free pricing. Required logo/gallery attachment and launch-date selection remain. |
| SaaSHub profile enrichment | Logos and screenshots remain. Chrome's file-upload permission error persisted after the owner enabled access. Free submission receipts are still valid. |
| AlternativeTo | Sign-in succeeds; the site still reports an unverified email and disables app submission. |
| G2 / Capterra | G2 shows a verification challenge. Capterra's current vendor listing route points to G2's form. No submission was made. |
| Zyla | Provider route returns a Cloudflare access block. |
| API.market | Seller route resolves to account sign-in and terms; no provider product was activated. |
| MCPServers.com | Sign-in requested Calendar and Contacts scopes. Access was not granted for a directory listing. |
| StackShare | The prior `/submit` URL is now an unrelated public user profile; no current self-service form was established. |
| Datarade | Provider application found. Legal-address fields and the proposed commercial terms need completion/review. Commission-only pricing is not an ordinary free directory listing. |

SourceForge remains under the concurrent session's existing form ownership.
Previously received applications were not resubmitted. AWS remains excluded by
the owner's instruction. The broader ApyHub Research API remains rights-held;
the narrower FX submission is separate.

## Automation integrations

Source candidates now exist for
[n8n](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/n8n-node),
[Zapier](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/zapier),
[Make](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/make) and
[Dify](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/dify).
Each retrieves one bounded public research page. Source links, dates, units,
missing values, coverage diagnostics and pagination remain attached. There is
no automatic downstream message, transaction or unbounded pagination loop.

| Candidate | Checks completed | Still required |
| --- | --- | --- |
| n8n | Official CLI build and lint; 4 behavior tests; npm package contents inspected | Real n8n workflow, npm publication and Creator Portal review |
| Zapier | 28 CLI validation checks without errors or warnings; 4 SDK behavior tests | Authorized developer registration, Zap editor test and review |
| Dify | 4 behavior tests; SDK manifest/provider registration; official CLI packaging | Native remote-debugging workflow and marketplace review |
| Make | Four JSON files parse successfully | Custom-app installation, scenario execution and review |

The n8n and Zapier checks use Node 22; Dify uses Python 3.12. Dify's local
SDK process printed interpreter-exit cleanup warnings on macOS, despite passing
its tests; the real Dify runtime is not yet verified. A bounded live bank-risk
request also returned the expected page contract. No marketplace acceptance is
inferred from these checks.

These are candidates, not accepted marketplace integrations. Publisher access,
native workflow tests and each platform's review remain separate gates.

## Adoption measurement

The private Research Desk scorecard was read before this work. It did not
establish monthly active people, repeat independent users or paid customers.
Our own checks use the synthetic traffic class. This ledger adds distribution
evidence; it does not claim that new listings have already produced traction.
The [measurement contract](../start/measurement.md) explains what the counters
can and cannot establish.
