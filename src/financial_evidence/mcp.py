"""Dependency-free stdio MCP server for the financial-evidence router."""

from __future__ import annotations

import json
import sys
from typing import Any

from . import __version__
from .core import ROUTES, build_packet, route_manifest


LEGACY_PROTOCOL = "2025-11-25"
MODERN_PROTOCOL = "2026-07-28"
SERVER_INFO = {"name": "financial-evidence", "version": __version__}
TOOL_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}
TOPIC_SCHEMA = {
    "type": "array",
    "items": {"type": "string", "enum": list(ROUTES)},
    "minItems": 1,
    "uniqueItems": True,
}


TOOLS = [
    {
        "name": "financial_evidence_topics",
        "title": "List Financial Evidence Topics",
        "description": "List supported topics and their fixed public product routes without network access.",
        "inputSchema": {"type": "object", "additionalProperties": False},
        "annotations": TOOL_ANNOTATIONS,
    },
    {
        "name": "financial_evidence_route",
        "title": "Route Financial Research",
        "description": "Resolve one or more financial research topics to fixed public evidence sources without fetching them.",
        "inputSchema": {
            "type": "object",
            "properties": {"topics": TOPIC_SCHEMA},
            "required": ["topics"],
            "additionalProperties": False,
        },
        "annotations": TOOL_ANNOTATIONS,
    },
    {
        "name": "financial_evidence_fetch",
        "title": "Fetch Financial Evidence",
        "description": "Fetch bounded read-only JSON evidence from LiquiLens, Undertow, Seiche, and Palimpsest. Missing evidence remains unavailable, never zero or calm.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topics": TOPIC_SCHEMA,
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4_194_304,
                    "default": 1_048_576,
                },
                "timeout": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "maximum": 30,
                    "default": 10,
                },
            },
            "required": ["topics"],
            "additionalProperties": False,
        },
        "annotations": TOOL_ANNOTATIONS,
    },
]


def _tool_result(value: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(value, ensure_ascii=False, sort_keys=True),
            }
        ],
        "structuredContent": value,
        "isError": is_error,
    }


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "financial_evidence_topics":
        if arguments:
            raise ValueError("financial_evidence_topics accepts no arguments")
        return _tool_result(route_manifest())
    if name == "financial_evidence_route":
        return _tool_result(route_manifest(arguments.get("topics", [])))
    if name == "financial_evidence_fetch":
        max_bytes = arguments.get("max_bytes", 1_048_576)
        timeout = arguments.get("timeout", 10.0)
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool):
            raise ValueError("max_bytes must be an integer")
        if not 1 <= max_bytes <= 4_194_304:
            raise ValueError("max_bytes must be between 1 and 4194304")
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
            raise ValueError("timeout must be a number")
        if not 0 < timeout <= 30:
            raise ValueError("timeout must be greater than 0 and at most 30")
        packet = build_packet(
            arguments.get("topics", []),
            max_bytes=max_bytes,
            timeout=float(timeout),
        )
        return _tool_result(packet, is_error=packet["status"] == "unavailable")
    raise LookupError(f"unknown tool {name!r}")


def dispatch(message: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch one JSON-RPC message for modern and legacy MCP clients."""

    if message.get("jsonrpc") != "2.0":
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {"code": -32600, "message": "Invalid Request"},
        }
    if "id" not in message:
        return None
    request_id = message["id"]
    method = message.get("method")
    try:
        if method == "server/discover":
            result = {
                "resultType": "complete",
                "supportedVersions": [MODERN_PROTOCOL, LEGACY_PROTOCOL],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": (
                    "Use route before fetch when source selection matters. "
                    "Treat unavailable evidence as unavailable, never as zero."
                ),
            }
        elif method == "initialize":
            requested = message.get("params", {}).get("protocolVersion")
            result = {
                "protocolVersion": (
                    requested
                    if requested in {LEGACY_PROTOCOL, MODERN_PROTOCOL}
                    else LEGACY_PROTOCOL
                ),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": (
                    "Use route before fetch when source selection matters. "
                    "Treat unavailable evidence as unavailable, never as zero."
                ),
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = message.get("params")
            if not isinstance(params, dict):
                raise ValueError("tools/call params must be an object")
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise ValueError("tools/call requires a name and object arguments")
            result = call_tool(name, arguments)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "Method not found"},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except LookupError as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32602, "message": str(exc)},
        }
    except (TypeError, ValueError) as exc:
        if method == "tools/call":
            result = _tool_result({"error": str(exc)}, is_error=True)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32602, "message": str(exc)},
        }


def serve(stdin=None, stdout=None) -> int:
    """Serve newline-delimited JSON-RPC over stdio."""

    source = stdin or sys.stdin
    destination = stdout or sys.stdout
    for raw_line in source:
        if not raw_line.strip():
            continue
        try:
            message = json.loads(raw_line)
            if not isinstance(message, dict):
                raise ValueError("message must be an object")
            response = dispatch(message)
        except (json.JSONDecodeError, ValueError) as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
        if response is not None:
            destination.write(
                json.dumps(
                    response,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
            destination.flush()
    return 0


def main() -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
