import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { PIN, safeEnvironment, pageProjection, executionProjection, agentWorkflow, validatePublishable, redactDiagnostic } from './review_demo.mjs';

const page = dataset => ({ schema: 'liquidity-lab.openbb-table.v1', dataset, results: [{ value: null, availability: 'unavailable', as_of: '2026-06-30' }], sources: [{ status: 'PARTIAL' }], diagnostics: [], next_offset: 1, transport_status: 'complete' });
function execution(agent = false) {
  return { id: '12', status: 'success', finished: true, owner: { password: 'must-not-export' }, data: { resultData: { runData: {
    [agent ? 'Financial Evidence Tool' : 'Financial Evidence']: [{ executionStatus: 'success', data: { main: [[{ json: page('money_markets') }]] } }],
    ...(agent ? { 'Local Qwen3': [{}], 'Research Agent': [{ data: { main: [[{ json: { output: 'Observed unavailable value.', intermediateSteps: [{ action: { tool: 'Financial_Evidence_Tool', toolInput: {} }, observation: JSON.stringify([page('money_markets')]) }] } }]] } }] } : {}),
  } } } };
}
function receipt() {
  return { status: 'passed', package: { name: PIN.package, version: PIN.version, sha256: PIN.archiveSha256 }, n8n_version: PIN.n8n, model: { digest: PIN.modelDigest }, actions: Object.fromEntries(['money_markets', 'bank_risk', 'market_liquidity'].map(d => [d, { status: 'success', page: page(d) }])), agent: executionProjection(execution(true), 'money_markets', { agent: true }), video: { continuous: true, cuts: 0, duration_seconds: 240 }, ui_installed_package: true, ui_created_new_workflow: true, services_stopped: true, installed_files_match_published_archive: true, model_is_real: true, external_model_api_used: false, online_account_created: false, n8n_verified: false, independent_adoption_proven: false };
}

test('successful projections preserve unavailable values and source clocks, never owner or credentials', () => {
  const result = executionProjection(execution(), 'money_markets');
  assert.equal(result.page.results[0].value, null);
  assert.equal(result.page.sources[0].status, 'PARTIAL');
  assert.equal(result.page.results[0].as_of, '2026-06-30');
  assert.ok(!JSON.stringify(result).includes('must-not-export'));
});
test('HTTP-success envelope fails without native finished success and real tool/model invocation', () => {
  for (const mutate of [e => e.status = 'error', e => e.finished = false, e => e.data.resultData.error = {}, e => delete e.data.resultData.runData['Financial Evidence Tool'], e => delete e.data.resultData.runData['Local Qwen3'], e => e.data.resultData.runData['Research Agent'][0].data.main[0][0].json.intermediateSteps = [], e => e.data.resultData.runData['Research Agent'][0].data.main[0][0].json.intermediateSteps[0].observation = JSON.stringify([page('bank_risk')])]) {
    const e = execution(true); mutate(e);
    assert.throws(() => executionProjection(e, 'money_markets', { agent: true }));
  }
});
test('unbounded or changed dataset responses fail closed', () => {
  assert.throws(() => pageProjection(page('bank_risk'), 'money_markets'));
  assert.throws(() => pageProjection({ ...page('money_markets'), results: [{}, {}] }, 'money_markets'));
});
test('review output requires exact identity, every action, genuine model, no cuts and <=5min', () => {
  validatePublishable(receipt());
  for (const mutate of [r => r.status = 'failed', r => delete r.actions.bank_risk, r => r.video.duration_seconds = 301, r => r.video.cuts = 1, r => r.model_is_real = false, r => r.model.digest = 'different', r => r.package.sha256 = 'different', r => r.ui_installed_package = false, r => r.services_stopped = false, r => r.n8n_verified = true]) {
    const r = receipt(); mutate(r); assert.throws(() => validatePublishable(r));
  }
});
test('local model credentials contain only a reference; evidence node is connected only as an AI tool', () => {
  const workflow = agentWorkflow('local-only-id');
  const tool = workflow.nodes.find(n => n.name === 'Financial Evidence Tool');
  assert.equal(tool.type, 'n8n-nodes-financial-evidence.financialEvidenceTool');
  assert.equal(tool.parameters.limit, 1);
  assert.ok(!tool.credentials);
  assert.deepEqual(Object.keys(workflow.connections[tool.name]), ['ai_tool']);
  assert.ok(!JSON.stringify(workflow).includes('apiKey'));
});
test('service environment cannot inherit real instance credentials or DB/hooks', () => {
  process.env.N8N_ENCRYPTION_KEY = 'sentinel-private-key';
  process.env.DB_POSTGRESDB_PASSWORD = 'sentinel-db-password';
  process.env.OPENAI_API_KEY = 'sentinel-openai-key';
  process.env.NODE_AUTH_TOKEN = 'sentinel-npm-token';
  const env = safeEnvironment('/tmp/disposable-demo');
  assert.ok(!JSON.stringify(env).includes('sentinel'));
  assert.equal(env.N8N_LISTEN_ADDRESS, '127.0.0.1');
  assert.notEqual(env.N8N_PORT, env.N8N_RUNNERS_BROKER_PORT);
  assert.equal(env.N8N_RUNNERS_BROKER_LISTEN_ADDRESS, '127.0.0.1');
  assert.equal(env.OLLAMA_HOST, '127.0.0.1:11435');
  assert.equal(env.N8N_DIAGNOSTICS_ENABLED, 'false');
});
test('failure diagnostic strips actual private values and email addresses', () => {
  const clean = redactDiagnostic('cookie=privateCookie password=privatePassword test@example.invalid', ['privateCookie', 'privatePassword']);
  assert.ok(!clean.includes('privateCookie') && !clean.includes('privatePassword') && !clean.includes('test@example.invalid'));
});
test('workflow artifact allowlist never publishes failed video, auth state or private profile', () => {
  const workflow = readFileSync(new URL('../../../.github/workflows/n8n-review-demo.yml', import.meta.url), 'utf8');
  const paths = workflow.split('          path: |')[1].split('          if-no-files-found:')[0].trim().split('\n').map(s => s.trim());
  assert.deepEqual(paths, ['${{ runner.temp }}/n8n-review-demo/review/receipt.json', '${{ runner.temp }}/n8n-review-demo/review/review-demo.mp4', '${{ runner.temp }}/n8n-review-demo/review/original-uncut.webm']);
  assert.ok(workflow.includes('persist-credentials: false'));
  assert.ok(!workflow.includes('id-token: write'));
});
