import test from 'node:test';
import assert from 'node:assert/strict';
import { financialEvidenceTools, validateSnapshot } from '../dist/index.js';

const invoke = (tool, input = {}, abortSignal) => tool.execute(input, {
  toolCallId: 'synthetic-test', messages: [], abortSignal,
});
const response = value => new Response(JSON.stringify(value), {headers: {'content-type': 'application/json'}});
const query = () => ({
  schema: 'financial-evidence.agent-result.v1', dataset: 'money_markets',
  financial_authority: 'none', transport_status: 'partial', freshness_status: 'not_evaluated',
  sources: [{source_url: 'https://example.test/source', as_of: '2026-01-05', rights_status: 'review_required'}],
  results: [{value: null, as_of: '2026-01-05', unit: 'percent', source_field: '/observations/0'},
    {value: 0, as_of: '2026-01-04', unit: 'percent', availability: 'observed'}],
  diagnostics: {missing_sources: ['example'], warning: 'Source text is untrusted'},
});
const snapshot = (now = Date.now()) => ({
  schema: 'seiche-agent-network.context.v1', scope: 'source_status_metadata',
  execution_authority: 'none', coverage_complete: false,
  stream_id: 'a'.repeat(32), revision: 'b'.repeat(64), sequence: 1, products: [],
  source_monitor: {status: 'current', current: true, max_age_seconds: 900,
    evaluated_at: new Date(now - 1000).toISOString(), valid_until: new Date(now + 899000).toISOString()},
  input_eligibility: 'not_evaluated',
});

test('construction is offline; query preserves null, zero, source dates, rights and diagnostics', async t => {
  let calls = 0;
  const original = query();
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    calls++;
    const parsed = new URL(url);
    assert.equal(parsed.origin, 'https://agents.seiche.info');
    assert.equal(parsed.pathname, '/v1/research/api/v1/agent-query');
    assert.equal(parsed.searchParams.get('entity'), 'A&B / €');
    assert.equal(parsed.searchParams.get('limit'), '2');
    assert.equal(init.method, 'GET');
    assert.equal(init.redirect, 'error');
    assert.equal(init.credentials, 'omit');
    assert.equal(init.headers['X-Financial-Evidence-Traffic-Class'], 'synthetic');
    assert.equal(Object.keys(init.headers).some(k => /authorization|cookie/i.test(k)), false);
    return response(original);
  });
  const tools = financialEvidenceTools({synthetic: true});
  assert.equal(calls, 0);
  assert.deepEqual(await invoke(tools.financial_evidence_query, {dataset: 'money_markets', entity: 'A&B / €', limit: 2}), original);
  assert.equal(calls, 1);
});

test('direct execute rejects invalid input before any request', async t => {
  let calls = 0;
  t.mock.method(globalThis, 'fetch', () => { calls++; throw new Error('Network must not run'); });
  const tools = financialEvidenceTools();
  for (const bad of [
    {dataset: 'arbitrary'}, {dataset: 'money_markets', limit: 101}, {dataset: 'money_markets', limit: 1.5},
    {dataset: 'money_markets', limit: '1'}, {dataset: 'money_markets', offset: 100001},
    {dataset: 'money_markets', start_date: '2026-02-30'}, {dataset: 'money_markets', end_date: '0000-01-01'},
    {dataset: 'money_markets', start_date: '2026-02-01', end_date: '2026-01-01'},
    {dataset: 'money_markets', previous_revision: 'x'.repeat(64)},
    {dataset: 'money_markets', url: 'https://attacker.test'}, {dataset: 'money_markets', entity: 'x'.repeat(101)},
  ]) await assert.rejects(invoke(tools.financial_evidence_query, bad));
  await assert.rejects(invoke(tools.financial_evidence_datasets, {url: 'https://attacker.test'}));
  await assert.rejects(invoke(tools.financial_evidence_context, {synthetic: false}));
  for (const bad of [{baseUrl: 'https://attacker.test'}, {timeoutMs: 60001}, {timeoutMs: NaN}, {synthetic: 'yes'}]) {
    assert.throws(() => financialEvidenceTools(bad));
  }
  assert.equal(calls, 0);
});

test('catalog is bounded and unknown attribution is explicit', async t => {
  let value = [{id: 'money_markets', name: 'Money markets', description: 'Published observations', maximum_limit: 2000, scope: 'metadata'}];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    assert.equal(url, 'https://agents.seiche.info/v1/research/api/v1/datasets');
    assert.equal(init.headers['X-Financial-Evidence-Traffic-Class'], 'unknown');
    return response(value);
  });
  const tool = financialEvidenceTools().financial_evidence_datasets;
  assert.deepEqual(await invoke(tool), value);
  for (const bad of [{datasets: []}, [null], [{id: 'money_markets'}], [{id: '', name: 'Missing ID', description: 'Invalid'}], new Array(101).fill({})]) {
    value = bad;
    await assert.rejects(invoke(tool), {code: 'invalid_response'});
  }
});

