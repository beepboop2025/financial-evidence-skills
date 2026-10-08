const {test} = require('node:test');
const assert = require('node:assert/strict');
const modulePromise = import('../docs/agents/sandbox.mjs');
const evidencePromise = import('../docs/agents/evidence-scenarios.mjs');
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
test('each product can refuse a proposal and every refusal survives export', async () => {
  const {PaperSandbox} = await modulePromise; const desk = new PaperSandbox(()=>1000);
  const cases = [
    ['funding-pressure','hold','seiche_regime_strain_held_by_policy'],
    ['stale-cp','unavailable','liquilens_cp_observation_stale_or_invalid'],
    ['missing-rights','unavailable','undertow_rights_manifest_not_approved'],
    ['expensive-exit','limit','max_exit_cost_bps_exceeded'],
  ];
  for (const [scenario,outcome,reason] of cases) {
    desk.setScenario(scenario);
    const result = desk.assess(scenario,'buy',1000);
    assert.equal(result.decision.outcome,outcome);
    assert.deepEqual(result.decision.reason_codes,[reason]);
    assert.throws(()=>desk.submit(scenario));
  }
  const exported = desk.snapshot();
  assert.equal(exported.assessments.length,4);
  assert.equal(exported.orders.length,0);
  assert.equal(exported.cash,100000);
  assert.equal(exported.btc,0);
  assert.equal(exported.assessments[1].evidence.liquilens.rollover_observed_at,'2026-09-30T00:00:00Z');
  exported.assessments[0].decision.outcome='pass';
  exported.assessments[0].evidence.seiche.sofr_minus_iorb_bp=0;
  assert.equal(desk.snapshot().assessments[0].decision.outcome,'hold');
  assert.equal(desk.snapshot().assessments[0].evidence.seiche.sofr_minus_iorb_bp,18);
});
test('evidence changes invalidate previews even when returning to the original example', async () => {
  const {PaperSandbox} = await modulePromise; const desk = new PaperSandbox(()=>1000);
  const original = desk.assess('old','buy',1000);
  desk.setScenario('missing-rights');
  assert.throws(()=>desk.submit('old'),/evidence changed/);
  desk.setScenario('eligible');
  assert.throws(()=>desk.submit('old'),/evidence changed/);
  assert.equal(desk.assess('old','buy',1000).evidence_revision,original.evidence_revision);
  assert.equal(desk.snapshot().assessments.length,1);
  desk.assess('new','buy',1000); desk.submit('new');
  desk.setScenario('funding-pressure'); desk.stopped=true;
  assert.equal(desk.submit('new').state,'filled');
  assert.equal(desk.orders.size,1);
  assert.equal(desk.cash,99000);
});
test('BUY identity and hypothetical SELL identity are distinct and evidence copies are detached', async () => {
  const {PaperSandbox} = await modulePromise; const desk = new PaperSandbox(()=>1000);
  const input = desk.evidence; input.undertow.rights_status='unknown';
  const result = desk.assess('entry','buy',1000);
  assert.equal(result.decision.outcome,'pass');
  assert.equal(result.side,'buy');
  assert.equal(result.liquidation_scenario.side,'sell');
  assert.equal(result.liquidation_scenario.parent_intent,result.intent);
  assert.notEqual(result.liquidation_scenario.intent,result.intent);
  assert.equal(result.liquidation_scenario.executable_quote,false);
  assert.equal(result.decision.execution_authority,false);
  result.evidence.undertow.worst_sell_cost_bps=500;
  result.decision.outcome='unavailable';
  desk.submit('entry');
  const sell = desk.assess('exit','sell',500);
  assert.equal(sell.side,'sell');
  assert.notEqual(sell.liquidation_scenario.intent,sell.intent);
  assert.equal(desk.snapshot().assessments[0].evidence.undertow.worst_sell_cost_bps,12);
});
test('account refusals are retained without allowing short sales', async () => {
  const {PaperSandbox} = await modulePromise; const desk = new PaperSandbox(()=>1000);
  assert.throws(()=>desk.assess('short','sell',1000),/insufficient/);
  assert.equal(desk.snapshot().assessments[0].decision.outcome,'unavailable');
  assert.deepEqual(desk.snapshot().assessments[0].decision.reason_codes,['insufficient_simulated_balance']);
  assert.throws(()=>desk.submit('short'),/insufficient/);
  assert.equal(desk.btc,0);
});
test('scenario clocks and threshold boundaries preserve the selected paper semantics', async () => {
  const {getScenario,evaluateEvidence,fundingRegime} = await evidencePromise;
  for (const [pressure,regime] of [[5,'CALM'],[5.01,'EROSION'],[15,'EROSION'],[15.01,'STRAIN'],[25,'STRAIN'],[25.01,'STRESS']]) assert.equal(fundingRegime(pressure),regime);
  const cp = getScenario('eligible');
  cp.liquilens.rollover_observed_at='2026-09-30T12:00:00Z';
  assert.equal(evaluateEvidence(cp).outcome,'unavailable'); // Exactly eight days is rejected.
  cp.liquilens.rollover_observed_at='2026-09-30T12:00:01Z';
  assert.equal(evaluateEvidence(cp).outcome,'pass');
  const exit = getScenario('eligible');
  exit.undertow.worst_sell_cost_bps=25; exit.undertow.venue_spread_bps=15;
  assert.equal(evaluateEvidence(exit).outcome,'pass');
  exit.undertow.observed_at='2026-10-08T11:55:00Z';
  assert.equal(evaluateEvidence(exit).outcome,'unavailable');
  const malformed = getScenario('eligible'); malformed.seiche.effr_minus_iorb_bp=null;
  assert.equal(evaluateEvidence(malformed).outcome,'unavailable');
  const fresh = getScenario('eligible'); fresh.liquilens.retrieved_at='2026-10-08T12:00:01Z';
  assert.equal(evaluateEvidence(fresh).outcome,'unavailable');
  assert.equal(getScenario('eligible').undertow.worst_sell_cost_bps,12);
});
test('uncertain orders remain reconcilable after evidence changes and STOP', async () => {
  const {PaperSandbox} = await modulePromise; const desk = new PaperSandbox(()=>1000);
  desk.assess('first','buy',1000); desk.submit('first',{timeout:true});
  desk.setScenario('missing-rights'); desk.stopped=true;
  desk.reconcile('first');
  assert.equal(desk.orders.size,1); assert.equal(desk.cash,99000);
  assert.equal(desk.snapshot().orders[0].state,'filled');
  assert.equal(desk.snapshot().orders[0].evidence.id,'eligible');
});
