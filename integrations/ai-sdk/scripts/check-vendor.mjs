import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const canonical = await readFile(new URL('../../../docs/agents/context-client.mjs', import.meta.url));
const vendored = await readFile(new URL('../vendor/context-client.mjs', import.meta.url));
assert.deepEqual(vendored, canonical, 'Update the vendored context validator from docs/agents/context-client.mjs');
console.log('Canonical context client SHA-256:', createHash('sha256').update(vendored).digest('hex'));
