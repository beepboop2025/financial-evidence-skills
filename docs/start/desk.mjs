export const BASE = 'https://api.seiche.info/openbb';
export const DATASETS = ['money_markets', 'money_market_history', 'bank_risk', 'market_liquidity', 'capital_markets', 'china_economy', 'source_health'];
export const MAX_BYTES = 4 * 1024 * 1024;

export function querySettings(value) {
  const dataset = value.dataset || 'bank_risk';
  const entity = (value.entity || '').trim();
  const start_date = value.start_date || '', end_date = value.end_date || '';
  if (!DATASETS.includes(dataset) || entity.length > 100) throw new Error('Choose a supported dataset and a filter of at most 100 characters.');
  for (const date of [start_date, end_date]) {
    if (date && (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date)) throw new Error('Use a valid observation date.');
  }
  if (start_date && end_date && start_date > end_date) throw new Error('The first observation date must come before the last.');
  return {dataset, entity, start_date, end_date};
}

export function safeSource(value) {
  try { const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password ? url.href : null; } catch { return null; }
}

export async function readJSON(response) {
  if (!response.ok) throw new Error(`The research service returned HTTP ${response.status}. Please retry later.`);
  if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('The service returned a challenge or unexpected response.');
  const reader = response.body.getReader(), chunks = [];
  let length = 0;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      length += value.length;
      if (length > MAX_BYTES) throw new Error('The response exceeded the research desk limit. Use the Python capture client.');
      chunks.push(value);
    }
  } catch (error) { await reader.cancel(); throw error; }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  const value = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
  function finite(item) {
    if (typeof item === 'number' && !Number.isFinite(item)) throw new Error('The service returned a non-finite number.');
    if (item && typeof item === 'object') Object.values(item).forEach(finite);
  }
  finite(value); return value;
}

function signature(page) {
  if (!Array.isArray(page.sources) || !page.sources.length) throw new Error('Source provenance is missing.');
  return JSON.stringify(page.sources.map(source => {
    if (!safeSource(source.source_url) || !/^(sha256:)?[a-f0-9]{64}$/.test(source.content_sha256 || '') || source.ok !== true) throw new Error('A source could not be verified for this capture.');
    return [source.source_url, source.content_sha256];
  }).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))));
}

export async function capture(settings, {fetcher = fetch, token = '', synthetic = false, signal, progress = () => {}} = {}) {
  const request = querySettings(settings), results = [], pages = [];
  const limit = 200; let offset = 0, firstSignature, expectedTotal;
  for (let number = 0; number < 20; number++) {
    const params = new URLSearchParams({...request, limit, offset});
    const headers = {Accept: 'application/json'};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (synthetic) headers['X-Liquilens-Traffic-Class'] = 'synthetic';
    const response = await fetcher(`${BASE}/api/v1/query?${params}`, {headers, signal: signal || AbortSignal.timeout(20000), credentials: 'omit', redirect: 'error', cache: 'no-store'});
    const page = await readJSON(response);
    if (page?.schema !== 'liquidity-lab.openbb-table.v1' || page.dataset !== request.dataset || page.transport_status !== 'complete' || page.status_semantics !== 'transport_only' || page.evidence_status !== 'not_evaluated' || page.carrier_verification !== 'not_performed') throw new Error('The source response is incomplete or its evidence contract changed. Inspect source status before retrying.');
    if (!Array.isArray(page.results) || !Number.isSafeInteger(page.total_rows) || page.total_rows < 0 || page.total_rows > 4000 || page.offset !== offset || page.limit !== limit || page.returned_rows !== page.results.length || page.results.length > limit || !Object.hasOwn(page, 'next_offset')) throw new Error('Incomplete or oversized table. Use the complete-capture Python client.');
    for (const row of page.results) {
      if (!row || row.dataset !== request.dataset || !safeSource(row.source_url) || typeof row.availability !== 'string' || !Object.hasOwn(row, 'value') || (row.value !== null && (typeof row.value !== 'number' || !Number.isFinite(row.value)))) throw new Error('An observation failed its evidence contract.');
    }
    const current = signature(page);
    if (firstSignature !== undefined && (current !== firstSignature || page.total_rows !== expectedTotal)) throw new Error('The source changed while loading. Run the review again for one consistent capture.');
    firstSignature = current; expectedTotal = page.total_rows;
    results.push(...page.results);
    const {results: ignored, ...metadata} = page;
    pages.push(metadata); progress(results.length, expectedTotal);
    if (page.next_offset === null) {
      if (results.length !== expectedTotal) throw new Error('The last page did not complete the expected row count.');
      return {schema: 'financial-evidence.research-capture.v1', dataset: request.dataset, captured_at: new Date().toISOString(), request: {...request, limit}, results, returned_rows: results.length, pages, transport_status: 'complete', evidence_status: 'not_evaluated', carrier_verification: 'not_performed', financial_authority: 'none', history_scope: 'currently_published_not_as_published_vintages'};
    }
    if (!page.results.length || page.next_offset !== results.length || page.next_offset >= expectedTotal) throw new Error('Pagination did not advance consistently.');
    offset = page.next_offset;
  }
  throw new Error('This capture needs more than 20 pages. Narrow the observation dates or use the Python client.');
}

export function csv(capture) {
  const preferred = ['dataset','product','entity_id','entity_name','metric','value','unit','as_of','availability','source_status','observation_url','source_url','source_field','published_at','knowledge_time','retrieved_at','content_sha256','rights_status','context','transport_status','evidence_status','financial_authority','carrier_verification'];
  const keys = [...new Set([...preferred, ...capture.results.flatMap(row => Object.keys(row))])];
  const cell = value => {
    if (value === null || value === undefined) return '""';
    let text = typeof value === 'object' ? JSON.stringify(value) : String(value);
    if (typeof value === 'string' && /^[\s\u0000-\u001f]*[=+@-]/.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  return [keys.map(cell).join(','), ...capture.results.map(row => keys.map(key => cell(row[key])).join(','))].join('\r\n') + '\r\n';
}

export function viewLink(settings, origin = 'https://beepboop2025.github.io') {
  const value = querySettings(settings), url = new URL('/financial-evidence-skills/start/', origin);
  for (const [key, item] of Object.entries(value)) if (item) url.searchParams.set(key, item);
  url.searchParams.set('utm_source', 'shared_research');
  url.searchParams.set('utm_medium', 'referral');
  return url.href;
}

export function summary(capture) {
  const rows = capture.results, dates = rows.map(row => row.as_of).filter(Boolean).sort();
  return {total: rows.length, available: rows.filter(row => row.value !== null && ['published', 'available'].includes(row.availability.toLowerCase())).length, earliest: dates[0] || null, latest: dates.at(-1) || null};
}

export function citations(capture) {
  const info = summary(capture);
  const sources = capture.pages[0].sources.map(source => `${source.source_url}\nSHA-256: ${source.content_sha256}`);
  return `Financial Evidence — ${capture.dataset}\nCaptured: ${capture.captured_at}\nObservation dates: ${info.earliest || 'unknown'} to ${info.latest || 'unknown'}\n${info.total} rows; ${info.available} published numeric values.\n\n${sources.join('\n\n')}\n\n${viewLink(capture.request)}\nRetrieval is complete; evidence validity and redistribution rights are not independently evaluated. Missing values remain missing. The link reruns the query; retain the downloaded JSON for this exact capture.\n`;
}
