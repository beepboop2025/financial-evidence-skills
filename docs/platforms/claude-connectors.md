# Add LiquiLens research servers to Claude

Status: packaged, not submitted (3 November 2026). No Claude directory listing
is claimed.

Each server below is hosted by LIQUILENS PRIVATE LIMITED, is read-only and needs
no API key. The URL is the remote in the product's latest official MCP Registry
entry, checked with a read-only `initialize` and `tools/list` on 2 November 2026
(UTC). See the [dated receipt](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/copilot-studio/verification-20261103.json).

| Product | Server URL | Claude Code plugin |
| --- | --- | --- |
| LiquiLens | `https://api.liquilens.in/mcp` | `liquilens@liquidity-lab` |
| Seiche | `https://api.seiche.info/mcp` | `seiche@liquidity-lab` |
| LiquiLens Undertow | `https://api.seiche.info/undertow/mcp` | `undertow@liquidity-lab` |
| Palimpsest | `https://api.seiche.info/palimpsest/mcp` | `palimpsest@liquidity-lab` |
| NoiseFloor | `https://api.seiche.info/noisefloor/mcp` | `noisefloor@liquidity-lab` |
| GroundCheck | `https://groundcheck.seiche.info/mcp` | `groundcheck@liquidity-lab` |
| Data Breach Detector | `https://breach.seiche.info/mcp` | `data-breach-detector@liquidity-lab` |

The Claude Code plugins for the first five reach the same servers through
`https://agents.seiche.info/products/<product>/mcp`. Either URL works; the dated
check saw the same server version and tool names on both.

## Claude Desktop and claude.ai

A custom connector belongs to your Claude account, so the same connector works on
claude.ai and in Claude Desktop. You do not need `claude_desktop_config.json`;
that file is for local servers.

On Free, Pro and Max plans:

1. Open **Customize**, then **Connectors**.
2. Select **+ Add**, then **Add custom connector**.
3. Enter a name, for example `LiquiLens`, and the server URL from the table.
   Select **Continue**.
4. Under **Authentication**, choose **No sign in**. Leave request headers empty.
5. Select **Add**.
6. In a chat, select **+** at the lower left, then **Connectors**, and turn the
   connector on for that conversation.

A Free plan allows one custom connector.

On Team and Enterprise plans, an Owner or Primary Owner adds the connector once.
On Enterprise, a custom role with Manage access to Libraries can also do this.

1. Open **Organization settings**, then **Connectors**.
2. Select **Add**, hover over **Custom**, then select **Web**.
3. Enter the name and server URL, select **Continue**, choose **No sign in**,
   then select **Add**.

Members then open **Customize**, then **Connectors**, find the connector and
select **Connect**.

Claude does not verify custom connectors, and it connects to them from
Anthropic's cloud. Steps follow Anthropic's
[custom connector guide](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

## Claude Code

Install a plugin, which adds the server and a short skill with the product's
claim boundaries:

```sh
claude plugin marketplace add beepboop2025/financial-evidence-skills
claude plugin install undertow@liquidity-lab
```

Or add the server alone:

```sh
claude mcp add --transport http undertow https://api.seiche.info/undertow/mcp
```

The GroundCheck and Data Breach Detector plugins were packaged on 3 November
2026. All seven plugins installed from a local copy of this marketplace in an
isolated Claude Code 2.1.316 configuration, and all seven servers reported
connected. Installation from the public marketplace has not been rechecked.

## Keep each product's claim boundaries

Each server states its limits in its tool descriptions. On claude.ai, add the
product's recommended instructions to a Project so every chat keeps them. The
same text serves Copilot Studio agents:
[LiquiLens](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/copilot-studio/liquilens/intro.md#recommended-agent-instructions) ·
[Seiche](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/copilot-studio/seiche/intro.md#recommended-agent-instructions) ·
[LiquiLens Undertow](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/copilot-studio/undertow/intro.md#recommended-agent-instructions) ·
[Palimpsest](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/copilot-studio/palimpsest/intro.md#recommended-agent-instructions) ·
[NoiseFloor](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/copilot-studio/noisefloor/intro.md#recommended-agent-instructions) ·
[GroundCheck](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/copilot-studio/groundcheck/intro.md#recommended-agent-instructions) ·
[Data Breach Detector](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/copilot-studio/data-breach-detector/intro.md#recommended-agent-instructions).

Points that most often matter:

- Seiche is free public research. Withheld or missing readings are gaps, never
  calm, and licensed values stay withheld.
- LiquiLens Undertow: PARTIAL means missing history, never calm. Anonymous use is
  metered at 200 calls per UTC day per source address, and Claude connects from
  Anthropic's cloud, so users can share that allowance.
- GroundCheck: only `verify_claim` is free. The other tools answer with an x402
  payment offer. Never approve a payment from a chat.
- NoiseFloor: send only public, synthetic or explicitly authorized observations.
- Data Breach Detector reports appearances in public disclosures, never breach
  contents.
- Every product is research, not investment advice.

## Why there is no MCPB bundle

All seven are hosted Streamable HTTP servers that Claude Desktop and claude.ai
reach by URL. An MCPB bundle would add a local bridge process and a new supply
chain without adding a capability. The one local case with real value is
NoiseFloor, whose statistics could run on the user's machine so private
observations never leave it. NoiseFloor already publishes a stdio package
(`noisefloor` on PyPI, listed in the official MCP Registry), so an MCPB wrapper
for it is a possible follow-up rather than part of this package.
