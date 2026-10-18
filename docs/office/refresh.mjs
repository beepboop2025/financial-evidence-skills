#!/usr/bin/env node
// Node 20+; no dependencies, account, service or automatic schedule.
import E from './office-core.js';
import W from './workbook.js';
import {mkdir, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {createHash} from 'node:crypto';

const help = `Financial Evidence office refresh (Node 20+)
node refresh.mjs --currencies USD,EUR,INR --institutions au-sfb,bajaj-finance --output ./review-2026-10-18
  --datasets market_liquidity,china_economy  optional published dataset previews
  --verification                           mark operator tests as synthetic
Output must be a new directory. Rerun with a new path for your next review.
Writes ODS, XLSX, CSV, HTML, original evidence JSON and a file-hash receipt.
No background polling, credentials, workbook upload or automatic mailing.
`;
const options = {currencies: '', institutions: '', datasets: []};
let output;
try {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.length === 0) { console.log(help); process.exit(0); }
  const seen = new Set();
  while (args.length) {
    const key = args.shift();
    if (seen.has(key)) throw new Error(`Repeated option: ${key}`);
    seen.add(key);
    if (key === '--verification') { options.verification = true; continue; }
    if (!['--currencies', '--institutions', '--datasets', '--output'].includes(key) || !args.length || args[0].startsWith('--')) throw new Error('Unexpected or missing option. Run with --help.');
    const value = args.shift();
    if (key === '--output') output = value;
    else options[key.slice(2)] = key === '--datasets' ? value.split(',').map(v => v.trim()) : value;
  }
  if (!output) throw new Error('--output is required.');
  E.plan(options); // Validate inputs before creating a directory or issuing requests.
  await mkdir(output); // Deliberately refuses existing paths, including symlinks.
  const capture = await E.run(options);
  const files = {
    'review.ods': W.ods(capture), 'review.xlsx': W.xlsx(capture),
    'brief.html': E.html(capture), 'evidence.json': JSON.stringify(capture, null, 2) + '\n',
  };
  for (const sheet of capture.sheets) files[sheet.name.toLowerCase().replaceAll(' ', '-') + '.csv'] = E.csv(sheet.rows);
  for (const [name, data] of Object.entries(files)) await writeFile(join(output, name), data, {flag: 'wx'});
  const failed = capture.requests.filter(r => r.status.request_status === 'failed').length;
  const receipt = {schema: 'financial-evidence.office-export.v1', captured_at: capture.captured_at,
    requests: capture.requests.length, failed_requests: failed,
    traffic_class: options.verification ? 'synthetic' : 'unverified',
    hashes: Object.fromEntries(Object.entries(files).map(([name, data]) => [name, createHash('sha256').update(data).digest('hex')])),
    scope: 'File integrity and request outcomes only; no external adoption, freshness or financial authority claim.'};
  await writeFile(join(output, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
  console.log(JSON.stringify({output, requests: receipt.requests, failed_requests: failed}));
  process.exitCode = failed ? 2 : 0;
} catch (error) { console.error(error.message); process.exitCode = 1; }
