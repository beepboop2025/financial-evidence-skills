#!/usr/bin/env python3
"""Build the media hub and RSS from reviewed local metadata; never fetch or publish."""
from datetime import date, datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'docs/media'
BASE = 'https://beepboop2025.github.io/financial-evidence-skills/media/'
IDENTIFIER = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
TIMESTAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\Z')
CORRECTION_KINDS = {'correction': 'Correction', 'source_revision': 'Source revision'}


def identifier(value, label):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f'Invalid {label}: expected a lowercase hyphenated identifier')
    return value


def timestamp(value):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ValueError('Publication timestamps must carry a time and timezone')
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        self.ids.add(dict(attrs).get('id'))


def editions():
    result = []
    for path in sorted((MEDIA / 'briefs').glob('*/brief.json'), reverse=True):
        item = json.loads(path.read_text())
        identifier(item.get('id'), 'edition ID')
        if item['id'] != path.parent.name or not (path.parent / 'index.html').is_file():
            raise ValueError(f'Edition identity or page missing: {path}')
        for field in ('title', 'description', 'published_at', 'headline_finding', 'source_urls', 'coverage', 'limitations'):
            if not item.get(field):
                raise ValueError(f'Missing {field} in {path}')
        timestamp(item['published_at'])
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


def corrections(items):
    """Validate the reviewed log before any generated output is overwritten."""
    log = json.loads((MEDIA / 'corrections.json').read_text())
    if not isinstance(log, dict) or log.get('schema') != 'liquilens.media.corrections.v1':
        raise ValueError('Invalid correction log schema')
    updated = log.get('updated_at')
    if not isinstance(updated, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', updated):
        raise ValueError('Correction log updated_at must be an ISO date')
    updated_date = date.fromisoformat(updated)
    if not isinstance(log.get('records'), list):
        raise ValueError('Correction log records must be an array')
    by_id = {item['id']: item for item in items}
    reserved = Anchors()
    reserved.feed((MEDIA / '_header.txt').read_text() + (MEDIA / '_footer.txt').read_text())
    seen = set()
    result = []
    for record in log['records']:
        if not isinstance(record, dict):
            raise ValueError('Correction records must be objects')
        event_id = identifier(record.get('id'), 'correction ID')
        if event_id in reserved.ids:
            raise ValueError(f'Correction ID conflicts with a page anchor: {event_id}')
        if event_id in seen:
            raise ValueError(f'Duplicate correction ID: {event_id}')
        seen.add(event_id)
        edition_id = identifier(record.get('edition_id'), 'correction edition ID')
        if edition_id not in by_id:
            raise ValueError(f'Unknown correction edition: {edition_id}')
        item = by_id[edition_id]
        kind = record.get('kind')
        if not isinstance(kind, str) or kind not in CORRECTION_KINDS:
            raise ValueError('Correction kind must be correction or source_revision')
        published = timestamp(record.get('published_at'))
        if published < timestamp(item['published_at']):
            raise ValueError('Correction predates the original edition')
        if published.astimezone(timezone.utc).date() > updated_date:
            raise ValueError('Correction log updated_at predates an event')
        summary = record.get('summary')
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError('Correction summary must be nonempty text')
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]', summary):
            raise ValueError('Correction summary contains invalid XML characters')
        anchor = identifier(record.get('notice_anchor'), 'correction notice anchor')
        page = Anchors()
        page.feed((MEDIA / 'briefs' / edition_id / 'index.html').read_text())
        if anchor not in page.ids:
            raise ValueError(f'Correction notice anchor missing from edition: {anchor}')
        result.append({**record, 'title': f'{CORRECTION_KINDS[kind]}: {item["title"]}',
                       'url': BASE + 'corrections.html#' + event_id,
                       'edition_url': item['url'] + '#' + anchor})
    return updated_date, sorted(result, key=lambda event: (timestamp(event['published_at']), event['id']), reverse=True)


