const {test} = require('node:test');
const assert = require('node:assert/strict');
const desk = import('../docs/start/desk.mjs');
const source = {source_url:'https://example.org/data', content_sha256:'a'.repeat(64), ok:true};
function page(offset, count, total = 201) {
  return {schema:'liquidity-lab.openbb-table.v1', dataset:'bank_risk', offset, limit:200, total_rows:total, returned_rows:count, next_offset:offset + count < total ? offset + count : null, transport_status:'complete', status_semantics:'transport_only', evidence_status:'not_evaluated', carrier_verification:'not_performed', sources:[source], diagnostics:[], results:Array.from({length:count}, (_, i) => ({dataset:'bank_risk',entity_id:String(offset+i),metric:'ratio',value:i ? null : 0,unit:'percent',as_of:'2026-06-30',availability:i ? 'unavailable' : 'published',source_url:source.source_url}))};
}
function response(value) { return new Response(JSON.stringify(value), {headers:{'Content-Type':'application/json'}}); }
test('complete capture follows pagination, preserves null and zero, and excludes credentials from output', async () => {
  const {capture} = await desk; let calls = 0;
  const result = await capture({dataset:'bank_risk'}, {token:'secret', synthetic:true, fetcher:async (url, options) => {
    assert.equal(options.headers.Authorization, 'Bearer secret'); assert.equal(options.headers['X-Liquilens-Traffic-Class'], 'synthetic');
    const offset = Number(new URL(url).searchParams.get('offset')); calls++;
    return response(page(offset, offset ? 1 : 200));
  }});
  assert.equal(calls, 2); assert.equal(result.returned_rows, 201); assert.equal(result.results[0].value, 0); assert.equal(result.results[1].value, null);
  assert.ok(!JSON.stringify(result).includes('secret'));
});
test('changed source or total cannot produce a mixed complete capture', async () => {
  const {capture} = await desk;
  for (const mutation of [p => p.sources = [{...source, content_sha256:'b'.repeat(64)}], p => p.total_rows = 202]) {
    let calls = 0;
    await assert.rejects(capture({dataset:'bank_risk'}, {fetcher:async () => { const value = calls++ ? page(200, 1) : page(0, 200); if(calls > 1) mutation(value); return response(value); }}), /source changed/);
  }
});
test('partial, truncated, malformed and non-advancing results cannot be exported', async () => {
  const {capture} = await desk;
  for (const mutate of [p => p.transport_status='partial', p => p.next_offset=null, p => p.next_offset=0, p => p.results[0].value='0', p => p.sources=[], p => p.results[0].source_url='javascript:alert(1)']) {
    const value = page(0,200); mutate(value);
    await assert.rejects(capture({dataset:'bank_risk'}, {fetcher:async()=>response(value)}));
  }
});
test('empty matches retain a valid empty capture without inventing observations', async () => {
  const {capture, summary} = await desk;
  const value = await capture({dataset:'bank_risk'}, {fetcher:async()=>response(page(0,0,0))});
  assert.deepEqual(summary(value), {total:0,available:0,earliest:null,latest:null});
});
test('CSV protects formulas and preserves numeric negatives, zero and missingness', async () => {
  const {csv} = await desk;
  const text = csv({results:[{entity_name:'\t=HYPERLINK("evil")',value:0},{entity_name:'safe',value:-3},{entity_name:'+SUM(1)',value:null}]});
  assert.ok(text.includes('"\'\t=HYPERLINK(""evil"")"'));
  assert.ok(text.includes('"-3"')); assert.ok(text.includes('"0"')); assert.ok(text.includes('"\'+SUM(1)"'));
});
test('sharing contains only validated query fields and fixed attribution, never keys or operator labels', async () => {
  const {viewLink, querySettings, safeSource} = await desk;
  const link = new URL(viewLink({dataset:'bank_risk', entity:'ESAF', token:'private', operator:'1', utm_source:'private'}));
  assert.deepEqual([...link.searchParams.keys()], ['dataset','entity','utm_source','utm_medium']);
  assert.ok(!link.href.includes('private')); assert.equal(safeSource('javascript:alert(1)'),null);
  for(const date of ['2026-02-31','wrong']) assert.throws(()=>querySettings({start_date:date}));
});
test('network challenges, numeric overflow and oversized response bodies fail explicitly', async () => {
  const {readJSON, MAX_BYTES} = await desk;
  await assert.rejects(readJSON(new Response('<html>',{headers:{'Content-Type':'text/html'}})), /challenge/);
  await assert.rejects(readJSON(new Response('{"value":1e999}',{headers:{'Content-Type':'application/json'}})), /non-finite/);
  await assert.rejects(readJSON(new Response(' '.repeat(MAX_BYTES+1),{headers:{'Content-Type':'application/json'}})), /exceeded/);
});
