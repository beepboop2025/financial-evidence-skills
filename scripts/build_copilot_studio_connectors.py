#!/usr/bin/env python3
"""Build Copilot Studio MCP custom connector definitions from the reviewed catalog.

Offline (default): regenerate apiDefinition.swagger.json, apiProperties.json and
intro.md for every connector in integrations/copilot-studio/connectors.json.
--check: fail when a generated file differs from its source.
--observe PATH: read-only network check that writes a dated receipt. It reads
each product's latest official MCP Registry entry, then sends only initialize,
notifications/initialized and tools/list to the published remote. It never calls
a tool and sends no credentials.

Microsoft references:
https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent
https://learn.microsoft.com/en-us/connectors/custom-connectors/certification-submission
https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-troubleshooting
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "integrations/copilot-studio"
CATALOG = BASE / "connectors.json"
GATEWAY_CATALOG = ROOT / "docs/connect/native-connections.json"
REGISTRY = "https://registry.modelcontextprotocol.io/v0/servers/{name}/versions/latest"
AGENTIC_PROTOCOL = "mcp-streamable-1.0"
ACCEPT = "application/json, text/event-stream"
PROTOCOL_VERSION = "2025-06-18"
USER_AGENT = "liquilens-packaging-check/2026-11-03 (synthetic; read-only; initialize+tools/list only)"
# Title words Microsoft's connector certification guidance forbids.
RESTRICTED_TITLE = re.compile(
    r"\b(api|connector|copilot studio|power apps|power automate|power platform|"
    r"power bi|power pages|logic apps|dataverse)\b", re.IGNORECASE)
PRODUCT_NAMES = re.compile(
    r"\b(copilot studio|power apps|power automate|power platform|power bi|"
    r"power pages|logic apps|dataverse)\b", re.IGNORECASE)
SUMMARY = re.compile(r"[A-Za-z0-9 ()]{1,80}")
DASHES = (chr(0x2013), chr(0x2014))  # en and em dash


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def https_url(value, field):
    parts = urllib.parse.urlsplit(value)
    require(parts.scheme == "https" and parts.hostname, f"{field} must be an https URL")
    require(not parts.username and not parts.password, f"{field} must not embed credentials")
    return parts


def validate_text(title, description, summary, operation_description):
    """Apply the connector text rules from Microsoft's certification guidance."""
    require(0 < len(title) <= 30, "title must be 1-30 characters")
    require(title[-1].isalnum(), "title must end with an alphanumeric character")
    require(not RESTRICTED_TITLE.search(title), "title contains a restricted word")
    require(30 < len(description) < 500, "description must be 31-499 characters")
    require(not PRODUCT_NAMES.search(description), "description names a Power Platform product")
    require(SUMMARY.fullmatch(summary), "summary must be 80 or fewer alphanumeric, space or parenthesis characters")
    require(operation_description.rstrip().endswith((".", "!", "?")),
            "operation description must be a sentence ending with punctuation")
    require(not PRODUCT_NAMES.search(operation_description), "operation description names a Power Platform product")
    for text in (title, description, summary, operation_description):
        require(not any(dash in text for dash in DASHES), "text must not contain en or em dashes")


def product_name(entry):
    return entry["title"].removesuffix(" MCP")


def swagger(catalog, entry):
    url = https_url(entry["remote_url"], "remote_url")
    require(not url.query and not url.fragment and not url.port, "remote_url must be a plain host and path")
    for field in ("website", "guide", "privacy_policy"):
        if entry.get(field):
            https_url(entry[field], field)
    name = product_name(entry)
    summary = f"{name} MCP server"
    operation = (f"Sends Model Context Protocol messages to the hosted {name} server over "
                 "Streamable HTTP. The agent runtime manages the session, so makers do not "
                 "call this operation directly.")
    validate_text(entry["title"], entry["description"], summary, operation)
    metadata = [{"propertyName": "Website", "propertyValue": entry["website"]}]
    if entry.get("privacy_policy"):
        metadata.append({"propertyName": "Privacy policy", "propertyValue": entry["privacy_policy"]})
    metadata.append({"propertyName": "Categories", "propertyValue": entry["categories"]})
    return {
        "swagger": "2.0",
        "info": {
            "title": entry["title"],
            "description": entry["description"],
            "version": "1.0.0",
            "contact": {"name": catalog["publisher"], "url": catalog["support_url"]},
        },
        "host": url.hostname,
        "basePath": "/",
        "schemes": ["https"],
        "consumes": ["application/json"],
        "produces": ["application/json", "text/event-stream"],
        "paths": {url.path: {"post": {
            "summary": summary,
            "description": operation,
            "operationId": "InvokeMCP",
            "x-ms-agentic-protocol": AGENTIC_PROTOCOL,
            "x-ms-visibility": "advanced",
            "parameters": [{
                "name": "Accept",
                "in": "header",
                "required": True,
                "type": "string",
                "default": ACCEPT,
                "x-ms-summary": "Accept",
                "description": "Media types the MCP server may return.",
                "x-ms-visibility": "internal",
            }],
            "responses": {"200": {"description": "MCP Streamable HTTP response."}},
        }}},
        "securityDefinitions": {},
        "security": [],
        "x-ms-connector-metadata": metadata,
    }


