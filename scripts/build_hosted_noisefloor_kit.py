#!/usr/bin/env python3
"""Derive a reproducible hosted kit without modifying the verified 0.4.0 archive."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/api/noisefloor"
OUT = ROOT / "docs/api/noisefloor-hosted"
BASE = "https://agents.seiche.info/v1/noisefloor"
NATIVE = "https://api.seiche.info/noisefloor"


def assets():
    original = json.loads((ARCHIVE / "manifest.json").read_text())
    for name, digest in original["files"].items():
        if hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Archival source differs: {name}")
    selected = ("bruno.json", "dyson.bru", "dyson.json", "liquilens.json", "noisefloor.http",
                "noisefloor.postman_collection.json", "palimpsest.json", "riptide.json",
                "seiche.json", "spectral.bru", "trading_agents.json", "undertow.json")
    result = {name: (ARCHIVE / name).read_text().replace(NATIVE, BASE).encode() for name in selected}
    spec = json.loads((ARCHIVE / "openapi.json").read_text())
    paths = {"/healthz", "/v1/capabilities", "/v1/market/assess", "/v1/narrative/triage",
             "/v1/spectral/assess", "/v1/research/dyson"}
    spec["paths"] = {path: value for path, value in spec["paths"].items() if path in paths}
    spec["servers"] = [{"url": BASE}]
    spec["info"]["title"] = "Hosted NoiseFloor research API"
    spec["x-hosted-transport"] = {"native_schema_sha256": original["files"]["openapi.json"],
        "source_commit": original["source_commit"], "request_body_retained_in_demand_metrics": False,
        "native_fallback": False, "archive_url": "../noisefloor/"}
    result["openapi.json"] = (json.dumps(spec, indent=2) + "\n").encode()
    result["hosted_review.py"] = (ROOT / "scripts/templates/noisefloor_hosted_client.py").read_bytes()
    result["README.md"] = f'''# Hosted NoiseFloor client kit

Use the central service at `{BASE}`. Import the Postman or Bruno collection,
use the OpenAPI schema, or run the standard-library Python client:

```sh
python hosted_review.py spectral seiche.json --synthetic --output review.json
python hosted_review.py dyson dyson.json --synthetic --output reference.json
```

The six sample panels and Dyson request are synthetic examples. For your own
permitted input, select one JSON request and omit `--synthetic`. The client
sends that selected JSON to our server; no data is fetched from your files
unless you supply its path. The server counts operation demand and outcomes;
private request bodies and arbitrary text are not stored in demand metrics.
Inspect the [current privacy notice](https://agents.seiche.info/privacy).

An unavailable service remains an error. This client has no local assessment
or native-origin fallback. Outputs preserve source clocks, gaps and research
limits. No operation authorizes a trade or establishes predictive performance.

The [0.4.0 archive](../noisefloor/) retains its original bytes and offline
implementation. This hosted kit derives its input schemas and synthetic panels
from that verified source; it is not a new NoiseFloor algorithm release.
MCP: https://agents.seiche.info/products/noisefloor/mcp
'''.encode()
    result["index.html"] = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hosted NoiseFloor client kit</title><link rel="stylesheet" href="../../styles.css"></head><body><main class="section"><p>FREE HOSTED RESEARCH</p><h1>NoiseFloor through the central service.</h1><p>Send your selected observations for correlation, market or narrative research. Explore a separate synthetic Dyson reference. The included sample panels are synthetic.</p><p><a href="noisefloor-hosted-kit.zip">Download the current kit</a> · <a href="README.md">Setup and data handling</a></p><ul><li><a href="noisefloor.postman_collection.json">Postman</a></li><li><a href="openapi.json">OpenAPI</a></li><li><a href="noisefloor.http">HTTP requests</a></li><li><a href="hosted_review.py">Python client</a></li><li><a href="manifest.json">Source and file hashes</a></li></ul><p>Research requests go to our servers. Operation counts remain separate from optional learning or training contributions. Retain source dates, rights and unavailable values; research output grants no trading authority.</p><p><a href="../noisefloor/">Verified 0.4.0 archive</a> · <a href="https://agents.seiche.info/connect">Connect all hosted products</a></p></main></body></html>'''.encode()
    manifest = {"schema": "noisefloor.hosted-client-kit.v1", "version": "2026-10-13",
        "api_base": BASE, "mcp_url": "https://agents.seiche.info/products/noisefloor/mcp",
        "source_archive": {"version": original["version"], "commit": original["source_commit"],
            "manifest_sha256": hashlib.sha256((ARCHIVE / "manifest.json").read_bytes()).hexdigest()},
        "example_traffic": "synthetic", "native_fallback": False,
        "files": {name: hashlib.sha256(body).hexdigest() for name, body in sorted(result.items())}}
    result["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    result["SHA256SUMS"] = "".join(f"{hashlib.sha256(body).hexdigest()}  {name}\n" for name, body in sorted(result.items())).encode()
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, body in sorted(result.items()):
            info = ZipInfo(name, (2026, 10, 13, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, body)
    result["noisefloor-hosted-kit.zip"] = buffer.getvalue()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, body in assets().items():
        path = OUT / name
        if args.check:
            if not path.exists() or path.read_bytes() != body:
                raise SystemExit(f"Hosted NoiseFloor asset differs: {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    print("Hosted NoiseFloor assets match" if args.check else "Hosted NoiseFloor assets generated")


if __name__ == "__main__":
    main()
