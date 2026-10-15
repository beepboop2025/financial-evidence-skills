#!/usr/bin/env python3
"""Rebuild the dated bank disclosure brief from retained, reviewed factual extracts.

Offline: no new requests, issuer document copying, account access or publication.
Requires matplotlib for SVG, PNG and PDF charts; the input records every source.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
from html import escape
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF_ID = "2026-10-11-bank-disclosures"
DEFAULT = ROOT / "docs/media/briefs" / BRIEF_ID
CANONICAL = f"https://beepboop2025.github.io/financial-evidence-skills/media/briefs/{BRIEF_ID}/"
TITLE = "ESAF: net NPA ratio fell, gross ratio stayed at 5.4%"


def validate(facts):
    if facts["schema"] != "liquilens.media-bank-facts.v1" or facts["brief_id"] != BRIEF_ID:
        raise ValueError("Unexpected dated brief input")
    rows = facts["rows"]
    indexed = {(row["metric"], row["period_end"]): row for row in rows}
    if len(rows) != 22 or len(indexed) != len(rows):
        raise ValueError("Expected 20 observed facts and two explicit missing fields")
    for row in rows:
        if row["entity_id"] != "esaf-sfb" or row["period_end"] not in facts["observation_dates"]:
            raise ValueError("Unexpected issuer or observation date")
        if row["value"] is None:
            if row["availability"] != "unavailable" or row["api_reconciliation"] != "unavailable_not_imputed":
                raise ValueError("Missingness must be explicit")
        elif (type(row["value"]) not in (int, float) or not math.isfinite(row["value"]) or row["availability"] != "reported"
              or row["source_pdf_page"] not in (6, 9, 18, 19)):
            raise ValueError("Every observed fact needs a numeric value and source page")
        if row["source_url"] != facts["primary_source"]["url"]:
            raise ValueError("Unexpected primary source")
        if row["api_reconciliation"] == "matched" and row["api_value"] != row["value"]:
            raise ValueError("Primary fact differs from API observation")
    for metric in ("gnpa_pct", "nnpa_pct"):
        a, b = (indexed[(metric, period)] for period in facts["observation_dates"])
        if a["unit"] != "percent" or b["unit"] != "percent" or a["basis"] != b["basis"]:
            raise ValueError("Compare identical metric definitions and units")
    # This is a dated editorial artifact, not a template that silently refreshes.
    # A revised source fact requires reviewing its corresponding prose as well.
    headline_inputs = {
        "gnpa_pct": (5.4, 5.4), "nnpa_pct": (1.8, .8),
        "gnpa_amount": (1213.9, 1253.3), "advances": (22426, 23216),
    }
    for metric, expected in headline_inputs.items():
        if tuple(indexed[(metric, period)]["value"] for period in facts["observation_dates"]) != expected:
            raise ValueError("Headline inputs changed; re-review the dated editorial text")
    if facts["api_capture"]["coverage_complete"] is not False:
        raise ValueError("This one-bank brief cannot assert complete coverage")
    if facts["primary_source"]["pdf_bytes_independently_hashed_in_this_run"] is not False:
        raise ValueError("This run did not independently retrieve PDF bytes")
    return indexed


def chart(facts, indexed, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.hashsalt": BRIEF_ID, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold"})
    periods = facts["observation_dates"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8), gridspec_kw={"width_ratios": [1.15, 1]})
    fig.patch.set_facecolor("white")
    fig.suptitle("ESAF Small Finance Bank | March to June 2026", x=.075, ha="left", fontsize=19, fontweight="bold")
    for metric, label, color, marker in [("gnpa_pct", "Gross NPA ratio", "#006d77", "o"),
                                        ("nnpa_pct", "Net NPA ratio", "#b74f00", "s")]:
        values = [indexed[(metric, p)]["value"] for p in periods]
        axes[0].plot([0, 1], values, marker=marker, markersize=9, linewidth=2.5, label=label, color=color)
        for x, value in enumerate(values):
            axes[0].annotate(f"{value:.1f}%", (x, value), xytext=(0, 11), textcoords="offset points", ha="center", color=color, fontweight="bold")
    axes[0].set(xlim=(-.2, 1.2), ylim=(0, 6.4), ylabel="Reported ratio (%)", title="Net ratio down 1.0 percentage point")
    axes[0].set_xticks([0, 1], ["31 March", "30 June"])
    axes[0].legend(loc="center left", frameon=False)
    axes[0].grid(axis="y", color="#dde4e8", linewidth=.7)
    axes[0].set_axisbelow(True)
    balances = [indexed[("gnpa_amount", p)]["value"] for p in periods]
    axes[1].bar([0, 1], balances, width=.55, color=["#93b9be", "#006d77"])
    for x, value in enumerate(balances):
        axes[1].text(x, value + 40, f"{value:,.1f}", ha="center", fontweight="bold")
    axes[1].set(ylim=(0, 1550), ylabel="Gross NPA balance (INR crore)", title="Gross NPA balance rose by INR 39.4 crore")
    axes[1].set_xticks([0, 1], ["31 March", "30 June"])
    axes[1].yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    axes[1].grid(axis="y", color="#dde4e8", linewidth=.7)
    axes[1].set_axisbelow(True)
    fig.text(.075, .11, "Gross advances also rose: INR 22,426 crore → INR 23,216 crore. Ratios and balances answer different questions.", fontsize=10)
    fig.text(.075, .065, "Source: ESAF Q1 FY2027 investor presentation, dated 31 July 2026, PDF pages 9 and 18. Chart: LiquiLens, 11 October 2026.", fontsize=9, color="#445566")
    fig.text(.075, .025, "Quarter-end disclosures; not current deposit liquidity, a credit rating or a peer ranking. Gross and net NPA ratios use different denominators.", fontsize=9, color="#445566")
    fig.subplots_adjust(left=.075, right=.97, bottom=.25, top=.82, wspace=.38)
    fig.savefig(output / "esaf-disclosure-comparison.svg", metadata={"Date": facts["prepared_at"], "Creator": "LiquiLens"})
    fig.savefig(output / "esaf-disclosure-comparison.png", dpi=180, metadata={"Software": "LiquiLens media brief"})
    fig.savefig(output / "esaf-disclosure-comparison.pdf", metadata={"Title": TITLE, "Author": "LiquiLens", "CreationDate": None, "ModDate": None})
    plt.close(fig)
    return matplotlib.__version__


def build(source, output):
    facts = json.loads(source.read_text())
    indexed = validate(facts)
    output.mkdir(parents=True, exist_ok=True)
    rows = facts["rows"]
    with (output / "data.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output / "data.json").write_text(json.dumps({"schema": "liquilens.media-bank-extracts.v1",
        "brief_id": BRIEF_ID, "primary_source": facts["primary_source"],
        "api_capture": facts["api_capture"], "rows": rows}, indent=2, ensure_ascii=False) + "\n")
    version = chart(facts, indexed, output)
    coverage = {
        "selected_entities": [{"id": "esaf-sfb", "name": "ESAF Small Finance Bank", "jurisdiction": "IN"}],
        "selection_basis": facts["selection"], "covered_institution_count_in_this_brief": 1,
        "coverage_complete": False, "observation_dates": facts["observation_dates"],
        "observed_numeric_facts": 20, "api_reconciled_numeric_facts": 10,
        "supplemental_primary_filing_numeric_facts": 10,
        "unavailable_fields_in_selected_api": ["cet1_pct", "lcr_pct"],
        "missing_not_zero": True, "point_in_time_vintage_history": False,
        "current_intraday_liquidity": False, "credit_rating": False,
        "api_status": facts["api_capture"]["status"],
        "publication_clock": "Issuer cover letter dated 2026-07-31; API publication timestamps unknown",
        "latest_observation_age_days_at_brief_date": (date(2026, 10, 11) - date(2026, 6, 30)).days,
        "limitations": ["One selected issuer; not a census or representative bank sample.",
            "Historical comparison is read in the July presentation; it is not a backdated publication-vintage dataset.",
            "Ratios are displayed at issuer precision; gross and net NPA denominators differ.",
            "A falling ratio does not identify recoveries or explain the contribution of provisions, sales, write-offs or loan growth.",
            "No live withdrawal, complete counterparty exposure or intraday liquidity evidence is supplied.",
            "CET1 and LCR are missing in the selected API projection, not proven absent from all issuer disclosures.",
            "The PDF was checked through official-source web text. Direct local downloads returned HTTP 403; its API-reported hash is not independently verified in this run."]}
    (output / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    url = facts["primary_source"]["url"]
    metric_order = ["gnpa_pct", "nnpa_pct", "gnpa_amount", "nnpa_amount", "advances", "deposits", "crar_pct", "tier1_pct", "casa_pct", "pcr_reported_pct"]
    table_rows = []
    for metric in metric_order:
        a, b = (indexed[(metric, period)] for period in facts["observation_dates"])
        fmt = lambda row: f'{row["value"]:,.1f}' if row["unit"] == "percent" or metric.endswith("amount") else f'{row["value"]:,.0f}'
        unit = "%" if a["unit"] == "percent" else "INR crore"
        table_rows.append(f'<tr><th scope="row">{escape(a["label"])}</th><td>{fmt(a)}</td><td>{fmt(b)}</td><td>{unit}</td><td><a href="{escape(url)}#page={a["source_pdf_page"]}">PDF p. {a["source_pdf_page"]}</a></td></tr>')
    downloads = [{"label": label, "url": name} for label, name in [
        ("CSV data", "data.csv"), ("JSON data", "data.json"), ("SVG chart", "esaf-disclosure-comparison.svg"),
        ("PNG chart", "esaf-disclosure-comparison.png"), ("PDF chart", "esaf-disclosure-comparison.pdf"),
        ("Coverage", "coverage.json"), ("Validation", "validation.json")]]
    links = "".join(f'<a class="button" href="{d["url"]}">{d["label"]}</a>' for d in downloads)
    brief = {"id": BRIEF_ID, "title": TITLE,
        "description": "A dated, source-linked comparison of ESAF's March and June 2026 disclosures, with editable data and original charts.",
        "published_at": facts["prepared_at"], "observation_dates": facts["observation_dates"],
        "headline_finding": "ESAF reported NNPA of 0.8% at June 2026 versus 1.8% in March. GNPA remained 5.4% at reported precision, while its gross NPA balance increased from INR 1,213.9 crore to INR 1,253.3 crore.",
        "source_urls": [url, facts["api_capture"]["institution_url"], facts["api_capture"]["table_url"]],
        "downloads": downloads, "coverage": {"entities": ["esaf-sfb"], "coverage_complete": False,
            "observed_numeric_facts": 20, "unavailable_fields": ["cet1_pct", "lcr_pct"]},
        "limitations": coverage["limitations"]}
    (output / "brief.json").write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n")
    article_schema = {"@context": "https://schema.org", "@type": "Article", "headline": TITLE,
        "datePublished": brief["published_at"], "url": CANONICAL,
        "author": {"@type": "Organization", "name": "LiquiLens"}, "citation": url}
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE} | LiquiLens Bank Disclosure Watch</title>
<meta name="description" content="ESAF March–June 2026 filing comparison with source pages, missing fields, CSV/JSON and reusable original charts.">
<link rel="canonical" href="{CANONICAL}"><link rel="stylesheet" href="../../media.css">
<script type="application/ld+json">{json.dumps(article_schema)}</script></head>
<body><a class="skip" href="#content">Skip to brief</a><header class="media-header"><nav><a class="brand" href="../../">LiquiLens Media Desk</a><div><a href="../../../tools/">Research tools</a><a href="../../../start/workflows.html">Try a workflow</a></div></nav></header>
<main id="content" class="media-main"><header><p class="eyebrow">Bank Disclosure Watch · 11 October 2026</p>
<h1>{TITLE}</h1><p class="lede">One covered issuer. Two reporting dates. A source-linked check of what the reported ratios and balances actually say.</p>
<p>Observation dates: <strong>31 March and 30 June 2026</strong> · Issuer filing dated <strong>31 July 2026</strong> · Reviewed <strong>11 October 2026</strong>.</p>
<p class="note">June figures are 103 days old at this brief's date. These are quarterly disclosures, not a view of today's withdrawals, funding access or deposit safety.</p></header>
<section aria-labelledby="finding"><h2 id="finding">The finding</h2>
<p>ESAF reported a net NPA ratio of <strong>0.8%</strong> for June, down <strong>1.0 percentage point</strong> from March's 1.8%. Its gross NPA ratio stayed at <strong>5.4%</strong> at the reported precision. The gross NPA balance nevertheless rose from <strong>INR 1,213.9 crore to INR 1,253.3 crore</strong>; gross advances rose from INR 22,426 crore to INR 23,216 crore. <a href="{escape(url)}#page=18">Issuer asset-quality table, PDF p. 18</a>; <a href="{escape(url)}#page=9">advances, p. 9</a>.</p>
<p>A ratio alone does not explain recoveries, provisioning, write-offs, sales or loan growth. Gross and net NPA ratios have different denominators; their difference is not provision coverage.</p>
<figure><img src="esaf-disclosure-comparison.svg" width="1200" height="580" alt="ESAF net NPA ratio falls from 1.8 to 0.8 percent; gross NPA ratio remains 5.4 percent, while gross NPA balances rise from INR 1213.9 crore to INR 1253.3 crore between March and June 2026."><figcaption>Original LiquiLens chart using ESAF's dated factual disclosures. Values and source pages are provided below and in the downloadable extracts.</figcaption></figure>
<div class="actions">{links}</div></section>
<section aria-labelledby="facts"><h2 id="facts">The reported comparison</h2><div class="table-wrap"><table><caption>ESAF Small Finance Bank — period-end facts at issuer precision</caption><thead><tr><th scope="col">Measure</th><th scope="col">31 March 2026</th><th scope="col">30 June 2026</th><th scope="col">Unit</th><th scope="col">Primary source</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<p class="small">PDF page numbers include the exchange-cover letter. The printed slide number is one lower. June reported PCR includes an additional INR 64.7 crore provision; the issuer separately shows 80.5% excluding that provision. Consult its basis on PDF p. 18. Tier 1 is not substituted for CET1.</p></section>
<section aria-labelledby="coverage"><h2 id="coverage">Coverage and missing evidence</h2><div class="grid"><article class="card"><h3>Exactly one selected bank</h3><p>LiquiLens identifies this institution as <code>esaf-sfb</code>. This comparison is neither an industry census nor a ranking. Twenty numerical facts are extracted; ten also reconcile to the current or comparative institution API records.</p></article><article class="card"><h3>Two fields remain missing</h3><p>CET1 and liquidity coverage ratio are null in the selected current table. They remain null in the downloads. This does not establish that the issuer has never disclosed them elsewhere.</p></article></div>
<p>The API's institution status is <code>insufficient_visibility</code> and coverage remains incomplete. Missing private withdrawals, exposures or reporting fields do not establish financial safety or distress. No combined score, credit decision or intraday liquidity claim is produced.</p></section>
<section aria-labelledby="method"><h2 id="method">Source checks and clocks</h2><ol>
<li>Queried the <a href="{escape(facts['api_capture']['institution_url'])}">exact ESAF institution record with history</a> and the <a href="{escape(facts['api_capture']['table_url'])}">covered-bank table</a> using operator-verification traffic labels.</li>
<li>Checked the <a href="{escape(url)}">bank-hosted Q1 FY2027 presentation</a>: cover-letter date on p. 1, deposits on p. 6, advances on p. 9, asset quality on p. 18 and capital on p. 19. Ten numerical API observations match the selected issuer facts; the other ten are labelled supplemental primary-filing extracts.</li>
<li>Retained the API's unknown publication timestamps. Its knowledge time for the reviewed facts is 4 October 2026; the period dates are March and June. Neither that knowledge time nor this request's retrieval time is the issuer's publication timestamp.</li>
</ol><p class="small">Primary verification used the official-source PDF text available through web retrieval. Direct local downloads returned HTTP 403. The API reports a PDF hash, retained in JSON, but this run did not independently hash the PDF bytes. No issuer PDF or screenshot is republished here.</p>
<p>Rebuild the chart and brief from <a href="source-facts.json">the retained factual inputs</a> using <a href="https://github.com/beepboop2025/financial-evidence-skills/blob/main/scripts/build_bank_media_brief.py">build_bank_media_brief.py</a>. The build is offline. See <a href="validation.json">validation details</a> and <a href="coverage.json">full scope limits</a>.</p></section>
<section aria-labelledby="reuse"><h2 id="reuse">Use in a report</h2><p>Suggested credit: “Source: ESAF Small Finance Bank, Q1 FY2027 investor presentation, dated 31 July 2026. Chart and extraction: LiquiLens, 11 October 2026.” Preserve the reporting dates, units and scope notes when adapting the chart or factual extracts. Issuer documents, branding and third-party material retain their own rights; no licence to redistribute them is granted by this brief.</p>
<p><a href="https://liquilens.in/banking/monitoring/">Review a covered institution</a> · <a href="../../../tools/">Use these research tools in a spreadsheet or notebook</a> · Corrections: <a href="mailto:mrinal@liquilens.in">mrinal@liquilens.in</a></p></section>
<footer>Prepared by LiquiLens / LIQUILENS PRIVATE LIMITED. Research evidence; no rating, investment recommendation or independent adoption claim. <a href="../../">More media briefs</a></footer></main></body></html>
'''
    (output / "index.html").write_text(html)
    validation = {"schema": "liquilens.media-bank-validation.v1", "status": "selected_facts_reconciled",
        "prepared_at": facts["prepared_at"], "primary_source_text_reviewed": True,
        "primary_source_pdf_bytes_independently_hashed": False,
        "api_reconciled_rows": sum(r["api_reconciliation"] == "matched" for r in rows),
        "primary_only_rows": sum(r["api_reconciliation"] == "supplemental_primary_filing_extract" for r in rows),
        "missing_rows_retained": sum(r["value"] is None for r in rows), "mismatches": [],
        "nnpa_change_percentage_points": round(indexed[("nnpa_pct", "2026-06-30")]["value"] - indexed[("nnpa_pct", "2026-03-31")]["value"], 6),
        "gnpa_change_percentage_points_at_reported_precision": 0.0,
        "gross_npa_balance_change_INR_crore": round(indexed[("gnpa_amount", "2026-06-30")]["value"] - indexed[("gnpa_amount", "2026-03-31")]["value"], 6),
        "matplotlib_version": version, "source_facts_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "traffic_class": "synthetic", "external_users_or_adoption_verified": False,
        "checks": ["exact issuer identity", "same-period units", "same-metric comparison basis", "nulls retained",
            "issuer source page per numerical fact", "API publication timestamps not backdated", "partial coverage retained",
            "API values checked against retained primary transcription", "PDF-byte verification limitation retained"],
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name != "validation.json"}}
    (output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-facts", type=Path, default=DEFAULT / "source-facts.json")
    parser.add_argument("--output", type=Path, default=DEFAULT)
    args = parser.parse_args()
    result = build(args.source_facts, args.output)
    print(json.dumps({key: result[key] for key in ("status", "api_reconciled_rows", "primary_only_rows", "missing_rows_retained", "matplotlib_version")}))


if __name__ == "__main__":
    main()
