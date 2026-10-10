# Connect a financial research agent

Use the public Streamable HTTP server:

```text
https://api.seiche.info/openbb/mcp
```

Our connection needs no API key. Your agent platform may require its own account,
model credentials and paid plan. Inspect its current tool list before enabling it.

Start with this task:

> Discover the available Financial Evidence datasets. Review USD funding and the
> covered institution ESAF. Cite the source URL, observation date, unit and
> availability for each observation. Keep the funding and institution sections
> separate. Save the evidence and identify what needs human review.

## Claude / Cowork

In Settings → Connectors, add a custom connector with the URL above. For Claude
Code, run:

```sh
claude mcp add --transport http financial-evidence https://api.seiche.info/openbb/mcp
```

This uses a custom connection. Official connector-directory publication is a
separate process. [Claude instructions](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

## ChatGPT / Codex

Use a custom Streamable HTTP MCP connection where your account and administrator
permit it. For the Codex CLI:

```sh
codex mcp add financial-evidence --url https://api.seiche.info/openbb/mcp
```

The repository also contains an installable Codex plugin. Universal directory
publication remains pending; this guide does not claim a ChatGPT listing.
[Plugin installation](https://beepboop2025.github.io/financial-evidence-skills/llms.txt) ·
[OpenAI submission documentation](https://developers.openai.com/plugins/deploy/submission).

## Microsoft Copilot Studio

Add an MCP server tool to an agent using Copilot Studio's current MCP flow. Enter
the URL above and use the unauthenticated connection option where available.
Select the dataset discovery and research-query tools, test the task in the test
pane, and inspect the cited result before publishing your agent. Tenant policy
can restrict external servers. This setup has not been tested in your tenant.
[Microsoft instructions](https://learn.microsoft.com/en-us/microsoft-copilot-studio/agent-extend-action-mcp).

## Flowise

Add a Custom MCP tool with Streamable HTTP transport, point it at the URL above,
refresh the tool list, and attach the research tools to your agent. Use your own
model connection. Run the task and retain its tool response with the final note.
Native Flowise execution remains to be verified.
[Flowise instructions](https://docs.flowiseai.com/tutorials/tools-and-mcp).

## Dify

Use a remote MCP connection where supported, or evaluate the repository's native
tool plugin in `integrations/dify`. Version 0.1.1 passed three bounded Dify Cloud
remote-debug workflows. Its [Marketplace submission](https://github.com/langgenius/dify-plugins/pull/3278)
remains under review; [package and validation scope](native-packages.md#dify)
are available for evaluation.
[Plugin source](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/dify).

## Haystack

Use the existing Financial Evidence component from
[`integrations/haystack`](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/haystack).
Its upstream integration review is tracked in
[PR 650](https://github.com/deepset-ai/haystack-integrations/pull/650). Source
installation and upstream catalog acceptance are distinct states.

## TradingView companion

Connect Financial Evidence alongside TradingView's official server only if you
already have eligible TradingView access. TradingView uses OAuth and requires
Essential or above; trials are excluded. Its URL is:

```text
https://mcp.tradingview.com/mcp
```

For a narrowly scoped review, enable only `list_watchlists`, `get_watchlist` and
`search_symbols` from TradingView. Do not enable `get_active_watchlist`: its
documentation says it can activate or create a watchlist. Tool-name instructions
are not an access-control mechanism; enforce the selection in your client's tool
permissions where supported, otherwise leave TradingView disconnected.

> Read my existing watchlist. Ask me to select an institution covered by
> LiquiLens; do not infer a symbol-to-bank match. Retrieve that institution's
> evidence and the USD funding context. Cite sources and dates, distinguish
> market data from filing evidence, and produce a research note for review.

This is a companion workflow in an MCP client, not a TradingView indicator or
marketplace listing. [Official TradingView setup and tool behavior](https://www.tradingview.com/mcp/docs).

## Alpaca companion

Keep Financial Evidence in a separate research step beside an existing Alpaca
paper-trading project. Run the cited funding task above before reviewing a paper
simulation. This kit does not connect a brokerage account, ingest credentials or
submit an order. Alpaca's official MCP has broader capabilities; any account
connection and tool permission must be chosen separately.
[Alpaca MCP documentation](https://docs.alpaca.markets/us/docs/trading-api-mcp).

## Acceptance check

1. Retrieve one bounded research response and open its cited source.
2. Confirm unavailable values stay missing and observation dates remain visible.
3. Save the response with a useful research note.
4. Repeat on another working day and record whether it changed the review.

The first three prove a useful setup. Repeat use by an independent user is the
adoption signal. A synthetic probe, download or directory listing does not prove
customer adoption.
