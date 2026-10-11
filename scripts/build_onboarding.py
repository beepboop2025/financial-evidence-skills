#!/usr/bin/env python3
"""Keep the downloadable connection guide on the same contract as REST and MCP."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from financial_evidence.onboarding import starter_catalog  # noqa: E402


def assets():
    catalog = starter_catalog()
    endpoint = catalog["mcp_url"]
    output = {
        "catalog.json": catalog,
        "mcp.json": {"mcpServers": {"financial-evidence": {"type": "http", "url": endpoint}}},
        "vscode.json": {"servers": {"financial-evidence": {"type": "http", "url": endpoint}}},
    }
    native = json.loads((ROOT / "docs/connect/native-connections.json").read_text())
    for product in native["products"]:
        output[product["id"] + ".mcp.json"] = {
            "mcpServers": {product["id"]: {"type": "http", "url": product["mcp_url"]}}
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, value in assets().items():
        path = ROOT / "docs/connect" / name
        expected = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            if not path.exists() or path.read_text() != expected:
                raise SystemExit("Stale onboarding artifact: " + str(path))
        else:
            path.parent.mkdir(exist_ok=True)
            path.write_text(expected)
    products = json.loads((ROOT / "docs/connect/native-connections.json").read_text())["products"]
    cards = []
    for product in products:
        p = {key: html.escape(value, quote=True) for key, value in product.items()}
        cards.append(f'<article><h3>{p["name"]}</h3><p>{p["scope"]}</p><pre><code>{p["mcp_url"]}</code></pre><div><a href="{p["guide_url"]}">API and research guide</a><a href="{p["id"]}.mcp.json" download>MCP config</a></div></article>')
    fragment = '<div class="native-connection-grid">' + ''.join(cards) + '</div>'
    path = ROOT / "docs/connect/index.html"
    page = path.read_text()
    start, end = '<!-- NATIVE-CONNECTIONS:START -->', '<!-- NATIVE-CONNECTIONS:END -->'
    before, rest = page.split(start, 1)
    current, after = rest.split(end, 1)
    expected = '\n' + fragment + '\n'
    if args.check and current != expected:
        raise SystemExit("Stale native connection cards")
    if not args.check:
        path.write_text(before + start + expected + end + after)
    print("Onboarding catalog and MCP configurations match.")


if __name__ == "__main__":
    main()
