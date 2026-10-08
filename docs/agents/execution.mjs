import {PaperSandbox} from './sandbox.mjs';
import {scenarios, evaluateEvidence} from './evidence-scenarios.mjs';
const desk = new PaperSandbox();
const $ = id => document.getElementById(id);
let assessment = null, lastOrderIntent = null;
for (const scenario of scenarios()) {
  const option = document.createElement('option'); option.value = scenario.id;
  option.textContent = scenario.label; $('scenario').append(option);
}
function renderEvidence() {
  const evidence = desk.evidence, decision = evaluateEvidence(evidence);
  const s = evidence.seiche, c = evidence.liquilens, u = evidence.undertow;
  $('scenario-clock').textContent = `${evidence.evaluated_at} · evidence revision ${desk.evidenceRevision}`;
  $('seiche-value').textContent = `${decision.pressure_bp} bp pressure / ${decision.regime}`;
  $('seiche-clocks').textContent = `Observed ${s.observed_at} · Retrieved ${s.retrieved_at}`;
  $('seiche-detail').textContent = `SOFR − IORB: ${s.sofr_minus_iorb_bp} bp. EFFR − IORB: ${s.effr_minus_iorb_bp} bp. Experimental operator bands: ≤5 CALM; >5 EROSION; >15 STRAIN; >25 STRESS. STRAIN and STRESS hold the proposal. This is not Seiche’s composite or a return forecast.`;
  $('liquilens-value').textContent = decision.reason_codes.some(code => code.startsWith('liquilens_')) ? 'CP observation outside the age limit' : 'Both CP observations within the age limit';
  $('liquilens-clocks').textContent = `Spread observed ${c.spread_observed_at} · Rollover observed ${c.rollover_observed_at} · Retrieved ${c.retrieved_at}`;
  $('undertow-value').textContent = `${u.worst_sell_cost_bps} bp hypothetical SELL cost / ${u.venue_spread_bps} bp venue spread`;
  $('undertow-clocks').textContent = `Observed ${u.observed_at} · Retrieved ${u.retrieved_at}`;
  $('undertow-rights').textContent = u.rights_status === 'approved_in_example_only' ? 'Permissions assumed for this synthetic example only.' : 'Permissions unknown: the evidence is unavailable.';
  $('evidence-decision').dataset.outcome = decision.outcome;
  $('evidence-outcome').textContent = `${decision.outcome}: ${decision.summary}`;
  $('evidence-reasons').textContent = decision.reason_codes.join(', ');
}
function render() {
  $('cash').textContent = desk.cash.toLocaleString('en-US', {style:'currency',currency:'USD'});
  $('btc').textContent = desk.btc.toFixed(8);
  $('journal').textContent = JSON.stringify(desk.snapshot(), null, 2);
  $('stop').textContent = desk.stopped ? 'Resume simulation' : 'Activate STOP';
  $('submit').disabled = !assessment || desk.stopped || assessment.decision.outcome !== 'pass' || assessment.evidence_revision !== desk.evidenceRevision;
  $('reconcile').disabled = !lastOrderIntent;
  renderEvidence();
}
function action(fn) { try { fn(); } catch(error) { $('status').textContent = error.message; } render(); }
$('scenario').addEventListener('change', () => action(() => {
  desk.setScenario($('scenario').value); assessment = null;
  $('preview').textContent = 'Evidence changed. Preview a new proposal to bind this revision.';
  $('status').textContent = 'Scenario changed. Earlier assessments remain in the export and cannot authorize a new submission.';
}));
for (const field of ['side','amount']) $(field).addEventListener('input', () => action(() => {
  assessment = null;
  $('preview').textContent = 'Proposal changed. Preview this side and amount before submitting.';
  $('status').textContent = 'Preview the updated proposal. Existing assessments remain in the journal.';
}));
$('proposal').addEventListener('submit', event => {
  event.preventDefault();
  action(() => {
    assessment = null;
    $('preview').textContent = 'No eligible proposal. Inspect the status and retained journal.';
    const intent = crypto.randomUUID();
    assessment = desk.assess(intent, $('side').value, Number($('amount').value));
    $('preview').textContent = JSON.stringify(assessment, null, 2);
    $('status').textContent = assessment.decision.outcome === 'pass' ? 'Preview saved for 60 seconds. Submit explicitly to simulate this exact order.' : `Assessment retained: ${assessment.decision.summary}`;
  });
});
$('submit').addEventListener('click', () => action(() => {
  const result = desk.submit(assessment.intent, {timeout:$('timeout').checked});
  lastOrderIntent = result.intent;
  $('status').textContent = result.state === 'uncertain' ? 'The simulated broker accepted the order, but its response timed out. Reconcile this intent; do not submit a replacement.' : 'Simulated fill recorded. Repeating this submission returns the same order.';
}));
$('reconcile').addEventListener('click', () => action(() => {
  desk.reconcile(lastOrderIntent);
  $('status').textContent = 'The existing simulated order was found and its fill recorded. No second order was created.';
}));
$('stop').addEventListener('click', () => action(() => { desk.stopped = !desk.stopped; $('status').textContent = desk.stopped ? 'STOP blocks new submissions. Existing orders remain available for reconciliation.' : 'Simulation resumed. Preview a new decision when ready.'; }));
$('export').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(desk.snapshot(),null,2)+'\n'],{type:'application/json'}));
  const link = document.createElement('a'); link.href=url; link.download='execution-simulation.json'; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
});
render();
