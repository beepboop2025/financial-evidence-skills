#!/usr/bin/env python3
"""Rebuild the dated funding brief from retained, independently fetched evidence.

No network requests. Raw publisher responses remain in the operator evidence
directory; only bounded factual extracts, hashes and the already-public packet
are published. Requires matplotlib==3.11.2 for identical chart rendering.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import textwrap
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SLUG = "2026-10-11-dollar-funding"
DEST = ROOT / "docs/media/briefs" / SLUG
BASE = "https://api.seiche.info/funding-evidence"
CANONICAL = f"https://beepboop2025.github.io/financial-evidence-skills/media/briefs/{SLUG}/"
NAMES = {
    "policy.sofr": "SOFR", "policy.effr": "Effective federal funds rate",
    "policy.iorb": "Interest on reserve balances (IORB)",
    "distribution.sofr.p99": "SOFR 99th percentile",
    "distribution.sofr.volume": "SOFR transaction volume",
    "liquidity.reserves": "Reserve balances: weekly average",
    "liquidity.tga": "Treasury General Account: opening balance",
    "liquidity.on_rrp": "Overnight reverse repo: accepted amount",
    "liquidity.srf": "Standing repo: morning + afternoon accepted amount",
}
FILES = {"sofr": "original-sofr.json", "effr": "original-effr.json",
         "iorb": "original-prates.zip", "reserves": "original-reserves.html",
         "tga": "original-tga.json", "on_rrp": "original-on_rrp.json",
         "srf": "original-srf.json"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def one(values, message):
    require(len(values) == 1, message)
    return values[0]


def cell(document, identifier):
    blocks = re.findall(r'<(?:td|th)\b[^>]*\bid="' + re.escape(identifier)
                        + r'"[^>]*>(.*?)</(?:td|th)>', document, re.S)
    value = one(blocks, f"Missing or ambiguous H.4.1 cell {identifier}")
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def parse_originals(evidence, horizon):
    """Extract the matching economic dates, never the latest record by position."""
    read = lambda name: json.loads((evidence / FILES[name]).read_text())
    values = {}
    sofr = one([x for x in read("sofr")["refRates"]
                if x["effectiveDate"] == horizon and x["type"] == "SOFR"], "SOFR date/type")
    effr = one([x for x in read("effr")["refRates"]
                if x["effectiveDate"] == horizon and x["type"] == "EFFR"], "EFFR date/type")
    for metric, field in (("policy.sofr", "percentRate"), ("distribution.sofr.p99", "percentPercentile99"),
                          ("distribution.sofr.volume", "volumeInBillions")):
        values[metric] = (Decimal(str(sofr[field])), horizon, "sofr", field)
    values["policy.effr"] = (Decimal(str(effr["percentRate"])), horizon, "effr", "percentRate")
    with zipfile.ZipFile(evidence / FILES["iorb"]) as archive:
        tree = ET.fromstring(archive.read("PRATES_data.xml"))
    series = one([x for x in tree.iter() if x.attrib.get("SERIES_NAME") == "RESBM_N.D"], "IORB series")
    require(series.attrib.get("UNIT") == "Percent", "IORB unit")
    obs = one([x for x in series if x.attrib.get("TIME_PERIOD") == horizon], "IORB observation date")
    require(obs.attrib.get("OBS_STATUS") == "A", "IORB unavailable")
    values["policy.iorb"] = (Decimal(obs.attrib["OBS_VALUE"]), horizon, "iorb", "RESBM_N.D/OBS_VALUE")
    document = (evidence / FILES["reserves"]).read_text()
    require(cell(document, "t2h1c2") == "Averages of daily figures", "H.4.1 weekly-average heading")
    header = cell(document, "t2h2c1")
    require(header.startswith("Week ended "), "H.4.1 week heading")
    date = datetime.strptime(header.removeprefix("Week ended "), "%b %d, %Y").date().isoformat()
    require(date <= horizon, "H.4.1 observation after horizon")
    require("Reserve balances with Federal Reserve Banks" in cell(document, "t2r16c1"), "H.4.1 row identity")
    values["liquidity.reserves"] = (Decimal(cell(document, "t2r16c2").replace(",", "")) / 1000,
                                     date, "reserves", "t2r16c2: USD millions / 1000")
    treasury = read("tga")
    require(treasury["meta"]["dataFormats"]["open_today_bal"] == "$1,000,000", "Treasury unit")
    tga = one([x for x in treasury["data"] if x["record_date"] == horizon
               and x["account_type"] == "Treasury General Account (TGA) Opening Balance"], "TGA date/account")
    values["liquidity.tga"] = (Decimal(tga["open_today_bal"]) / 1000, horizon, "tga", "open_today_bal: USD millions / 1000")
    for name, operation, count in (("srf", "Repo", 2), ("on_rrp", "Reverse Repo", 1)):
        rows = [x for x in read(name)["repo"]["operations"] if x["operationDate"] == horizon
                and x["operationType"] == operation and x["term"] == "Overnight"
                and x["auctionStatus"] == "Results"]
        require(len(rows) == count, f"{name} operation completeness")
        require(len({x["operationId"] for x in rows}) == count, f"{name} duplicate operation")
        if name == "srf":
            require({x["releaseTime"] for x in rows} == {"08:15", "13:30"}, "Both SRF sessions required")
        values["liquidity." + name] = (sum(Decimal(str(x["totalAmtAccepted"])) for x in rows) / 10**9,
                                        horizon, name, "sum(totalAmtAccepted): USD dollars / 1000000000")
    return values


def verify(evidence):
    acquisition = json.loads((evidence / "acquisition.json").read_text())
    receipts = {item["file"]: item for item in acquisition["receipts"]}
    require(len(receipts) == len(acquisition["receipts"]), "Duplicate acquisition receipt")
    for name, receipt in receipts.items():
        require(Path(name).name == name, "Unsafe receipt path")
        require(digest((evidence / name).read_bytes()) == receipt["sha256"], f"Acquisition digest mismatch: {name}")
    latest = json.loads((evidence / "latest.json").read_text())
    manifest = json.loads((evidence / "manifest.json").read_text())
    review = json.loads((evidence / "review.json").read_text())
    require(manifest["packet_id"] == latest["packet_id"] == review["capture_id"], "Packet identity")
    require(manifest["packet_id"].startswith("20261011T"), "This brief freezes an 11 October capture")
    require(latest["review_asof"] == review["review_asof"] == "2026-10-08", "This brief has an 8 October horizon")
    require(latest["ready"] is True and manifest["ready_at_capture"] is True and review["ready"] is True, "Unavailable frozen capture")
    require(digest((evidence / "manifest.json").read_bytes()) == latest["manifest_sha256"], "Manifest digest mismatch")
    for name in ("review.json", "observations.csv"):
        require(digest((evidence / name).read_bytes()) == manifest["artifacts"][name], f"Manifest mismatch: {name}")
    originals = parse_originals(evidence, review["review_asof"])
    rows = review["results"]
    require(len(rows) == len(NAMES) and {x["metric_id"] for x in rows} == set(NAMES), "Nine unique metrics required")
    csv_rows = list(csv.DictReader(io.StringIO((evidence / "observations.csv").read_text())))
    require(len(csv_rows) == len(NAMES) and {x["metric_id"] for x in csv_rows} == set(NAMES), "CSV metric contract")
    csv_by_id = {row["metric_id"]: row for row in csv_rows}
    checks = []
    for row in rows:
        metric = row["metric_id"]
        original, date, source, field = originals[metric]
        unit = "$B" if metric.startswith("liquidity.") or metric.endswith("volume") else "%"
        require(row["value_state"] == "available" and row["unit"] == unit, f"Missing/wrong-unit {metric}")
        require(Decimal(str(row["value"])) == original and row["observation_date"] == date, f"Original-publisher mismatch {metric}")
        c = csv_by_id[metric]
        require(Decimal(c["value"]) == original and c["observation_date"] == date and c["unit"] == unit, f"CSV mismatch {metric}")
        receipt = receipts[FILES[source]]
        require(receipt["url"] == manifest["publisher_receipts"][source]["source_url"], f"Publisher URL mismatch {metric}")
        checks.append({"metric_id": metric, "name": NAMES[metric], "value": str(original), "unit": unit,
                       "observation_date": date, "source_url": receipt["url"], "publisher_field": field,
                       "source_sha256": receipt["sha256"], "independent_retrieved_at": receipt["retrieved_at"],
                       "matches_frozen_packet": True, "newer_observation_available": row["newer_observation_available"],
                       "canonical_latest_asof": row["canonical_latest_asof"]})
    return latest, manifest, review, acquisition, checks


def fit_notice_footer(figure, axes, notice_artist, source_artist):
    """Add canvas below the chart so the complete notice has a visible margin."""
    figure.canvas.draw()
    bounds = notice_artist.get_window_extent(figure.canvas.get_renderer())
    margin = figure.dpi * .2
    extra_inches = max(0, margin - bounds.y0) / figure.dpi
    if extra_inches:
        width, old_height = figure.get_size_inches()
        new_height = old_height + extra_inches
        position = axes.get_position()
        for artist in figure.texts:
            x, y = artist.get_position()
            artist.set_position((x, (y * old_height + extra_inches) / new_height))
        figure.set_size_inches(width, new_height)
        axes.set_position([position.x0, (position.y0 * old_height + extra_inches) / new_height,
                           position.width, position.height * old_height / new_height])
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    bounds = notice_artist.get_window_extent(renderer)
    require(bounds.x0 >= 0 and bounds.x1 <= figure.bbox.width and bounds.y0 >= margin - 1,
            "Publisher notice extends outside the chart canvas")
    require(bounds.y1 < source_artist.get_window_extent(renderer).y0,
            "Publisher notice overlaps the source or calculation note")


def chart(output, checks, notice):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    by_id = {x["metric_id"]: x for x in checks}
    iorb = Decimal(by_id["policy.iorb"]["value"])
    metrics = ["policy.sofr", "policy.effr", "distribution.sofr.p99"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none",
                         "svg.hashsalt": SLUG, "axes.spines.top": False, "axes.spines.right": False})
    figure, axes = plt.subplots(figsize=(10.8, 7.2))
    figure.subplots_adjust(left=.31, right=.94, top=.72, bottom=.43)
    values = [float((Decimal(by_id[x]["value"]) - iorb) * 100) for x in metrics]
    labels = [f"{NAMES[x]}\n{Decimal(by_id[x]['value']):.2f}%" for x in metrics]
    axes.barh(range(3), values, color=["#0072B2", "#56B4E9", "#D55E00"], height=.5)
    axes.set_yticks(range(3), labels)
    axes.invert_yaxis()
    axes.axvline(0, color="#263a34", linewidth=1)
    axes.set_xlim(-5, 7)
    axes.set_xticks([-4, -2, 0, 2, 4, 6])
    axes.set_xlabel("Difference from IORB (basis points)", labelpad=10)
    axes.xaxis.grid(True, alpha=.15)
    axes.set_axisbelow(True)
    for position, value in enumerate(values):
        axes.text(value + (.18 if value >= 0 else -.18), position, f"{value:+.0f} bp",
                  va="center", ha="left" if value >= 0 else "right", fontweight="bold")
    figure.text(.065, .955, "SOFR was 3 basis points below IORB", fontsize=23, weight="bold", color="#183229", va="top")
    figure.text(.065, .875, "8 October 2026 observations · IORB reference: 3.90%", fontsize=14, va="top")
    figure.text(.065, .824, "The SOFR 99th percentile was 5 bp above IORB.\nA same-date rate comparison; no institution-stress score is inferred.", fontsize=11, linespacing=1.5, va="top")
    source_artist = figure.text(.065, .29, "Calculation: (rate in percent − IORB in percent) × 100. One basis point = 0.01 percentage point.\nSOFR's 99th percentile describes its transaction-rate distribution; it is not another policy rate.\nSources: New York Fed Markets API; Federal Reserve Board PRATES. Analysis: Seiche / LiquiLens.\nFrozen review: 8 October; packet captured 11 October 2026. Newer dates exist for some other inputs.", fontsize=9, linespacing=1.45, va="top")
    notice_artist = figure.text(.065, .13, "\n".join(textwrap.wrap(notice, 145)), fontsize=7.2, linespacing=1.45, va="top", gid="publisher-notice")
    fit_notice_footer(figure, axes, notice_artist, source_artist)
    for extension in ("svg", "png", "pdf"):
        metadata = {"Creator": "Financial Evidence by LiquiLens"}
        if extension == "svg": metadata["Date"] = "2026-10-11"
        if extension == "pdf": metadata.update(CreationDate=None, ModDate=None)
        figure.savefig(output / f"funding-rate-comparison.{extension}", dpi=300, metadata=metadata)
    plt.close(figure)
    return matplotlib.__version__


def build(evidence, output):
    latest, manifest, review, acquisition, checks = verify(evidence)
    os.environ.setdefault("MPLCONFIGDIR", str(evidence / ".matplotlib-cache"))
    output.mkdir(parents=True, exist_ok=True)
    if (output / "validation.json").exists():
        previous = json.loads((output / "validation.json").read_text())
        require(previous["packet_id"] == manifest["packet_id"], "Cannot replace a dated brief with a different capture")
    for name in ("manifest.json", "review.json", "observations.csv"):
        (output / name).write_bytes((evidence / name).read_bytes())
    write_json = lambda name, value: (output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    by_id = {x["metric_id"]: x for x in checks}
    differences = {x: str((Decimal(by_id[x]["value"]) - Decimal(by_id["policy.iorb"]["value"])) * 100)
                   for x in ("policy.sofr", "policy.effr", "distribution.sofr.p99")}
    require(differences == {"policy.sofr": "-3.00", "policy.effr": "-2.00", "distribution.sofr.p99": "5.00"}, "Dated headline assumptions differ")
    title = "SOFR was 3 basis points below IORB on 8 October"
    finding = "SOFR was 3.87%, compared with IORB at 3.90%, on 8 October 2026. The SOFR–IORB difference was −3 basis points; the SOFR 99th percentile was 3.95%, or 5 basis points above IORB."
    limitations = ["A fixed 8 October funding review, not the latest observation for every instrument.",
                   "System funding evidence does not measure an individual institution's liquidity or probability of failure.",
                   "A rate difference alone does not establish rising or falling stress; this brief makes no historical trend claim.",
                   "Reserve balances are a weekly average for the week ended 7 October; other rows have separate source dates.",
                   "Archive time begins at first verified capture. This is not complete historical publisher-vintage data.",
                   "Publisher terms remain attached; chart and API availability do not grant blanket data redistribution rights."]
    prepared = max(x["retrieved_at"] for x in acquisition["receipts"])
    packet_url = BASE + "/packets/" + manifest["packet_id"]
    validation = {"schema": "financial-evidence.media-validation.v1", "packet_id": manifest["packet_id"],
                  "verified_at": prepared, "traffic_class": "synthetic", "operator_owned_validation": True,
                  "independent_audit": False, "manifest_sha256": latest["manifest_sha256"],
                  "packet_hashes_verified": True, "csv_json_reconciled": True,
                  "original_publisher_checks": checks, "checked_metrics": 9, "matched_metrics": 9,
                  "calculation": {"formula": "(rate_percent - iorb_percent) * 100", "unit": "basis points", "results": differences},
                  "scope": "Exact nine observations, source dates, declared units and headline calculation; no forecasting or stress-label validation."}
    provenance = {"schema": "financial-evidence.media-provenance.v1", "packet_id": manifest["packet_id"],
                  "source_release": manifest["source_release"], "producer_source_commit": manifest["producer_source_commit"],
                  "source_captured_at": manifest["source_captured_at"], "archived_at": manifest["archived_at"],
                  "media_verified_at": prepared, "canonical_packet_url": packet_url,
                  "acquisition": acquisition, "publisher_notice": review["publisher_notice"], "source_terms": review["source_terms"],
                  "methodology": "https://beepboop2025.github.io/financial-evidence-skills/funding/sources.md",
                  "raw_publisher_responses": "Retained in operator evidence; only bounded factual extracts are included in the public brief."}
    write_json("validation.json", validation)
    write_json("provenance.json", provenance)
    write_json("data.json", {"schema": "financial-evidence.media-funding-data.v1", "packet_id": manifest["packet_id"],
                             "observations": checks, "derived_differences_basis_points": differences,
                             "publisher_notice": review["publisher_notice"], "source_terms": review["source_terms"]})
    with (output / "chart-data.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["metric_id", "observation_date", "rate_percent", "iorb_percent", "difference_basis_points", "source_url", "iorb_source_url"])
        writer.writeheader()
        for metric, value in differences.items():
            writer.writerow({"metric_id": metric, "observation_date": by_id[metric]["observation_date"],
                             "rate_percent": by_id[metric]["value"], "iorb_percent": by_id["policy.iorb"]["value"],
                             "difference_basis_points": value, "source_url": by_id[metric]["source_url"],
                             "iorb_source_url": by_id["policy.iorb"]["source_url"]})
    validation["chart_renderer"] = {"name": "matplotlib", "version": chart(output, checks, review["publisher_notice"]), "png_dpi": 300}
    write_json("validation.json", validation)
    downloads = {"csv": "observations.csv", "json": "data.json", "chart_csv": "chart-data.csv",
                 "svg": "funding-rate-comparison.svg", "png": "funding-rate-comparison.png", "pdf": "funding-rate-comparison.pdf",
                 "packet": "review.json", "manifest": "manifest.json", "validation": "validation.json", "provenance": "provenance.json"}
    brief = {"id": SLUG, "title": title, "description": finding, "published_at": prepared,
             "prepared_at": prepared, "observation_dates": ["2026-10-07", "2026-10-08"], "headline_finding": finding,
             "canonical_url": CANONICAL, "source_urls": sorted({x["source_url"] for x in checks}), "downloads": downloads,
             "coverage": "Nine US dollar-funding inputs; eight observations dated 8 October 2026 and weekly-average reserves dated 7 October.",
             "limitations": limitations, "revision": 1, "corrections": []}
    write_json("brief.json", brief)
    esc = html.escape
    rows = "\n".join(f"<tr><th scope='row'>{esc(x['name'])}</th><td>{esc(x['value'])}</td><td>{esc(x['unit'])}</td><td>{x['observation_date']}</td><td><a href='{esc(x['source_url'], quote=True)}'>Original publisher</a></td></tr>" for x in checks)
    limits = "".join(f"<li>{esc(value)}</li>" for value in limitations)
    links = " ".join(f"<a class='button' href='{name}' download>{label.upper()}</a>" for label, name in downloads.items() if label in {"csv", "json", "svg", "png", "pdf"})
    body = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | Seiche / LiquiLens</title><meta name="description" content="{esc(finding, quote=True)}">
<link rel="canonical" href="{CANONICAL}"><link rel="stylesheet" href="../../media.css">
<meta property="og:title" content="{title}"><meta property="og:description" content="Dated funding evidence with original-publisher checks, chart downloads and reproducible data.">
<meta property="og:image" content="{CANONICAL}funding-rate-comparison.png"><meta property="og:type" content="article"></head>
<body><header class="media-header"><nav><a href="../../">LiquiLens media desk</a> · <a href="../../../funding/">Live funding review</a></nav></header>
<main class="media-main"><article><p class="eyebrow">Seiche / US dollar funding · Dated evidence brief</p><h1>{title}</h1>
<p class="lede">{finding}</p><p>Prepared 11 October 2026 · Observation horizon: <strong>8 October 2026</strong> · Revision 1</p>
<p>This comparison separates the central SOFR fixing from the upper end of its transaction-rate distribution. It identifies where the reported rates stood relative to IORB on the same day. It does not, by itself, show whether funding stress was increasing or decreasing.</p>
<figure><img src="funding-rate-comparison.svg" alt="On 8 October 2026, SOFR was 3 basis points below IORB, EFFR 2 basis points below, and the SOFR 99th percentile 5 basis points above. IORB was 3.90 percent." width="1080" height="720" style="max-width:100%;height:auto"><figcaption>Rate differences use the same 8 October observation date. Source: New York Fed and Federal Reserve Board; calculations and chart by Seiche / LiquiLens.</figcaption></figure>
<div class="actions">{links}</div><p><a href="chart-data.csv">Exact chart data and source URLs</a> · <a href="brief.json">Machine-readable brief</a></p>
<h2>What the packet contains</h2><p>The frozen review includes nine observations. Reserve balances refer to the weekly average for the week ended 7 October; the remaining rows refer to 8 October. The $B unit means billions of US dollars. In particular, $0.003 billion of standing-repo usage equals $3 million, not zero.</p>
<div class="table-wrap"><table><thead><tr><th>Observation</th><th>Value</th><th>Unit</th><th>Observation date</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Calculation and independent source check</h2><p>SOFR–IORB = (3.87 − 3.90) × 100 = −3 basis points. The SOFR 99th-percentile difference is (3.95 − 3.90) × 100 = +5 basis points. One basis point is 0.01 percentage point. No composite score, stress threshold or forecast is computed.</p>
<p>The media build independently downloaded the New York Fed Markets API, Federal Reserve Board PRATES and H.4.1, and US Treasury Daily Treasury Statement responses. It selected the packet's economic dates and reconciled all nine numerical values exactly using decimal arithmetic. It also checked the packet manifest hashes and matching CSV/JSON. This is an operator-performed reproducibility check, not an independent third-party audit.</p>
<p>Rates retain publisher precision. Reserves and Treasury cash convert millions to billions; overnight operation amounts convert dollars to billions. Standing-repo amounts sum the morning and afternoon overnight results only when both are present. <a href="../../../funding/sources.md">Detailed methodology and attribution</a> · <a href="../../../funding/contract.json">Dataset contract</a> · <a href="validation.json">Exact validation record</a>.</p>
<h2>Dates, limits and revisions</h2><p>The source packet was captured at {esc(manifest['source_captured_at'])} and first archived at {esc(manifest['archived_at'])}. Our separate source reconciliation completed at {esc(prepared)}. These are different from the economic observation dates.</p>
<p>This is a fixed common-horizon review. The frozen packet flags newer entries for IORB (13 October) and overnight operations (9 October); those entries are not substituted into this 8 October comparison. This brief verifies the 8 October IORB value and makes no inference from the later-dated entry.</p><ul>{limits}</ul>
<h2>Cite and reproduce</h2><blockquote>Seiche / LiquiLens, “{title}”, 11 October 2026, revision 1. Underlying data: Federal Reserve Bank of New York, Federal Reserve Board and US Treasury. Observation dates: 7–8 October 2026.</blockquote>
<p><a href="{CANONICAL}">Permanent brief URL</a> · <a href="{packet_url}/manifest.json">Original immutable packet manifest</a> · <a href="manifest.json">Retained manifest copy</a> · <a href="review.json">Retained review JSON</a> · <a href="provenance.json">Provenance and acquisition receipts</a> · <a href="SHA256SUMS">File checksums</a>.</p>
<h2>Source credit and reuse</h2><p>{esc(review['publisher_notice'])}</p><p><a href="https://www.newyorkfed.org/privacy/termsofuse">New York Fed terms</a> · <a href="https://www.federalreserve.gov/disclaimer.htm">Federal Reserve Board disclaimer</a> · <a href="https://fiscaldata.treasury.gov/about-us/">Treasury data policy</a>. Keep original-publisher attribution, units, dates, modifications and applicable notices when reusing the material. The repository's MIT software licence does not relicense publisher data. No publisher endorsement, exclusive data rights or blanket redistribution licence is claimed.</p>
<h2>Corrections and contact</h2><p>No corrections recorded in revision 1. For a factual query or correction, contact <a href="mailto:mrinal@liquilens.in?subject=Funding%20brief%202026-10-11">mrinal@liquilens.in</a> and identify the observation, source and date. A material correction will be dated here with its reason; this frozen packet will remain available.</p>
</article></main><footer class="media-main"><p>LIQUILENS PRIVATE LIMITED · Source-linked research evidence · <a href="../../">Media desk</a></p></footer></body></html>'''
    (output / "index.html").write_text(body + "\n")
    hashes = "".join(f"{digest(path.read_bytes())}  {path.name}\n" for path in sorted(output.iterdir())
                     if path.is_file() and path.name != "SHA256SUMS")
    (output / "SHA256SUMS").write_text(hashes)
    print(json.dumps({"output": str(output), "packet_id": manifest["packet_id"], "matched_metrics": len(checks), "headline": title}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True, help="Retained operator capture directory")
    parser.add_argument("--output", type=Path, default=DEST)
    args = parser.parse_args()
    build(args.evidence, args.output)


if __name__ == "__main__":
    main()
