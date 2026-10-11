# Hosted MCP discovery and first use — 11 October 2026

Connect Claude Code to the three public research desks:

```sh
claude mcp add --transport http liquilens https://api.liquilens.in/mcp
claude mcp add --transport http seiche https://api.seiche.info/mcp
claude mcp add --transport http undertow https://api.seiche.info/undertow/mcp
```

[Try a cited example in your browser](https://liquilens.in/start/) · [Free Claude, Cursor and Codex configs and research skill](https://liquilens.in/agents/).

No API key or local server is required for the public tools. Client/model providers may charge separately; fair-use limits and source-specific coverage apply.

## Try one useful question

- **LiquiLens:** What changed in Cosmos Co-operative Bank's NPAs? Show reporting periods, source documents and missing evidence.
- **Seiche:** What is the current US funding-stress regime, and what is on the calendar? Cite source dates and coverage limits.
- **Undertow:** What is the estimated exit cost for a $100k BTC position? Show venue coverage, timestamps and excluded fees.

Anonymous initialization, tool discovery and one actual call per product passed: `bank_asset_quality_review`, `funding_stress_now` and `crypto_exit_check`. Live public tool counts were 24, 16 and 16. These are operator checks, not outside-user adoption. Keep institution, funding and exit evidence separate; the public tools do not execute trades.

## Directory corrections

| Surface | Verified outcome | Remaining action |
| --- | --- | --- |
| Official MCP Registry | All three active/latest records have the current versions and hosted URLs | Monitor future releases |
| Smithery | All three public inventories match live tool names: 24 / 16 / 16 | Already current; no redundant republish |
| LobeHub | Earlier accepted claims and updates now publicly show Claimed, validated, current versions and correct HTTP connections for all three | LiquiLens and Seiche's generated local alternatives still need correction. Their existing owner records were refreshed and read back. The existing support thread includes the newly found LiquiLens recipe-as-stdio error; sent bodies were verified, while delivery, resolution and public propagation remain unverified |
| MCP.so Seiche | Existing listing claimed. Hosted description, overview, commands, prompts, documentation link and kit links saved; owner readback confirms the new copy; anonymous propagation remains inconsistent | Canonical cache propagation and nine-to-sixteen tool rescan remain pending. The existing support ticket remains Open with no reply |
| Glama connectors | All three existing hosted connectors are owner-verified, Healthy and expose 24 / 16 / 16 public tools | Tool-description grades update separately; LiquiLens has eight ungraded tools queued |
| Glama repository entries | Seiche and Undertow repository syncs completed; new quickstarts verified on both public pages | Repository schema scores remain separate from the current remote tool inventories |

These are corrections and reconciliation of existing listings, not new placements. The four newly recorded product/channel rows in the family ledger describe previously existing pages. Other ledger rows retain their own observation dates.

## Setup visibility and publication

The primary READMEs lead with the three commands, a useful question and the free kit. All three developer pages and the combined kit are deployed. Mobile (390px) and desktop (1440px) checks passed with no horizontal overflow or JavaScript errors, and the developer quickstarts copy all three commands.

[Seiche's refreshed developer page](https://seiche.info/developers) is now public on both its canonical domain and Pages origin, following [PR 334](https://github.com/beepboop2025/seiche/pull/334). Its full publication passed 5,238 tests and 139 subtests. Independent checks verified the signed catalog, copied commands and an actual funding-tool response on both domains. The existing backend release is unchanged, and the normal four-hour refresh schedule is restored. [Publication and browser receipts](mcp-presentation-refresh-20261011.json).

## OpenBB

`openbb-seiche` **0.1.1 is already public on PyPI**. The old ecosystem PR is open/unmerged in an archived repository. The official Marketplace application was already submitted at 11:08:46 UTC on 11 October, with a first-year fee-waiver request. Marketplace review, waiver acceptance and a public marketplace entry remain pending. No duplicate application or paid commitment was made. [Existing application receipt](openbb-marketplace-20261011.md).

## Published setup notes

- [Liquidity Lab Telegram post](https://t.me/LiquidityLabDesk/411): all three commands, three example questions, browser link and combined kit.
- [LiquiLens X post](https://x.com/LiquiLens/status/2109256192430403720): exact Seiche command, a funding question and the combined client configs/skill.

Both posts were read back after publication. Posting, views, directory validation and synthetic checks do not establish customer acquisition, repeat use or revenue. No paid advertising or directory boost was purchased.

[Machine-readable receipts](mcp-discovery-20261011.json) · [Product/channel ledger](../marketplaces.json).

## Fresh presentation check

A second check on 11 October covered ten entry pages at 390px and 1440px: all twenty views loaded without JavaScript errors, broken images or horizontal overflow. The browser bank, funding and BTC-exit examples returned real evidence; all three snapshots were retained and exported as a Markdown brief and JSON bundle on desktop and mobile. Copied Claude, Codex and Cursor configurations match the downloadable server configurations. These are operator checks.

[Presentation polish PR 167](https://github.com/beepboop2025/liquilens-site/pull/167) aligns the Cosmos Bank quickstart with its browser destination and repairs joined words in share titles. [PR 168](https://github.com/beepboop2025/liquilens-site/pull/168) shows repeated bank caveats once in the readable summary while retaining the original evidence. [PR 169](https://github.com/beepboop2025/liquilens-site/pull/169) restores readable keyboard skip-link contrast. These changes are deployed and independently checked in the browser. [Fresh machine-readable check](mcp-presentation-refresh-20261011.json).
