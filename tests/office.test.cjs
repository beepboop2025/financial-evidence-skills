const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const E = require('../docs/office/office-core.js');
const W = require('../docs/office/workbook.js');
const {row,funding,institutions} = require('./office-fixtures.cjs');
const request = () => E.plan({currencies:'USD'})[0];
const sheet = (capture,name) => capture.sheets.find(s=>s.name===name).rows;

test('range selection is bounded, deduplicated and fixed to public endpoints',()=>{
  const requests=E.plan({currencies:[['usd'],['EUR'],[''],['USD']],institutions:'au-sfb,au-sfb'});
  assert.equal(requests.length,3);
  assert.equal(requests[0].url,'https://agents.seiche.info/v1/research/api/v1/workflow?workflow=funding&selection=USD');
  for(const options of [{},{currencies:'USDD'},{institutions:'../local'},{currencies:['USD','EUR','INR','GBP','JPY','CHF']},{currencies:[[1]]},{datasets:['private']}]) assert.throws(()=>E.plan(options));
});
test('numeric zero, missingness, negative values and explicit restrictions remain distinct',()=>{
  const value=E.project(request(),funding('USD',[row(0),row(null),row(-1),row(99,{rights_status:'derived-only'}),row(99,{publication_allowed:false})]));
  assert.deepEqual(value.data.map(r=>[r.value,r.value_state]),[[0,'number'],['','null'],[-1,'number'],['','withheld_by_client'],['','withheld_by_client']]);
  assert.equal(value.data[0].as_of,'2026-10-15');
  assert.match(value.status.sources_json,/PARTIAL/);
});
test('transport and pagination remain visible independently',()=>{
  const v=funding(); v.evidence.transport_status='partial';v.evidence.total_rows=101;v.evidence.results=Array.from({length:100},()=>row());v.evidence.returned_rows=100;v.evidence.next_offset=100;
  const p=E.project(request(),v);assert.equal(p.status.transport_status,'partial');assert.equal(p.status.page_scope,'partial_dataset_page');assert.equal(p.status.next_offset,100);
  v.evidence.next_offset=null;assert.throws(()=>E.project(request(),v));
});
test('mismatched identity, authority, values and provenance fail before display',()=>{
  for(const mutate of [v=>v.selection='EUR',v=>v.evidence.schema='other',v=>v.evidence.results[0].value='3.9',v=>v.evidence.results[0].value=Infinity,v=>v.evidence.results[0].financial_authority='credit',v=>v.evidence.sources=[],v=>v.evidence.returned_rows=2,v=>v.content_sha256='none',v=>v.evidence.results[0].context='x'.repeat(30001)]) {
    const v=funding();mutate(v);assert.throws(()=>E.project(request(),v));
  }
});
test('unknown institutions are explicit and coverage gaps survive export',()=>{
  const r=E.plan({institutions:'au-sfb,unknown-bank'})[0], p=E.project(r,institutions());
  assert.equal(p.banks.length,2);assert.equal(p.banks[1].status,'not_covered');assert.equal(p.banks[1].current_metrics,undefined);
  assert.equal(p.gaps[0].field,'withdrawals');assert.equal(p.status.coverage_complete,false);
  for(const mutate of [v=>v.evidence.not_covered=[],v=>v.evidence.not_covered=['au-sfb'],v=>v.evidence.can_authorize_credit=true,v=>v.evidence.rows[0].slug='different']) {const v=institutions();mutate(v);assert.throws(()=>E.project(r,v));}
});
test('source strings cannot execute through CSV or HTML; genuine numeric negatives stay numeric',()=>{
  assert.equal(E.csv([['=SUM(1,2)',' +cmd','@formula',-2,null]]),'"\'=SUM(1,2)","\' +cmd","\'@formula","-2",""\r\n');
  const capture=E.bundle([E.project(request(),funding('USD',[row(0,{entity_name:'<script>alert(1)</script>'})]))]);
  assert.ok(!E.html(capture).includes('<script>'));assert.ok(E.html(capture).includes('&lt;script&gt;'));
});
test('a failed currency does not hide successful requests or substitute an old capture',async()=>{
  const calls=[];const capture=await E.run({currencies:'USD,EUR',verification:true,fetcher:async(url,options)=>{
    calls.push([url,options]);if(url.endsWith('EUR'))return new Response('private provider body',{status:503});
    return new Response(JSON.stringify(funding()),{headers:{'Content-Type':'application/json'}});
  }});
  assert.equal(sheet(capture,'Funding').length,2);assert.equal(capture.requests[1].status.request_status,'failed');
  assert.ok(!JSON.stringify(capture).includes('private provider body'));assert.equal(calls[0][1].headers['X-Liquilens-Traffic-Class'],'synthetic');
  assert.equal(calls[0][1].redirect,'error');assert.equal(calls[0][1].credentials,'omit');
});
test('browser transport refuses oversized, redirected, non-JSON and malformed bodies',async()=>{
  for(const fetcher of [async()=>new Response('x'.repeat(4*1024*1024+1),{headers:{'Content-Type':'application/json'}}),async()=>new Response('{}',{status:302}),async()=>new Response('<html>challenge</html>'),async()=>new Response('{bad',{headers:{'Content-Type':'application/json'}})]) {
    const capture=await E.run({currencies:'USD',fetcher});assert.equal(capture.requests[0].status.request_status,'failed');assert.equal(sheet(capture,'Funding').length,1);
  }
});
test('Google functions share the same contract, keep refresh cells private and spill rectangular tables',()=>{
  const calls=[];const context=vm.createContext({UrlFetchApp:{fetchAll(requests){calls.push(...requests);return requests.map(r=>{
    const u=new URL(r.url),v=u.searchParams.get('workflow')==='funding'?funding(u.searchParams.get('selection')):institutions(),raw=JSON.stringify(v);
    return {getResponseCode:()=>200,getHeaders:()=>({'Content-Type':'application/json'}),getContent:()=>({length:Buffer.byteLength(raw)}),getContentText:()=>raw};
  });}}});
  vm.runInContext(fs.readFileSync('docs/office/FinancialEvidenceOffice.gs','utf8'),context);
  const rows=context.FINANCIAL_FUNDING([['USD'],['EUR'],['']], 'private refresh token');
  assert.equal(calls.length,2);assert.ok(rows.every(r=>r.length===25));assert.ok(!JSON.stringify(calls).includes('private refresh'));
  assert.equal(calls[0].followRedirects,false);assert.equal(calls[0].validateHttpsCertificates,true);
  const banks=context.FINANCIAL_WATCHLIST('au-sfb,unknown-bank',1);assert.ok(banks.every(r=>r.length===17));assert.match(JSON.stringify(banks),/withdrawals/);assert.match(JSON.stringify(banks),/not_covered/);
  assert.throws(()=>context.FINANCIAL_FUNDING('USD',[[1]]));
});
test('Google failures retain a visible status and do not leak provider errors',()=>{
  const context=vm.createContext({UrlFetchApp:{fetchAll:()=>[{getResponseCode:()=>429,getHeaders:()=>({'Content-Type':'application/json'}),getContent:()=>({length:5}),getContentText:()=>'{bad'}]}});
  vm.runInContext(fs.readFileSync('docs/office/FinancialEvidenceOffice.gs','utf8'),context);
  const rows=context.FINANCIAL_FUNDING('USD',1);assert.match(JSON.stringify(rows),/failed/);assert.ok(!JSON.stringify(rows).includes('{bad'));
});
test('workbooks are genuine ZIP containers; formula-looking cells stay typed strings',()=>{
  const capture=E.bundle([E.project(request(),funding('USD',[row(0,{context:'=1+1'})]))]);
  for(const bytes of [W.ods(capture),W.xlsx(capture)]) assert.equal(Buffer.from(bytes).subarray(0,4).toString('hex'),'504b0304');
  assert.ok(Buffer.from(W.xlsx(capture)).includes(Buffer.from('t="s"')));assert.ok(!Buffer.from(W.xlsx(capture)).includes(Buffer.from('<f>')));
  assert.ok(!Buffer.from(W.ods(capture)).includes(Buffer.from('table:formula=')));
});
