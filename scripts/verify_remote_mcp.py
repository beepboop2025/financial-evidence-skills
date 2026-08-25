#!/usr/bin/env python3
"""Verify the public Financial Evidence MCP before publishing a release."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "integrations" / "financial-evidence-mcp-v0.1.5.json").read_text(
        encoding="utf-8"
    )
)
DEFAULT_URL = "https://liquilens.in/mcp/financial-evidence"


def decode_response(body: bytes, content_type: str) -> dict[str, Any]:
    text = body.decode("utf-8")
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type == "application/json":
        candidate = text
    elif media_type == "text/event-stream":
        candidates = [
            line.removeprefix("data: ")
            for line in text.splitlines()
            if line.startswith("data: ") and line != "data: [DONE]"
        ]
        if len(candidates) != 1:
            raise RuntimeError(
                f"expected one MCP SSE data event, received {len(candidates)}"
            )
        candidate = candidates[0]
    else:
        raise RuntimeError(f"unexpected MCP content type: {content_type!r}")
    payload = json.loads(candidate)
    if not isinstance(payload, dict):
        raise RuntimeError("MCP response must be one JSON-RPC object")
    return payload


def normalize_tools(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list):
        raise RuntimeError("MCP tools/list did not return an array")
    normalized = json.loads(json.dumps(tools))
    for tool in normalized:
        schema = tool.get("inputSchema", {})
        schema.pop("$schema", None)
        if schema.get("properties") == {}:
            schema.pop("properties")
    return normalized


def require_fetch_semantics(result: dict[str, Any]) -> None:
    summary = result.get("structuredContent")
    if not isinstance(summary, dict):
        raise RuntimeError("MCP fetch omitted structuredContent")
    required = {
        "status": "complete",
        "transport_status": "complete",
        "status_semantics": "transport_only",
        "evidence_status": "not_evaluated",
        "carrier_verification": "not_performed",
        "output_status": "complete",
        "output_error": None,
    }
    actual = {name: summary.get(name) for name in required}
    if result.get("isError") is not False or actual != required:
        raise RuntimeError(f"remote MCP semantic boundary differs: {actual!r}")
    sources = summary.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise RuntimeError("remote MCP money-market source count differs")
    source = sources[0]
    digest = source.get("content_sha256", "")
    reported = source.get("source_reported")
    if (
        source.get("product") != "Seiche"
        or source.get("ok") is not True
        or not isinstance(source.get("bytes"), int)
        or source["bytes"] <= 0
        or not isinstance(digest, str)
        or not digest.startswith("sha256:")
        or len(digest) != 71
        or not isinstance(reported, dict)
        or reported.get("adapter") != "seiche_money_markets_v1"
        or not isinstance(reported.get("state"), list)
        or not reported["state"]
    ):
        raise RuntimeError(f"remote MCP provenance receipt differs: {source!r}")
    for field in reported["state"]:
        provenance = field.get("provenance") if isinstance(field, dict) else None
        if provenance != {
            "kind": "source_reported_allowlisted_field",
            "source_url": source.get("source_url"),
            "content_sha256": digest,
        }:
            raise RuntimeError(
                f"remote MCP source-reported provenance differs: {reported!r}"
            )


def _post(
    url: str,
    payload: dict[str, Any],
    *,
    protocol_version: str | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "User-Agent": "Financial-Evidence-release-check/1",
    }
    if protocol_version:
        headers["MCP-Protocol-Version"] = protocol_version
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        decoded = decode_response(
            response.read(), response.headers.get("Content-Type", "")
        )
        response_headers = {
            key.lower(): value for key, value in response.headers.items()
        }
    return decoded, response_headers


def _result(payload: dict[str, Any], request_id: str) -> dict[str, Any]:
    if payload.get("id") != request_id or not isinstance(payload.get("result"), dict):
        raise RuntimeError(f"MCP response differs for {request_id}: {payload!r}")
    return payload["result"]


def verify(url: str, expected_worker_tag: str) -> None:
    initialized, headers = _post(
        url,
        {
            "jsonrpc": "2.0",
            "id": "initialize",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "release-check", "version": "1"},
            },
        },
    )
    if headers.get("x-liquilens-worker-tag") != expected_worker_tag:
        raise RuntimeError(
            "remote Worker tag does not equal current liquilens-site main"
        )
    identity = _result(initialized, "initialize")
    if identity.get("serverInfo") != CONTRACT["serverInfo"]:
        raise RuntimeError(f"remote MCP identity differs: {identity!r}")

    listed, headers = _post(
        url,
        {"jsonrpc": "2.0", "id": "tools", "method": "tools/list", "params": {}},
    )
    if headers.get("x-liquilens-worker-tag") != expected_worker_tag:
        raise RuntimeError("remote Worker changed during release verification")
    tools = _result(listed, "tools").get("tools")
    if normalize_tools(tools) != CONTRACT["tools"]:
        raise RuntimeError("remote and stdio MCP tool contracts differ")

    fetched, headers = _post(
        url,
        {
            "jsonrpc": "2.0",
            "id": "fetch",
            "method": "tools/call",
            "params": {
                "name": "financial_evidence_fetch",
                "arguments": {"topics": ["money-market"]},
            },
        },
        protocol_version="2026-07-28",
    )
    if headers.get("x-liquilens-worker-tag") != expected_worker_tag:
        raise RuntimeError("remote Worker changed during release verification")
    require_fetch_semantics(_result(fetched, "fetch"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--expected-worker-tag", required=True)
    args = parser.parse_args()
    verify(args.url, args.expected_worker_tag)
    print(
        "remote MCP identity, exact tools, output semantics, provenance, and "
        f"Worker tag {args.expected_worker_tag} verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
