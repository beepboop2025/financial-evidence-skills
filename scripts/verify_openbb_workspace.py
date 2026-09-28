#!/usr/bin/env python3
"""Verify a running OpenBB backend using actual HTTP and MCP requests."""

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def verify(base_url):
    base_url = base_url.rstrip("/")
    headers = {
        "User-Agent": "Financial-Evidence-Operator-Verification/1.0",
        "X-Liquilens-Traffic-Class": "synthetic",
    }

    def get(path):
        with urllib.request.urlopen(
            urllib.request.Request(base_url + path, headers=headers), timeout=45
        ) as response:
            return json.load(response)

    def rpc(method, params=None):
        request = urllib.request.Request(
            base_url + "/mcp",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params or {},
                }
            ).encode(),
            headers={
                **headers,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-11-25",
            },
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.load(response)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["result"]

    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "operator_traffic": True,
        "backend": base_url,
        "datasets": {},
    }
    assert get("/healthz")["status"] == "ok"
    definitions = get("/widgets.json")
    app = get("/apps.json")[0]
    assert all(
        widget["i"] in definitions
        for tab in app["tabs"].values()
        for widget in tab["layout"]
    )
    for dataset in get("/api/v1/datasets"):
        started = time.monotonic()
        result = get(
            "/api/v1/query?"
            + urllib.parse.urlencode({"dataset": dataset["id"], "limit": 2})
        )
        assert result["returned_rows"] == len(result["results"]) <= 2
        assert result["evidence_status"] == "not_evaluated"
        assert result["carrier_verification"] == "not_performed"
        report["datasets"][dataset["id"]] = {
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "total_rows": result["total_rows"],
            "transport_status": result["transport_status"],
            "diagnostic_count": len(result["diagnostics"]),
        }
    report["mcp_server"] = rpc(
        "initialize",
        {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "operator-verification", "version": "1"},
        },
    )["serverInfo"]
    tools = rpc("tools/list")["tools"]
    assert len(tools) == 5 and all(
        tool["annotations"]["readOnlyHint"] for tool in tools
    )
    result = rpc(
        "tools/call",
        {
            "name": "financial_evidence_query",
            "arguments": {"dataset": "money_markets", "limit": 2},
        },
    )
    assert not result.get("isError"), result
    assert result["structuredContent"]["dataset"] == "money_markets"
    report["tool_count"] = len(tools)
    report["widget_count"] = len(definitions)
    report["contract_checks"] = "passed"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:6900")
    args = parser.parse_args()
    print(json.dumps(verify(args.url), indent=2))
