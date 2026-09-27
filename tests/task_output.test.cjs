const { test } = require('node:test');
const assert = require('node:assert/strict');
const { formatTaskResponse } = require('../integrations/n8n/task-output.cjs');
const now = new Date('2026-09-27T10:00:00Z');
const funding = () => ({ schema: 'seiche.public.v2', generated_at: now.toISOString(),
  conclusion: { regime: 'EROSION', value: 42, coverage_pct: 90 },
  data_quality: { status_counts: { fresh: 2, aging: 1, dead: 0, unknown: 1 } },
  proof: { historical_evidence: { validated_backtest_eligible: false } } });
const bank = () => ({ schema: 'liquilens.bank-specialisation.v1', slug: 'cosmos-ucb',
  status: 'observed', scope: 'research', score_authority: false, can_authorize_credit: false,
  period_end: '2026-03-31', sources: ['https://example.com/filing.pdf'],
  metrics: { gnpa_pct: { status: 'observed', unit: 'percent', value: 3.11 }, nnpa_pct: { value: null, status: 'not_disclosed' } },
  npa_movement: { status: 'reconciled', amount_unit: 'INR_crore', reductions: { cash_recoveries: 92.88, write_offs: 161.13, upgrades: 98.56 } } });
const exit = () => ({ asset: 'BTC', generated_at: now.toISOString(), requested_size_usd: 100000,
  published_rung_used_usd: 100000, sell_cost_bp_by_venue: { alpha: 1.25, beta: null },
  unable_at_observed_depth: ['beta'], method: 'published depth bands' });
const settings = { toolInput: {}, maxAgeSeconds: 7200 };
const call = (product, evidence, config = settings) => formatTaskResponse(product, { structuredContent: evidence }, config, now);

test('transport errors and malformed response shapes cannot produce updates', () => {
  for (const response of [{ isError: true, structuredContent: funding() }, { error: {} }, {}, { content: [{ type: 'text', text: 'not json' }] }]) {
    assert.throws(() => formatTaskResponse('seiche', response, settings, now));
  }
});

test('source gaps and validation flags survive; summary cannot silently imply complete funding evidence', () => {
  const evidence = funding();
  const output = call('seiche', evidence);
  assert.equal(output.source_status, 'DATA_GAPS');
  assert.strictEqual(output.evidence, evidence);
  assert.match(output.message_text, /1 unknown/);
  delete evidence.data_quality.status_counts.unknown;
  assert.throws(() => call('seiche', evidence));
});

test('stale and future snapshot clocks withhold current funding readings and BTC costs', () => {
  for (const date of ['2026-09-26T10:00:00Z', '2026-09-28T10:00:00Z']) {
    const f = funding(); f.generated_at = date;
    const b = exit(); b.generated_at = date;
    assert.doesNotMatch(call('seiche', f).message_text, /gauge 42/);
    const result = call('undertow', b, { ...settings, toolInput: { size_usd: 100000 } });
    assert.doesNotMatch(result.message_text, /alpha: 1.25/);
    assert.strictEqual(result.evidence, b);
  }
});

test('bank summary keeps cash recoveries distinct from write-offs and unknown ratios', () => {
  const evidence = bank();
  const config = { ...settings, toolInput: { slug: 'cosmos-ucb' } };
  const result = call('liquilens', evidence, config);
  assert.match(result.message_text, /Cash recoveries: INR 92.88 crore/);
  assert.match(result.message_text, /Write-offs: INR 161.13 crore/);
  assert.match(result.message_text, /NNPA not disclosed/);
  assert.strictEqual(result.evidence, evidence);
  evidence.slug = 'another-bank';
  assert.throws(() => call('liquilens', evidence, config));
});

test('historical, stale, unavailable and uncited bank evidence cannot produce current ratios', () => {
  for (const status of ['historical', 'stale', 'unavailable', 'observed']) {
    const evidence = bank(); evidence.status = status;
    if (status === 'observed') evidence.sources = [];
    const result = call('liquilens', evidence, { ...settings, toolInput: { slug: 'cosmos-ucb' } });
    assert.doesNotMatch(result.message_text, /GNPA 3.11/);
    assert.strictEqual(result.evidence, evidence);
  }
});

test('BTC depth gaps, rung approximation and excluded fees stay visible; wrong sizes and invalid costs fail', () => {
  const config = { ...settings, toolInput: { size_usd: 110000 } };
  const evidence = exit(); evidence.requested_size_usd = 110000;
  const result = call('undertow', evidence, config);
  assert.equal(result.source_status, 'DEPTH_GAPS');
  assert.match(result.message_text, /Requested: USD 110000; published rung used: USD 100000/);
  assert.match(result.message_text, /beta: unavailable/);
  assert.match(result.message_text, /fees excluded/);
  assert.throws(() => call('undertow', evidence, { ...config, toolInput: { size_usd: 5000 } }));
  for (const invalid of [-1, '1.25', Infinity]) {
    evidence.sell_cost_bp_by_venue.alpha = invalid;
    assert.throws(() => call('undertow', evidence, config));
  }
});

test('MCP text fallback preserves the same evidence contract', () => {
  const evidence = funding();
  for (const text of [evidence, JSON.stringify(evidence)]) {
    const output = formatTaskResponse('seiche', { content: [{ type: 'text', text }] }, settings, now);
    assert.deepEqual(output.evidence, evidence);
  }
});
