#!/usr/bin/env python3
"""Capture a narrow ECB sample with exact clocks and current-vintage parity.

Writes only to the explicitly chosen output/evidence directories. No broker APIs.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

CURRENCIES = ('USD', 'GBP', 'JPY', 'INR')
ECB_URL = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml'
NOTICE = 'Source: European Central Bank. Original reference data is available free from the ECB. Informational reference rates, not executable quotes.'
RIGHTS = 'https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html'


def read_url(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'SeicheReferenceQualification/1.0'}), timeout=45) as response:
        data = response.read(8_000_001)
        if len(data) > 8_000_000:
            raise ValueError('Response exceeds the bounded capture limit')
        return data, dict(response.headers)


def parse_series(text, currency):
    comments = '\n'.join(line for line in text.splitlines() if line.startswith('#'))
    if 'European Central Bank' not in comments or 'freely available' not in comments:
        raise ValueError('Missing ECB source/free-data notice')
    if f'unit: {currency}/EUR' not in comments:
        raise ValueError('Unexpected units')
    rows = list(csv.DictReader(line for line in text.splitlines() if line and not line.startswith('#')))
    if not rows or set(rows[0]) != {'date', 'value'}:
        raise ValueError('Unexpected CSV schema')
    previous = ''
    for row in rows:
        parsed = datetime.strptime(row['date'], '%Y-%m-%d')
        if parsed.strftime('%Y-%m-%d') != row['date'] or row['date'] <= previous:
            raise ValueError('Invalid/duplicate/unsorted observation date')
        value = Decimal(row['value'])
        if not value.is_finite() or value <= 0:
            raise ValueError('Invalid FX value')
        previous = row['date']
    retrieved = re.search(r'retrieved_at: ([^,\n]+)', comments)
    last = re.search(r'last_observation: ([^,\n]+)', comments)
    stale = re.search(r'staleness: ([^,\n]+)', comments)
    if not all((retrieved, last, stale)) or last.group(1).strip() != rows[-1]['date']:
        raise ValueError('Missing or inconsistent source clocks')
    clock = datetime.fromisoformat(retrieved.group(1).strip())
    if clock.tzinfo is None:
        raise ValueError('Retrieval clock must contain timezone')
    return rows, comments, retrieved.group(1).strip(), stale.group(1).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.evidence.mkdir(parents=True, exist_ok=True)
    captured = datetime.now(timezone.utc).isoformat()
    xml, _ = read_url(ECB_URL)
    (args.evidence / 'ecb-history.xml').write_bytes(xml)
    original = {}
    for node in ET.fromstring(xml).iter():
        if 'time' in node.attrib:
            for child in node:
                original[(node.attrib['time'], child.attrib['currency'])] = Decimal(child.attrib['rate'])
    sample, sources = [], []
    for currency in CURRENCIES:
        url = f'https://api.seiche.info/api/series/ECBFX_{currency}.csv'
        raw, headers = read_url(url)
        (args.evidence / f'ECBFX_{currency}.csv').write_bytes(raw)
        rows, comments, retrieved, stale = parse_series(raw.decode('utf-8'), currency)
        for row in rows[-20:]:
            if original.get((row['date'], currency)) != Decimal(row['value']):
                raise ValueError(f'ECB parity failed: {currency} {row["date"]}')
            sample.append({'series_id': f'ECBFX_{currency}', 'base_currency': 'EUR', 'quote_currency': currency,
                           'observation_date': row['date'], 'value': row['value'], 'unit': f'{currency}/EUR',
                           'source_retrieved_at': retrieved, 'sample_captured_at': captured,
                           'source_staleness': stale, 'vintage': 'current_amended', 'first_available_at': None,
                           'source_publisher': 'European Central Bank', 'source_url': ECB_URL, 'delivery_url': url,
                           'rights_url': RIGHTS, 'notice': NOTICE})
        sources.append({'currency': currency, 'url': url, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'rows': len(rows), 'first_date': rows[0]['date'], 'last_date': rows[-1]['date'],
                        'sample_rows': 20, 'sample_parity': '20/20', 'source_comments': comments,
                        'cors': headers.get('Access-Control-Allow-Origin'),
                        'release_sha': headers.get('X-Seiche-Release-Sha')})
    payload = {'schema': 'liquilens.reference-fx-sample.v1', 'captured_at': captured,
               'rights_scope': 'four_ecb_reference_fx_series_only', 'notice': NOTICE,
               'transformation': 'ECB XML values to dated CSV/JSON; no interpolation, inversion or economic adjustment.',
               'point_in_time_eligible': False, 'row_count': len(sample), 'rows': sample}
    (args.output / 'reference-fx-sample.json').write_text(json.dumps(payload, indent=2)+'\n')
    with (args.output / 'reference-fx-sample.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(sample[0]));writer.writeheader();writer.writerows(sample)
    manifest={'captured_at': captured, 'sources': sources, 'ecb_xml_url': ECB_URL,
              'ecb_xml_sha256': hashlib.sha256(xml).hexdigest(), 'sample_parity_pass': True,
              'sample_scope': 'Last 20 published dates per currency; missing dates absent.',
              'coverage_complete': False, 'independent_customer_use': None}
    (args.output / 'sample-verification.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'rows':len(sample),'currencies':list(CURRENCIES),'sample_parity_pass':True,'captured_at':captured}))

if __name__ == '__main__':
    main()