def correction_page(updated_date, events, header, footer):
    if events:
        log = ''.join(
            f'<article id="{escape(event["id"])}"><h3>{escape(event["title"])}</h3>'
            f'<p><time datetime="{escape(event["published_at"])}">{escape(event["published_at"])}</time></p>'
            f'<p>{escape(event["summary"])}</p><p><a href="{escape(event["edition_url"])}">'
            'Read the notice on the affected edition</a></p></article>' for event in events)
    else:
        log = f'<p>No corrections have been recorded as of {updated_date.day} {updated_date.strftime("%B %Y")}. This statement does not claim that the publications are error-free.</p>'
    return header.format(title='Corrections and edition history', description='How to report errors and find corrections to LiquiLens media briefings.', file='corrections.html') + '''<p class="eyebrow">Transparent editions</p><h1>Corrections stay visible.</h1><p class="lede">Report a suspected error to <a href="mailto:mrinal@liquilens.in?subject=Media%20briefing%20correction">mrinal@liquilens.in</a>, including the edition URL, field or sentence, and supporting source.</p><h2>What happens to a corrected edition</h2><p>We check the original source, the retained extract and our calculation separately. When a published conclusion or value needs correction, we add a dated notice to the affected edition and this log, explain the change and link to the replacement. Original downloadable data stays identifiable by its edition and hash.</p><p>A source publisher’s revision, a new reporting period, a newly captured value and an error in our own analysis are different events. A difference alone is not proof of a publisher revision.</p><p><a href="feed.xml">Follow editions and correction notices with RSS</a>. Corrections have their own feed entries; an edition’s original publication timestamp is retained. This feed changes only when reviewed records are published; it is not a live-data feed or an automatic notification to people who downloaded a file.</p><h2>Correction log</h2>''' + log + '''<p><a href="corrections.json">Machine-readable log</a> · <a href="catalog.json">Edition catalog</a></p>''' + footer + '\n'


