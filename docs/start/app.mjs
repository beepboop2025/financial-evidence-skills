import {BASE, capture, citations, csv, querySettings, readJSON, safeSource, summary, viewLink} from './desk.mjs';

const $ = id => document.getElementById(id);
const operator = new URLSearchParams(location.search).get('operator') === '1';
const STORAGE = 'financial-evidence-research-measurement-v1';
let current = null, controller = null, shown = 0, identity = null;
const presets = {bank: {dataset:'bank_risk', entity:'ESAF'}, funding: {dataset:'money_markets', entity:'USD'}, liquidity: {dataset:'market_liquidity', entity:''}};

function message(id, text) { $(id).textContent = text; }
function element(name, text, className = '') { const node = document.createElement(name); node.textContent = text; if (className) node.className = className; return node; }
function sourceLink(url, text) { const link = element('a', text); const safe = safeSource(url); if (safe) { link.href = safe; link.target = '_blank'; link.rel = 'noopener noreferrer'; } return link; }
function settings() { return querySettings(Object.fromEntries(['dataset','entity','start_date','end_date'].map(key => [key, $(key).value]))); }
function apply(value) { for (const key of ['dataset','entity','start_date','end_date']) $(key).value = value[key] || ''; }
function saveIdentity() { try { if (identity) localStorage.setItem(STORAGE, JSON.stringify(identity)); else localStorage.removeItem(STORAGE); } catch { message('measurement-status', 'Browser storage is unavailable. Your choice applies to this visit only.'); } }
try {
  const saved = JSON.parse(localStorage.getItem(STORAGE) || 'null');
  if (saved && /^fe_[A-Za-z0-9_-]{43}$/.test(saved.token) && Number.isFinite(saved.created)) {
    identity = saved;
    identity.enabled = saved.enabled === true && Date.now() - saved.created < 30 * 86400000 && saved.created <= Date.now();
  }
} catch { /* Optional storage cannot prevent research. */ }
$('measurement').checked = !operator && identity?.enabled === true;
if (operator) { $('measurement').disabled = true; message('measurement-status', 'Operator verification: optional visitor measurement is disabled; requests are labelled synthetic.'); }
try {
  const params = Object.fromEntries(new URLSearchParams(location.search));
  if (params.dataset) apply(querySettings(params));
} catch (error) { message('status', error.message); }

for (const button of document.querySelectorAll('[data-preset]')) button.addEventListener('click', () => {
  apply(presets[button.dataset.preset]);
  for (const item of document.querySelectorAll('[data-preset]')) item.setAttribute('aria-pressed', String(item === button));
  message('status', 'Starting point selected. Run this research to retrieve the current published evidence.');
  $('run').focus();
});

function busy(value) {
  for (const item of document.querySelectorAll('#research-form input, #research-form select, #run, [data-preset]')) item.disabled = value;
  $('cancel').hidden = !value;
  $('run').textContent = value ? 'Loading evidence…' : 'Run this research';
}

$('research-form').addEventListener('submit', async event => {
  event.preventDefault();
  let selected;
  try { selected = settings(); } catch (error) { message('status', error.message); return; }
  controller?.abort(); const active = new AbortController(); controller = active;
  const timeout = setTimeout(() => active.abort(), 90000);
  current = null; $('result-section').hidden = true; $('status').classList.remove('error'); busy(true);
  message('status', 'Retrieving the selected evidence and checking source identities…');
  try {
    const result = await capture(selected, {signal: active.signal, synthetic: operator, token: !operator && $('measurement').checked && identity?.enabled ? identity.token : '', progress: (count, total) => message('status', `Retrieved ${count} of ${total} rows. Checking pagination and source consistency…`)});
    if (active !== controller || active.signal.aborted) return;
    current = result; render(result);
    message('status', result.returned_rows ? 'Capture ready. Review the observation dates and gaps before using the values.' : 'No covered observations match this filter. This does not establish a low-risk or empty market.');
    $('results-title').focus({preventScroll: true});
    $('result-section').scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
  } catch (error) {
    if (active !== controller) return;
    message('status', active.signal.aborted ? 'The review was cancelled or timed out. Run it again when ready.' : error.message || 'The service could not be reached. Please retry later.');
    $('status').classList.add('error');
  } finally { clearTimeout(timeout); if (active === controller) { controller = null; busy(false); } }
});
$('cancel').addEventListener('click', () => controller?.abort());

function render(value) {
  const info = summary(value); shown = 0;
  message('description', value.pages[0].description);
  message('row-count', String(info.total)); message('available-count', String(info.available));
  message('date-range', info.earliest ? `${info.earliest} → ${info.latest}` : 'Not reported');
  $('rows').replaceChildren(); $('sources').replaceChildren();
  message('diagnostics', `${value.pages.reduce((sum, page) => sum + page.diagnostics.length, 0)} diagnostic entries are retained in the JSON. Inspect them before interpreting coverage.`);
  $('diagnostics').hidden = !value.pages.some(page => page.diagnostics.length);
  for (const source of value.pages[0].sources) {
    const article = document.createElement('article');
    article.append(element('h3', source.product || source.topic), sourceLink(source.source_url, source.source_url));
    article.append(element('p', `Retrieved: ${source.retrieved_at || 'unknown'}. Retrieval time is not an observation date.`));
    article.append(element('pre', JSON.stringify({content_sha256:source.content_sha256, source_reported:source.source_reported, financial_authority:source.financial_authority}, null, 2)));
    $('sources').append(article);
  }
  message('export-status', ''); $('copy-fallback').hidden = true; $('result-section').hidden = false;
  renderMore();
}