def api_properties(catalog):
    color = catalog["icon_brand_color"]
    require(re.fullmatch(r"#[0-9A-Fa-f]{6}", color), "icon_brand_color must be a hex color")
    require(color.lower() not in {"#ffffff", "#007ee5"}, "icon_brand_color must not be white or the default")
    # stackOwner is deliberately absent: paconn cannot update a connector that carries it.
    return {"properties": {
        "connectionParameters": {},
        "iconBrandColor": color,
        "capabilities": [],
        "policyTemplateInstances": [],
        "publisher": catalog["publisher"],
    }}


def intro(catalog, entry, observed, observed_at):
    name = product_name(entry)
    tools = ", ".join(f"`{tool}`" for tool in observed["tools"])
    lines = [
        f"# {entry['title']}",
        "",
        entry["description"],
        "",
        f"Publisher: {catalog['publisher']}. Packaged on {catalog['packaged_on']}; "
        "not submitted to Microsoft certification or any marketplace.",
        "",
        "## Connection",
        "",
        "| Setting | Value |",
        "| --- | --- |",
        f"| Server URL | `{entry['remote_url']}` |",
        f"| Official MCP Registry entry | `{entry['registry_name']}` |",
        f"| Transport | Streamable HTTP (`x-ms-agentic-protocol: {AGENTIC_PROTOCOL}`) |",
        "| Authentication | None. No API key, OAuth or sign-in. |",
        f"| Product guide | {entry['guide']} |",
    ]
    if entry.get("privacy_policy"):
        lines.append(f"| Privacy policy | {entry['privacy_policy']} |")
    else:
        lines.append("| Privacy policy | None published for this endpoint yet. |")
    lines += [
        "",
        "## Tools",
        "",
        f"A read-only check at {observed_at} (initialize and tools/list only) found server "
        f"version {observed['server_version']} with {len(observed['tools'])} tools: {tools}.",
        "",
        "Copilot Studio reflects tool changes on the server automatically, so this list is "
        "a dated observation, not a contract. Turn off any tool your agent does not need.",
        "",
        "## Recommended agent instructions",
        "",
        f"Add these lines to the agent's instructions so answers keep {name}'s claim boundaries:",
        "",
    ]
    lines += [f"> {sentence}" if index == 0 else f">\n> {sentence}"
              for index, sentence in enumerate(entry["instructions"])]
    lines += ["", "## Known limitations", ""]
    lines += [f"- {item}" for item in entry["limitations"]]
    lines += [
        "- Requests reach the service from Microsoft's connector infrastructure, not from "
        "the user's network, so any limit keyed by source address applies to that shared "
        "infrastructure.",
        "- Not yet imported into a Copilot Studio tenant; the import steps are untested.",
        "",
        "## Setup",
        "",
        "Follow the [import guide](../README.md). Use `apiDefinition.swagger.json` and "
        "`apiProperties.json` from this folder and the shared `../icon.png`.",
        "",
    ]
    text = "\n".join(lines)
    require(not any(dash in text for dash in DASHES), f"intro for {entry['id']} contains a dash")
    return text.encode()


def load():
    catalog = json.loads(CATALOG.read_text())
    receipt = json.loads((BASE / catalog["verification_receipt"]).read_text())
    observed = {row["id"]: row for row in receipt["connectors"]}
    return catalog, receipt, observed


def build():
    catalog, receipt, observed = load()
    ids = [entry["id"] for entry in catalog["connectors"]]
    require(len(ids) == len(set(ids)), "connector ids must be unique")
    require(set(ids) == set(observed), "receipt and catalog must cover the same connectors")
    output = {}
    properties = encode(api_properties(catalog))
    for entry in catalog["connectors"]:
        row = observed[entry["id"]]
        require(row["status"] == "ok", f"unverified remote: {entry['id']}")
        require(row["url"] == entry["remote_url"], f"receipt URL differs: {entry['id']}")
        require(row["registry"]["remote_url"] == entry["remote_url"], f"registry remote differs: {entry['id']}")
        require(row["registry"]["name"] == entry["registry_name"], f"registry name differs: {entry['id']}")
        require(row["registry"]["remote_type"] == "streamable-http", f"registry transport differs: {entry['id']}")
        folder = f"integrations/copilot-studio/{entry['id']}"
        output[f"{folder}/apiDefinition.swagger.json"] = encode(swagger(catalog, entry))
        output[f"{folder}/apiProperties.json"] = properties
        output[f"{folder}/intro.md"] = intro(catalog, entry, row, receipt["observed_at"])
    return output


