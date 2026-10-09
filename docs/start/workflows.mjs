import {BASE, readJSON} from './desk.mjs';

export const TASKS = {
  funding: {name:'Funding watch', audience:'Agent developers', product:'Seiche', selection:'USD', label:'Currency', hint:'Three-letter currency, such as USD, INR or EUR.', headers:['Market / measure','Published value','Observed','Availability / rights'], boundary:'Published benchmarks retain their native units and source dates. Rate levels alone do not establish funding stress.', guide:'../agents/#developers'},
  institutions: {name:'Institution watch', audience:'Treasury & risk teams', product:'LiquiLens', selection:'au-sfb,bajaj-finance', label:'Institution slugs', hint:'Up to five, separated by commas. For example: au-sfb,bajaj-finance.', headers:['Institution','Reviewed metrics / gaps','Latest period','Review state'], boundary:'Coverage gaps remain visible. These are evidence-review states, not credit ratings or lending approvals.', guide:'../agents/#risk-teams'},
  exit: {name:'BTC exit check', audience:'Traders & researchers', product:'Undertow', selection:'10000,100000', label:'Sell sizes in USD', hint:'Up to four sizes from 0.01 to 1,000,000, separated by commas.', headers:['Published size / venue','Indicative cost','Observed','Availability / quote currency'], boundary:'Published BTC sell estimates are indicative, exclude fees, transfer costs and latency, and are not executable quotes. Unsupported sizes show bounding rungs only.', guide:'../agents/#traders'},
};