function renderMore() {
  if (!current) return;
  for (const row of current.results.slice(shown, shown + 100)) {
    const tr = document.createElement('tr'), entity = document.createElement('td');
    entity.append(element('strong', row.entity_name || row.entity_id || 'Source'), element('span', `${row.entity_id || ''} · ${row.metric || 'availability'}`, 'metric'));
    const numeric = row.value === null ? 'Unavailable' : `${row.value} ${row.unit || ''}`;
    const value = element('td', numeric); if (row.value === null) value.className = 'missing';
    const evidence = document.createElement('td');
    evidence.append(sourceLink(safeSource(row.observation_url) || row.source_url, row.observation_url ? 'Original / scope source ↗' : 'Source response ↗'));
    const details = document.createElement('details'); details.append(element('summary', 'Dates, rights and context'));
    details.append(element('pre', JSON.stringify({source_status:row.source_status, published_at:row.published_at, knowledge_time:row.knowledge_time, retrieved_at:row.retrieved_at, rights_status:row.rights_status, source_field:row.source_field, context:row.context}, null, 2))); evidence.append(details);
    tr.append(entity, value, element('td', row.as_of || 'Not reported'), element('td', row.availability), evidence); $('rows').append(tr);
  }
  shown = Math.min(shown + 100, current.results.length);
  message('table-count', `Showing ${shown} of ${current.results.length} rows. Downloads contain the complete capture.`);
  $('more').hidden = shown >= current.results.length;
}
$('more').addEventListener('click', renderMore);

function download(text, extension, type) {
  if (!current) return;
  const url = URL.createObjectURL(new Blob([text], {type}));
  const link = document.createElement('a'); link.href = url; link.download = `${current.dataset}-${current.captured_at.slice(0, 10)}.${extension}`;
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  message('export-status', 'Download prepared. Keep the cited JSON with any spreadsheet or research note.');
}
$('download-json').addEventListener('click', () => current && download(JSON.stringify(current, null, 2) + '\n', 'json', 'application/json'));
$('download-csv').addEventListener('click', () => current && download(csv(current), 'csv', 'text/csv;charset=utf-8'));
async function copy(text, done) {
  try { await navigator.clipboard.writeText(text); message('export-status', done); }
  catch { $('copy-fallback').value = text; $('copy-fallback').hidden = false; $('copy-fallback').focus(); $('copy-fallback').select(); message('export-status', 'Copy the selected text below.'); }
}
$('copy-citation').addEventListener('click', () => current && copy(citations(current), 'Source note copied. It includes observation dates and source hashes.'));
$('share').addEventListener('click', () => current && copy(viewLink(current.request), 'Research-view link copied. It shares the dataset and filter, without your measurement key.'));

$('measurement').addEventListener('change', async () => {
  if (operator) return;
  if (!$('measurement').checked) { if (identity) { identity.enabled = false; saveIdentity(); } message('measurement-status', 'Measurement disabled. Use the delete action below to remove previous linked records.'); return; }
  $('measurement').disabled = true;
  try {
    if (!identity) {
      const response = await fetch(`${BASE}/api/v1/applications`, {method:'POST', credentials:'omit', redirect:'error', headers:{'Content-Type':'application/json'}, body:JSON.stringify({measurement_consent:true}), signal:AbortSignal.timeout(12000)});
      const value = await readJSON(response);
      if (!/^fe_[A-Za-z0-9_-]{43}$/.test(value.token)) throw new Error('Measurement enrollment returned an invalid key.');
      identity = {token:value.token, created:Date.now(), enabled:false};
    }
    identity.enabled = true; identity.created = Date.now(); saveIdentity();
    message('measurement-status', 'Optional measurement enabled for future research requests. Past anonymous activity is not linked.');
  } catch (error) { $('measurement').checked = false; if (identity) identity.enabled = false; saveIdentity(); message('measurement-status', `${error.message} Research still works with measurement off.`); }
  finally { $('measurement').disabled = false; }
});
$('forget').addEventListener('click', async () => {
  $('measurement').checked = false;
  if (!identity) { message('measurement-status', 'Measurement is off. This browser has no measurement key.'); return; }
  identity.enabled = false; saveIdentity(); $('forget').disabled = true;
  try {
    const response = await fetch(`${BASE}/api/v1/applications/current`, {method:'DELETE', credentials:'omit', redirect:'error', headers:{Authorization:`Bearer ${identity.token}`}, signal:AbortSignal.timeout(12000)});
    if (response.status !== 401) { const value = await readJSON(response); if (value.deleted !== true) throw new Error('Deletion was not confirmed.'); }
    identity = null; saveIdentity(); message('measurement-status', 'Linked measurement deleted or already expired. Measurement stays off. Anonymous aggregate counts remain.');
  } catch { message('measurement-status', 'Measurement is off. Deletion could not be confirmed; your disabled key remains here so you can retry.'); }
  finally { $('forget').disabled = false; }
});
