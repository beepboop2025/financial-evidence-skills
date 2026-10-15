#!/usr/bin/env python3
"""Check the separately versioned hosted MCP interfaces before registration."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "integrations/mcp-registry"


async def verify(contract):
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    manifest = json.loads((MANIFESTS / contract["manifest"]).read_text())
    url = manifest["remotes"][0]["url"]
    expected_url = f"https://agents.seiche.info/products/{contract['product']}/mcp"
    if url != expected_url:
        raise ValueError("Registry endpoint differs from the reviewed product")
    async with asyncio.timeout(60):
        async with httpx.AsyncClient(timeout=30, follow_redirects=False, headers={
            "X-Financial-Evidence-Traffic-Class": "synthetic",
            "User-Agent": "Financial-Evidence-registry-verification/1",
        }) as http:
            async with streamable_http_client(url, http_client=http) as (read, write, _):
                async with ClientSession(read, write) as session:
                    identity = await session.initialize()
                    actual = {"name": identity.serverInfo.name, "version": identity.serverInfo.version}
                    if actual != contract["server_info"] or identity.protocolVersion != contract["protocol_version"]:
                        raise ValueError("Hosted MCP identity or protocol changed")
                    inventory = await session.list_tools()
                    tools = [tool.model_dump(mode="json", exclude_none=True) for tool in inventory.tools]
                    digest = hashlib.sha256(json.dumps(tools, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                    if digest != contract["tools_sha256"]:
                        raise ValueError("Hosted MCP tool schemas changed; review before publishing")
                    result = await session.call_tool(contract["first_tool"], {})
                    if result.isError:
                        raise ValueError("Reviewed catalog call failed")
    return {"registry_name": manifest["name"], "registry_version": manifest["version"],
            "url": url, "server_info": actual, "tools_sha256": digest,
            "tool_count": len(tools), "first_tool": contract["first_tool"],
            "result_sha256": hashlib.sha256(result.model_dump_json().encode()).hexdigest(),
            "status": "PASS", "observed_at": datetime.now(timezone.utc).isoformat(),
            "traffic": "synthetic", "independent_adoption": "not_measured"}


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    contracts = json.loads((MANIFESTS / "contracts.json").read_text())["contracts"]
    receipts = await asyncio.gather(*(verify(contract) for contract in contracts))
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps({"schema": "financial-evidence.hosted-registry-check.v1",
                                      "status": "PASS", "interfaces": receipts}, indent=2) + "\n")
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
