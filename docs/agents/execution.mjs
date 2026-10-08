import {PaperSandbox} from './sandbox.mjs';
const desk = new PaperSandbox();
const $ = id => document.getElementById(id);
let assessment = null, lastOrderIntent = null;
function render() {
  $('cash').textContent = desk.cash.toLocaleString('en-US', {style:'currency',currency:'USD'});
  $('btc').textContent = desk.btc.toFixed(8);
  $('journal').textContent = JSON.stringify(desk.snapshot(), null, 2);
  $('stop').textContent = desk.stopped ? 'Resume simulation' : 'Activate STOP';
  $('submit').disabled = !assessment || desk.stopped;
  $('reconcile').disabled = !lastOrderIntent;
}
function action(fn) { try { fn(); } catch(error) { $('status').textContent = error.message; } render(); }
$('proposal').addEventListener('submit', event => {
  event.preventDefault();
  action(() => {
    assessment = null;
    const intent = crypto.randomUUID();
    assessment = desk.assess(intent, $('side').value, Number($('amount').value));
    $('preview').textContent = JSON.stringify(assessment, null, 2);
    $('status').textContent = 'Preview saved for 60 seconds. Submit explicitly to simulate this exact order.';
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
