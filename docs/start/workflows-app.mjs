import {TASKS, settings, apiURL, shareURL, run, rows, baseline, compare, reminder} from './workflows.mjs';
import {createMeasurement} from './measurement.mjs';
import {safeSource} from './desk.mjs';
const $ = id => document.getElementById(id), params = new URLSearchParams(location.search);
const operator = params.get('operator') === '1', measurement = createMeasurement({operator});
const STORAGE = 'financial-evidence-local-review-v1:';
let workflow = 'funding', current = null, controller = null;
function text(id,value) { $(id).textContent = value; }
function element(name,value) { const node = document.createElement(name); node.textContent = value; return node; }
function load() { try { const raw = localStorage.getItem(STORAGE + workflow); return raw && raw.length < 100000 ? JSON.parse(raw) : null; } catch { return null; } }
function choose(value, selection) {
  const selected = settings(value, selection), task = TASKS[value]; workflow = value; current = null;
  $('selection').value = selected.selection; text('selection-label',task.label); text('selection-hint',task.hint); text('run',`Run ${task.name.toLowerCase()}`);
  $('result-section').hidden = true; text('status', 'Run this check to retrieve the current published evidence.');
  for (const button of document.querySelectorAll('[data-workflow]')) button.setAttribute('aria-pressed',String(button.dataset.workflow === value));
}
try { choose(params.get('workflow') || 'funding', params.get('selection')); } catch (error) { text('status',error.message); }
for (const button of document.querySelectorAll('[data-workflow]')) button.addEventListener('click',() => { choose(button.dataset.workflow); $('selection').focus(); });
function busy(value) { for (const node of document.querySelectorAll('#run,#selection,[data-workflow]')) node.disabled = value; $('cancel').hidden = !value; text('run',value ? 'Retrieving evidence…' : `Run ${TASKS[workflow].name.toLowerCase()}`); }
$('workflow-form').addEventListener('submit',async event => {
  event.preventDefault(); let request;
  try { request = settings(workflow,$('selection').value); } catch (error) { text('status',error.message); return; }
  controller?.abort(); const active = new AbortController(); controller = active;
  const timer = setTimeout(() => active.abort(),45000); current = null; $('result-section').hidden = true; $('status').classList.remove('error'); busy(true); text('status','Retrieving original product evidence…');
  try {
    const value = await run(request,{token:measurement.token,synthetic:operator,signal:active.signal});
    if (active !== controller || active.signal.aborted) return;
    current = value; render(); text('status','Response ready. Inspect the source dates, coverage and limitations before using it.');
    $('results-title').focus({preventScroll:true}); $('result-section').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',block:'start'});
  } catch (error) { if (active === controller) { text('status',active.signal.aborted ? 'This request was cancelled or timed out. Run it again when ready.' : error.message); $('status').classList.add('error'); } }
  finally { clearTimeout(timer); if (active === controller) { controller = null; busy(false); } }
});
$('cancel').addEventListener('click',() => controller?.abort());
function render() {
  const task = TASKS[workflow], entries = rows(current), prior = load(), changes = compare(prior,current);
  text('result-product',task.product); text('results-title',task.name); text('prepared-state',current.prepared_response ? 'Evidence to review' : 'Review availability'); text('boundary',task.boundary);
  $('source-summary').replaceChildren(element('span',`Retrieved ${current.retrieved_at}. Original source: `));
  const link = element('a',task.product+' response ↗'); const safe = safeSource(current.source_url); if (safe) { link.href = safe; link.target = '_blank'; link.rel = 'noopener noreferrer'; } $('source-summary').append(link);
  const e = current.evidence;
  text('requests-summary',workflow === 'exit' ? (e.requests || []).map(item => `$${item.requested_size_usd}: ${item.match}; estimate ${item.estimate_at_requested_size}.`).join(' ') + ' ' + (e.method || '') : workflow === 'institutions' ? `Not covered: ${(e.not_covered || []).map(item => typeof item === 'string' ? item : JSON.stringify(item)).join(', ') || 'none in this selection'}. Full coverage: ${e.coverage_complete === true ? 'reported complete' : 'not established'}.` : `Transport: ${e.transport_status}. Evidence eligibility: ${e.evidence_status}. ${e.diagnostics?.length || 0} diagnostic entries retained below.`);
  text('comparison',changes ? `Compared with your saved review from ${prior.captured_at}: ${changes.changed.length} changed rows, ${changes.added.length} added, ${changes.removed.length} no longer returned. Comparison covers displayed values, dates and states; unchanged does not mean fresh.` : 'No baseline for this exact selection. Save this review to compare the next check.');
  $('columns').replaceChildren(...task.headers.map(value => { const th = element('th',value); th.scope = 'col'; return th; }));
  $('rows').replaceChildren();
  for (const entry of entries) {
    const tr = document.createElement('tr'); if (changes?.changed.includes(entry.id) || changes?.added.includes(entry.id)) tr.className = 'changed';
    for (const cell of entry.cells) tr.append(element('td',cell));
    const details = document.createElement('details'); details.append(element('summary','Evidence details'),element('pre',JSON.stringify(entry.details,null,2))); tr.lastChild.append(details); $('rows').append(tr);
  }
  text('original',JSON.stringify(current.evidence,null,2)); $('empty').hidden = entries.length > 0;
  text('api-example',`curl --fail '${apiURL(current)}'`); $('guide').href = task.guide; text('export-status',''); $('copy-fallback').hidden = true; $('result-section').hidden = false;
}
function download(data,name,type) { const url = URL.createObjectURL(new Blob([data],{type})), link = document.createElement('a'); link.href = url; link.download = name; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url),1000); }
async function copy(value,message) { try { await navigator.clipboard.writeText(value); text('export-status',message); } catch { $('copy-fallback').value = value; $('copy-fallback').hidden = false; $('copy-fallback').focus(); $('copy-fallback').select(); text('export-status','Copy the selected text below.'); } }
$('keep').addEventListener('click',() => { if (!current) return; try { localStorage.setItem(STORAGE+workflow,JSON.stringify(baseline(current))); render(); text('export-status','Baseline saved on this browser. Run this exact selection again to compare it.'); } catch { text('export-status','Browser storage is unavailable. Download the full evidence JSON instead.'); } });
$('clear').addEventListener('click',() => { try { localStorage.removeItem(STORAGE+workflow); if (current) render(); text('export-status','Saved baseline deleted from this browser.'); } catch { text('export-status','Browser storage could not be accessed.'); } });
$('download').addEventListener('click',() => { if (current) { download(JSON.stringify(current,null,2)+'\n',`${workflow}-${current.retrieved_at.slice(0,10)}.json`,'application/json'); text('export-status','Full evidence download prepared, including the original product response.'); } });
$('share').addEventListener('click',() => current && copy(shareURL(current),'Workflow link copied. The recipient can run a fresh check.'));
$('copy-api').addEventListener('click',() => current && copy(`curl --fail '${apiURL(current)}'`,'API request copied. No account or measurement key is required.'));
$('reminder').addEventListener('click',() => { if (current) { download(reminder(current),`${workflow}-daily-review.ics`,'text/calendar;charset=utf-8'); text('export-status','Calendar file prepared. Import it to enable 30 daily review reminders.'); } });
