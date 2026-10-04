#!/usr/bin/env python3
"""Exercise a published stdio artifact offline; never import checkout code."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "integrations/financial-evidence-mcp-v0.1.6.json"
TOPICS = [
    "money-market", "capital-market", "china-economy", "bank-risk",
    "market-liquidity", "gift-city", "forex", "gold",
]


def verify(command: list[str]) -> dict:
    contract = json.loads(CONTRACT.read_text())
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "published-artifact-verifier", "version": "1"},
        }},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    calls = [
        ("financial_evidence_topics", {}),
        ("financial_evidence_route", {"topics": TOPICS}),
        ("financial_evidence_route", {"topics": ["gift-city", "forex", "gold"]}),
        ("financial_evidence_route", {"topics": ["gold"], "url": "https://example.com/"}),
        ("financial_evidence_route", {"topics": ["gold"], "scenario": {"quantity": 1}}),
        ("financial_evidence_route", {"topics": ["gold", "gold"]}),
        ("financial_evidence_route", {"topics": ["unknown"]}),
        ("financial_evidence_fetch", {"topics": ["gold"], "url": "https://example.com/"}),
    ]
    for request_id, (name, arguments) in enumerate(calls, start=3):
        messages.append({"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
                         "params": {"name": name, "arguments": arguments}})
    completed = subprocess.run(
        command, input="".join(json.dumps(item) + "\n" for item in messages),
        text=True, capture_output=True, timeout=60, check=True,
    )
    responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    assert len(responses) == 10, "Unexpected output or response count"
    assert [item["id"] for item in responses] == list(range(1, 11))
    by_id = {item["id"]: item for item in responses}
    assert by_id[1]["result"]["serverInfo"] == contract["serverInfo"]
    assert by_id[1]["result"]["protocolVersion"] == "2025-11-25"
    actual_tools = by_id[2]["result"]["tools"]
    assert actual_tools == contract["tools"], "Published tools differ from frozen contract"
    tool_hash = hashlib.sha256(json.dumps(
        actual_tools, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()
    assert tool_hash == contract["toolsSha256"]
    for request_id in (3, 4, 5):
        result = by_id[request_id]["result"]
        assert result["isError"] is False
        assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
    routes = by_id[3]["result"]["structuredContent"]
    assert set(routes["topics"]) == set(TOPICS)
    assert by_id[4]["result"]["structuredContent"] == routes
    selected = by_id[5]["result"]["structuredContent"]["topics"]
    assert set(selected) == {"gift-city", "forex", "gold"}
    assert selected["gift-city"] == selected["gold"]
    assert selected["gold"][0]["url"] == "https://api.seiche.info/api/v2/gift-city"
    assert selected["forex"][0]["url"] == "https://api.seiche.info/api/v2/world-markets?section=forex"
    for sources in routes["topics"].values():
        for source in sources:
            assert source["financial_authority"] == "none"
            assert source["carrier_state"] == "not_published"
            assert "carrier_url" not in source
    expected_errors = {
        6: "unknown arguments: url",
        7: "unknown arguments: scenario",
        8: "topics must contain unique values",
        9: f"topics must use canonical values: {', '.join(TOPICS)}",
        10: "unknown arguments: url",
    }
    for request_id, message in expected_errors.items():
        result = by_id[request_id]["result"]
        assert result["isError"] is True, "Unsafe arguments accepted"
        # A failed network retrieval is not evidence of argument validation.
        expected = {"error": message}
        assert result["structuredContent"] == expected
        assert json.loads(result["content"][0]["text"]) == expected
    return {
        "schema": "financial-evidence.published-artifact-check.v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS", "command": command,
        "server_info": contract["serverInfo"], "tools_sha256": tool_hash,
        "topic_count": len(TOPICS), "topics": TOPICS,
        "checks": ["initialize", "frozen_tools_contract", "all_topic_routes",
                   "new_topic_routes", "shared_gold_gift_source", "strict_arguments"],
        "valid_fetch_requests": 0,
        "scope": "Artifact runtime contract; no source freshness or external adoption claim",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("A published artifact command is required after --")
    receipt = verify(command)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
