# OpenBB Marketplace — existing submission readback

Observed **18 October 2026, 09:00 UTC**. No new application, payment, message or
waitlist registration was created.

The [existing 11 October application](../../distribution/openbb-marketplace-20261011.md)
remains **submitted**. That receipt already covers the Research Desk application
and MCP server. Its first-year fee-waiver request has not been verified as
approved. No paid listing or automatic renewal is authorized by that submission.

| Public check | Observation |
| --- | --- |
| [Official Marketplace catalogue](https://openbb.co/solutions/marketplace/) | HTTP 200; no Financial Evidence, LiquiLens, Seiche, Undertow or Palimpsest text match in the served catalogue; rendered text also had no Financial Evidence/LiquiLens match |
| [Workspace login](https://pro.openbb.co/login) | Redirected to [BQ Workspace — Coming Soon](https://workspace.brightquery.com/) |
| [App manifest](https://api.seiche.info/openbb/apps.json) | HTTP 200, one application definition |
| [Widgets manifest](https://api.seiche.info/openbb/widgets.json) | HTTP 200, nine widget definitions |

These observations do not establish a rejected application or the absence of
private reviewer progress. They establish no new public acceptance evidence.
An anonymous catalogue read is not a check of the private submission queue.
Backend manifests are available, but native Workspace rendering remains a
separate test. The public login route cannot currently supply that walkthrough.

The publisher should reconcile any reviewer reply with the retained submission,
confirm the review owner and waiver, and use a supported Workspace session for
native acceptance. Verify a public listing URL before changing the marketplace
ledger to live. Do not duplicate the application or the archived Awesome OpenBB
PRs to work around the transition.

Public readback SHA-256:

- Catalogue HTML: `02107dbfd9b2861d3ecfaf662777200146445d0fc5cf0d8b9ebf54dee68a50a6`
- Redirect destination HTML: `e2cdd9966b938bf6ce777b72d1badb73dc92b05e3e785533e8de71bad9463bef`
- `apps.json`: `ad7667ade4d7a482cf04d0ff1ca1f54029e284b773e68910a3377468859c8e8a`
- `widgets.json`: `5d15ee9ebfd0fe2d3b35ccebc866fe4db872e4f8fa48a724a14ac108757e9251`

Metadata requests were labelled synthetic. Availability is not independent
adoption, Marketplace approval, fee waiver or native acceptance.
