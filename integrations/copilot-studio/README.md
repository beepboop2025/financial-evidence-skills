# Copilot Studio MCP connectors

Status: packaged, not submitted (3 November 2026). Nothing in this folder has been
imported into a Copilot Studio tenant, submitted for Microsoft certification or
listed in any catalog.

These are custom connector definitions for the hosted MCP servers of
LIQUILENS PRIVATE LIMITED. Each definition is one POST operation marked
`x-ms-agentic-protocol: mcp-streamable-1.0`, the Streamable HTTP pattern from
Microsoft's [MCP custom connector guide](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent).
The servers are public and read-only, so every connection uses no
authentication and stores no key.

| Product | Folder | Server URL |
| --- | --- | --- |
| LiquiLens | [`liquilens/`](liquilens/intro.md) | `https://api.liquilens.in/mcp` |
| Seiche | [`seiche/`](seiche/intro.md) | `https://api.seiche.info/mcp` |
| LiquiLens Undertow | [`undertow/`](undertow/intro.md) | `https://api.seiche.info/undertow/mcp` |
| Palimpsest | [`palimpsest/`](palimpsest/intro.md) | `https://api.seiche.info/palimpsest/mcp` |
| NoiseFloor | [`noisefloor/`](noisefloor/intro.md) | `https://api.seiche.info/noisefloor/mcp` |
| GroundCheck | [`groundcheck/`](groundcheck/intro.md) | `https://groundcheck.seiche.info/mcp` |
| Data Breach Detector | [`data-breach-detector/`](data-breach-detector/intro.md) | `https://breach.seiche.info/mcp` |

Each folder holds `apiDefinition.swagger.json`, `apiProperties.json` and
`intro.md`. The intro lists the tools seen in the dated check, recommended agent
instructions that keep the product's claim boundaries, and known limitations.
Read it before adding a server to an agent. Riptide is deliberately excluded.
For Claude Desktop, claude.ai and Claude Code, use the
[Claude connector guide](../../docs/platforms/claude-connectors.md).

## Before you start

- Turn on generative orchestration for the agent. Copilot Studio requires it for MCP.
- You need permission to create custom connectors in the environment. Power
  Platform data policies govern MCP connectors like any other connector, and
  your tenant's licensing decides who may use a custom connector.
- Copilot Studio calls the server from Microsoft's connector infrastructure. Any
  rate limit keyed by source address applies to that shared infrastructure.

## Import with the files (reviewable, repeatable)

From the agent in Copilot Studio:

1. Go to the agent's **Tools** page and select **Add a tool**.
2. Select **New tool**, then **Custom connector**. Power Apps opens.
3. Select **New custom connector**, then **Import an OpenAPI file**.
4. Name the connector with the product title (for example `Seiche MCP`), choose
   that product's `apiDefinition.swagger.json`, and select **Continue**.
5. On **General**, upload `icon.png` from this folder and set the icon
   background color to `#0B2628`. Confirm the host and base URL match the table.
6. On **Security**, keep **No authentication**.
7. Select **Create connector**.

Then add it to the agent:

1. On the agent's **Tools** page, select **Add a tool**, then **Model Context Protocol**.
2. Select the new connector, create a connection (there is nothing to enter), and
   select **Add and configure**.
3. On the server's settings page, turn off **Allow all** and switch off any tool
   listed under the product's known limitations, such as GroundCheck's paid tools.
4. Paste the product's recommended agent instructions from its `intro.md` into
   the agent's instructions.
5. Ask one bounded question in the test pane. Check that the answer cites source
   dates and keeps missing, withheld or PARTIAL states as gaps.

The command line works too, after a device-code sign-in to your own tenant:

```sh
pip install paconn
paconn login
cd integrations/copilot-studio/seiche
paconn create --api-def apiDefinition.swagger.json --api-prop apiProperties.json --icon ../icon.png
```

`paconn create` asks for the environment. `apiProperties.json` omits
`stackOwner` because paconn cannot update a connector that carries it.

## Quickest route without the files

Copilot Studio's MCP onboarding wizard needs only the URL. On **Tools**, select
**Add a tool**, **New tool**, then **Model Context Protocol**. Enter the product
title as the server name, the description at the top of its `intro.md` as the
server description, and the server URL from the table. Choose **None** for
authentication, select **Create**, then create a connection and add it to the
agent. The files above give the same connection a reviewable, versioned
definition that can live in a solution.

