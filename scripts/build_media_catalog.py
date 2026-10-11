#!/usr/bin/env python3
"""Build the media index and RSS from retained edition metadata, without fetching data."""
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'docs/media'
BASE = 'https://beepboop2025.github.io/financial-evidence-skills/media/'


def editions():
    result = []
    for path in sorted((MEDIA / 'briefs').glob('*/brief.json'), reverse=True):
        item = json.loads(path.read_text())
        if item['id'] != path.parent.name or not (path.parent / 'index.html').is_file():
            raise ValueError(f'Edition identity or page missing: {path}')
        for field in ('title', 'description', 'published_at', 'headline_finding', 'source_urls', 'coverage', 'limitations'):
            if not item.get(field):
                raise ValueError(f'Missing {field} in {path}')
        timestamp = datetime.fromisoformat(item['published_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError('Edition timestamps must carry a timezone')
        item['url'] = BASE + 'briefs/' + item['id'] + '/'
        downloads = item.get('downloads', [])
        if isinstance(downloads, dict):
            downloads = [{'label': label, 'url': url} for label, url in downloads.items()]
        for download in downloads:
            target = (path.parent / download['url']).resolve()
            if not target.is_relative_to(path.parent.resolve()) or not target.is_file():
                raise ValueError(f'Download missing or outside edition: {download}')
            download['url'] = item['url'] + download['url']
        item['downloads'] = downloads
        result.append(item)
    if not result:
        raise ValueError('No publishable editions found')
    return result


def build():
    items = editions()
    catalog = {'schema': 'liquilens.media.catalog.v1', 'publisher': 'LIQUILENS PRIVATE LIMITED',
               'contact': 'mrinal@liquilens.in', 'editions': items}
    (MEDIA / 'catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n')
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', 'LiquiLens Media Desk'), ('link', BASE),
                       ('description', 'Dated dollar-funding and bank-disclosure research with original sources, charts and numerical extracts.'),
                       ('language', 'en'), ('managingEditor', 'mrinal@liquilens.in (LiquiLens Media Desk)')]:
        ET.SubElement(channel, key).text = value
    cards = []
    for item in items:
        node = ET.SubElement(channel, 'item')
        for key in ('title', 'description'):
            ET.SubElement(node, key).text = item[key]
        ET.SubElement(node, 'link').text = item['url']
        ET.SubElement(node, 'guid', isPermaLink='true').text = item['url']
        timestamp = datetime.fromisoformat(item['published_at'].replace('Z', '+00:00'))
        ET.SubElement(node, 'pubDate').text = format_datetime(timestamp.astimezone(timezone.utc))
        cards.append(f'''<article class="card"><p class="eyebrow">Edition · {escape(timestamp.date().isoformat())}</p><h3><a href="briefs/{escape(item['id'])}/">{escape(item['title'])}</a></h3><p>{escape(item['description'])}</p><a class="button" href="briefs/{escape(item['id'])}/">Read and download</a></article>''')
    ET.indent(rss)
    ET.ElementTree(rss).write(MEDIA / 'feed.xml', encoding='utf-8', xml_declaration=True)
    header = (MEDIA / '_header.txt').read_text().format(title='Source-ready financial research', description='Download dated dollar-funding and bank-disclosure briefings with charts, data, original sources and transparent calculations.', file='')
    body = '''<header><p class="eyebrow">Public research · For newsrooms and data teams</p><h1>Financial evidence you can trace.</h1><p class="lede">Dated dollar-funding and bank-disclosure briefings, with the chart, data and original sources together. Use a fixed edition to check a claim or reproduce a calculation.</p><div class="actions"><a class="button primary" href="#briefings">Read the briefings</a><a class="button" href="feed.xml">Follow new editions with RSS</a><a class="button" href="mailto:mrinal@liquilens.in?subject=Newsroom%20data%20question">Ask a data question</a></div></header><section id="briefings"><h2>Published briefings</h2><p>Publication dates identify these editions. Each briefing separately states the observation dates and reporting periods behind its findings.</p><div class="grid">''' + ''.join(cards) + '''</div></section><section><h2>Everything needed to check the finding</h2><div class="grid"><article class="card"><h3>Use the chart</h3><p>Download publication-quality PNG, SVG and PDF graphics. Preserve their source notes, dates and units.</p><a href="rights.html">Attribution and reuse</a></article><article class="card"><h3>Reproduce the arithmetic</h3><p>Download the edition’s CSV or JSON extract and inspect its calculation and verification record. Missing evidence stays visible.</p><a href="methodology.html">Read our method</a></article><article class="card"><h3>Return to the same edition</h3><p>Each briefing has a dated URL and retained source identity. Corrections receive a visible notice and an entry in the correction log.</p><a href="corrections.html">Corrections and history</a></article></div></section><section><h2>Work with the evidence</h2><p>Open a briefing without registration. For a newsroom evaluation, send the question, deadline, institution or market, and required format to <a href="mailto:mrinal@liquilens.in">Mrinal Singh at mrinal@liquilens.in</a>. We can discuss a scoped evaluation; no turnaround or coverage commitment is made until agreed.</p><p>For recurring research, connect the <a href="../funding/automate/">funding API</a> or use the <a href="../platforms/">spreadsheet, notebook and agent tools</a>. Data teams can inspect the <a href="catalog.json">edition catalog</a>, <a href="../funding/contract.json">funding contract</a> and <a href="platform-evaluation.html">platform evaluation packet</a>.</p><p class="note">Seiche covers system funding evidence; LiquiLens covers specified institution disclosures. These briefings do not establish a combined stress score, universal bank coverage or an institution’s current ability to meet withdrawals.</p></section>'''
    (MEDIA / 'index.html').write_text(header + body + (MEDIA / '_footer.txt').read_text() + '\n')
    print(f'Built media hub, catalog and RSS for {len(items)} editions')


if __name__ == '__main__':
    build()
