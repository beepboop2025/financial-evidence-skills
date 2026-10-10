import test from 'node:test';
import assert from 'node:assert/strict';
import {parseSeries, seriesURL, loadSeries, noteFor} from './reference-fx.mjs';
const fixture = '# source: ecb_fx, unit: USD/EUR, cadence: daily\n# retrieved_at: 2026-10-10T16:07:22+00:00, last_observation: 2026-10-09, staleness: fresh\n# Source: European Central Bank. Reference data is freely available from the ECB; not executable quotes.\ndate,value\n2026-10-08,1.1186\n2026-10-09,1.1206\n';
test('preserves exact decimal string, dates and provenance in saved note',()=>{
  const data=parseSeries(fixture,'USD');assert.equal(data.rows[1].value,'1.1206');
  assert.match(noteFor(data,'2026-10-11T00:00:00Z'),/European Central Bank/);
  assert.match(noteFor(data,'2026-10-11T00:00:00Z'),/2026-10-09,1.1206/);
});
test('rejects arbitrary source selection',()=>assert.throws(()=>seriesURL('../private')));
test('does not turn blanks, null, NaN or zero into observations',()=>{
  for(const value of ['', 'null', 'NaN', '0']) assert.throws(()=>parseSeries(fixture.replace('1.1206',value),'USD'));
});
test('rejects source notice, clock, unit and date corruption',()=>{
  for(const text of [fixture.replace('freely available',''),fixture.replace('USD/EUR','EUR/USD'),fixture.replace('last_observation: 2026-10-09','last_observation: 2026-10-08'),fixture.replace('2026-10-08,','2026-02-30,'),fixture.replace('2026-10-08,','2026-10-09,')]) assert.throws(()=>parseSeries(text,'USD'));
});
test('fetches only fixed public CSV without account credentials or referrer',async()=>{
  const parsed=await loadSeries('USD',async(url,options)=>{
    assert.equal(url,seriesURL('USD'));assert.equal(options.credentials,'omit');assert.equal(options.method,'GET');assert.equal(options.referrerPolicy,'no-referrer');
    return {ok:true,headers:new Headers({'Content-Type':'text/csv'}),text:async()=>fixture};
  });assert.equal(parsed.rows.length,2);
});
test('fails explicitly on access restrictions and non-CSV responses',async()=>{
  await assert.rejects(loadSeries('USD',async()=>({ok:false,status:451})),/451/);
  await assert.rejects(loadSeries('USD',async()=>({ok:true,headers:new Headers({'Content-Type':'text/html'})})),/CSV/);
});
