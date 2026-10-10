export const currencies = Object.freeze(['USD', 'GBP', 'JPY', 'INR']);

export function seriesURL(currency) {
  if (!currencies.includes(currency)) throw new Error('Choose USD, GBP, JPY or INR.');
  return `https://api.seiche.info/api/series/ECBFX_${currency}.csv`;
}

export function parseSeries(text, currency) {
  seriesURL(currency);
  if (text.length > 1_000_000) throw new Error('The evidence response is too large.');
  const lines = text.trim().split(/\r?\n/);
  const comments = lines.filter(line => line.startsWith('#')).join('\n');
  if (!comments.includes('European Central Bank') || !comments.includes('freely available')) {
    throw new Error('Source attribution or free-data notice is missing.');
  }
  if (!comments.includes(`unit: ${currency}/EUR,`)) throw new Error('The source returned unexpected units.');
  const body = lines.filter(line => line && !line.startsWith('#'));
  if (body.shift() !== 'date,value') throw new Error('The source returned an unexpected CSV schema.');
  let previous = '';
  const rows = body.map(line => {
    const fields = line.split(',');
    const [date, value] = fields;
    if (fields.length !== 2 || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(`${date}T00:00:00Z`)) || new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date || date <= previous) {
      throw new Error('The source returned an invalid or duplicate observation date.');
    }
    if (!/^\d+(?:\.\d+)?$/.test(value) || !Number.isFinite(Number(value)) || Number(value) <= 0) {
      throw new Error('The source returned an unavailable or invalid value.');
    }
    previous = date;
    return {date, value};
  });
  const sourceRetrievedAt = comments.match(/retrieved_at: ([^,\n]+)/)?.[1]?.trim();
  const lastObservation = comments.match(/last_observation: ([^,\n]+)/)?.[1]?.trim();
  const staleness = comments.match(/staleness: ([^,\n]+)/)?.[1]?.trim();
  if (!rows.length || !sourceRetrievedAt || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(sourceRetrievedAt) || !Number.isFinite(Date.parse(sourceRetrievedAt)) || !staleness || lastObservation !== rows.at(-1).date) {
    throw new Error('The source clocks are missing or inconsistent.');
  }
  return {currency, unit: `${currency} per EUR`, rows, comments, sourceRetrievedAt, lastObservation, staleness};
}

export async function loadSeries(currency, fetcher = globalThis.fetch) {
  const response = await fetcher(seriesURL(currency), {
    method: 'GET', credentials: 'omit', referrerPolicy: 'no-referrer', cache: 'no-store',
    signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) throw new Error(`Source unavailable (HTTP ${response.status}).`);
  if (!response.headers.get('content-type')?.includes('text/csv')) throw new Error('Expected a CSV source response.');
  return parseSeries(await response.text(), currency);
}

export function noteFor(result, fetchedAt) {
  return `Seiche reference-FX review\nFetched by this browser: ${fetchedAt}\nUnit: ${result.unit}\n${result.comments}\n\nLast ten published observations (missing dates stay absent):\ndate,value\n${result.rows.slice(-10).map(row => `${row.date},${row.value}`).join('\n')}\n\nXML-to-CSV presentation only; values are not inverted, interpolated or economically adjusted. Current amended history, not an as-published vintage archive. No broker quote or trading instruction.\n`;
}
