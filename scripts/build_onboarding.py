#!/usr/bin/env python3
"""Keep the downloadable connection guide on the same contract as REST and MCP."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from financial_evidence.onboarding import starter_catalog  # noqa: E402


def assets():
    catalog = starter_catalog()
    endpoint = catalog["mcp_url"]
    return {
        "catalog.json": catalog,
        "mcp.json": {"mcpServers": {"financial-evidence": {"type": "http", "url": endpoint}}},
        "vscode.json": {"servers": {"financial-evidence": {"type": "http", "url": endpoint}}},
    }


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
    print("Onboarding catalog and MCP configurations match.")


if __name__ == "__main__":
    main()
