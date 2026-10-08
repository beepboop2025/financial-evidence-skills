const {test} = require('node:test');
const assert = require('node:assert/strict');
const modulePromise = import('../docs/agents/sandbox.mjs');
test('simulation preserves intent identity and cannot double fill', async () => {
  const {PaperSandbox} = await modulePromise; const desk = new PaperSandbox(()=>1000);
  const preview=desk.assess('intent-1','buy',1000); preview.notional=100000;
  assert.equal(desk.submit('intent-1').notional,1000);
  desk.submit('intent-1'); assert.equal(desk.cash,99000); assert.equal(desk.orders.size,1);
  assert.throws(()=>desk.assess('intent-1','sell',1000),/another proposal/);
  assert.equal(desk.snapshot().broker_contacted,false);
});
test('timeout blocks replacement until original is reconciled without another fill', async () => {
  const {PaperSandbox} = await modulePromise; const desk = new PaperSandbox(()=>1000);
  desk.assess('first','buy',1000); desk.submit('first',{timeout:true});
  desk.assess('second','buy',500); assert.throws(()=>desk.submit('second'),/uncertain/);
  desk.stopped=true; desk.reconcile('first'); assert.equal(desk.cash,99000);
  assert.throws(()=>desk.submit('second'),/STOP/);
});
test('expiry, clock rollback, limits, quote changes and short sales are rejected', async () => {
  const {PaperSandbox} = await modulePromise; let now=1000; const desk=new PaperSandbox(()=>now);
  assert.throws(()=>desk.assess('short','sell',1000),/insufficient/);
  for(const amount of [0,-1,1001,NaN,Infinity]) assert.throws(()=>desk.assess('bad','buy',amount));
  desk.assess('first','buy',1000); now=61000; assert.throws(()=>desk.submit('first'),/expired/);
  now=0; assert.throws(()=>desk.submit('first'),/expired/);
  now=1000; desk.quote.ask++; assert.throws(()=>desk.submit('first'),/quote changed/);
  assert.equal(desk.cash,100000);
});
test('account changes invalidate outstanding previews and exports are detached', async () => {
  const {PaperSandbox} = await modulePromise; const desk = new PaperSandbox(()=>1000);
  desk.assess('first','buy',1000); desk.assess('second','buy',1000);
  desk.submit('first'); assert.throws(()=>desk.submit('second'),/account change/);
  const exported=desk.snapshot(); exported.orders[0].state='uncertain';
  assert.equal(desk.snapshot().orders[0].state,'filled');
});