## What was validated

- **Live servers.** A read-only check at 2026-11-02T20:40:24Z read each
  product's latest entry in the official MCP Registry, then sent only
  `initialize`, `notifications/initialized` and `tools/list` to the published
  remote. All seven answered over Streamable HTTP with protocol 2025-06-18, and
  each URL matches its registry entry. No tool was called. See
  [`verification-20261103.json`](verification-20261103.json).
- **Microsoft's published schemas.** Every `apiProperties.json` passes
  `schemas/paconn-apiProperties.schema.json`. Every swagger fails
  `schemas/apiDefinition.swagger.schema.json` on exactly one key,
  `x-ms-agentic-protocol`, which that schema predates. Microsoft's own
  `custom-connectors/MCP-Streamable-HTTP` template and all eight certified MCP
  connectors in the same repository fail on the same single key. Schemas were
  read from [microsoft/PowerPlatformConnectors](https://github.com/microsoft/PowerPlatformConnectors)
  at commit `1a5c168a0358bd6d29d843ce4fe6ad0df3eaa70b`.
- **OpenAPI 2.0.** All seven swaggers pass `openapi-spec-validator` 0.7.1.
- **Connector text rules.** `scripts/build_copilot_studio_connectors.py` and
  `tests/test_copilot_studio_connectors.py` enforce Microsoft's certification
  limits on titles, descriptions and summaries.
- **Not run.** `paconn validate` sends the definition to Microsoft's service and
  needs a signed-in account, so it was not run. Solution Checker, a tenant
  import and test pane calls were not run either.

## Known limitations across the set

Microsoft [lists MCP known issues](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-troubleshooting)
that match some of these servers' input schemas:

- NoiseFloor: nine of ten tools use integer `exclusiveMinimum` or
  `exclusiveMaximum` bounds, which Microsoft says throw `System.FormatException`,
  and two also use type arrays, which Microsoft says truncate the input schema.
  Expect those tools to fail until the server schemas change.
- LiquiLens Undertow: `exit_cost` uses an integer `exclusiveMinimum`.
- Several servers declare enum inputs, which arrive as plain strings. The
  servers still validate the allowed values.
- GroundCheck: four of five tools are paid per call over x402 and answer with a
  payment offer that these connections cannot settle. Keep `verify_claim` only.

## Microsoft certification is not ready

Microsoft certifies MCP servers through the Power Platform connector
certification program ([overview](https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-server-certification)).
These packages are for tenant import. Certification still needs:

1. A verified publisher: a Partner Center account with business verification,
   enrolled in the Microsoft 365 and Copilot program.
2. Authentication. MCP certification requires OAuth 2.0, an API key or basic
   authentication, plus test credentials. These servers are anonymous by design,
   and changing that is a server decision outside this package.
3. A solution package built in a Power Platform environment, with Solution
   Checker results and a test flow.
4. A published privacy policy for each endpoint. LiquiLens and Seiche have one;
   LiquiLens Undertow, Palimpsest, NoiseFloor, GroundCheck and Data Breach
   Detector do not yet.
5. A unique icon per connector. All seven share `icon.png` here.
6. A `stackOwner` value in a separate certification copy of `apiProperties.json`.

## Endpoint choice

Each definition calls the remote in the product's latest official MCP Registry
entry. This repository's Claude Code, Codex and Copilot CLI plugins reach five of
the same servers through the central gateway at
`https://agents.seiche.info/products/<product>/mcp`. In the dated check both
routes returned the same server version and tool names. Routing a connector
through the gateway would change `remote_url` in `connectors.json` and the
registry rule in the build script, so it is left as a product decision.
GroundCheck and Data Breach Detector are not on the gateway.

## Regenerate

`connectors.json` is the source. The per-product files are generated:

```sh
python3 scripts/build_copilot_studio_connectors.py --observe integrations/copilot-studio/verification-YYYYMMDD.json
# point verification_receipt in connectors.json at the new receipt, then
python3 scripts/build_copilot_studio_connectors.py
python3 scripts/build_copilot_studio_connectors.py --check
```

`--observe` is the only networked step. It sends `initialize` and `tools/list`
and never calls a tool.
