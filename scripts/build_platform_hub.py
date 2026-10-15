#!/usr/bin/env python3
"""Render the platform guide and a reproducible, source-only evaluation kit."""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/platforms"


def page(manifest: dict) -> bytes:
    escape = html.escape
    cards = []
    for route in manifest["routes"]:
        search_text = ' '.join([route['name'], route['category'], route['workflow'],
                                route.get('audience', ''), route['id'], route.get('artifact_label', ''),
                                *route.get('products', []), *route.get('search_terms', [])])
        cards.append(f'''<article id="{escape(route['id'])}" data-platform-search="{escape(search_text, quote=True)}">
<p class="eyebrow">{escape(route['category'])}</p><h3>{escape(route['name'])}</h3>
<p>{escape(route['workflow'])}</p><p class="status">{escape(route['status'])}</p>
<p><a href="{escape(route['artifact_url'], quote=True)}">{escape(route['artifact_label'])}</a>
 · <a href="{escape(route['official_source'], quote=True)}">Platform documentation</a></p></article>''')
    return ('''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connect your finance tools | Financial Evidence</title>
<meta name="description" content="Connect sourced financial research to OpenBB, Excel, AI agents and quant workflows. Download examples and inspect platform-specific setup requirements.">
<link rel="canonical" href="https://beepboop2025.github.io/financial-evidence-skills/platforms/">
<link rel="stylesheet" href="../styles.css">
<script type="module" src="platform-search.mjs"></script><script type="module" src="../experience.mjs"></script>
<style>.hero{min-height:auto}.hero main{padding:4rem 0}h1{max-width:22ch;font-size:clamp(2.5rem,6vw,5rem)}.section{padding-block:3rem}.status{font-size:.9rem;color:var(--muted-ink)}article{scroll-margin-top:2rem}article h3{font-size:1.45rem}.quick{display:flex;flex-wrap:wrap;gap:1rem}.grid{align-items:start}.grid article[hidden]{display:none}.platform-search{display:flex;flex-wrap:wrap;align-items:center;gap:.75rem;margin:1.5rem 0 .5rem}.platform-search[hidden]{display:none}.platform-search input{font:inherit;min-width:12rem;max-width:100%;padding:.8rem;border:1px solid currentColor;border-radius:.3rem}.platform-search label{font-weight:600}a:focus-visible,input:focus-visible,button:focus-visible{outline:3px solid #438500;outline-offset:4px}</style>
</head><body><header class="hero"><nav aria-label="Main navigation"><a class="brand" href="../">Financial Evidence</a><div><a href="../start/">Research desk</a><a href="../tools/">Setup guides</a><a href="../partners/">For teams</a></div></nav>
<main><p class="eyebrow">Use your existing workspace</p><h1>Put source-cited research beside your next decision.</h1>
<p class="lede">Bring funding, institution and liquidity evidence into your spreadsheet, research agent or trading research workflow. Start with one useful task and keep the sources with the result.</p>
<div class="actions"><a class="button primary" href="../start/workflows.html?workflow=funding">Try a funding review</a><a class="button" href="finance-platform-kit.zip" download>Download the platform kit</a><a class="button" href="agent-clients.md">Connect an agent</a></div>
<p>Public evidence needs no financial-data API key. Platform accounts, model access and source terms may differ.</p></main></header><aside class="quick-start-ribbon" data-audience-entry><p><strong>One task, your tools.</strong> Open a public example, then use the same evidence through API or MCP.</p><a href="../connect/">Choose your connection</a></aside>
<section class="section"><h2>Choose your tool.</h2><p class="quick"><a href="#openbb">OpenBB</a><a href="#excel">Excel</a><a href="#google-sheets">Google Sheets</a><a href="#colab">Colab</a><a href="#langchain">LangChain</a><a href="#n8n">n8n</a><a href="#node-red">Node-RED</a><a href="#quantconnect">Quant research</a></p>
<p>Ready-to-use connections, source examples and provider evaluation packets are labelled separately below. A provider packet still requires the platform's acceptance.</p>
<div class="platform-search" hidden id="platform-search-controls"><label for="platform-query">Find your tool</label><input id="platform-query" type="search" placeholder="Try Sheets, Python, funding or MCP" aria-controls="platform-list" autocomplete="off"><button class="button" type="button" id="platform-clear">Clear search</button></div>
<p id="platform-count" role="status" aria-live="polite"></p><p id="platform-empty" hidden>No matching tools. Try a product name or clear the search to browse all routes.</p>
<div class="grid" id="platform-list">''' + "\n".join(cards) + '''</div></section>
<section class="section"><h2>Make the next review repeatable.</h2><ol><li>Run one task and inspect the cited source, date, unit and gaps.</li><li>Save the capture and the note it helped you write.</li><li>Return on another working day and compare with that capture.</li></ol>
<p>The kit includes forward-research examples, agent setup instructions and provider evaluation material. Historical observation dates do not establish historical data availability. These connections do not authorize trades or grant redistribution rights.</p>
<p><a href="SHA256SUMS">Download checksums</a> · <a href="routes.json">Machine-readable routes</a> · <a href="../distribution/">Publication status</a></p></section>
<footer><p>LIQUILENS PRIVATE LIMITED · Updated 15 October 2026 · <a href="../privacy/">Privacy</a> · <a href="../terms/">Terms</a> · <a href="../support/">Support</a></p></footer></body></html>
''').encode()


