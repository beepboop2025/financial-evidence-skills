import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';

function externalImports(text) {
  const found = [];
  // Emitted import/export-from declarations, import types and reference directives.
  for (const pattern of [
    /\bfrom\s*["']([^"']+)["']/g,
    /\bimport\s*(?:\(\s*)?["']([^"']+)["']/g,
    /<reference\s+types=["']([^"']+)["']/g,
  ]) {
    for (const match of text.matchAll(pattern)) {
      if (!match[1].startsWith('.')) found.push(match[1]);
    }
  }
  return found;
}

const packageName = specifier => specifier.startsWith('@')
  ? specifier.split('/').slice(0, 2).join('/') : specifier.split('/')[0];

test('declaration guard detects inferred transitive imports and their scoped package root', () => {
  const imports = externalImports(`import { Tool } from 'ai';
    export { z } from 'zod';
    type Provider = import('@ai-sdk/provider').ProviderV4;
    type Context = import("@ai-sdk/provider-utils/private").Context;
    export { validateSnapshot } from '../vendor/context-client.mjs';`);
  assert.deepEqual(imports.map(packageName), ['ai', 'zod', '@ai-sdk/provider', '@ai-sdk/provider-utils']);
});

test('all packaged declarations reference only declared runtime dependencies or peers', async () => {
  const manifest = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));
  const allowed = new Set(Object.keys({...manifest.dependencies, ...manifest.peerDependencies}));
  let checked = 0;
  for (const folder of ['dist', 'vendor']) {
    const base = new URL(`../${folder}/`, import.meta.url);
    for (const path of await readdir(base, {recursive: true})) {
      if (!/\.d\.(?:ts|mts|cts)$/.test(path)) continue;
      const text = await readFile(new URL(path, base), 'utf8');
      for (const specifier of externalImports(text)) {
        assert.ok(allowed.has(packageName(specifier)), `${folder}/${path} imports undeclared runtime dependency ${specifier}`);
      }
      checked++;
    }
  }
  assert.ok(checked >= 2, 'Check both the main declarations and the vendored validator declaration');
});
