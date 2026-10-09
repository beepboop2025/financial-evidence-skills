const {test} = require('node:test');
const assert = require('node:assert/strict');
const mod = import('../docs/start/workflows.mjs');
const funding = {workflow:'funding',selection:'USD',retrieved_at:'2026-10-09T08:00:00Z',evidence:{schema:'financial-evidence.agent-result.v1',results:[{entity_id:'USD',entity_name:'US dollar',metric:'SOFR',source_field:'/rate',value:3.88,unit:'%',as_of:'2026-10-07',availability:'AVAILABLE',rights_status:'allowed'}]}};

test('bounded settings cannot inject URLs or calendar content',async () => {
 const {settings}=await mod;
 for (const [w,s] of [['funding','USD\nURL:x'],['exit','NaN'],['exit','0'],['institutions','../x'],['institutions','a,b,c,d,e,f']]) assert.throws(()=>settings(w,s));
 assert.deepEqual(settings('exit','10000.00,10000'),{workflow:'exit',selection:'10000'});
});
test('baseline compares only same query and retains unavailable transitions',async () => {
 const {baseline,compare}=await mod;
 const saved=baseline(funding), next=structuredClone(funding); next.evidence.results[0].value=null; next.evidence.results[0].availability='unavailable';
 assert.equal(compare(saved,next).changed.length,1);
 assert.equal(compare(saved,{...next,selection:'EUR'}),null);
 assert.equal(compare(saved,funding).changed.length,0);
 assert.equal(compare(saved,{...next,evidence:{...next.evidence,results:[]}}).removed.length,1);
});
test('shared URLs and reminder have no identity and opt-in finite recurrence',async () => {
 const {shareURL,reminder}=await mod;
 const url=shareURL({...funding,token:'secret'}); assert.ok(!url.includes('secret')); assert.ok(url.includes('workflow=funding'));
 const calendar=reminder(funding,new Date('2026-10-09T08:00:00Z'));
 assert.ok(calendar.includes('DTSTART;VALUE=DATE:20261010')); assert.ok(calendar.includes('RRULE:FREQ=DAILY;COUNT=30')); assert.ok(!calendar.includes('ATTENDEE'));
});
test('withheld exit costs remain unavailable and risk gaps stay visible',async () => {
 const {rows}=await mod;
 const exit={workflow:'exit',evidence:{schema:'undertow.crypto-workbench.v1',rungs:[{published_size_usd:10000,venues:[{venue:'test',status:'withheld',sell_cost_bps:null}]}]}};
 assert.equal(rows(exit)[0].cells[1],'Unavailable');
 const institutions={workflow:'institutions',evidence:{schema:'liquilens.institution-monitoring.v1',rows:[{slug:'a',name:'A',current_metrics:2,gaps:[{},{}],status:'insufficient_visibility'}]}};
 assert.equal(rows(institutions)[0].cells[1],'2 reviewed / 2 gaps');
});
test('browser uses bounded same-origin-independent read and rejects changed identity',async () => {
 const {run}=await mod; let options;
 const response={...funding,schema:'financial-evidence.workflow-result.v1',content_sha256:'a'.repeat(64)};
 const fetcher=async(url,opts)=>{options=opts; return new Response(JSON.stringify(response),{headers:{'content-type':'application/json'}});};
 await run(funding,{fetcher,synthetic:true}); assert.equal(options.headers['X-Liquilens-Traffic-Class'],'synthetic'); assert.equal(options.credentials,'omit'); assert.equal(options.redirect,'error');
 await assert.rejects(()=>run({...funding,selection:'EUR'},{fetcher}));
});
test('institution fingerprint detects evidence changes behind identical summary counts',async () => {
 const {baseline,compare,rows}=await mod;
 const initial={workflow:'institutions',selection:'au-sfb',evidence:{schema:'liquilens.institution-monitoring.v1',rows:[{slug:'au-sfb',name:'AU',current_metrics:2,gaps:[],status:'insufficient_visibility',content_sha256:'a'.repeat(64)}]}};
 const saved=baseline(initial), next=structuredClone(initial); next.evidence.rows[0].content_sha256='b'.repeat(64);
 const result=compare(saved,next);
 assert.deepEqual(result.changed,['au-sfb']); assert.ok(result.details[0].fields[0].label.includes('aging'));
 assert.equal(rows(next)[0].url,'https://api.liquilens.in/api/experimental/v1/banking/monitoring/institutions/au-sfb');
 assert.equal(compare(saved,initial).changed.length,0);
});
test('old baselines disclose reduced comparison and corrupt baselines are ignored',async () => {
 const {baseline,compare}=await mod; const saved=baseline(funding);
 saved.schema='financial-evidence.local-review.v1'; assert.equal(compare(saved,funding).legacy,true);
 saved.rows=[null]; assert.equal(compare(saved,funding),null);
 saved.rows=[{id:'x',cells:[]}]; assert.equal(compare(saved,funding),null);
});
