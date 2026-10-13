const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

test('central browser reads never enroll or forward legacy identity; explicit deletion stays at original issuer', async () => {
  const {createMeasurement} = await import('../docs/start/measurement.mjs');
  const key = 'fe_' + 'a'.repeat(43);
  let stored = JSON.stringify({token:key, created:Date.now(), enabled:true});
  const calls = [], controls = new Map();
  const prior = {document:global.document, localStorage:global.localStorage, fetch:global.fetch};
  global.document = {getElementById(id) {
    if (!controls.has(id)) controls.set(id, {addEventListener(event, handler) {this[event] = handler;}});
    return controls.get(id);
  }};
  global.localStorage = {getItem:()=>stored, setItem:(name,value)=>{stored=value;}, removeItem:()=>{stored=null;}};
  global.fetch = async (url, options) => {
    calls.push({url,options});
    return new Response(JSON.stringify({deleted:true}), {headers:{'content-type':'application/json'}});
  };
  try {
    const measurement = createMeasurement();
    assert.equal(measurement.token, '');
    assert.equal(calls.length, 0);
    assert.equal(JSON.parse(stored).enabled, false);
    assert.match(controls.get('measurement-status').textContent, /operational counts/);
    await controls.get('forget').click();
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, 'https://api.seiche.info/openbb/api/v1/applications/current');
    assert.equal(calls[0].options.method, 'DELETE');
    assert.equal(calls[0].options.headers.Authorization, 'Bearer '+key);
    assert.equal(stored, null);
  } finally {
    for (const [key,value] of Object.entries(prior)) {
      if (value === undefined) delete global[key]; else global[key] = value;
    }
  }
});

test('both desks disclose hosted counts and separate optional learning without enrollment checkbox', () => {
  for (const name of ['index.html','workflows.html']) {
    const html = fs.readFileSync(new URL('../docs/start/'+name, 'file://'+__filename), 'utf8');
    assert.match(html, /bounded product, tool and dataset demand/);
    assert.match(html, /Optional learning and task sharing require separate owner authorization/);
    assert.ok(!html.includes('id="measurement"'));
    assert.ok(html.includes('https://agents.seiche.info/connect'));
  }
});
