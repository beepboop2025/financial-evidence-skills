const { test } = require('node:test');
const assert = require('node:assert/strict');
const { financialEvidence } = require('../dist');
const { ResearchResponseError } = require('../dist/lib/research');

const page = () => ({
  schema: 'liquidity-lab.openbb-table.v1', dataset: 'money_markets',
  results: [{ value: null, availability: 'UNAVAILABLE', as_of: '2026-10-01', unit: '%', rights_status: 'restricted' }],
  sources: [{ source_url: 'https://example.org/source', source_reported: { clocks: [{ name: 'as_of', value: '2026-10-01' }] } }],
  diagnostics: [{ error: 'source_unavailable' }], next_offset: 1,
  status_semantics: 'transport_only', additional_field: { preserved: true },
});
const action = (name = 'get_evidence_page') => financialEvidence.getAction(name);
const run = (propsValue) => action().run({ propsValue });

test('SDK loads two credential-free read actions and preserves the complete page', async (t) => {
  assert.deepEqual(Object.keys(financialEvidence.actions()).sort(), ['get_evidence_page', 'list_research_datasets']);
  assert.equal(financialEvidence.auth, undefined);
  assert.deepEqual(financialEvidence.triggers(), {});
  assert.equal(action().requireAuth, false);
  const originalTlsSetting = process.env.NODE_TLS_REJECT_UNAUTHORIZED;
  const expected = page();
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls++;
    assert.equal(url.origin, 'https://agents.seiche.info');
    assert.equal(url.pathname, '/v1/research/api/v1/query');
    assert.equal(url.searchParams.get('entity'), 'A&B?limit=1000');
    assert.equal(url.searchParams.get('limit'), '1');
    assert.equal(options.method, 'GET');
    assert.equal(options.redirect, 'error');
    assert.equal(options.headers.Authorization, undefined);
    assert.ok(options.signal instanceof AbortSignal);
    return new Response(JSON.stringify(expected), { status: 200 });
  });
  assert.deepEqual(await run({ dataset: 'money_markets', entity: 'A&B?limit=1000', limit: 1 }), expected);
  assert.equal(calls, 1, 'next_offset does not cause hidden pagination');
  assert.equal(process.env.NODE_TLS_REJECT_UNAUTHORIZED, originalTlsSetting);
});

test('rejects invalid inputs before making network requests', async (t) => {
  t.mock.method(globalThis, 'fetch', () => assert.fail('invalid input reached network'));
  for (const input of [
    { dataset: 'https://other.example/' }, { entity: 'x'.repeat(101) }, { entity: null },
    { limit: 0 }, { limit: 101 }, { limit: 1.5 }, { limit: '25' },
    { offset: -1 }, { offset: 100001 }, { offset: NaN },
  ]) {
    await assert.rejects(run({ dataset: 'money_markets', ...input }), /Choose a supported dataset/);
  }
});

test('rejects schema drift, wrong datasets, excess rows and broken pagination', async (t) => {
  for (const change of [
    { schema: 'other' }, { dataset: 'bank_risk' }, { sources: undefined },
    { diagnostics: undefined }, { next_offset: undefined }, { next_offset: 0 },
    { results: [{ value: 1 }, { value: 2 }] },
  ]) {
    t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ ...page(), ...change })));
    await assert.rejects(run({ dataset: 'money_markets', limit: 1 }), /Unexpected research page contract/);
    t.mock.restoreAll();
  }
});

test('HTTP and transport failures remain failures with their original details', async (t) => {
  const errorBody = { error: 'upstream_unavailable', diagnostics: ['coverage unknown'] };
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(errorBody), { status: 503 }));
  await assert.rejects(run({ dataset: 'money_markets' }), (error) => {
    assert.ok(error instanceof ResearchResponseError);
    assert.equal(error.status, 503);
    assert.deepEqual(error.body, errorBody);
    return true;
  });
  t.mock.restoreAll();
  const networkError = new Error('TLS or network failed');
  t.mock.method(globalThis, 'fetch', async () => { throw networkError; });
  await assert.rejects(run({ dataset: 'money_markets' }), (error) => error === networkError);
});

test('catalog retains coverage metadata and rejects non-catalog content', async (t) => {
  const catalog = [{ id: 'money_markets', name: 'Money Markets', description: 'Published rates', filters: ['entity'], maximum_limit: 2000 }];
  t.mock.method(globalThis, 'fetch', async (url) => {
    assert.equal(url.href, 'https://agents.seiche.info/v1/research/api/v1/datasets');
    return new Response(JSON.stringify(catalog));
  });
  assert.deepEqual(await action('list_research_datasets').run({ propsValue: {} }), catalog);
  t.mock.restoreAll();
  t.mock.method(globalThis, 'fetch', async () => new Response('<html>Unavailable</html>', { status: 502 }));
  await assert.rejects(action('list_research_datasets').run({ propsValue: {} }), (error) => {
    assert.equal(error.status, 502);
    assert.equal(error.body, '<html>Unavailable</html>');
    return true;
  });
});
