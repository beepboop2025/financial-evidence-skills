# AI-agent infrastructure publication — 15 October 2026

Financial Evidence **0.1.9 is published on PyPI, Homebrew, GitHub Releases and GHCR**.
The JavaScript AI SDK **0.1.0 is published on npm**. All **14 products** in the
installed client catalog have an active official MCP Registry record.

```sh
python3 -m pip install 'financial-evidence[workspace]==0.1.9'
financial-evidence-trading doctor
```

```sh
npm install @moomoo202020/financial-evidence-ai-sdk@0.1.0 ai zod
```

[Start a research task](ai-trading-tools.html) · [AI SDK setup](../platforms/ai-sdk.md) ·
[14 product connection cards](../connect/) · [37 platform setup routes](../platforms/).

## Published and checked

| Channel | Result | Verification |
| --- | --- | --- |
| [PyPI](https://pypi.org/project/financial-evidence/0.1.9/) | 0.1.9 public | Fresh anonymous installation, all 11 commands, 60 source-file byte comparisons, stdio and persistent MCP/context clients |
| [GitHub release](https://github.com/beepboop2025/financial-evidence-skills/releases/tag/v0.1.9) | Signed release with Python archives, MCP bundle, SBOM and checksums | PyPI/GitHub archives match; four build attestations bind to the exact source and workflow |
| [GHCR](https://github.com/beepboop2025/financial-evidence-skills/pkgs/container/financial-evidence-skills) | 0.1.9 public for amd64 and arm64 | Both actual containers passed the MCP contract using the immutable image digest |
| [Homebrew](https://github.com/beepboop2025/homebrew-tap/pull/10) | 0.1.9 formula published | Independent macOS audit, style, actual install, formula test and all entrypoints passed; tap Actions remain disabled |
| [npm AI SDK](https://www.npmjs.com/package/@moomoo202020/financial-evidence-ai-sdk/v/0.1.0) | 0.1.0 public | Fresh registry installation, five native SDK tests, strict TypeScript and seven installed-file byte comparisons |
| Official MCP Registry | All 14 catalog products covered | Exact active/latest records, including newly published Workspace 1.3.0 and Market Atlas Corpus 1.0.0 |

[Python/container/Homebrew verification](../releases/0.1.9.json) ·
[npm verification](ai-sdk-publication.json) ·
[new hosted MCP verification](hosted-mcp-registry-20261015.json).

## Official MCP Registry coverage

The namespace query returned **23 current records**. The table maps the **14 products**
in the 0.1.9 client catalog. A product may register its native endpoint while the
connection cards use its central gateway alias. Package and hosted versions remain independent.

| Product | Registered version | Public registry record |
| --- | --- | --- |
| Seiche | 0.16.4 | [io.github.beepboop2025/seiche](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fseiche/versions/0.16.4) |
| LiquiLens | 1.8.1 | [io.github.beepboop2025/liquilens](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fliquilens/versions/1.8.1) |
| Undertow | 1.13.0 | [io.github.beepboop2025/undertow](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fundertow/versions/1.13.0) |
| Palimpsest | 1.9.3 | [io.github.beepboop2025/palimpsest](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fpalimpsest/versions/1.9.3) |
| NoiseFloor | 0.4.0 | [io.github.beepboop2025/noisefloor](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fnoisefloor/versions/0.4.0) |
| NarcoScope | 1.6.0 | [io.github.beepboop2025/narcoscope](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fnarcoscope/versions/1.6.0) |
| Wake | 0.4.0 | [io.github.beepboop2025/wake](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fwake/versions/0.4.0) |
| Source Data Research Workspace | 1.1.0 | [io.github.beepboop2025/financial-source-data](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Ffinancial-source-data/versions/1.1.0) |
| Seiche Market Atlas Corpus | 1.0.0 | [io.github.beepboop2025/seiche-market-corpus](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fseiche-market-corpus/versions/1.0.0) |
| Riptide | 1.3.0 | [io.github.beepboop2025/riptide](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Friptide/versions/1.3.0) |
| MyQuant Editorial | 2.1.1 | [io.github.beepboop2025/myquant-editorial](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fmyquant-editorial/versions/2.1.1) |
| MyQuant App Discovery | 2.0.0 | [io.github.beepboop2025/myquant-app](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fmyquant-app/versions/2.0.0) |
| LiquiLens Trade Safety | 0.2.2 | [io.github.beepboop2025/liquilens-trade-safety-gateway](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Fliquilens-trade-safety-gateway/versions/0.2.2) |
| Financial Evidence Workspace | 1.3.0 | [io.github.beepboop2025/financial-evidence-workspace](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.beepboop2025%2Ffinancial-evidence-workspace/versions/1.3.0) |

[Machine-readable product coverage](product-registry-coverage.json).

## Complete listing tracker

The tracker has **176 product/channel records**. These are not unique
marketplaces, people, customers or tool invocations. Each entry retains its own verification date.

| Recorded state | Records |
| --- | ---: |
| live | 82 |
| submitted | 62 |
| closed unmerged | 1 |
| eligible automatic | 1 |
| ready account action | 5 |
| conditional artifact | 2 |
| paused external | 1 |
| skipped paid | 2 |
| listed incomplete | 18 |
| approved pending public | 1 |
| sent delivery unverified | 1 |

[Download every record and its next action](../marketplaces.json).
Three previously submitted directory records were confirmed merged and corrected to live.
The existing [Docker PR](https://github.com/docker/mcp-registry/pull/4765) and
[Kilo PR](https://github.com/Kilo-Org/kilo-marketplace/pull/366) now reference 0.1.9;
both still need maintainer approval/review. The new
[Vercel AI SDK registry PR](https://github.com/vercel/ai/pull/23401) is submitted.
[Submission refresh evidence](directory-refresh-20261015.json).

The bounded publication monitor checked **29 configured public identities/contracts**
with **zero findings**. It also inventories all 176 tracker records, including records
outside those live checks. Its daily schedule is 06:17 UTC; a configured schedule
alone does not prove future execution. [Current audit](publication-audit-20261015.json) ·
[Monitor scope and instructions](gap-monitor.md).

## Usage and traction

Availability and installation checks do not establish independent agent adoption.
These verification calls are operator test traffic. A directory showing “No recent usage”
means it has not detected tool invocations in its own measurement window; it cannot
establish zero usage through direct clients, PyPI, REST or other gateways.
A “Try in Browser” call can validate that directory's connection, but must stay labelled
as an operator test rather than external traction.

The next adoption evidence is an independently attributable useful task followed by a
return visit or repeat task. Downloads, listing counts, synthetic calls and marketplace
audience size remain separate. No heavy independent usage or universal directory
coverage is claimed by this publication record.
