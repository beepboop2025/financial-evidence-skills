# Fleet routing and citation contract

## Topic routes

| Topic | Primary product | Public JSON | Human scope page | Boundary |
|---|---|---|---|---|
| Money markets and funding | Seiche | `https://api.seiche.info/api/v2/money-markets` | `https://seiche.info/use-cases/money-market-research/` | Registered or discovered markets are not necessarily live or evidence-eligible. |
| Capital-market transmission | Seiche | `https://api.seiche.info/api/v2/world-markets?section=capital_markets` | `https://seiche.info/use-cases/capital-market-transmission/` | A macro transmission projection is not a security master, executable tape, or causal proof. |
| China economy | Palimpsest plus Seiche context | `https://www.palimpsest.info/readings/china-index-latest.json`; `https://api.seiche.info/api/v2/world-markets?section=china_macro` | `https://palimpsest.info/china/`; `https://seiche.info/markets/china-macro/` | Palimpsest observations and Seiche structural context retain separate clocks, rights, and evidence classes. |
| Bank or institution risk | LiquiLens | `https://api.liquilens.in/api/failure-radar/board` | `https://liquilens.in/use-cases/` | Published diagnostics are not a supervisory determination, credit rating, or certainty of failure. |
| Market and exit liquidity | Undertow | `https://api.seiche.info/undertow/x402/summary` | `https://liquilens-undertow.com/use-cases/` | Public market-liquidity context is not an executable quote or a promise that size can trade. |
| GIFT City and IFSC research | Seiche; add institution/exit topics as needed | `https://api.seiche.info/api/v2/gift-city` | `https://seiche.info/gift-city/` | India–UAE funding/FX/gold context serves multiple research audiences, not regulatory eligibility, fund NAVs or private-book ALM. |
| Forex and currency conversion references | Seiche | `https://api.seiche.info/api/v2/world-markets?section=forex` | `https://seiche.info/markets/forex/` | Dated references and conventions, not executable spot quotes, complete forward curves or a conversion transaction. |
| Gold context | Seiche; Undertow for an explicit sale scenario | `https://api.seiche.info/api/v2/gift-city` | `https://seiche.info/gift-city/` | Gold positioning has its own weekly clock; a null bullion price stays null. Funding context is not a dealer bid or cash admission. |

## Topic aliases accepted by the helper

- `money-market`, `money-markets`, `funding`
- `capital-market`, `capital-markets`, `capital`
- `china-economy`, `china`, `china-macro`
- `bank-risk`, `institution-risk`, `financial-institution-risk`
- `market-liquidity`, `exit-liquidity`, `liquidity`
- `gift-city`, `giftcity`, `gift-city-ifsc`, `ifsc`
- `forex`, `fx`, `foreign-exchange`, `currency-conversion`
- `gold`, `bullion`, `gold-conversion`, `gold-funding`

The last three topic groups are additions in the 0.1.6 candidate. Published
0.1.5 installs retain their five-topic contract until explicitly upgraded.

## GIFT City audience and scenario routing

| Audience or question | Context first | Explicit next step and boundary |
|---|---|---|
| Gold importer or treasury desk | `gift-city`, `gold`, `forex` | Seiche `gold_inventory_carry` for supplied weight, purity, bullion price, funding rate, fees, FX and term. Undertow `gold_cash_realisation` for supplied sale/settlement/access assumptions. Neither confirms IIBX access. |
| Investor or fund manager | `gift-city`, `forex`, `money-market`, `market-liquidity` | Inspect dated provider/pair evidence with Seiche `market_workbench`; retain fund-specific NAV, redemption and eligibility gaps. |
| Bank or IFSC institution | `gift-city`, `bank-risk`, `money-market` | Use covered legal-entity disclosures and dated funding evidence; private facilities, collateral, ALM and supervisory conclusions remain outside public context. |
| Gold weight, purity or conversion | `gold`, `forex` | Normalise the stated unit and fineness; use the user's actual price and FX assumptions for a requested calculation. Weekly futures positions cannot supply a bullion price. |

The helper never executes these scenario steps. Native Seiche tools are at
`https://api.seiche.info/mcp`; Undertow tools are at
`https://liquilens-undertow.com/mcp`. Inspect `tools/list` for the current input
contract. Gold calculations require explicit user inputs; missing quote dates,
fees, FX, settlement or access assertions cannot be silently invented.
Seiche `gift_city_context` reads the same dated desk. Its `market_workbench`
selects H.10/ECB provider, currency pair and bounded history; the fixed helper
`forex` route is broad reference context rather than a caller-selected pair.

## Route and packet semantics

Every route exposes its canonical `human_scope_url`, declares
`financial_authority: none`, and declares `carrier_state: not_published`. No
route in that state advertises a `carrier_url` key.

Packet `status` is retained for compatibility and equals `transport_status`.
Both are transport reachability only: `complete`, `partial`, or `unavailable`.
They do not evaluate evidence. Every packet therefore declares
`status_semantics: transport_only`, `evidence_status: not_evaluated`, and
`carrier_verification: not_performed`.

Successful-source adapter summaries contain only explicitly configured,
source-reported state and clock scalars. Each record includes an RFC 6901 path,
the exact source URL, and fetched-byte SHA-256 provenance. Missing or null
configured values are `not_reported`. Do not derive freshness, eligibility, or
rights from these summaries; inspect and cite the source document's own fields
when a claim requires them.

Shared GIFT City and gold context is fetched once per packet and appears under
each requested topic with the same source receipt. This is not independent
corroboration. Source `status: partial` or `gated`, null gold prices, unavailable
funding rows and missing observation clocks remain intact even when every HTTP
request succeeds. Summaries do not replace per-series clocks in the raw JSON.

## Evidence classes

- **observed**: a public value with unit, identity, source, and observation or
  as-of clock.
- **derived**: a product computation over identified inputs; cite the product
  method and input clocks.
- **structural**: identities, release calendars, or source metadata without a
  publishable value.
- **restricted**: evidence exists but the public response intentionally
  withholds values or history.
- **unavailable**: required evidence was absent, stale beyond policy,
  unreachable, or ineligible. Absence is not zero.

## Cross-product joins

Keep each product's output in its own section. A useful order is system funding
(Seiche), institution exposure (LiquiLens), market exit conditions (Undertow),
then China observations and information availability (Palimpsest). Join them in
prose only after recording their separate clocks and evidence classes. Do not
average their labels or imply that one product validates another.

## Citation minimum

For a numerical or status claim, include the product, exact source URL,
original publisher when supplied, observation or as-of time, product knowledge
or generation time, retrieval time, unit, evidence class, and any revision or
rights field. For a static scope claim, cite the human scope page and access
date.
