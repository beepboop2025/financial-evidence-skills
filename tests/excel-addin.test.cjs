const test=require('node:test'),assert=require('node:assert/strict');
const E=require('../docs/office/office-core.js'),I=require('../docs/office/excel/insert.js');
const {row,funding,institutions}=require('./office-fixtures.cjs');
function capture(){const r=E.plan({currencies:'USD',institutions:'au-sfb,unknown-bank'});return E.bundle([E.project(r[0],funding('USD',[row(0,{entity_name:'=2+3'}),row(null),row(-2),row(99,{rights_status:'restricted'})])),E.project(r[1],institutions())]);}
function excel(fail=false){
 const calls=[],ranges={},existing={name:'My analysis'};Object.defineProperty(existing,'getRange',{get(){throw Error('Existing cells must not be accessed');}});
 let count=0;
 const worksheets={
   items:[existing],
   load(value){calls.push(['load',value]);},
   add(name){calls.push(['add',name]);return {getRange(address){return ranges[name+':'+address]??={format:{fill:{},font:{}}};}};}
 };
 const context={workbook:{worksheets},async sync(){calls.push(['sync']);if(fail&&++count===2)throw Error('Simulated partial Office batch');}};
 return {api:{run:fn=>fn(context)},calls,ranges};
}
test('keeps zeros, negative numbers, missingness, rights and hostile text distinct',()=>{
 const plans=I.prepare(capture(),[],'1018090000'),p=plans[1],headers=p.values[0],value=headers.indexOf('value'),entity=headers.indexOf('entity_name');
 assert.equal(p.values[1][value],0);assert.equal(p.values[2][value],'');assert.equal(p.values[3][value],-2);assert.equal(p.values[4][value],'');
 assert.equal(p.values[1][entity],"'=2+3");assert.equal(p.formats[1][entity],'@');assert.equal(p.formats[1][value],'General');
 const institution=plans[2];assert.equal(institution.values[1][institution.values[0].indexOf('coverage_complete')],false);
 assert.ok(plans[3].values.some(r=>r.includes('No current reviewed disclosure')));
 assert.ok(plans[5].values.some(r=>r.includes('["unknown-bank"]')));
});
test('repeated insertions allocate unique case-insensitive names of at most31 characters',()=>{
 const first=I.prepare(capture(),[],'1018090000');const second=I.prepare(capture(),first.map(p=>p.name.toUpperCase()),'1018090000');
 assert.equal(new Set([...first,...second].map(p=>p.name.toLowerCase())).size,12);assert.ok(second.every(p=>p.name.length<=31&&p.name.endsWith(' 2')));
});
test('rejects malformed tables and oversized batches before creating any worksheet',async()=>{
 for(const mutate of [c=>c.sheets.reverse(),c=>c.sheets[1].rows[1].pop(),c=>c.sheets[1].rows=Array.from({length:1001},()=>c.sheets[1].rows[0]),c=>c.sheets[1].rows=Array.from({length:200},()=>Array(25).fill('a'.repeat(1000)))]){
 const c=capture();mutate(c);const x=excel();await assert.rejects(I.insert(c,x.api,'1'));assert.equal(x.calls.filter(r=>r[0]==='add').length,0);
 }
});
test('reads sheet names only and writes six fresh sheets with explicit cell formats',async()=>{
 const x=excel(),names=await I.insert(capture(),x.api,'1018090000');assert.equal(names.length,6);assert.deepEqual(x.calls[0],['load','items/name']);assert.equal(x.calls.filter(r=>r[0]==='add').length,6);assert.equal(x.calls.filter(r=>r[0]==='sync').length,2);
 const range=Object.values(x.ranges).find(r=>r.values?.[0]?.includes('value_state'));assert.equal(range.values[1][6],0);assert.equal(range.numberFormat[1][6],'General');
});
test('reports partial writes without deleting or overwriting sheets on failure',async()=>{
 const x=excel(true);await assert.rejects(I.insert(capture(),x.api,'1'),/some may be incomplete/);assert.equal(x.calls.filter(r=>r[0]==='add').length,6);
});