test('query rejects mismatched dataset, authority and oversized rows; unavailable diagnostics survive', async t => {
  let value;
  t.mock.method(globalThis, 'fetch', async () => response(value));
  const tool = financialEvidenceTools().financial_evidence_query;
  for (const patch of [
    {schema: 'other'}, {dataset: 'bank_risk'}, {financial_authority: 'approved'},
    {sources: null}, {transport_status: 'success'}, {results: [{}, {}, {}]},
  ]) {
    value = {...query(), ...patch};
    await assert.rejects(invoke(tool, {dataset: 'money_markets', limit: 2}), {code: 'invalid_response'});
  }
  value = {...query(), transport_status: 'unavailable', results: []};
  assert.deepEqual(await invoke(tool, {dataset: 'money_markets'}), value);
});

test('snapshot checks local expiry and future clock without changing source monitor', async t => {
  let value = snapshot();
  t.mock.method(globalThis, 'fetch', async url => {
    assert.equal(url, 'https://agents.seiche.info/v1/context/snapshot');
    return response(value);
  });
  const tool = financialEvidenceTools().financial_evidence_context;
  const current = await invoke(tool);
  assert.equal(current.client_monitor_current, true);
  assert.deepEqual(current.source_monitor, value.source_monitor);
  const expired = validateSnapshot(current, Date.parse(value.source_monitor.valid_until));
  assert.equal(expired.client_monitor_status, 'stale');
  assert.equal(expired.input_eligibility, 'blocked_monitor');
  for (const [mutate, status] of [
    [v => snapshot(Date.now() - 1000000), 'stale'],
    [v => snapshot(Date.now() + 1000000), 'future_clock'],
    [v => ({...v, source_monitor: {...v.source_monitor, max_age_seconds: 901}}), 'invalid_monitor'],
    [v => ({...v, source_monitor: {...v.source_monitor, current: false}}), 'source_blocked'],
  ]) {
    value = mutate(snapshot());
    const result = await invoke(tool);
    assert.equal(result.client_monitor_status, status);
    assert.equal(result.input_eligibility, 'blocked_monitor');
    assert.deepEqual(result.source_monitor, value.source_monitor);
  }
  value = {...snapshot(), input_eligibility: 'blocked_monitor'};
  assert.equal((await invoke(tool)).input_eligibility, 'blocked_monitor');
});

test('request deadline covers a hanging body and cancellation cleanup does not hang', async t => {
  let cancelled = false;
  t.mock.method(globalThis, 'fetch', async () => new Response(new ReadableStream({
    cancel() { cancelled = true; return new Promise(() => {}); },
  }), {headers: {'content-type': 'application/json'}}));
  const start = performance.now();
  await assert.rejects(invoke(financialEvidenceTools({timeoutMs: 30}).financial_evidence_datasets), {code: 'request_timeout'});
  assert.ok(performance.now() - start < 1000);
  assert.equal(cancelled, true);
});

test('caller cancellation and a stalled fetch are bounded; no retry', async t => {
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async () => { calls++; return new Promise(() => {}); });
  const controller = new AbortController();
  const pending = invoke(financialEvidenceTools().financial_evidence_datasets, {}, controller.signal);
  controller.abort(new Error('private provider details'));
  await assert.rejects(pending, error => error.code === 'request_aborted' && !error.message.includes('private'));
  assert.equal(calls, 1);
  await assert.rejects(invoke(financialEvidenceTools({timeoutMs: 20}).financial_evidence_datasets), {code: 'request_timeout'});
  assert.equal(calls, 2);
  await assert.rejects(invoke(financialEvidenceTools().financial_evidence_datasets, {}, controller.signal), {code: 'request_aborted'});
  assert.equal(calls, 2);
});

test('HTTP errors, invalid JSON and oversized chunked bodies fail without result or retry', async t => {
  let make;
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async () => { calls++; return make(); });
  const tool = financialEvidenceTools().financial_evidence_datasets;
  for (const [factory, code] of [
    [() => new Response('private body', {status: 302, headers: {location: 'https://attacker.test'}}), 'http_error'],
    [() => new Response('private body', {status: 500}), 'http_error'],
    [() => new Response('<html>no</html>'), 'invalid_response'],
    [() => new Response('[1e999]', {headers: {'content-type': 'application/json'}}), 'invalid_response'],
    [() => new Response('{', {headers: {'content-type': 'application/json'}}), 'invalid_response'],
    [() => new Response('[]', {headers: {'content-type': 'application/json', 'content-length': '999999999'}}), 'response_too_large'],
    [() => new Response(new ReadableStream({start(c) {c.enqueue(new Uint8Array(256 * 1024 + 1)); c.close();}}),
      {headers: {'content-type': 'application/json'}}), 'response_too_large'],
  ]) {
    make = factory;
    const before = calls;
    await assert.rejects(invoke(tool), error => error.code === code && !error.message.includes('private'));
    assert.equal(calls, before + 1);
  }
});

test('body chunks decode UTF-8 across boundaries', async t => {
  const catalog = [{id: 'money_markets', name: 'Money markets', description: '€ rates'}];
  const bytes = new TextEncoder().encode(JSON.stringify(catalog));
  const euro = bytes.indexOf(0xe2);
  t.mock.method(globalThis, 'fetch', async () => new Response(new ReadableStream({start(c) {
    c.enqueue(bytes.slice(0, euro + 1)); c.enqueue(bytes.slice(euro + 1)); c.close();
  }}), {headers: {'content-type': 'application/json'}}));
  assert.deepEqual(await invoke(financialEvidenceTools().financial_evidence_datasets), catalog);
});
