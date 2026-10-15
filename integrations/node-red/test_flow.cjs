#!/usr/bin/env node
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const base = __dirname;
const flow = JSON.parse(fs.readFileSync(path.join(base, 'financial-evidence.flow.json')));
const prepareCode = fs.readFileSync(path.join(base, 'functions/prepare.js'), 'utf8');
const validateCode = fs.readFileSync(path.join(base, 'functions/validate.js'), 'utf8');
const run = (code, msg) => vm.runInNewContext(`(function(msg){${code}\n})(input)`, {input: msg, Buffer}, {timeout: 1000});
const task = {dataset: 'money_markets', entity: 'USD', limit: 25, synthetic: true};
const hash = 'sha256:' + 'a'.repeat(64);
const source = {source_url: 'https://example.org/source', content_sha256: hash, retrieved_at: '2026-10-11T00:00:00Z', ok: true, source_reported: {state: [{name: 'response_status', value: 'PARTIAL'}]}};
const row = {dataset: 'money_markets', entity_id: 'USD', entity_name: 'USD', metric: 'example', value: null, unit: '%', as_of: '2026-10-10', source_status: 'UNAVAILABLE', availability: 'unavailable', source_url: source.source_url, source_field: '/value', observation_url: source.source_url, retrieved_at: source.retrieved_at, content_sha256: hash, published_at: null, knowledge_time: null, rights_status: null, context: 'An unavailable value is not zero.', transport_status: 'complete', evidence_status: 'not_evaluated', carrier_verification: 'not_performed', financial_authority: 'none'};
function page() {return {schema: 'liquidity-lab.openbb-table.v1', dataset: 'money_markets', results: [{...row}], total_rows: 1, returned_rows: 1, offset: 0, limit: 25, next_offset: null, transport_status: 'complete', status_semantics: 'transport_only', evidence_status: 'not_evaluated', carrier_verification: 'not_performed', absence_policy: 'Missing is never zero.', diagnostics: [], sources: [structuredClone(source)]};}
function message(body = page()) {return {task: {...task}, statusCode: 200, headers: {'content-type': 'application/json; charset=utf-8'}, payload: JSON.stringify(body)};}
const checks = [];
function test(name, fn) {fn(); checks.push(name);}
function rejected(msg) {const result = run(validateCode, msg); assert.equal(result[0], null); assert.equal(result[1].payload.status, 'response_rejected');}
test('all nodes are core and injects are manual', () => {
  const allowed = ['tab', 'comment', 'inject', 'function', 'http request', 'debug', 'catch'];
  assert(flow.every(n => allowed.includes(n.type)));
  for (const n of flow.filter(n => n.type === 'inject')) {assert.equal(n.once, false); assert.equal(n.repeat, ''); assert.equal(n.crontab, ''); assert.equal(JSON.parse(n.payload).synthetic, false);}
});
test('download identical and source embedded exactly', () => {
  assert.equal(fs.readFileSync(path.join(base, '../../docs/automations/node-red/financial-evidence.flow.json'), 'utf8'), fs.readFileSync(path.join(base, 'financial-evidence.flow.json'), 'utf8'));
  assert(flow.some(n => n.func === prepareCode)); assert(flow.some(n => n.func === validateCode));
});
test('request fixes host method headers and timeout', () => {
 const [m, e] = run(prepareCode, {payload: task, url: 'https://evil.example', headers: {Authorization: 'secret'}, arbitrary: 'x'});
 assert.equal(e, null); assert.equal(m.method, 'GET'); assert.equal(m.requestTimeout, 20000); assert.equal(m.followRedirects, false);
 assert.equal(new URL(m.url).origin, 'https://agents.seiche.info'); assert.equal(new URL(m.url).pathname, '/v1/research/api/v1/query'); assert.equal(m.headers['X-Financial-Evidence-Traffic-Class'], 'synthetic'); assert.equal(m.headers['X-Liquilens-Traffic-Class'], 'synthetic'); assert.equal(m.headers.Authorization, undefined); assert.equal(m.arbitrary, undefined); assert.equal(m.payload, undefined);
});
for (const patch of [{dataset: 'unknown'}, {limit: 0}, {limit: 201}, {limit: 1.5}, {entity: 'a'.repeat(101)}, {synthetic: 'true'}, {url: 'https://evil.example'}]) {
 test('bad configuration: ' + JSON.stringify(patch), () => assert.equal(run(prepareCode, {payload: {...task, ...patch}})[1].payload.status, 'request_rejected'));
}
test('entity query injection is encoded', () => assert.equal(new URL(run(prepareCode, {payload: {...task, entity: 'USD&limit=2000'}})[0].url).searchParams.get('limit'), '25'));
test('normal research is not labelled operator verification', () => assert.equal(run(prepareCode, {payload: {...task, synthetic: false}})[0].headers['X-Liquilens-Traffic-Class'], undefined));
test('unknown metadata and null value retained; source partial exposed', () => {
 const p = page(); p.extra_future_metadata = {a: null}; const v = run(validateCode, message(p))[0].payload;
 assert.equal(v.table.results[0].value, null); assert.equal(v.source_partial_reported, true); assert.equal(v.transport_complete, true); assert.equal(JSON.stringify(v.table), JSON.stringify(p));
});
test('more rows explicitly incomplete', () => {const p = page(); p.total_rows = 3; p.next_offset = 1; assert.equal(run(validateCode, message(p))[0].payload.pagination_complete, false);});
test('partial transport preserved as incomplete', () => {const p = page(); p.transport_status = 'partial'; assert.equal(run(validateCode, message(p))[0].payload.transport_complete, false);});
test('empty coverage remains empty with warning', () => {const p = page(); p.results = []; p.total_rows = p.returned_rows = 0; const v = run(validateCode, message(p))[0].payload; assert.equal(v.table.results.length, 0); assert(v.warnings.some(w => w.startsWith('No matching')));});
for (const [name, mutate] of [
 ['HTTP failure', m => m.statusCode = 503], ['redirect', m => m.statusCode = 302], ['HTML challenge', m => m.headers['content-type'] = 'text/html'], ['malformed JSON', m => m.payload = '{'], ['oversize response', m => m.payload = ' '.repeat(2*1024*1024+1)], ['overflow number', m => m.payload = m.payload.replace('"value":null', '"value":1e999')]
]) test(name, () => {const m = message(); mutate(m); rejected(m);});
for (const [name, mutate] of [
 ['wrong dataset', p => p.dataset = 'bank_risk'], ['schema drift', p => p.schema = 'wrong'], ['authority escalation', p => p.evidence_status = 'verified'], ['missing source', p => p.sources = []], ['source hash changed', p => p.sources[0].content_sha256 = 'sha256:'+'b'.repeat(64)], ['missing units', p => delete p.results[0].unit], ['rights dropped', p => delete p.results[0].rights_status], ['unavailable becomes zero', p => p.results[0].value = 0], ['pagination hidden', p => p.total_rows = 2], ['nonadvancing next', p => {p.total_rows=2;p.next_offset=0;}], ['missing diagnostics', p => delete p.diagnostics]
]) test(name, () => {const p=page(); mutate(p); rejected(message(p));});
console.log(JSON.stringify({status: 'passed', tests: checks.length, checks}, null, 2));
