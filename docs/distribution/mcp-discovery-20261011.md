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

- **LiquiLens:** What changed in ESAF Small Finance Bank's NPAs? Show reporting periods, source documents and missing evidence.
- **Seiche:** What is the current US funding-stress regime, and what is on the calendar? Cite source dates and coverage limits.
- **Undertow:** What is the estimated exit cost for a $100k BTC position? Show venue coverage, timestamps and excluded fees.

Anonymous initialization, tool discovery and one actual call per product passed: `bank_asset_quality_review`, `funding_stress_now` and `crypto_exit_check`. Live public tool counts were 24, 16 and 16. These are operator checks, not outside-user adoption. Keep institution, funding and exit evidence separate; the public tools do not execute trades.

## Directory corrections

| Surface | Verified outcome | Remaining action |
| --- | --- | --- |
| Official MCP Registry | All three active/latest records have the current versions and hosted URLs | Monitor future releases |
| Smithery | All three public inventories match live tool names: 24 / 16 / 16 | Already current; no redundant republish |
| LobeHub | Earlier accepted claims and updates now publicly show Claimed, validated, current versions and correct HTTP connections for all three | Seiche's generated local alternatives still need correction. Owner description/summary update accepted and read back; public propagation remains pending |
| MCP.so Seiche | Existing listing claimed. Hosted description, overview, commands, prompts, documentation link and kit links saved; fresh anonymous readback shows the new copy | Canonical cache propagation and nine-to-sixteen tool rescan remain pending. One support ticket is Open |
| Glama connectors | All three existing hosted connectors are owner-verified, Healthy and expose 24 / 16 / 16 public tools | Tool-description grades update separately; LiquiLens has eight ungraded tools queued |
| Glama repository entries | Seiche and Undertow repository syncs acknowledged as Scheduled | Verify the queued repository refreshes separately from the healthy remote connectors |

These are corrections and reconciliation of existing listings, not new placements. The four newly recorded product/channel rows in the family ledger describe previously existing pages. Other ledger rows retain their own observation dates.

## Setup visibility and publication

The primary READMEs now lead with the three commands, a useful question and the free kit. LiquiLens and Undertow developer pages, and the combined kit entry page, are deployed. Their public mobile (390px) and desktop (1440px) checks passed with no horizontal overflow or JavaScript errors. The two live developer blocks match their reviewed DOM exactly and copy all three commands.

Seiche's developer-page edit is tested and merged in [PR 333](https://github.com/beepboop2025/seiche/pull/333). Its unchanged signed publication verifier excludes `frontend/public/developers.html` from the standalone frontend allowlist. No publication receipt was signed, no publisher was deployed, and no runtime or schedule was changed. The public Seiche developer page is therefore not claimed updated; the change awaits an admissible signed release.

## OpenBB

`openbb-seiche` **0.1.1 is already public on PyPI**. The old ecosystem PR is open/unmerged in an archived repository. The official Marketplace application was already submitted at 11:08:46 UTC on 11 October, with a first-year fee-waiver request. Marketplace review, waiver acceptance and a public marketplace entry remain pending. No duplicate application or paid commitment was made. [Existing application receipt](openbb-marketplace-20261011.md).

## Published setup notes

- [Liquidity Lab Telegram post](https://t.me/LiquidityLabDesk/411): all three commands, three example questions, browser link and combined kit.
- [LiquiLens X post](https://x.com/LiquiLens/status/2109256192430403720): exact Seiche command, a funding question and the combined client configs/skill.

Both posts were read back after publication. Posting, views, directory validation and synthetic checks do not establish customer acquisition, repeat use or revenue. No paid advertising or directory boost was purchased.

[Machine-readable receipts](mcp-discovery-20261011.json) · [Product/channel ledger](../marketplaces.json).
