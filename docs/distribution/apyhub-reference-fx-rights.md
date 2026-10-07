# Seiche Reference FX API: submitted scope and source terms

Submitted to ApyHub on **7 October 2026** by **LIQUILENS PRIVATE LIMITED**.
The operator receipt says **submitted for review**. This is not a live API
listing or evidence of customer adoption. Provider onboarding was already
authorized and completed; the owner accepted responsibility for escalated
support within 24 hours.

## Exact offer

One service, `seiche-reference-fx-api` v1.0.0, contains four fixed GET routes:

| Gateway path | Seiche upstream path | Unit |
| --- | --- | --- |
| `/usd.csv` | `/api/series/ECBFX_USD.csv` | USD per one EUR |
| `/gbp.csv` | `/api/series/ECBFX_GBP.csv` | GBP per one EUR |
| `/jpy.csv` | `/api/series/ECBFX_JPY.csv` | JPY per one EUR |
| `/inr.csv` | `/api/series/ECBFX_INR.csv` | INR per one EUR |

Each request is priced at **one ApyHub atom**. The gateway uses the customer's
ApyHub token; the Seiche upstream is public. There is no arbitrary dataset,
mnemonic, upstream URL or path parameter. The
[import specification](apyhub-reference-fx.openapi.json) describes the public
upstream, not a claim that ApyHub's gateway is already live.

Responses are `text/csv` with provenance comments followed by `date,value`
rows. Preserve the comments, including source credit, free-data notice,
observation date, retrieval time, units and staleness. Missing dates remain
absent. These are daily informational reference rates, not executable quotes.

## Source permission and its conditions

The ECB's [copyright policy](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html),
checked on 7 October 2026, permits reuse of information obtained directly from
its website subject to accurate reproduction and source attribution. Where
the information is sold, customers must be told before payment and whenever
they access it that the original information is available free from the ECB.
Modifications must be identified. Its exception for named-author papers is
outside this offer's numerical reference-rate scope.

Seiche collects the ECB's own
[reference-rate XML](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml).
The reviewed implementation is Seiche v0.16.2, commit
`10d8acd99add9aceed1eb3919c118f62005eefdf`, specifically
`backend/seiche/sources/ecb_fx.py`, `config.py`, `methodology.py` and the fixed
CSV export route in `api.py`.

The submitted service overview, endpoint documentation and quickstarts
identify the ECB and link to its freely available data and reuse terms.
Every tested CSV response also retained its ECB credit and free-data notice.
The overview explains the XML-to-CSV conversion and states that the values
are not converted to another currency, interpolated or economically adjusted.
The service claims no ECB affiliation or endorsement.

This evidence supports only the four listed ECB reference series. It does
not establish rights for unrelated ECB content, FRED-hosted licensed indices,
bank disclosures or the broader Financial Evidence Research API. That
separate four-endpoint JSON draft remains unpublished pending its own
source-specific review.

## Verification and remaining gate

- Four upstream exports returned HTTP 200 with CSV content and source notices.
- USD, GBP and JPY contained 7,109 observations from 4 January 1999;
  INR contained 4,549 from 2 January 2009. All ended on 7 October 2026.
- All four latest observations matched the ECB's original daily XML.
- ApyHub recorded **4/4 tested**. The retained responses confirmed that the
  source and free-data notices survived the platform test.
- ApyHub's review reported no issues, two suggestions and one nit. Catalog
  review acknowledgement was recorded and final pricing was one atom each.
- ApyHub returned its submission receipt. An administrator must approve and
  publish the offer; public catalog and authenticated gateway acceptance
  remain unverified until then.

The dated response evidence is retained locally. Public
[receipt summaries](receipt-summaries.json) contain its hashes. Do not
resubmit the accepted draft while waiting for the operator's decision.
