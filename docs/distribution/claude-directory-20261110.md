# Claude directory submissions, 10 November 2026

Anthropic's [directory submission portal](https://claude.ai/directory/manage) opened on an owner
account with a qualifying paid Claude plan, which removes the blocker recorded on 16 October. The
submitting organization holds each listing long term. Review mail goes to the company contact.

## Connectors submitted

Each connector is the product's endpoint on the LiquiLens agent gateway, with no sign-in. Every tool
is read-only and annotated `readOnlyHint: true`.

| Product | Slug | Tools | State at 18:45Z |
| --- | --- | --- | --- |
| NoiseFloor | `noisefloor` | 10 | Published; [public page](https://claude.ai/directory/noisefloor) resolved about 19:25Z |
| MyQuant Editorial | `myquant-editorial` | 5 | Published; [public page](https://claude.ai/directory/myquant-editorial) resolved about 19:25Z |
| LiquiLens | `liquilens` | 26 | In review |
| Riptide | `riptide` | 7 | In review |
| MyQuant App Discovery | `myquant-app-discovery` | 2 | In review |

The portal says a new listing can take up to an hour to appear. A listing is marked live in the
[ledger](../marketplaces.json) only after its public page resolves.

Before submission, every tool on these servers was called with valid inputs through MCP Inspector
2.12.0 (`npx @modelcontextprotocol/inspector@2.12.0 --cli <url> --method tools/call`). All 87 calls on
eight servers succeeded, after retries for a rate limit and corrected test inputs. Seiche was not
self-tested because the tester's address had reached Seiche's anonymous daily quota.

The LiquiLens listing text is written to be true before the pending LiquiLens release. It gives no
coverage counts. It should be edited after the release, and edits to a published listing go back
through review.

## Held until a server fix

| Product | Finding | Effect |
| --- | --- | --- |
| Undertow | `side`, `mode` and `instrument` declare `enum` or `const` without `type` | Portal marks two tools "to fix"; draft saved |
| Palimpsest | `initialize` with `MCP-Protocol-Version: 2025-11-25` returns 400 | Claude cannot connect |
| NarcoScope | Same 400 on the 2025-11-25 header; `get_federation` with the default lane `all` returns over 4 MB that fails to parse | Claude cannot connect; one tool fails with defaults |
| Trade Safety | `assess_trade_safety` takes `request` and `policy` objects with no published schema | Reviewers cannot call it with valid inputs |
| Research Data, Seiche Market Corpus, Wake, Financial Evidence | Tools carry no `title` | Required annotation missing |
| Seiche | Ready, but not yet self-tested | Submit after the self-test |

The portal also suggests `annotations.title` for tools that carry only a top-level `title`. That
suggestion doesn't block submission.

## Plugin bundles

All 13 product plugin folders and the root plugin pass `claude plugin validate` with Claude Code
2.1.322. The repository is public and archives to about 22 MB, inside the 50 MiB limit. A bundle can
be created only after the owner connects GitHub to the Claude organization. Each folder is then its
own submission, tracking `main`, paired with its connector.

These submissions don't establish adoption. Directory placement and the Verified label are decided
by Anthropic during review.
