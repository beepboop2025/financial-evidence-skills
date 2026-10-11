#!/usr/bin/env python3
"""Build a dated newsroom reuse page and deterministic ZIP from retained files.

No network requests or market-data refresh. Review SPECS before adding an edition.
Run from any directory: python3 -B scripts/build_newsroom_reuse_kit.py
"""
import argparse
import hashlib
import html
import io
import json
import struct
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://beepboop2025.github.io/financial-evidence-skills/"
MEDIA_URL = BASE + "media/"
KIT_NAME = "newsroom-evaluation-kit-20261011.zip"
ZIP_TIME = (2026, 10, 11, 0, 0, 0)
NYFED_NOTICE = (
    "Copyright 2026 Federal Reserve Bank of New York. Content from the New York Fed "
    "subject to the Terms of Use at https://www.newyorkfed.org/privacy/termsofuse. "
    "SOFR, EFFR and operation results are subject to those Terms of Use. The New York "
    "Fed is not responsible for publication of these data by Liquidity Lab, does not "
    "sanction or endorse this republication, and has no liability for your use. "
    "Liquidity Lab is not affiliated with the New York Fed. The SOFR terms also "
    "address DTCC Solutions LLC data used by the publisher; no ownership of that "
    "underlying data is claimed here."
)
SPECS = {
    "2026-10-11-dollar-funding": {
        "observation_dates": ["2026-10-07", "2026-10-08"],
        "label": "Dollar funding",
        "credit": "Source: New York Fed and Federal Reserve Board, 8 October 2026; calculation and chart: Seiche / LiquiLens, 11 October 2026.",
        "clock": "Chart: 8 October 2026. Full packet: eight observations dated 8 October; weekly-average reserves dated 7 October.",
        "limit": "Fixed historical rate comparison; not a current market reading, stress trend, or measure of an individual bank’s solvency.",
        "notice": NYFED_NOTICE,
        "rights": "Original chart design and commentary may be reproduced with attribution, subject to the attached source notices. Numerical data remains subject to publisher terms; this is not an unrestricted data licence.",
        "source_publication": "Observation and publisher-release clocks are separate; see the retained provenance record for each input.",
    },
    "2026-10-11-bank-disclosures": {
        "observation_dates": ["2026-03-31", "2026-06-30"],
        "label": "Bank disclosures",
        "credit": "Source: ESAF Small Finance Bank, Q1 FY2027 investor presentation, dated 31 July 2026. Chart and extraction: LiquiLens, 11 October 2026.",
        "clock": "Reported periods: 31 March and 30 June 2026. Source presentation: 31 July 2026.",
        "limit": "One covered issuer and historical March/June disclosures; not current liquidity, a representative bank sample, or a rating. The source PDF was checked via official web text; its reported hash was not independently verified.",
        "notice": "Issuer documents, branding and third-party material retain their own rights; no licence to redistribute them is granted by this brief. Link to the original filing. No original issuer PDF is included in this kit.",
        "rights": "Original chart design and commentary may be reproduced with attribution. Factual extracts retain source credit; issuer documents, branding and commercial data-feed redistribution require separate qualification.",
        "source_publication": "Historical comparisons were read in the 31 July 2026 presentation; these are not reconstructed publication-vintage observations.",
    },
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def local_download(folder, value):
    """Accept only direct files in the reviewed edition, never URLs or traversal."""
    parsed = urlparse(value)
    name = unquote(parsed.path)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or Path(name).name != name:
        raise ValueError(f"Not an edition-local asset: {value}")
    path = folder / name
    if path.suffix not in {".csv", ".json", ".png", ".svg", ".pdf"} or not path.is_file():
        raise ValueError(f"Missing or unsupported asset: {value}")
    if path.resolve().parent != folder.resolve():
        raise ValueError(f"Asset leaves reviewed edition: {value}")
    return path


def caption(edition, spec):
    return "\n".join([
        edition["title"],
        f"Edition: {edition['id']}; published {edition['published_at']}.",
        spec["clock"], spec["credit"], spec["limit"], spec["notice"],
        "Data, original sources and methodology: " + edition["canonical_url"],
        "Reuse terms: " + MEDIA_URL + "rights.html",
        "Full funding source notices: " + BASE + "funding/sources.md" if "dollar-funding" in edition["id"] else "Original source: " + edition["source_urls"][0],
        "Check corrections before reuse: " + MEDIA_URL + "corrections.html",
    ]) + "\n"


def embed(edition, spec, image_url, width, height):
    esc = html.escape
    return f'''<!-- Fixed historical edition. Keep the dates, limitations, credit and source notice. -->
<figure style="max-width:960px;margin:1rem auto">
  <a href="{esc(edition['canonical_url'])}"><img src="{esc(image_url)}" width="{width}" height="{height}" alt="{esc(edition['headline_finding'])}" style="display:block;width:100%;height:auto" loading="lazy"></a>
  <figcaption>
    <p><strong>{esc(edition['title'])}</strong></p>
    <p>Edition: {esc(edition['id'])}; published {esc(edition['published_at'])}.</p>
    <p>{esc(spec['clock'])}</p>
    <p>{esc(spec['credit'])}</p>
    <p>{esc(spec['limit'])}</p>
    <p>{esc(spec['notice'])}</p>
    <p><a href="{esc(edition['canonical_url'])}">Data, original sources and methodology</a> · <a href="{MEDIA_URL}rights.html">Reuse terms and source notices</a> · <a href="{BASE}funding/sources.md">Funding source attribution</a> · <a href="{MEDIA_URL}corrections.html">Check corrections before reuse</a></p>
  </figcaption>
</figure>
'''


def file_rights(path):
    if path.suffix in {".png", ".svg", ".pdf"}:
        return "Original LiquiLens chart; attribution required, with underlying-source notices retained. No original issuer document is included."
    return "Edition-specific numerical extract or verification metadata. Publisher terms remain attached; software MIT licensing does not confer additional data rights."


def text_box(ident, label, text):
    esc = html.escape
    return f'''<div class="copy-field"><div class="field-header"><label for="{ident}">{esc(label)}</label><button type="button" data-copy="{ident}" aria-label="Copy {esc(label)}">Copy</button></div><textarea id="{ident}" readonly spellcheck="false" rows="8">{esc(text)}</textarea></div>'''


def render_page(editions, archive_sha, archive_bytes):
    esc = html.escape
    cards = []
    for edition in editions:
        ident = edition["id"]
        spec = SPECS[ident]
        image = next(asset for asset in edition["assets"] if asset["format"] == "png")
        downloads = "".join(f'<a class="button" href="{esc(a["public_url"])}" download>{esc(a["label"])} <span class="small">{a["format"].upper()}</span></a>' for a in edition["assets"])
        rows = "".join(f'<tr><td><a href="{esc(a["public_url"])}">{esc(a["filename"])}</a></td><td>{esc(a["reuse_scope"])}</td><td><code>{a["sha256"]}</code></td></tr>' for a in edition["assets"])
        limits = "".join(f"<li>{esc(item)}</li>" for item in edition["limitations"])
        cards.append(f'''<article class="edition" id="{ident}">
<header><p class="eyebrow">{esc(spec['label'])} · historical edition</p><h2>{esc(edition['title'])}</h2><p class="source-clock">{esc(spec['clock'])}</p><p class="small">Edition <code>{ident}</code> · Published <time datetime="{esc(edition['published_at'])}">{esc(edition['published_at'])}</time></p></header>
<div class="edition-layout"><div><a href="{esc(edition['canonical_url'])}"><img class="chart-preview" src="{esc(image['public_url'])}" alt="{esc(edition['headline_finding'])}" width="{image['width']}" height="{image['height']}" loading="lazy"></a><p class="credit">{esc(spec['credit'])}</p><p class="small">{esc(spec['limit'])}</p><a href="{esc(edition['canonical_url'])}">Read the full method and original sources →</a></div>
<div class="reuse-panel"><h3>Copy with context</h3><p class="small">The caption and embed include source credit, dates and limitations. Preserve these when editing for your publication.</p>{text_box(ident+'-caption',spec['label']+' caption',edition['caption'])}<details><summary>HTML image embed</summary>{text_box(ident+'-embed',spec['label']+' HTML embed',edition['embed'])}<p class="small">Paste into a CMS HTML block and check the published result. If external images are blocked, use the downloaded PNG with the same caption.</p></details><div class="actions"><a href="{ident}/preview.html">Preview embed</a><a href="{ident}/embed.html" download>Download HTML</a><a href="{ident}/CAPTION.txt" download>Download caption</a></div></div></div>
<h3>Download the retained assets</h3><div class="actions download-actions">{downloads}</div><p class="small">These links use the existing edition files. A download does not refresh observations or expand source permissions.</p>
<details><summary>Asset rights, checksums and coverage limits</summary><p>{esc(spec['rights'])}</p><div class="table-wrap"><table><caption>Edition asset identity and reuse scope</caption><thead><tr><th scope="col">File</th><th scope="col">Reuse boundary</th><th scope="col">SHA-256</th></tr></thead><tbody>{rows}</tbody></table></div><ul>{limits}</ul><p>{esc(spec['source_publication'])}</p></details></article>''')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Charts, data and source notes — LiquiLens Media Desk</title><meta name="description" content="Copy source-linked captions and chart embeds, download dated financial research assets, and check per-asset reuse terms."><link rel="canonical" href="{MEDIA_URL}reuse/"><link rel="stylesheet" href="../media.css"><link rel="stylesheet" href="reuse.css"><link rel="alternate" type="application/rss+xml" title="LiquiLens Media Desk" href="../feed.xml"><script src="reuse.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header class="media-header"><nav aria-label="Primary"><a class="brand" href="../">LiquiLens Media Desk</a><div><a href="../#briefings">Briefings</a><a href="../methodology.html">Methodology</a><a href="../rights.html">Reuse terms</a><a href="../corrections.html">Corrections</a></div></nav></header>
<main class="media-main" id="main"><header><p class="eyebrow">Research utility · Fixed editions</p><h1>Charts, data and source notes.</h1><p class="lede">Use the complete context behind a financial finding. Copy a caption or image embed, download the underlying extract, and trace it to the original publisher.</p><div class="actions"><a class="button primary" href="{KIT_NAME}" download>Download both editions · ZIP ({archive_bytes/1024:.0f} KB)</a><a class="button" href="manifest.json">Inspect the asset manifest</a></div><p class="small">Two historical editions published 11 October 2026. Packaging does not update their observation dates. <a href="../corrections.html">Check the live correction log before reuse.</a></p></header>
<nav class="edition-nav" aria-label="Choose an edition"><a href="#2026-10-11-dollar-funding">Dollar funding · 8 October</a><a href="#2026-10-11-bank-disclosures">ESAF disclosures · March / June</a></nav><p id="copy-status" class="copy-status small" role="status" aria-live="polite"></p><noscript><p class="note">Select the caption or HTML text below and copy it manually. All downloads work without JavaScript.</p></noscript>
{''.join(cards)}
<section class="reuse-notes"><h2>Keep the evidence intact</h2><div class="grid"><div><h3>What the package contains</h3><p>Original charts, selected CSV/JSON extracts, verification records and ready-to-copy source notes. The ZIP contains copies of the same retained files plus captions and embeds.</p></div><div><h3>What reuse means</h3><p>Our original commentary and chart design may be reproduced with attribution, subject to the underlying-source notices. Issuer documents, licensed feeds and third-party branding retain their own rights.</p></div><div><h3>Corrections and revisions</h3><p>Check the <a href="../corrections.html">live correction log</a>. A downloaded copy cannot notify its editor of a later correction. Follow the <a href="../feed.xml">edition feed</a> and retain the edition URL in your publication.</p></div></div><p><a href="../rights.html">Read material-specific reuse terms</a> · <a href="../../funding/sources.md">Full funding source attribution</a> · <a href="README.md">Package instructions</a> · <a href="manifest.json">Machine-readable manifest</a></p><details><summary>Verify the ZIP</summary><p>SHA-256: <code>{archive_sha}</code></p><p>The manifest hashes identify copied bytes; they do not independently validate publisher statements or confer legal permission. The ZIP contains its own file checksums and archival notices. Live notices may change.</p></details></section>
<footer><p>Published by LIQUILENS PRIVATE LIMITED. Questions about a source, deadline or intended use: <a href="mailto:mrinal@liquilens.in?subject=Newsroom%20reuse%20question">mrinal@liquilens.in</a>. Scope, coverage and any service terms are agreed separately.</p><p><a href="../">Media Desk</a> · <a href="../../funding/">Current funding review</a> · <a href="../../platforms/">Research integrations</a> · <a href="../../privacy/">Privacy</a></p></footer></main></body></html>'''


README = f'''# Newsroom reuse kit

Two retained historical editions, published 11 October 2026. No market data is
fetched or refreshed when this package is built. The edition times identify the
research publication; underlying observations and source-release dates differ.

Each edition contains unchanged chart/data assets, source links, an HTML image
embed, a preview and a caption. The online reuse page links the existing edition
assets rather than duplicating their binaries. The ZIP includes those binaries
for convenience, plus the existing source notices and an integrity manifest.

Read the live [reuse terms]({MEDIA_URL}rights.html),
[correction log]({MEDIA_URL}corrections.html) and
[funding source attribution]({BASE}funding/sources.md) before using an asset.
The copies inside this archive are snapshots; website-relative navigation in
archived HTML may not work offline. The manifest carries original public URLs.

Open preview.html for an edition, or copy embed.html into a CMS HTML block. Its
image and verification links use the public Media Desk. Test the CMS output.
For offline or blocked-image use, take the included PNG and retain CAPTION.txt.
An image embed does not dynamically refresh the dates, source notes or caption.
Downloaded and republished copies cannot automatically receive corrections.

The bank brief records that the original issuer PDF hash was not independently
verified; no issuer PDF is included. No broad bank coverage, live funding quote,
data-feed licence, newsroom adoption, endorsement or service level is asserted.

checksums.json covers every other file inside the archive. The public manifest
also identifies the ZIP. A hash proves file identity, not source accuracy or
legal permission. Build locally with python3 -B scripts/build_newsroom_reuse_kit.py.

Contact: mrinal@liquilens.in
'''


def build(repo=ROOT, output=None):
    repo = Path(repo)
    output = Path(output) if output else repo / "docs/media/reuse"
    media = repo / "docs/media"
    archive = {"README.md": README.encode()}
    notices = []
    for relative in ("media/rights.html", "media/corrections.html", "media/corrections.json", "funding/sources.md"):
        raw = (repo / "docs" / relative).read_bytes()
        dest = "notices/" + Path(relative).name
        archive[dest] = raw
        notices.append({"path": dest, "public_url": BASE + relative, "sha256": digest(raw)})
    # Require the reviewed source-notice markers before materializing the kit.
    if b"Federal Reserve Bank of New York" not in archive["notices/sources.md"] or b"third-party material" not in archive["notices/rights.html"]:
        raise ValueError("Reviewed source notices are missing; review rights before rebuilding")
    editions, files = [], {}
    for ident, spec in SPECS.items():
        folder = media / "briefs" / ident
        raw_brief = (folder / "brief.json").read_bytes()
        edition = json.loads(raw_brief)
        if edition["id"] != ident or not edition.get("limitations") or not edition.get("source_urls"):
            raise ValueError(f"Incomplete reviewed edition: {ident}")
        if edition["observation_dates"] != spec["observation_dates"]:
            raise ValueError(f"Observation dates require a caption review: {ident}")
        published = datetime.fromisoformat(edition["published_at"])
        if published.tzinfo is None or published.date().isoformat() != ident[:10]:
            raise ValueError(f"Edition publication clock differs: {ident}")
        edition["canonical_url"] = MEDIA_URL + "briefs/" + ident + "/"
        downloads = edition["downloads"]
        downloads = [{"label": k, "url": v} for k, v in downloads.items()] if isinstance(downloads, dict) else downloads
        assets = []
        archive[ident + "/brief.json"] = raw_brief
        for item in downloads:
            path = local_download(folder, item["url"])
            raw = path.read_bytes()
            archive[ident + "/" + path.name] = raw
            asset = {"filename": path.name, "label": item["label"], "format": path.suffix[1:], "bytes": len(raw), "sha256": digest(raw), "public_url": edition["canonical_url"] + path.name, "archive_path": ident + "/" + path.name, "reuse_scope": file_rights(path)}
            if path.suffix == ".png":
                if raw[:8] != b"\x89PNG\r\n\x1a\n":
                    raise ValueError("Invalid PNG signature")
                asset["width"], asset["height"] = struct.unpack(">II", raw[16:24])
            assets.append(asset)
        image = next(a for a in assets if a["format"] == "png")
        edition.update(assets=assets, caption=caption(edition, spec), source_notice=spec["notice"], reuse_scope=spec["rights"], source_clock=spec["clock"], corrections_url=MEDIA_URL + "corrections.html", rights_url=MEDIA_URL + "rights.html", brief_sha256=digest(raw_brief))
        edition["embed"] = embed(edition, spec, image["public_url"], image["width"], image["height"])
        preview = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(spec["label"]) + ' — embed preview</title><style>body{max-width:1000px;margin:2rem auto;padding:0 1rem;font:16px/1.6 system-ui;color:#182b3a}a{color:#005d82}</style></head><body>' + edition["embed"] + '</body></html>'
        for name, content in {"embed.html": edition["embed"], "preview.html": preview, "CAPTION.txt": edition["caption"]}.items():
            archive[ident + "/" + name] = content.encode()
            files[ident + "/" + name] = content.encode()
        editions.append(edition)
    manifest = {"schema": "liquilens.newsroom.reuse-kit.v1", "edition_ids": list(SPECS), "market_data_refreshed": False, "freshness": "Historical editions; packaging time is not observation or publisher-release time.", "source": MEDIA_URL, "native_cms_or_platform_acceptance_verified": False, "source_notices": notices, "editions": editions}
    archive["manifest.json"] = json_bytes(manifest)
    archive["checksums.json"] = json_bytes({name: digest(raw) for name, raw in sorted(archive.items())})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for name, raw in sorted(archive.items()):
            info = zipfile.ZipInfo("newsroom-kit/" + name, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, raw)
    bundle = stream.getvalue()
    manifest["archive"] = {"filename": KIT_NAME, "bytes": len(bundle), "sha256": digest(bundle), "contents_prefix": "newsroom-kit/", "checksum_scope": "Every archive file except checksums.json itself; archive manifest excludes its own ZIP hash."}
    files.update({KIT_NAME: bundle, "manifest.json": json_bytes(manifest), "README.md": README.encode(), "index.html": render_page(editions, digest(bundle), len(bundle)).encode()})
    for name, raw in files.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    return {"editions": len(editions), "asset_count": sum(len(e["assets"]) for e in editions), "zip_sha256": digest(bundle), "zip_bytes": len(bundle), "market_data_refreshed": False, "files_written": sorted(files)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(output=args.output_dir), indent=2))
