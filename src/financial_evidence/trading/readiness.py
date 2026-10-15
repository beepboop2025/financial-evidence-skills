"""Anonymous connection diagnostics, never an input or order admission policy."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math

from ..hosted import platform_base

# One reviewed public read per endpoint; no execution, subscription or quota-heavy
# proof tools. Keep this independent of ambient network and broker credentials.
PROBES = {
    "seiche": ("data_health", {}),
    "liquilens": ("institution_research_coverage", {"scope": "dossiers", "limit": 3}),
    "undertow": ("liquidity_tiers", {}),
    "financial-evidence": ("financial_evidence_agent_query", {
        "dataset": "money_markets", "entity": "USD", "limit": 1}),
}
MAX_BYTES = 2_097_152
MAX_MONITOR_AGE = 900
HEADERS = {"X-Financial-Evidence-Traffic-Class": "synthetic",
           "User-Agent": "Financial-Evidence-readiness/1"}


def _encoded(value):
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(body) > MAX_BYTES:
        raise ValueError("response_too_large")
    return body


async def probe_mcp(url, tool, arguments, timeout):
    """Use the actual MCP SDK, including session setup, pagination and teardown."""
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False,
                                 headers=HEADERS) as http:
        async with streamable_http_client(url, http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                server = await session.initialize()
                tools, cursor, seen = {}, None, set()
                for _ in range(8):
                    page = await session.list_tools(cursor=cursor)
                    _encoded(page.model_dump(mode="json", exclude_none=True))
                    for item in page.tools:
                        if item.name in tools or len(tools) >= 256:
                            raise ValueError("invalid_tool_inventory")
                        tools[item.name] = item
                    cursor = page.nextCursor
                    if not cursor:
                        break
                    if cursor in seen:
                        raise ValueError("repeated_tool_cursor")
                    seen.add(cursor)
                else:
                    raise ValueError("tool_inventory_page_limit")
                if tool not in tools or tools[tool].inputSchema.get("type") != "object":
                    return {"status": "failed", "reason": "required_tool_missing_or_invalid"}
                result = await session.call_tool(tool, arguments)
                encoded = _encoded(result.model_dump(mode="json", exclude_none=True))
                if result.isError:
                    return {"status": "failed", "reason": "mcp_tool_error"}
                if not result.content and result.structuredContent is None:
                    return {"status": "failed", "reason": "empty_tool_result"}
                return {"status": "passed", "server": server.serverInfo.model_dump(mode="json"),
                        "protocol_version": server.protocolVersion, "tool_count": len(tools),
                        "result_sha256": hashlib.sha256(encoded).hexdigest(),
                        "result_bytes": len(encoded)}


async def fetch_status(url, timeout):
    import httpx

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False,
                                 headers=HEADERS) as http:
        async with http.stream("GET", url) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ValueError("response_too_large")
    return json.loads(body)


def summarize_sources(document, products, now):
    """A current monitor is not complete source coverage or a rights grant."""
    _encoded(document)
    if not isinstance(document, dict) or document.get("schema") != "seiche-agent-network.freshness.v1":
        raise ValueError("invalid_source_monitor")
    rows = document.get("products")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("invalid_source_monitor")
    evaluated_at = document.get("evaluated_at")
    evaluated = datetime.fromisoformat(evaluated_at.replace("Z", "+00:00"))
    if evaluated.tzinfo is None:
        raise ValueError("monitor_clock_requires_timezone")
    age = (now - evaluated).total_seconds()
    reported_age = document.get("monitor_age_seconds")
    current = (document.get("monitor_current") is True and -60 <= age <= MAX_MONITOR_AGE
               and type(reported_age) in {int, float} and math.isfinite(reported_age)
               and 0 <= reported_age <= MAX_MONITOR_AGE)
    selected = []
    for product in products:
        matches = [row for row in rows if row.get("product") == product]
        if len(matches) != 1 or matches[0].get("freshness") not in {"fresh", "stale", "restricted", "unknown"}:
            raise ValueError("missing_or_invalid_product_status")
        row = matches[0]
        selected.append({key: row[key] for key in (
            "product", "transport", "tool", "freshness", "scope", "use_boundary",
            "coverage", "reasons", "rights", "source_reason_counts", "critical_subset") if key in row})
    return {"status": "current" if current else "stale_or_unknown",
            "evaluated_at": evaluated_at, "monitor_age_seconds": reported_age,
            "locally_evaluated_age_seconds": round(age, 3),
            "max_monitor_age_seconds": MAX_MONITOR_AGE,
            "products": selected, "scope": "inspected_source_rows_only"}


async def check_readiness(*, platform_url=None, products=None, timeout=30,
                          probe=probe_mcp, status_fetcher=fetch_status, now=None):
    """Check the selected integration within one deadline per concurrent request."""
    base = platform_base(platform_url)
    selected = list(PROBES) if products is None else list(dict.fromkeys(products))
    if not selected or any(product not in PROBES for product in selected):
        raise ValueError("choose a supported product")
    if type(timeout) not in {int, float} or not 0 < timeout <= 120:
        raise ValueError("timeout must be between zero and 120 seconds")

    async def connection(product):
        tool, arguments = PROBES[product]
        url = base + f"/products/{product}/mcp"
        try:
            result = await asyncio.wait_for(probe(url, tool, dict(arguments), timeout), timeout)
            if not isinstance(result, dict) or result.get("status") not in {"passed", "failed"}:
                raise ValueError("invalid_probe_result")
        except (ImportError, ModuleNotFoundError):
            result = {"status": "failed", "reason": "install_workspace_extra"}
        except asyncio.TimeoutError:
            result = {"status": "failed", "reason": "timeout"}
        except Exception:
            # Exception strings can contain upstream bodies or caller secrets.
            result = {"status": "failed", "reason": "connection_or_protocol_error"}
        return {"product": product, "endpoint": url, "tool": tool, **result}

    async def sources():
        try:
            document = await asyncio.wait_for(status_fetcher(base + "/v1/data-status", timeout), timeout)
            return summarize_sources(document, selected, now or datetime.now(timezone.utc))
        except (ImportError, ModuleNotFoundError):
            reason = "install_workspace_extra"
        except asyncio.TimeoutError:
            reason = "timeout"
        except Exception:
            reason = "unavailable_or_invalid_source_monitor"
        return {"status": "unavailable", "reason": reason, "products": []}

    *connections, source_monitor = await asyncio.gather(
        *(connection(product) for product in selected), sources())
    return {"schema": "financial-evidence.integration-readiness.v1",
            "checked_at": (now or datetime.now(timezone.utc)).isoformat(),
            "connection_status": "passed" if all(c["status"] == "passed" for c in connections) else "failed",
            "connections": connections, "source_monitor": source_monitor,
            "traffic_class": "synthetic", "authentication": "anonymous",
            "input_eligibility": "not_evaluated", "execution_authority": "none",
            "external_adoption": "not_measured", "coverage_complete": False,
            "interpretation": "Connection success and a current monitor do not establish eligible trading inputs, execution readiness or adoption."}


def exit_code(report):
    return 0 if report["connection_status"] == "passed" and report["source_monitor"]["status"] == "current" else 2
