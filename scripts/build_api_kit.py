#!/usr/bin/env python3
"""Build bounded, read-only API client imports from the published contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/api"
BASE = "https://api.seiche.info/openbb"
BOUNDARY = (
    "Keep source dates, units, nulls, rights and diagnostics with every result. "
    "HTTP success is transport only. next_offset means more rows exist; use the "
    "research kit for a complete, source-consistent capture."
)
TABLE_TESTS = [
    'const body = pm.response.json();',
    'pm.test("Evidence boundary is explicit", function () {',
    '  pm.expect(body.schema).to.eql("liquidity-lab.openbb-table.v1");',
    '  pm.expect(body.evidence_status).to.eql("not_evaluated");',
    '  pm.expect(body.carrier_verification).to.eql("not_performed");',
    '  pm.expect(body.transport_status).to.be.a("string");',
    '  pm.expect(body.sources).to.be.an("array");',
    '  pm.expect(body.diagnostics).to.be.an("array");',
    '});',
    'pm.test("Pagination is explicit", function () {',
    '  pm.expect(body.returned_rows).to.eql(body.results.length);',
    '  pm.expect(body).to.have.property("next_offset");',
    '  pm.expect(body.total_rows).to.be.at.least(body.returned_rows);',
    '});',
    'console.info("Transport:", body.transport_status, "Next offset:", body.next_offset);',
]


def examples(spec):
    """Only explicit public reads enter the importable collection."""
    params = spec["paths"]["/api/v1/query"]["get"]["parameters"]
    datasets = next(p["schema"]["enum"] for p in params if p["name"] == "dataset")
    rows = [
        ("Release identity", "/api/v1/release", {}, False),
        ("Dataset coverage", "/api/v1/datasets", {}, False),
        ("Source status and clocks", "/api/v1/sources", {}, True),
    ]
    rows += [(name.replace("_", " ").title(), "/api/v1/query",
              {"dataset": name, "limit": "5", "offset": "0"}, True)
             for name in datasets]
    rows += [("Funding review", "/api/v1/funding-review", {}, False),
             ("Agent research review", "/api/v1/agent-review", {"limit": "3"}, False)]
    for _, path, _, _ in rows:
        if "get" not in spec["paths"].get(path, {}):
            raise ValueError(f"Example is missing from the public read contract: {path}")
    return rows


def build(out=OUT):
    spec = json.loads((out / "openapi.json").read_text())
    if spec["servers"][0]["url"] != BASE:
        raise ValueError("Distribution imports must target the explicit public API origin")
    items, bruno, http = [], [], []
    for index, (name, path, query, table) in enumerate(examples(spec), 1):
        suffix = path + ("?" + urlencode(query) if query else "")
        checks = ['pm.test("HTTP response succeeded", function () { pm.response.to.have.status(200); });']
        checks += TABLE_TESTS if table else []
        items.append({"name": name, "request": {
            "method": "GET", "auth": {"type": "noauth"},
            "header": [{"key": "Accept", "value": "application/json"},
                       {"key": "X-Liquilens-Traffic-Class", "value": "{{traffic_class}}"}],
            "url": "{{base_url}}" + suffix,
            "description": BOUNDARY,
        }, "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": checks}}]})
        bruno.append((f"{index:02d}-{name.lower().replace(' ', '-')}.bru",
                      f"meta {{\n  name: {name}\n  type: http\n  seq: {index}\n}}\n\n"
                      f"get {{\n  url: {BASE}{suffix}\n  body: none\n  auth: none\n}}\n\n"
                      "headers {\n  Accept: application/json\n  X-Liquilens-Traffic-Class: {{traffic_class}}\n}\n\n"
                      "tests {\n  test(\"HTTP response succeeded\", function () {\n    expect(res.getStatus()).to.equal(200);\n  });\n}\n\n"
                      f"docs {{\n  {BOUNDARY}\n}}\n"))
        http.append(f"### {name}\n# {BOUNDARY}\nGET {BASE}{suffix}\nAccept: application/json\nX-Liquilens-Traffic-Class: developer\n")
    collection = {
        "info": {"name": "LiquiLens Financial Evidence Research API", "description": BOUNDARY + " Public reads; no API key. Current public and private interfaces: https://beepboop2025.github.io/financial-evidence-skills/agents/system.json . Setup guide: https://liquilens.in/agents/infrastructure/ . Private runtimes are separately installed and grant no public execution authority. Operator validation must set traffic_class=synthetic. These headers are diagnostic labels, not verified customer identities.",
                 "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "variable": [{"key": "base_url", "value": BASE},
                     {"key": "traffic_class", "value": "developer"}],
        "item": items,
    }
    (out / "financial-evidence.postman_collection.json").write_text(json.dumps(collection, indent=2) + "\n")
    (out / "financial-evidence.http").write_text("\n".join(http))
    folder = out / "bruno"
    folder.mkdir(exist_ok=True)
    (folder / "bruno.json").write_text(json.dumps({"version": "1", "name": "Financial Evidence", "type": "collection", "ignore": ["node_modules", ".git"]}, indent=2) + "\n")
    (folder / "collection.bru").write_text("vars:pre-request {\n  traffic_class: developer\n}\n")
    for name, content in bruno:
        (folder / name).write_text(content)
    paths = [out / "openapi.json", out / "financial-evidence.postman_collection.json",
             out / "financial-evidence.http", out / "README.md", *sorted(folder.glob("*.bru")), folder / "bruno.json"]
    manifest = {"schema": "financial-evidence.api-kit.v1", "request_count": len(items),
                "dataset_count": len(items) - 5, "api_base": BASE,
                "source_observation": spec["x-source-observation"],
                "files": {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with ZipFile(out / "api-kit.zip", "w", compression=ZIP_DEFLATED) as archive:
        for path in [*paths, out / "manifest.json"]:
            info = ZipInfo(str(path.relative_to(out)), date_time=(2026, 10, 7, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    return manifest


if __name__ == "__main__":
    result = build()
    print(json.dumps({"request_count": result["request_count"], "dataset_count": result["dataset_count"]}))