def build():
    items = editions()
    updated_date, events = corrections(items)
    catalog = {'schema': 'liquilens.media.catalog.v1', 'publisher': 'LIQUILENS PRIVATE LIMITED',
               'contact': 'mrinal@liquilens.in', 'editions': items, 'corrections': events}
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', 'LiquiLens Media Desk'), ('link', BASE),
                       ('description', 'Dated dollar-funding and bank-disclosure research with original sources, charts, numerical extracts and reviewed correction notices.'),
                       ('language', 'en'), ('managingEditor', 'mrinal@liquilens.in (LiquiLens Media Desk)')]:
        ET.SubElement(channel, key).text = value
    cards = []
    for item in items:
        node = ET.SubElement(channel, 'item')
        for key in ('title', 'description'):
            ET.SubElement(node, key).text = item[key]
        ET.SubElement(node, 'link').text = item['url']
        ET.SubElement(node, 'guid', isPermaLink='true').text = item['url']
        published = timestamp(item['published_at'])
        ET.SubElement(node, 'pubDate').text = format_datetime(published.astimezone(timezone.utc))
        ET.SubElement(node, 'category').text = 'edition'
        chart = next((download['url'] for download in item['downloads'] if download['url'].endswith('.svg')), None)
        preview = (f'<a href="briefs/{escape(item["id"])}/"><img class="edition-preview" src="{escape(chart)}" '
                   f'alt="Chart preview: {escape(item["title"])}" loading="lazy" width="900" height="520"></a>') if chart else ''
        cards.append(f'''<article class="card">{preview}<p class="eyebrow">Edition · {escape(published.date().isoformat())}</p><h3><a href="briefs/{escape(item['id'])}/">{escape(item['title'])}</a></h3><p>{escape(item['description'])}</p><a class="button" href="briefs/{escape(item['id'])}/">Read and download</a></article>''')
    for event in events:
        node = ET.SubElement(channel, 'item')
        ET.SubElement(node, 'title').text = event['title']
        ET.SubElement(node, 'description').text = escape(event['summary']) + ' Affected edition: ' + event['edition_url']
        ET.SubElement(node, 'link').text = event['url']
        ET.SubElement(node, 'guid', isPermaLink='true').text = event['url']
        ET.SubElement(node, 'pubDate').text = format_datetime(timestamp(event['published_at']).astimezone(timezone.utc))
        ET.SubElement(node, 'category').text = event['kind']
    feed_items = channel.findall('item')
    for node in feed_items:
        channel.remove(node)
    for node in sorted(feed_items, key=lambda entry: (parsedate_to_datetime(entry.findtext('pubDate')), entry.findtext('guid')), reverse=True):
        channel.append(node)
    ET.indent(rss)
    template = (MEDIA / '_header.txt').read_text()
    footer = (MEDIA / '_footer.txt').read_text()
    header = template.format(title='Source-ready financial research', description='Download dated dollar-funding and bank-disclosure briefings with charts, data, original sources and transparent calculations.', file='')
    body = '''<header><p class="eyebrow">Public research · For newsrooms and data teams</p><h1>Financial evidence you can trace.</h1><p class="lede">Dated dollar-funding and bank-disclosure briefings, with the chart, data and original sources together. Use a fixed edition to check a claim or reproduce a calculation.</p><div class="actions"><a class="button primary" href="#briefings">Read the briefings</a><a class="button" href="reuse/">Reuse a chart or source packet</a><a class="button" href="feed.xml">Follow editions and corrections with RSS</a><a class="button" href="mailto:mrinal@liquilens.in?subject=Newsroom%20data%20question">Ask a data question</a></div></header><section id="briefings"><h2>Published briefings</h2><p>Publication dates identify these editions. Each briefing separately states the observation dates and reporting periods behind its findings.</p><div class="grid">''' + ''.join(cards) + '''</div></section><section><h2>Everything needed to check the finding</h2><div class="grid"><article class="card"><h3>Use the chart</h3><p>Download publication-quality PNG, SVG and PDF graphics. Preserve their source notes, dates and units.</p><a href="rights.html">Attribution and reuse</a></article><article class="card"><h3>Reproduce the arithmetic</h3><p>Download the edition’s CSV or JSON extract and inspect its calculation and verification record. Missing evidence stays visible.</p><a href="methodology.html">Read our method</a></article><article class="card"><h3>Return to the same edition</h3><p>Each briefing has a dated URL and retained source identity. Corrections receive a visible notice and an entry in the correction log.</p><a href="corrections.html">Corrections and history</a></article></div></section><section><h2>Work with the evidence</h2><p><a href="reuse/">Reuse a chart or source packet</a>: copy an embed or caption, download editable data, and check reuse terms for each asset.</p><p>Open a briefing without registration. For a newsroom evaluation, send the question, deadline, institution or market, and required format to <a href="mailto:mrinal@liquilens.in">Mrinal Singh at mrinal@liquilens.in</a>. We can discuss a scoped evaluation; no turnaround or coverage commitment is made until agreed.</p><p>For recurring research, connect the <a href="../funding/automate/">funding API</a> or use the <a href="../platforms/">spreadsheet, notebook and agent tools</a>. Data teams can inspect the <a href="catalog.json">edition catalog</a>, <a href="../funding/contract.json">funding contract</a> and <a href="platform-evaluation.html">platform evaluation packet</a>.</p><p class="note">Seiche covers system funding evidence; LiquiLens covers specified institution disclosures. These briefings do not establish a combined stress score, universal bank coverage or an institution’s current ability to meet withdrawals.</p></section>'''
    history = correction_page(updated_date, events, template, footer)
    (MEDIA / 'catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n')
    ET.ElementTree(rss).write(MEDIA / 'feed.xml', encoding='utf-8', xml_declaration=True)
    (MEDIA / 'corrections.html').write_text(history)
    (MEDIA / 'index.html').write_text(header + body + footer + '\n')
    print(f'Built media hub, catalog and RSS for {len(items)} editions and {len(events)} correction events')


if __name__ == '__main__':
    build()