export function settings(workflow, selection) {
  if (!Object.hasOwn(TASKS, workflow)) throw new Error('Choose a supported workflow.');
  selection = (selection || TASKS[workflow].selection).trim();
  if (selection.length > 160) throw new Error('Keep the selection within 160 characters.');
  if (workflow === 'funding') {
    selection = selection.toUpperCase();
    if (!/^[A-Z]{3}$/.test(selection)) throw new Error('Enter a three-letter currency, such as USD.');
  } else {
    let values = selection.split(',').map(value => value.trim());
    if (workflow === 'institutions') {
      if (values.length > 5 || values.some(value => !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value))) throw new Error('Enter one to five institution slugs, separated by commas.');
    } else {
      if (values.length > 4 || values.some(value => !/^\d+(?:\.\d{1,2})?$/.test(value) || !(Number(value) > 0 && Number(value) <= 1000000))) throw new Error('Enter one to four USD sizes from 0.01 to 1,000,000.');
      values = values.map(value => String(Number(value)));
    }
    selection = [...new Set(values)].join(',');
  }
  return {workflow, selection};
}
export function apiURL(request) { return `${BASE}/api/v1/workflow?${new URLSearchParams(settings(request.workflow, request.selection))}`; }
export function shareURL(request) { return `https://beepboop2025.github.io/financial-evidence-skills/start/workflows.html?${new URLSearchParams(settings(request.workflow, request.selection))}`; }
export async function run(request, {fetcher = fetch, token = '', synthetic = false, signal} = {}) {
  const selected = settings(request.workflow, request.selection), headers = {Accept:'application/json'};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (synthetic) headers['X-Liquilens-Traffic-Class'] = 'synthetic';
  const value = await readJSON(await fetcher(apiURL(selected), {headers, signal, credentials:'omit', redirect:'error', cache:'no-store'}));
  if (value?.schema !== 'financial-evidence.workflow-result.v1' || value.workflow !== selected.workflow || value.selection !== selected.selection || !/^[a-f0-9]{64}$/.test(value.content_sha256 || '') || !value.evidence) throw new Error('The workflow response could not be verified.');
  rows(value); // Validate the bounded display before accepting a capture.
  return value;
}
const display = value => value === null || value === undefined ? 'Unavailable' : String(value);
export function rows(capture) {
  const e = capture.evidence; let result;
  if (capture.workflow === 'funding' && e.schema === 'financial-evidence.agent-result.v1' && Array.isArray(e.results)) {
    result = e.results.map(row => ({id:`${row.entity_id}/${row.metric}/${row.source_field}`, cells:[`${row.entity_name} / ${row.metric}`, row.value === null ? 'Unavailable' : `${display(row.value)} ${row.unit || ''}`, row.as_of || 'Not reported', `${row.availability || 'Unknown'} / rights: ${row.rights_status || 'unknown'}`], details:row}));
  } else if (capture.workflow === 'institutions' && e.schema === 'liquilens.institution-monitoring.v1' && Array.isArray(e.rows)) {
    result = e.rows.map(row => ({id:row.slug, cells:[row.name, `${display(row.current_metrics)} reviewed / ${row.gaps?.length ?? 'unknown'} gaps`, row.latest_period || 'Not reported', row.status || 'Unknown'], details:{categories:row.categories, gaps:row.gaps, warnings:row.warnings, coverage_complete:row.coverage_complete, content_sha256:row.content_sha256}, record_sha256:/^[a-f0-9]{64}$/.test(row.content_sha256 || '') ? row.content_sha256 : null, url:/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(row.slug) ? `https://api.liquilens.in/api/experimental/v1/banking/monitoring/institutions/${row.slug}` : null}));
  } else if (capture.workflow === 'exit' && e.schema === 'undertow.crypto-workbench.v1' && Array.isArray(e.rungs)) {
    result = e.rungs.flatMap(rung => (rung.venues || []).map(venue => ({id:`${rung.published_size_usd}/${venue.venue}`, cells:[`$${rung.published_size_usd} / ${venue.venue}`, venue.sell_cost_bps === null || venue.sell_cost_bps === undefined ? 'Unavailable' : `${venue.sell_cost_bps} bps · $${display(venue.estimated_cost_usd)}`, e.venue_freshness?.[venue.venue]?.observed_at || 'Not reported', `${venue.status} / ${venue.quote_currency || 'unknown'}`], details:{...venue, freshness:e.venue_freshness?.[venue.venue], rung_status:rung.status}})));
  } else throw new Error('The original product evidence format changed.');
  if (result.length > 100 || result.some(row => typeof row.id !== 'string') || new Set(result.map(row => row.id)).size !== result.length) throw new Error('Unexpected or ambiguous research rows.');
  return result;
}
export function baseline(value) {
  return {schema:'financial-evidence.local-review.v2', request:settings(value.workflow,value.selection), captured_at:value.retrieved_at, rows:rows(value).map(row => ({id:row.id,cells:row.cells,record_sha256:row.record_sha256 ?? null})), scope:'Displayed values, dates and states, plus institution record fingerprints. Fingerprints include review aging and policy; a change does not by itself establish a new financial event.'};
}
export function compare(previous, current) {
  const next = baseline(current);
  if (!previous || !['financial-evidence.local-review.v1',next.schema].includes(previous.schema) || JSON.stringify(previous.request) !== JSON.stringify(next.request) || !Array.isArray(previous.rows) || previous.rows.length > 100 || previous.rows.some(row => !row || typeof row.id !== 'string' || !Array.isArray(row.cells) || row.cells.length !== 4 || row.cells.some(cell => typeof cell !== 'string'))) return null;
  const before = new Map(previous.rows.map(row => [row.id,row]));
  if (before.size !== previous.rows.length) return null;
  const after = new Map(next.rows.map(row => [row.id,row]));
  const legacy = previous.schema !== next.schema, details = [];
  for (const [id,row] of after) {
    const prior = before.get(id); if (!prior) continue;
    const fields = row.cells.flatMap((value,index) => value === prior.cells[index] ? [] : [{label:TASKS[current.workflow].headers[index],before:prior.cells[index],after:value}]);
    if (!legacy && (prior.record_sha256 ?? null) !== row.record_sha256) fields.push({label:'Evidence fingerprint (includes review aging and policy)',before:prior.record_sha256 || 'Unavailable',after:row.record_sha256 || 'Unavailable'});
    if (fields.length) details.push({id,name:row.cells[0],fields});
  }
  return {added:[...after.keys()].filter(id => !before.has(id)), removed:[...before.keys()].filter(id => !after.has(id)), changed:details.map(row => row.id), details, legacy, scope:next.scope};
}
export function reminder(request, now = new Date()) {
  const stamp = now.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
  const tomorrow = new Date(now.getTime() + 86400000).toISOString().slice(0,10).replaceAll('-','');
  const url = shareURL(request), task = TASKS[request.workflow];
  const escape = text => text.replaceAll('\\','\\\\').replaceAll('\n','\\n').replaceAll(';','\\;').replaceAll(',','\\,');
  // Fold long lines so large institution selections remain valid iCalendar.
  const fold = text => (text.match(/.{1,70}/g) || ['']).join('\r\n ');
  return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//LiquiLens//Research Review//EN','BEGIN:VEVENT',`UID:${crypto.randomUUID()}@liquilens.in`,`DTSTAMP:${stamp}`,`DTSTART;VALUE=DATE:${tomorrow}`,'RRULE:FREQ=DAILY;COUNT=30',`SUMMARY:${task.name} review`,`DESCRIPTION:${escape('Run a fresh review and inspect source dates.\n'+url)}`,`URL:${url}`,'END:VEVENT','END:VCALENDAR'].map(fold).join('\r\n')+'\r\n';
}
