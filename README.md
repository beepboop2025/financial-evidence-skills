# Financial Evidence Agent Skills

Open, read-only Agent Skills for routing financial research to bounded public
evidence. The first skill connects four complementary products without turning
them into one score:

- **Seiche** — money markets, repo, reserves, Treasury cash and system funding.
- **LiquiLens** — covered bank and lender evidence.
- **Undertow** — market depth, provider concentration and position-sized exit liquidity.
- **Palimpsest** — revision-safe China economy evidence and information-state history.

## Install

```bash
npx skills add beepboop2025/financial-evidence-skills --skill financial-evidence
```

Or copy [`financial-evidence/`](financial-evidence/) into the Agent Skills
directory supported by your agent. The folder follows the open
[Agent Skills specification](https://agentskills.io/specification).

Once installed, ask your agent to research a money-market, capital-market,
bank-risk, market-liquidity or China-economy question. The skill's description
lets compatible agents activate it when the work matches.

## Optional bounded retrieval

The bundled helper uses only Python's standard library, accepts a fixed topic
allowlist and fetches only fixed public HTTPS endpoints:

```bash
python3 financial-evidence/scripts/fetch_evidence.py \
  --topic money-market --topic china-economy
```

It returns one JSON packet with exact source URLs, retrieval clocks, byte
counts, separate product documents and explicit errors. Missing, restricted or
unavailable evidence is never converted to zero or “calm.”

## Boundaries

This repository provides public research routing, not investment advice,
security recommendations, execution quotes, credit ratings or guarantees.
Source publishers retain their rights; an open-source helper does not relicense
upstream data.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile financial-evidence/scripts/fetch_evidence.py
```

The code and skill instructions are MIT-licensed.
