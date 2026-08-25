# Fleet routing and citation contract

## Topic routes

| Topic | Primary product | Public JSON | Human scope page | Boundary |
|---|---|---|---|---|
| Money markets and funding | Seiche | `https://api.seiche.info/api/v2/money-markets` | `https://seiche.info/use-cases/money-market-research/` | Registered or discovered markets are not necessarily live or evidence-eligible. |
| Capital-market transmission | Seiche | `https://api.seiche.info/api/v2/world-markets?section=capital_markets` | `https://seiche.info/use-cases/capital-market-transmission/` | A macro transmission projection is not a security master, executable tape, or causal proof. |
| China economy | Palimpsest plus Seiche context | `https://palimpsest.info/readings/china-index-latest.json`; `https://api.seiche.info/api/v2/world-markets?section=china_macro` | `https://palimpsest.info/china/`; `https://seiche.info/markets/china-macro/` | Palimpsest observations and Seiche structural context retain separate clocks, rights, and evidence classes. |
| Bank or institution risk | LiquiLens | `https://api.liquilens.in/api/failure-radar/board` | `https://liquilens.in/use-cases/` | Published diagnostics are not a supervisory determination, credit rating, or certainty of failure. |
| Market and exit liquidity | Undertow | `https://api.seiche.info/undertow/x402/summary` | `https://liquilens-undertow.com/use-cases/` | Public market-liquidity context is not an executable quote or a promise that size can trade. |

## Topic aliases accepted by the helper

- `money-market`, `money-markets`, `funding`
- `capital-market`, `capital-markets`, `capital`
- `china-economy`, `china`, `china-macro`
- `bank-risk`, `institution-risk`, `financial-institution-risk`
- `market-liquidity`, `exit-liquidity`, `liquidity`

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
