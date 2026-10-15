# Connect a trading research agent

Use Financial Evidence as a source-cited research input in an existing agent.
Start with funding conditions, a covered institution or indicative exit liquidity.
The public service supplies research data; the separate customer-owned paper
host can retain exact assessments and consented broker-outcome records.

## Get the first result

For persistent connections, source-status streaming and repeatable latency
measurements, use the [agent infrastructure source release](low-latency.md).

Add this Streamable HTTP URL to your agent's MCP configuration:

```text
https://agents.seiche.info/products/financial-evidence/mcp
```

Public reads need no account or data API key. Discover the live schemas, then
call `financial_evidence_agent_query` with:

```json
{"dataset":"money_markets","entity":"USD","limit":3}
```

Keep source URLs, units, observation dates, restrictions and missing values
with the result. The [connection page](../connect/) provides downloadable MCP
configurations and the same tasks through a browser, REST and Python.

| Agent runtime | Integration path |
| --- | --- |
| Streamable HTTP MCP client | Use the public URL above; inspect and authorize the tools in your client |
| LangChain / LangGraph | `framework_tools('langchain', client)`; attach to the model and execution node |
| CrewAI | `framework_tools('crewai', client)` in the research agent's tool list |
| OpenAI Agents SDK | `framework_tools('openai', client)` in `Agent(tools=...)` |
| Pydantic AI | `framework_tools('pydantic-ai', client)` in `Agent(tools=...)` |
| Other frameworks and trading engines | Use REST or `tool_functions(client)` in a separate research step |

The [native framework recipes](https://github.com/beepboop2025/financial-evidence-skills/tree/trading-readiness-v1.0.0/integrations/agents)
use one shared evidence contract. Our automated SDK checks register tools and
invoke a query with fixtures that contain both zero and missing values. They
exercise LangChain Core 1.6.6, CrewAI 1.6.1, OpenAI Agents 0.22.3 and Pydantic AI
Slim 2.52.0. This establishes the tested SDK bindings, not every model, client
version or trading engine. No model call or broker connection is required.
See the [MCP client guide](https://modelcontextprotocol.io/docs/develop/connect-remote-servers)
for the client-side connection and permission model.

## Check your connection before integrating

Install the source release in a dedicated Python 3.10+ environment:

```sh
python3 -m pip install --force-reinstall 'financial-evidence[workspace] @ git+https://github.com/beepboop2025/financial-evidence-skills.git@trading-readiness-v1.0.0'
financial-evidence-trading doctor
```

The `doctor` command is in this source release; the older GitHub release 0.1.8 wheel does
not include it. The [platform kit](../platforms/finance-platform-kit.zip) also
contains the current package source. Save the source revision with your result.
The source package retains version 0.1.8; `--force-reinstall` is required when
replacing the older wheel. Plain install and `--upgrade` can retain the older
code despite the different source reference.

The diagnostic initializes four public MCP sessions, discovers their tools and
makes one reviewed read call to each: Seiche, LiquiLens, Undertow and Financial
Evidence. It fetches the public source monitor once. Requests are anonymous and
labelled synthetic; the command ignores `SEICHE_NETWORK_TOKEN`, reads no broker
credentials and does not enroll an installation or submit an order. It follows
no redirects, makes no retry or native-origin fallback, and uses a 30-second
deadline per concurrent connection.

For Undertow the read is `liquidity_tiers`. The native `agent_access_status`
tool describes the anonymous native caller's allowance, not the gateway's
authorized public research route. Its quota can be exhausted while the gateway
research call works. The gateway keeps that status tool anonymous to protect
its operator identity; it is not used as the research-readiness check.

For one product, or a shorter connection deadline:

```sh
financial-evidence-trading doctor --product seiche --timeout 15
```

The JSON separates:

- `connection_status`: MCP initialization, discovery and the read call.
- `source_monitor.status`: whether the monitor is current. Its timezone-aware
  evaluation clock and reported age must be within 15 minutes; a clock more
  than 60 seconds in the future cannot pass.
- `source_monitor.products`: the inspected sources' freshness, restrictions,
  coverage and reasons, including a separately scoped funding subset when present.
- `input_eligibility: not_evaluated` and `execution_authority: none`: connection
  success grants no permission to use an observation for an order.
- `external_adoption: not_measured`: this diagnostic is internal verification traffic.

Exit 0 means all selected connections passed and the monitor was current.
Exit 2 means a connection or monitor needs attention. **Neither exit code
approves a trade.** Stale, restricted and unknown inputs can appear alongside
exit 0: the diagnostic has successfully reported their limits. Inspect them.
Do not run this as a rapid polling loop; it consumes normal public request quotas.

## Decide which observations your workflow can use

Choose exact series, units, source rights, publication calendars and acceptable
ages for the task. The [input-policy guide](../start/trading-agents.md) shows
how to retain observation, publication, availability and capture clocks separately.
An unchanged result or successful retrieval does not refresh its observation.
Current published history is not proof of what was knowable for a historical trade.

Use [the Carrier setup guide](execution-setup.md) for the separate private paper
host. Its exact source pin, account controls and source-policy checks are distinct
from the public research connections. A customer can explicitly grant a named
recipient access to bounded decision and outcome records. Public MCP requests
alone reveal neither a private trading decision nor an executed fill.

## Establish useful recurring use

Start one independent pilot with a concrete recurring task. With the participant's
agreement, retain its source version, first useful result, setup time, refusal
reasons and a second task on another day. Use the [pilot scorecard](pilot-scorecard.md)
to distinguish activation, return use, continuation and verified payment.

Connection checks, internal paper runs, package downloads and anonymous requests
do not identify independent customers. Operators choose whether to integrate;
availability through a common protocol does not establish universal adoption.
Optional learning and outcome sharing remain separate from free research access.
Contact [support](../support/) with the workflow and redacted diagnostic, never
credentials, account IDs or private trading instructions.

## Dated verification

The [15 October 2026 operator check](readiness-20261015.json) passed all four
MCP connections and found the source monitor current. It retained Seiche's
mixed source coverage and separately fresh core funding subset, Undertow's
source-rights restriction, and unknown coverage where no qualified clock
adapter exists. This is a dated integration check; rerun the diagnostic for
your installation. It establishes no external users or executed trades.
