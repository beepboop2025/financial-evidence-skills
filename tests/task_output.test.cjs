const { test } = require('node:test');
const assert = require('node:assert/strict');
const { formatTaskResponse } = require('../integrations/n8n/task-output.cjs');
const fs = require('node:fs');
const path = require('node:path');
const now = new Date('2026-09-27T10:00:00Z');
// A real money_market_context {"section": "summary"} answer (19 November 2026), trimmed; its clock is moved to the test clock.
const desk = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/seiche-money-market-summary-20261119.json'), 'utf8'));
const funding = () => ({ ...structuredClone(desk), snapshot_generated_at: now.toISOString() });
const fundingSettings = { toolInput: { section: 'summary' }, maxAgeSeconds: 21600 };
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
    assert.throws(() => formatTaskResponse('seiche', response, fundingSettings, now));
  }
  const legacy = { schema: 'seiche.public.v2', generated_at: now.toISOString(), conclusion: {}, data_quality: {} };
  assert.throws(() => call('seiche', legacy, fundingSettings));
});

test('the funding task reads the money-market desk and keeps its gaps, dates and units', () => {
  const evidence = funding();
  const output = call('seiche', evidence, fundingSettings);
  assert.equal(output.tool, 'money_market_context');
  assert.equal(output.source_status, 'DATA_GAPS');
  assert.strictEqual(output.evidence, evidence);
  const s = desk.strongest_signal, c = desk.countercase, counts = desk.freshness.status_counts;
  assert.ok(output.message_text.includes(`${s.label}: ${s.value} ${s.unit}, observed ${s.asof} (${s.freshness})`));
  assert.ok(output.message_text.includes(`Countercase: ${c.label}: ${c.value} ${c.unit}, observed ${c.asof}`));
  assert.ok(output.message_text.includes(`${counts.fresh} fresh, ${counts.aging} aging, ${counts.stale} stale, ${counts.unavailable} unavailable`));
  assert.ok(output.message_text.includes(`Metrics available: ${desk.coverage.available_metrics} of ${desk.coverage.total_metrics}`));
  assert.match(output.message_text, /does not reconstruct/);
  assert.doesNotMatch(output.message_text, /\u2014|\u2013/);
  delete evidence.freshness.status_counts.stale;
  assert.throws(() => call('seiche', evidence, fundingSettings));
  assert.throws(() => call('seiche', funding(), { ...fundingSettings, toolInput: { section: 'all' } }));
});

test('a missing channel value stays unavailable and cannot read as complete evidence', () => {
  const evidence = funding();
  evidence.strongest_signal.value = null;
  evidence.freshness.status_counts = { fresh: 1, aging: 0, stale: 0, unavailable: 0 };
  evidence.coverage.available_metrics = evidence.coverage.total_metrics;
  const output = call('seiche', evidence, fundingSettings);
  assert.equal(output.source_status, 'DATA_GAPS');
  assert.ok(output.message_text.includes(`${desk.strongest_signal.label}: unavailable`));
});

test('withheld or unavailable desk answers stay visibly unavailable with no reading', () => {
  for (const change of [{ ok: false, reason: 'Source rights are not qualified.' },
    { publication_projection: { status: 'withheld', reason: 'Source rights are not qualified.' } }]) {
    const evidence = { ...funding(), ...change };
    const output = call('seiche', evidence, fundingSettings);
    assert.equal(output.source_status, 'UNAVAILABLE');
    assert.match(output.message_text, /Source rights are not qualified/);
    assert.doesNotMatch(output.message_text, /Most stretched|Countercase|SOURCE_REPORTED/);
    assert.strictEqual(output.evidence, evidence);
  }
});

test('stale and future snapshot clocks withhold current funding readings and BTC costs', () => {
  for (const date of ['2026-09-26T10:00:00Z', '2026-09-28T10:00:00Z']) {
    const f = funding(); f.snapshot_generated_at = date;
    const b = exit(); b.generated_at = date;
    const seiche = call('seiche', f, fundingSettings);
    assert.doesNotMatch(seiche.message_text, /Most stretched channel:/);
    assert.match(seiche.source_status, /STALE_SNAPSHOT|FUTURE_SOURCE_CLOCK/);
    assert.strictEqual(seiche.evidence, f);
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
    const output = formatTaskResponse('seiche', { content: [{ type: 'text', text }] }, fundingSettings, now);
    assert.deepEqual(output.evidence, evidence);
  }
});
