import {createHash} from 'node:crypto';
import {readFile, writeFile} from 'node:fs/promises';
import {basename} from 'node:path';

const [archive, receiptPath] = process.argv.slice(2);
if (!archive || !receiptPath) throw new Error('Usage: node scripts/verify_published.mjs <tarball> <receipt.json>');
const {name, version} = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));
const bytes = await readFile(archive);
const expected = `sha512-${createHash('sha512').update(bytes).digest('base64')}`;
const response = await fetch(`https://registry.npmjs.org/${encodeURIComponent(name)}/${encodeURIComponent(version)}`, {signal: AbortSignal.timeout(30000)});
if (!response.ok) throw new Error(`Registry readback failed: HTTP ${response.status}`);
const metadata = await response.json();
if (metadata.name !== name || metadata.version !== version || metadata.dist?.integrity !== expected) {
  throw new Error('Public registry identity or tarball integrity differs from the tested package');
}
const url = new URL(metadata.dist.tarball);
if (url.protocol !== 'https:' || url.hostname !== 'registry.npmjs.org') throw new Error('Unexpected tarball origin');
const download = await fetch(url, {signal: AbortSignal.timeout(30000), redirect: 'error'});
if (!download.ok) throw new Error(`Public tarball fetch failed: HTTP ${download.status}`);
const served = Buffer.from(await download.arrayBuffer());
if (!served.equals(bytes)) throw new Error('Public tarball bytes differ from the tested package');
if (!metadata.dist.attestations?.url) throw new Error('Registry does not expose publication provenance');
await writeFile(receiptPath, JSON.stringify({schema: 'financial-evidence.npm-readback.v1',
  observed_at: new Date().toISOString(), status: 'passed', name, version, archive: basename(archive),
  sha256: createHash('sha256').update(bytes).digest('hex'), integrity: expected,
  provenance_url: metadata.dist.attestations.url, n8n_verified: false, independent_adoption_proven: false}, null, 2) + '\n');
