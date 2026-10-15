#!/usr/bin/env python3
"""Print a credential-free migration plan; never rewrite the supplied config."""
import argparse
import hashlib
import json
from pathlib import Path

BASE = "https://agents.seiche.info"
URLS = {
    "https://api.seiche.info/riptide/api/v1/allocation": BASE + "/v1/data/riptide.allocation",
    "https://api.seiche.info/api/gauge": BASE + "/v1/data/seiche.gauge",
    "https://api.seiche.info/api/public": BASE + "/v1/data/seiche.public",
    "https://api.seiche.info/undertow/board.json": BASE + "/v1/data/undertow.board",
    "https://api.seiche.info/api/v2/corpus/v1/catalog": BASE + "/v1/corpus/v1/catalog",
    "https://api.seiche.info/api/v2/research-data/mcp": BASE + "/products/research-data/mcp",
    "https://api.seiche.info/api/v2/corpus/mcp": BASE + "/products/seiche-market-corpus/mcp",
    "https://api.seiche.info/api/v2/research-data": BASE + "/v1/source-data",
    "https://api.liquilens.in/api/experimental/v1/banking": BASE + "/v1/banking",
    "https://api.seiche.info/mcp": BASE + "/products/seiche/mcp",
    "https://api.liquilens.in/mcp": BASE + "/products/liquilens/mcp",
    "https://www.narcoscope.com/mcp": BASE + "/products/narcoscope/mcp",
    "https://myquantdoesntspeakenglish.com/mcp": BASE + "/products/myquant-editorial/mcp",
    "https://myquant-app.vercel.app/mcp": BASE + "/products/myquant-app/mcp",
    "https://trade-safety.liquilens.in/mcp": BASE + "/products/trade-safety/mcp",
    "https://api.seiche.info/openbb/mcp": BASE + "/products/financial-evidence/mcp",
    "https://api.seiche.info/openbb": BASE + "/v1/research",
    "https://api.seiche.info/noisefloor": BASE + "/v1/noisefloor",
}
for product in ("undertow", "palimpsest", "noisefloor", "riptide"):
    URLS[f"https://api.seiche.info/{product}/mcp"] = BASE + f"/products/{product}/mcp"


def plan(data):
    counts = {}
    credential_blocks = 0
    unsupported = 0
    def inspect(value):
        nonlocal credential_blocks, unsupported
        if isinstance(value, dict):
            if any(str(key).lower() in {"headers", "authorization", "token", "apikey", "api_key", "env"} for key in value):
                credential_blocks += 1
            for key, item in value.items():
                if key in {"url", "baseUrl", "base_url", "api_base"} and isinstance(item, str):
                    if item in URLS:
                        counts[item] = counts.get(item, 0) + 1
                    elif item.startswith(("http://", "https://")) and not item.startswith(BASE + "/"):
                        unsupported += 1
                elif isinstance(item, (list, dict)) and str(key).lower() not in {"headers", "authorization", "token", "apikey", "api_key", "env"}:
                    inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    inspect(data)
    return {"schema": "financial-evidence.hosted-migration-plan.v1", "writes_performed": False,
            "replacements": [{"from": old, "to": URLS[old], "occurrences": count} for old, count in sorted(counts.items())],
            "credential_blocks_require_review": credential_blocks, "unmapped_urls": unsupported,
            "credential_action": "Do not transfer native subscriber, browser or API credentials. Public reads need none; create a separate scoped workspace credential for attribution.",
            "coverage": "Exact reviewed URL matches only. Pinned packages, commands and custom adapters require their release-specific upgrade instructions."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with args.config.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        parser.error("Config exceeds 1 MiB")
    result = plan(json.loads(raw))
    result["config_sha256"] = hashlib.sha256(raw).hexdigest()
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
