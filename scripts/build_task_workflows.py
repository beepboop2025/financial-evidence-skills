#!/usr/bin/env python3
"""Build standalone n8n templates from the maintained evidence formatter."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/automations"
TASKS = {
    "seiche": ("Review morning dollar funding with Seiche and optional Slack or Telegram updates", "funding_stress_now", {}, 21600, "https://api.seiche.info/mcp", "funding"),
    "liquilens": ("Review Cosmos Bank NPA disclosures with LiquiLens and optional updates", "bank_asset_quality_review", {"slug": "cosmos-ucb", "include_history": True}, 21600, "https://api.liquilens.in/mcp", "bank"),
    "undertow": ("Compare a $100k BTC exit estimate with Undertow and optional updates", "exit_cost", {"size_usd": 100000}, 7200, "https://api.seiche.info/undertow/mcp", "exit"),
}


def node(name, kind, position, parameters, version=1, **extra):
    return dict(id=name.lower().replace(" ", "-"), name=name, type=kind,
                typeVersion=version, position=position, parameters=parameters, **extra)


def workflow(product, task):
    name, tool, inputs, age, endpoint, demo = task
    code = (ROOT / "integrations/n8n/task-output.cjs").read_text().split("if (typeof module")[0]
    code += "\nconst items = $input.all();\nif (items.length !== 1) throw new Error('Expected one MCP result');\n"
    code += f"return [{{json: formatTaskResponse({json.dumps(product)}, items[0].json, $('Task settings').first().json)}}];\n"
    nodes = [
        node("Try once", "n8n-nodes-base.manualTrigger", [100, 240], {}),
        node("Morning schedule", "n8n-nodes-base.scheduleTrigger", [100, 460], {"rule": {"interval": [{"field": "cronExpression", "expression": "0 8 * * 1-5"}]}}, 1.2),
        node("Task settings", "n8n-nodes-base.set", [400, 240], {"mode": "raw", "jsonOutput": json.dumps({"toolInput": inputs, "maxAgeSeconds": age}, indent=2), "options": {}}, 3.4),
        node("Fetch task evidence", "@n8n/n8n-nodes-langchain.mcpClient", [700, 240], {
            "serverTransport": "httpStreamable", "endpointUrl": endpoint, "authentication": "none",
            "tool": {"__rl": True, "mode": "id", "value": tool}, "inputMode": "json",
            "jsonInput": "={{ JSON.stringify($json.toolInput) }}", "options": {"timeout": 20000, "convertToBinary": False}}, 1.1),
        node("Keep evidence and prepare update", "n8n-nodes-base.code", [1000, 240], {"mode": "runOnceForAllItems", "jsCode": code}, 2),
        node("Optional Slack update", "n8n-nodes-base.slack", [1340, 180], {
            "resource": "message", "operation": "post", "select": "channel",
            "channelId": {"__rl": True, "mode": "id", "value": ""}, "text": "={{ $json.message_text }}",
            "otherOptions": {"includeLinkToWorkflow": False}}, 2.3, disabled=True),
        node("Optional Telegram update", "n8n-nodes-base.telegram", [1340, 420], {
            "resource": "message", "operation": "sendMessage", "chatId": "", "text": "={{ $json.message_text }}",
            "additionalFields": {"appendAttribution": False}}, 1.2, disabled=True),
        node("01 Start here", "n8n-nodes-base.stickyNote", [20, -240], {
            "width": 550, "height": 380, "color": 5,
            "content": f"## 01 · Try the research task\nImport into your n8n instance and select **Execute workflow**. Public evidence requires no API key, account or AI model.\n\n[Try the browser demo](https://liquilens.in/start/?task={demo})\n\nEdit **Task settings** for the bank slug, position size or snapshot-age limit where applicable. For another bank, check `banking_specialisation_coverage` first.\n\nThe workflow imports **inactive**. The schedule is weekdays at 08:00 **UTC**; change the workflow timezone and cron before publishing."}),
        node("02 Read the complete result", "n8n-nodes-base.stickyNote", [620, -240], {
            "width": 570, "height": 380, "color": 5,
            "content": "## 02 · Keep the source evidence\nOpen **Keep evidence and prepare update**. `evidence` preserves the complete source response; `message_text` is a short, deterministic summary.\n\nGeneration, retrieval and observation dates mean different things. Missing data stays missing. Old snapshots suppress current-looking summaries; transport/tool errors stop execution.\n\nFunding context is not a bank rating. An NPA reduction is not necessarily a cash recovery. BTC costs use published depth bands and exclude fees.\n\n[Setup and interpretation](https://beepboop2025.github.io/financial-evidence-skills/automations/)"}),
        node("03 Connect your update destination", "n8n-nodes-base.stickyNote", [1250, -240], {
            "width": 470, "height": 340, "color": 4,
            "content": "## 03 · Optional delivery\nBoth message nodes are **disabled** on import.\n\nTo receive updates, choose one node, attach your own Slack or Telegram credential, enter your channel/chat ID and enable it. Test with your own destination.\n\nKeep unused delivery nodes disabled. Activate the workflow only after reviewing its schedule.\n\nYour n8n execution retention settings determine how long the full evidence is kept. No trading or credit decision is automated."}),
    ]
    connections = {}
    for source, targets in [
        ("Try once", ["Task settings"]), ("Morning schedule", ["Task settings"]),
        ("Task settings", ["Fetch task evidence"]), ("Fetch task evidence", ["Keep evidence and prepare update"]),
        ("Keep evidence and prepare update", ["Optional Slack update", "Optional Telegram update"]),
    ]:
        connections[source] = {"main": [[{"node": target, "type": "main", "index": 0} for target in targets]]}
    return {"name": name, "active": False, "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1", "timezone": "UTC"}, "pinData": {}, "tags": []}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for product, task in TASKS.items():
        (OUT / f"{product}.json").write_text(json.dumps(workflow(product, task), indent=2) + "\n")
