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
        cards.append(f'''<article id="{escape(route['id'])}">
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
<style>.hero{min-height:auto}.hero main{padding:4rem 0}h1{max-width:22ch;font-size:clamp(2.5rem,6vw,5rem)}.section{padding-block:3rem}.status{font-size:.9rem;color:var(--muted-ink)}article{scroll-margin-top:2rem}article h3{font-size:1.45rem}.quick{display:flex;flex-wrap:wrap;gap:1rem}.grid{align-items:start}a:focus-visible{outline:3px solid #438500;outline-offset:4px}</style>
</head><body><header class="hero"><nav aria-label="Main navigation"><a class="brand" href="../">Financial Evidence</a><div><a href="../start/">Research desk</a><a href="../tools/">Setup guides</a><a href="../partners/">For teams</a></div></nav>
<main><p class="eyebrow">Use your existing workspace</p><h1>Put source-cited research beside your next decision.</h1>
<p class="lede">Bring funding, institution and liquidity evidence into your spreadsheet, research agent or trading research workflow. Start with one useful task and keep the sources with the result.</p>
<div class="actions"><a class="button primary" href="../start/workflows.html?workflow=funding">Try a funding review</a><a class="button" href="finance-platform-kit.zip" download>Download the platform kit</a><a class="button" href="agent-clients.md">Connect an agent</a></div>
<p>Public evidence needs no financial-data API key. Platform accounts, model access and source terms may differ.</p></main></header>
<section class="section"><h2>Choose your tool.</h2><p class="quick"><a href="#openbb">OpenBB</a><a href="#excel">Excel</a><a href="#langchain">LangChain</a><a href="#n8n">n8n</a><a href="#tradingview">TradingView</a><a href="#quantconnect">Quant research</a><a href="#ibkr">Institutional platforms</a></p>
<p>Ready-to-use connections, source examples and provider evaluation packets are labelled separately below. A provider packet still requires the platform's acceptance.</p>
<div class="grid">''' + "\n".join(cards) + '''</div></section>
<section class="section"><h2>Make the next review repeatable.</h2><ol><li>Run one task and inspect the cited source, date, unit and gaps.</li><li>Save the capture and the note it helped you write.</li><li>Return on another working day and compare with that capture.</li></ol>
<p>The kit includes forward-research examples, agent setup instructions and provider evaluation material. Historical observation dates do not establish historical data availability. These connections do not authorize trades or grant redistribution rights.</p>
<p><a href="SHA256SUMS">Download checksums</a> · <a href="routes.json">Machine-readable routes</a> · <a href="../distribution/">Publication status</a></p></section>
<footer><p>LIQUILENS PRIVATE LIMITED · Updated 11 October 2026 · <a href="../privacy/">Privacy</a> · <a href="../terms/">Terms</a> · <a href="../support/">Support</a></p></footer></body></html>
''').encode()


def assets() -> dict[str, bytes]:
    manifest = json.loads((DEST / "routes.json").read_text())
    ids = [route["id"] for route in manifest["routes"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate platform id")
    selected = [ROOT / "LICENSE", ROOT / "pyproject.toml", ROOT / "docs/tools/research_client.py",
                ROOT / "docs/tools/FinancialEvidenceRows.pq",
                ROOT / "tests/test_finance_research_forward.py",
                DEST / "agent-clients.md", DEST / "datarade.md", DEST / "routes.json",
                DEST / "pilot-scorecard.csv", DEST / "native-packages.md",
                DEST / "native-packages.json"]
    native = json.loads((DEST / "native-packages.json").read_text())
    downloads = {}
    expected_names = {"n8n-nodes-financial-evidence-0.1.0.tgz", "financial_evidence-0.1.0.difypkg"}
    if {item["filename"] for item in native["packages"]} != expected_names or len(native["packages"]) != 2:
        raise ValueError("unexpected native package set")
    for item in native["packages"]:
        name = "downloads/" + item["filename"]
        path = DEST / name
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Native package checksum mismatch: {name}")
        selected.append(path)
        downloads[name] = data
    # Only authored source formats. Never include environments, credentials,
    # runtime captures, debug keys or dependency trees in a public download.
    for folder in ("src/financial_evidence", "integrations/finance-research", "integrations/finance-desktop",
                   "docs/distribution/provider-packets-20261011"):
        for current, directories, files in os.walk(ROOT / folder):
            directories[:] = sorted(name for name in directories if not name.startswith(".")
                                    and name not in {"node_modules", "__pycache__", "captures", "artifacts"})
            for name in sorted(files):
                path = Path(current) / name
                if (not name.startswith(".") and path.suffix in
                        {".md", ".py", ".json", ".html", ".js", ".mjs", ".css", ".svg", ".txt", ".csv"}):
                    selected.append(path)
    readme = b"""# Financial Evidence platform kit

Start at docs/platforms/agent-clients.md or choose a platform in routes.json.
Forward quant examples: integrations/finance-research/README.md.
Desktop candidate: integrations/finance-desktop/README.md.
Institutional packets: docs/distribution/provider-packets-20261011/README.md.
Native automation candidates and receipts: docs/platforms/native-packages.md.
Python research client and Power Query: docs/tools/.
The shared Python package source and pyproject.toml are included, so the setup
commands in the forward-research README work from this extracted directory.

This is an evaluation kit, not a claim of marketplace acceptance or adoption.
Software licence is in LICENSE. Upstream data retains its source-specific terms.
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
    result = {"index.html": page(manifest), "finance-platform-kit.zip": buffer.getvalue(), **downloads}
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
