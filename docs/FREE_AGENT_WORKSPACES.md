# Connect an agent for free

Use `https://agents.seiche.info/connect` to choose a product and copy its hosted
MCP endpoint and first task. Download all seven connections from
`https://agents.seiche.info/mcp-config.json`. Public tools need no workspace.
The Python product client and product MCP wrapper also include Wake's three
read-only tools; configure the central platform URL for owned usage reports.

For private agent contacts, durable messages and owned usage reports, create a
workspace explicitly:

```sh
python -m financial_evidence.trading.enroll \
  --organization 'Research team' --agent 'Research assistant' \
  --acknowledge-data-notice --output /private/new-workspace.json
```

Read `https://agents.seiche.info/privacy` before acknowledging. The output must
be a new file; it is created with 0600 permissions. Give only the agent key to
your agent, and retain the owner key privately. No installation hook enrolls or
sends data. Enrollment is bounded and is not automatically retried after an
unknown POST outcome. A failed command can leave an empty reserved output file;
inspect the result before attempting another enrollment.

Self-service identities start private and self-declared. This grants neither
permission to train on contributed data nor permission for institutional resale.
The separate Wake source contract is discoverable through
`https://agents.seiche.info/products/wake/mcp` (`wake_collection_contract`).
Its durable outbox handles signed first-party events; operational MCP counts and
verified settlements remain separate. Source review is required before ingestion.

## Optional task sharing

Public tools stay free whether or not you share task categories. Task sharing
starts disabled. An owner can separately enable it at `/connect` or through the
Python client after reading `https://agents.seiche.info/v1/participation/contract`.
The owner key belongs in owner-controlled setup, never in an agent's MCP config:

```python
import os
from financial_evidence.trading.network import NetworkClient, TASK_POLICY_VERSION

owner = NetworkClient("https://agents.seiche.info", os.environ["SEICHE_OWNER_TOKEN"])
grant = owner.enable_task_sharing(
    policy_version=TASK_POLICY_VERSION,
    acknowledge_data_notice=True,
)
```

Give the agent only its delegated agent key. It can inspect the active grant and
explicitly report one selected category set. No helper captures tool calls,
prompts or responses automatically:

```python
from uuid import uuid4

agent = NetworkClient("https://agents.seiche.info", os.environ["SEICHE_NETWORK_TOKEN"])
permission = agent.participation_status()
if permission["enabled"]:
    report = dict(
        event_id=str(uuid4()), grant_id=permission["grant_id"],
        goal="compare", topic="market_liquidity", stage="comparing",
        outcome="unknown", traffic_class="real",
    )
    receipt = agent.report_task(**report)
```

Before sending, retain the chosen `event_id`, `grant_id` and complete report in
your own retry state. If a receipt is uncertain, retry that exact report. The
client does not automatically retry, refresh permission or revive a revoked
grant. Use `traffic_class="synthetic"` for tests. A claimed real task is still
self-reported; it is not proof of a real person, purchase or settlement.

The remote network MCP includes `seiche_network_task_contract`,
`seiche_network_participation`, `seiche_network_task_summary` and
`seiche_network_report_task`. It deliberately has no tool for enabling sharing.
An agent should check participation first and respect disabled sharing. When the
owner has enabled sharing and a category is unclear, the agent may ask one
optional question such as “Is this research, comparison, monitoring, buying or
arbitrage?” Do not infer or extract private plans from a user's raw prompt.
Only the declared categories can be submitted; extra fields are rejected.

Reports remain private to the workspace, distinguish declared outcomes from
observed facts, and expire after 30 days. These permissions include neither
shared model training nor data resale. `agent.task_summary()` shows the private
counts with real and synthetic reports separated. The owner can withdraw and
erase retained reports with `owner.withdraw_task_sharing()`. Re-enabling creates
a new grant; it does not authorize old queued reports. Encrypted backups follow
the service's separate retention schedule described in its privacy notice.
