const API_ROOT = 'https://agents.seiche.info/v1/research/api/v1';

export const datasets = [
  { label: 'Bank Risk', value: 'bank_risk' },
  { label: 'Capital Markets', value: 'capital_markets' },
  { label: 'China Economy', value: 'china_economy' },
  { label: 'Market Liquidity', value: 'market_liquidity' },
  { label: 'Money Market History', value: 'money_market_history' },
  { label: 'Money Markets', value: 'money_markets' },
  { label: 'Source Health', value: 'source_health' },
] as const;

type Query = { dataset: string; entity?: string; limit?: number; offset?: number };
type JsonObject = Record<string, unknown>;

function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export class ResearchResponseError extends Error {
  constructor(message: string, readonly status: number, readonly body: unknown) {
    super(`${message}: ${JSON.stringify({ status, body })}`);
    this.name = 'ResearchResponseError';
  }
}

async function read(path: '/datasets' | '/query', query?: Record<string, string>): Promise<unknown> {
  const url = new URL(`${API_ROOT}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) url.searchParams.set(key, value);
  // Native fetch preserves TLS verification and rejects redirects away from the fixed host.
  const response = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json', 'User-Agent': 'financial-evidence-activepieces/0.1.0' },
    redirect: 'error',
    signal: AbortSignal.timeout(30_000),
  });
  const text = await response.text();
  let body: unknown;
  try { body = JSON.parse(text); }
  catch { throw new ResearchResponseError('Research API returned non-JSON content', response.status, text); }
  if (!response.ok) throw new ResearchResponseError('Research API request failed', response.status, body);
  return body;
}

export async function listDatasets(): Promise<unknown[]> {
  const body = await read('/datasets');
  if (!Array.isArray(body) || !body.every((item) => isObject(item) &&
      typeof item.id === 'string' && typeof item.name === 'string' && typeof item.description === 'string')) {
    throw new ResearchResponseError('Unexpected research catalog contract', 200, body);
  }
  return body;
}

export async function getEvidencePage(input: Query): Promise<JsonObject> {
  const { dataset, entity = '', limit = 25, offset = 0 } = input;
  if (!datasets.some((item) => item.value === dataset) ||
      typeof entity !== 'string' || entity.length > 100 ||
      !Number.isInteger(limit) || limit < 1 || limit > 100 ||
      !Number.isInteger(offset) || offset < 0 || offset > 100_000) {
    throw new Error('Choose a supported dataset, entity up to 100 characters, limit 1–100 and offset 0–100000');
  }
  const body = await read('/query', { dataset, entity, limit: String(limit), offset: String(offset) });
  if (!isObject(body) || body.schema !== 'liquidity-lab.openbb-table.v1' || body.dataset !== dataset ||
      !Array.isArray(body.results) || body.results.length > limit ||
      !Array.isArray(body.sources) || !Array.isArray(body.diagnostics) ||
      !(body.next_offset === null || (typeof body.next_offset === 'number' &&
        Number.isInteger(body.next_offset) && body.next_offset > offset))) {
    throw new ResearchResponseError('Unexpected research page contract', 200, body);
  }
  // Return the whole page; source metadata and unavailable/null values remain intact.
  return body;
}