def _post(url, payload, session=None):
    headers = {"Content-Type": "application/json", "Accept": ACCEPT, "User-Agent": USER_AGENT,
               "MCP-Protocol-Version": PROTOCOL_VERSION}
    if session:
        headers["Mcp-Session-Id"] = session
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=40) as response:
        body = response.read().decode("utf-8", "replace")
        content_type = response.headers.get("Content-Type", "")
        session_id = response.headers.get("Mcp-Session-Id")
        status = response.status
    if "text/event-stream" in content_type:
        events = [line[5:].strip() for line in body.splitlines() if line.startswith("data:")]
        body = events[-1] if events else ""
    return status, content_type.split(";")[0], session_id, (json.loads(body) if body.strip() else None)


def schema_findings(schema, found):
    """Patterns Microsoft lists as Copilot Studio MCP known issues."""
    if isinstance(schema, dict):
        for key in ("exclusiveMinimum", "exclusiveMaximum"):
            if key in schema and not isinstance(schema[key], bool):
                found.add(f"integer {key}")
        if isinstance(schema.get("type"), list):
            found.add("type array")
        if "$ref" in schema:
            found.add("reference type input")
        if "enum" in schema:
            found.add("enum read as string")
        for value in schema.values():
            schema_findings(value, found)
    elif isinstance(schema, list):
        for value in schema:
            schema_findings(value, found)
    return found


def probe(url):
    status, content_type, session, body = _post(url, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                   "clientInfo": {"name": "liquilens-packaging-check", "version": "2026.11.03"}}})
    result = body["result"]
    _post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    tools, cursor = [], None
    for page in range(10):
        params = {"cursor": cursor} if cursor else {}
        listed = _post(url, {"jsonrpc": "2.0", "id": 2 + page, "method": "tools/list", "params": params}, session)[3]
        tools.extend(listed["result"]["tools"])
        cursor = listed["result"].get("nextCursor")
        if not cursor:
            break
    return {
        "http_status": status,
        "content_type": content_type,
        "protocol_version": result["protocolVersion"],
        "server_name": result["serverInfo"]["name"],
        "server_version": result["serverInfo"]["version"],
        "session_header_issued": bool(session),
        "tools": [tool["name"] for tool in tools],
        "copilot_studio_schema_findings": {
            tool["name"]: sorted(found) for tool in tools
            if (found := schema_findings(tool.get("inputSchema") or {}, set()))},
    }


def observe(path):
    catalog = json.loads(CATALOG.read_text())
    gateway = {row["id"]: row["mcp_url"] for row in json.loads(GATEWAY_CATALOG.read_text())["products"]}
    rows = []
    observed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for entry in catalog["connectors"]:
        request = urllib.request.Request(
            REGISTRY.format(name=urllib.parse.quote(entry["registry_name"], safe="")),
            headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=40) as response:
            listing = json.load(response)
        server = listing.get("server", listing)
        official = listing.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
        remotes = server.get("remotes") or [{}]
        row = {"id": entry["id"], "url": entry["remote_url"], "registry": {
            "name": server.get("name"), "version": server.get("version"),
            "is_latest": official.get("isLatest"), "remote_type": remotes[0].get("type"),
            "remote_url": remotes[0].get("url"), "remote_count": len(server.get("remotes") or [])}}
        try:
            row.update(probe(entry["remote_url"]))
            row["status"] = "ok" if row["tools"] else "no_tools"
        except (urllib.error.URLError, KeyError, ValueError, TypeError) as error:
            row["status"] = f"failed: {type(error).__name__}"
        if entry["id"] in gateway:
            try:
                other = probe(gateway[entry["id"]])
                row["central_gateway"] = {
                    "url": gateway[entry["id"]],
                    "same_server_version": other["server_version"] == row.get("server_version"),
                    "same_tool_names": other["tools"] == row.get("tools")}
            except (urllib.error.URLError, KeyError, ValueError, TypeError) as error:
                row["central_gateway"] = {"url": gateway[entry["id"]], "status": f"failed: {type(error).__name__}"}
        rows.append(row)
    receipt = {
        "schema": "liquilens.copilot-studio-mcp-verification.v1",
        "observed_at": observed_at,
        "method": ("Read the latest official MCP Registry entry, then send initialize, "
                   "notifications/initialized and tools/list over Streamable HTTP. No tools/call, "
                   "no credentials, no tenant import."),
        "user_agent": USER_AGENT,
        "requested_protocol_version": PROTOCOL_VERSION,
        "schema_findings_reference": "https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-troubleshooting",
        "copilot_studio_tenant_import_tested": False,
        "connectors": rows,
    }
    Path(path).write_bytes(encode(receipt))
    print(f"Wrote {path}: " + ", ".join(f"{row['id']}={row['status']}" for row in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--observe", metavar="PATH", help="write a read-only network receipt")
    args = parser.parse_args()
    if args.observe:
        observe(args.observe)
        return
    for relative, expected in build().items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit("Stale Copilot Studio connector file: " + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    print("Copilot Studio connector definitions match.")


if __name__ == "__main__":
    main()
