#!/usr/bin/env python3
"""Record the official MCP Registry remotes that the client plugin manifests carry.

The plugin build reads a committed, dated snapshot so that it stays offline and
reproducible. Run this script to take a new live reading, then point
"registry_snapshot" in docs/plugins/client-manifests.json at the new file and
update any canonical URL that changed:

    python3 scripts/snapshot_registry_remotes.py --output docs/plugins/registry-remotes-YYYYMMDD.json
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs/plugins/client-manifests.json"
REGISTRY = "https://registry.modelcontextprotocol.io/v0/servers"


def read_server(name: str) -> dict:
    query = REGISTRY + "?" + urlencode({"search": name, "version": "latest"})
    request = Request(query, headers={"Accept": "application/json", "User-Agent": "financial-evidence-skills registry snapshot"})
    with urlopen(request, timeout=30) as response:
        body = json.load(response)
    rows = [row for row in body.get("servers", []) if row["server"]["name"] == name]
    if len(rows) != 1:
        raise SystemExit(f"Expected one latest registry entry for {name}, found {len(rows)}")
    server, meta = rows[0]["server"], rows[0]["_meta"]["io.modelcontextprotocol.registry/official"]
    return {
        "name": name,
        "query": query,
        "version": server["version"],
        "title": server.get("title"),
        "status": meta["status"],
        "is_latest": meta["isLatest"],
        "published_at": meta["publishedAt"],
        "remotes": [{"type": remote["type"], "url": remote["url"]} for remote in server.get("remotes", [])],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    names = [row["registry_server"] for row in json.loads(TABLE.read_text())["products"]]
    read_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = {
        "schema": "liquilens.registry-remotes.v1",
        "read_at": read_at,
        "registry": REGISTRY,
        "method": "One GET per server name with version=latest; the entry whose name matches exactly.",
        "servers": [read_server(name) for name in names],
    }
    args.output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {args.output} ({len(names)} servers, read {read_at}).")


if __name__ == "__main__":
    main()