def assets() -> dict[str, bytes]:
    manifest = json.loads((DEST / "routes.json").read_text())
    ids = [route["id"] for route in manifest["routes"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate platform id")
    selected = [ROOT / "LICENSE", ROOT / "pyproject.toml", ROOT / "docs/tools/research_client.py",
                ROOT / "docs/tools/FinancialEvidenceRows.pq",
                ROOT / "docs/tools/FinancialEvidenceSheets.gs", ROOT / "docs/tools/google-sheets.md",
                ROOT / "docs/tools/research_desk.ipynb", ROOT / "docs/tools/mcp.remote.vscode.json",
                ROOT / "docs/HOSTED_MIGRATION.md", ROOT / "scripts/plan_hosted_migration.py",
                ROOT / "docs/api/noisefloor-hosted/noisefloor-hosted-kit.zip",
                ROOT / "docs/tools/mcp.remote.cursor.json", DEST / "platform-search.mjs",
                ROOT / "tests/test_finance_research_forward.py",
                DEST / "agent-clients.md", DEST / "datarade.md", DEST / "routes.json",
                DEST / "pilot-scorecard.csv", DEST / "native-packages.md",
                DEST / "native-packages.json", DEST / "hosted-native-packages.json",
                ROOT / "docs/distribution/langchain-pypi-publication-20261013.json",
                ROOT / "docs/distribution/langchain-pypi-consumer-20261013.json",
                DEST / "colab-verification-20261011.json",
                DEST / "n8n-publication-20261011.json",
                DEST / "n8n-publication-20261013.json",
                DEST / "n8n-creator-submission-20261011.json",
                DEST / "n8n-creator-submission-20261015.json",
                DEST / "activepieces.md", DEST / "activepieces-verification-20261015.json",
                ROOT / "docs/partners/adoption.md", ROOT / "docs/partners/evaluation.json"]
    # Explicit public allowlist: never collect the native runtime or its state.
    flowise_files = ("README.md", "NOTICE.md", "FLOWISE-LICENSE.md", "publication.json",
                     "native-proof.json", "financial-evidence-flowise-marketplace-candidate.json")
    selected.extend(DEST / "flowise" / name for name in flowise_files)
    downloads = {}
    receipt_name = "activepieces-native-20261015.json"
    receipt = json.loads((DEST / receipt_name).read_text())
    if (receipt["schema"] != "financial-evidence.activepieces-native.v1"
            or receipt["status"] != "passed"
            or receipt["package"] != "@moomoo202020/piece-financial-evidence"
            or receipt["version"] != "0.1.0"
            or receipt["filename"] != "moomoo202020-piece-financial-evidence-0.1.0.tgz"
            or {run["action"]: run["status"] for run in receipt["runs"]} != {
                "list_research_datasets": "SUCCEEDED", "get_evidence_page": "SUCCEEDED"}):
        raise ValueError("Activepieces native qualification is incomplete")
    name = "downloads/" + receipt["filename"]
    data = (DEST / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != receipt["sha256"] or len(data) != receipt["bytes"]:
        raise ValueError("Activepieces archive differs from native qualification")
    selected.extend([DEST / receipt_name, DEST / name])
    downloads[name] = data
    downloads[receipt_name] = (DEST / receipt_name).read_bytes()
    publication_name = "activepieces-publication-20261015.json"
    publication = json.loads((DEST / publication_name).read_text())
    if (publication["status"] != "published_bytes_verified"
            or publication["package"] != receipt["package"]
            or publication["version"] != receipt["version"]
            or publication["sha256"] != receipt["sha256"]
            or publication["bytes"] != receipt["bytes"]
            or not publication["anonymous_registry_readback"]
            or publication["registry_signature_verification"] != "passed"):
        raise ValueError("Activepieces publication differs from native qualification")
    selected.append(DEST / publication_name)
    downloads[publication_name] = (DEST / publication_name).read_bytes()
    registry_name = "activepieces-registry-20261015.json"
    registry = json.loads((DEST / registry_name).read_text())
    if (registry["status"] != "passed"
            or registry["installation"] != "registry_via_native_install_api"
            or registry["metadata"]["packageType"] != "REGISTRY"
            or any(registry[k] != publication[k] for k in ("package", "version", "sha256", "bytes"))
            or not registry["registry_verification"]["public_artifact_bytes_verified"]
            or registry["registry_verification"]["publication_receipt_sha256"] != hashlib.sha256((DEST / publication_name).read_bytes()).hexdigest()
            or {run["action"]: run["status"] for run in registry["runs"]} != {
                "list_research_datasets": "SUCCEEDED", "get_evidence_page": "SUCCEEDED"}):
        raise ValueError("Activepieces registry qualification differs from publication")
    selected.append(DEST / registry_name)
    downloads[registry_name] = (DEST / registry_name).read_bytes()
    package_sets = {
        "native-packages.json": {"n8n-nodes-financial-evidence-0.1.0.tgz", "financial_evidence-0.1.1.difypkg"},
        "hosted-native-packages.json": {"n8n-nodes-financial-evidence-0.1.1.tgz", "financial_evidence-0.1.2.difypkg"},
    }
    for manifest_name, expected_names in package_sets.items():
        native = json.loads((DEST / manifest_name).read_text())
        if {item["filename"] for item in native["packages"]} != expected_names or len(native["packages"]) != 2:
            raise ValueError(f"unexpected native package set: {manifest_name}")
        for item in native["packages"]:
            name = "downloads/" + item["filename"]
            path = DEST / name
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"] or len(data) != item["bytes"]:
                raise ValueError(f"Native package checksum or size mismatch: {name}")
            selected.append(path)
            downloads[name] = data
    # Only authored source formats. Never include environments, credentials,
    # runtime captures, debug keys or dependency trees in a public download.
    for folder in ("src/financial_evidence", "integrations/finance-research", "integrations/finance-desktop",
                   "integrations/node-red", "docs/automations/node-red",
                   "docs/distribution/provider-packets-20261011", "integrations/activepieces"):
        for current, directories, files in os.walk(ROOT / folder):
            directories[:] = sorted(name for name in directories if not name.startswith(".")
                                    and name not in {"node_modules", "__pycache__", "captures", "artifacts", "dist"})
            for name in sorted(files):
                path = Path(current) / name
                if (not name.startswith(".") and path.suffix in
                        {".md", ".py", ".json", ".html", ".js", ".mjs", ".cjs", ".css", ".svg", ".txt", ".csv", ".ts"}):
                    selected.append(path)
    readme = b"""# Financial Evidence platform kit

Start at docs/platforms/agent-clients.md or choose a platform in routes.json.
Forward quant examples: integrations/finance-research/README.md.
Desktop candidate: integrations/finance-desktop/README.md.
Institutional packets: docs/distribution/provider-packets-20261011/README.md.
Native automation candidates and receipts: docs/platforms/native-packages.md.
Existing Flowise 3.1.4 users: docs/platforms/flowise/README.md (upstream is EOL).
Python/Colab research notebook, Google Sheets and Power Query: docs/tools/.
Node-RED manual research flow: docs/automations/node-red/.
The shared Python package source and pyproject.toml are included, so the setup
commands in the forward-research README work from this extracted directory.

This is an evaluation kit, not a claim of marketplace acceptance or adoption.
Our software licence is in LICENSE. Flowise-derived template metadata retains
the upstream licence and attribution in docs/platforms/flowise/.
Upstream data retains its source-specific terms.
Retain observation and availability clocks; never backfill current captures into
historical decisions. No broker credentials or order execution is included.
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        entries = {str(path.relative_to(ROOT)): path.read_bytes() for path in selected}
        entries["README.md"] = readme
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    result = {"index.html": page(manifest), "finance-platform-kit.zip": buffer.getvalue(),
              "platform-search.mjs": (DEST / "platform-search.mjs").read_bytes(), **downloads}
    result["hosted-native-packages.json"] = (DEST / "hosted-native-packages.json").read_bytes()
    result["colab-verification-20261011.json"] = (DEST / "colab-verification-20261011.json").read_bytes()
    result["n8n-publication-20261011.json"] = (DEST / "n8n-publication-20261011.json").read_bytes()
    result["n8n-creator-submission-20261011.json"] = (DEST / "n8n-creator-submission-20261011.json").read_bytes()
    result["n8n-creator-submission-20261015.json"] = (DEST / "n8n-creator-submission-20261015.json").read_bytes()
    result.update({f"flowise/{name}": (DEST / "flowise" / name).read_bytes() for name in flowise_files})
    for name in ("index.html", "panel.css", "panel.mjs", "reference-fx.mjs"):
        result[f"desktop/{name}"] = (ROOT / "integrations/finance-desktop" / name).read_bytes()
    result["SHA256SUMS"] = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n"
                                  for name, data in sorted(result.items())).encode()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, data in assets().items():
        path = DEST / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"Generated platform asset differs: {name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Platform assets match source" if args.check else "Platform assets generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
