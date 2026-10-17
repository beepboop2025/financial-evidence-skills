import test from 'node:test';
import assert from 'node:assert/strict';
import { generateText, isStepCount } from 'ai';
import { MockLanguageModelV4 } from 'ai/test';
import { runFinancialWorkflow, financialEvidenceWorkflowTool } from '../dist/index.js';

function context(now = Date.now()) {
  return {schema: 'seiche-agent-network.context.v1', scope: 'source_status_metadata',
    execution_authority: 'none', coverage_complete: false, stream_id: 'a'.repeat(32),
    revision: 'b'.repeat(64), sequence: 1, products: [{product: 'seiche', freshness_at_evaluation: 'partial'}],
    source_monitor: {status: 'current', current: true, max_age_seconds: 900,
      evaluated_at: new Date(now - 1000).toISOString(), valid_until: new Date(now + 899000).toISOString()},
    input_eligibility: 'not_evaluated'};
}
function evidence(workflow = 'funding', selection = 'USD') {
  return {schema: 'financial-evidence.workflow-result.v1', workflow, selection,
    prepared_response: true, content_sha256: 'c'.repeat(64), evidence: {
      schema: {funding: 'financial-evidence.agent-result.v1', institutions: 'liquilens.institution-monitoring.v1',
        exit: 'undertow.crypto-workbench.v1'}[workflow], results: [{value: null, as_of: '2020-01-01', rights_status: 'review_required'}]}};
}
const response = value => new Response(JSON.stringify(value), {headers: {'Content-Type': 'application/json'}});

test('deterministic workflow preserves source gaps and checks context before evidence, without credentials or writes', async t => {
  const requests = [], original = evidence();
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    requests.push(url);
    assert.equal(new URL(url).origin, 'https://agents.seiche.info');
    assert.equal(init.method, 'GET');
    assert.equal(init.credentials, 'omit');
    assert.equal(init.headers.Authorization, undefined);
    assert.equal(init.headers['X-Financial-Evidence-Traffic-Class'], 'synthetic');
    return response(requests.length === 1 ? context() : original);
  });
  const result = await runFinancialWorkflow({workflow: 'funding', selection: ' usd '}, {synthetic: true});
  assert.equal(result.status, 'ready_for_review');
  assert.deepEqual(result.result, original);
  assert.equal(result.sharing, 'disabled');
  assert.equal(result.input_eligibility, 'not_evaluated');
  assert.equal(result.content_integrity, 'provider_digest_unverified');
  assert.equal(requests.length, 2);
  assert.ok(requests[0].endsWith('/v1/context/snapshot'));
  assert.ok(requests[1].endsWith('workflow?workflow=funding&selection=USD'));
});

test('expired or upstream blocked monitor prevents the research read', async t => {
  for (const snapshot of [context(Date.now() - 900000), {...context(), input_eligibility: 'blocked_monitor'}]) {
    let calls = 0;
    t.mock.method(globalThis, 'fetch', async () => { calls++; return response(snapshot); });
    const result = await runFinancialWorkflow({workflow: 'funding'});
    assert.equal(result.status, 'blocked_monitor');
    assert.equal(result.result, null);
    assert.equal(calls, 1);
    t.mock.restoreAll();
  }
});

test('monitor is revalidated after a slow evidence read', async t => {
  let now = Date.now(), calls = 0;
  const snapshot = context(now);
  t.mock.method(Date, 'now', () => now);
  t.mock.method(globalThis, 'fetch', async () => {
    if (++calls === 1) return response(snapshot);
    now += 900000;
    return response(evidence());
  });
  const result = await runFinancialWorkflow({workflow: 'funding'});
  assert.equal(result.status, 'blocked_monitor');
  assert.notEqual(result.result, null);
});

test('strict selection rejects arbitrary targets before any request and normalizes supported sizes', async t => {
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async url => {
    calls++;
    return response(url.endsWith('/snapshot') ? context() : evidence('exit', '10000'));
  });
  for (const input of [{workflow: 'funding', selection: 'https://example.test'}, {workflow: 'exit', selection: '0'},
    {workflow: 'institutions', selection: '../secret'}, {workflow: 'funding', token: 'private'}]) {
    await assert.rejects(() => runFinancialWorkflow(input));
  }
  assert.equal(calls, 0);
  const result = await runFinancialWorkflow({workflow: 'exit', selection: '10000.00,10000'});
  assert.equal(result.status, 'ready_for_review');
  assert.equal(result.selection, '10000');
});

test('malformed or mismatched evidence stays unavailable; private upstream errors are not echoed', async t => {
  const mutations = [value => { value.selection = 'EUR'; }, value => { value.evidence.schema = 'invented'; },
    value => { value.content_sha256 = ''; }, value => { value.prepared_response = 'true'; }];
  for (const mutate of mutations) {
    const value = evidence(); mutate(value);
    t.mock.method(globalThis, 'fetch', async url => response(url.endsWith('/snapshot') ? context() : value));
    const result = await runFinancialWorkflow({workflow: 'funding'});
    assert.equal(result.status, 'evidence_unavailable');
    assert.equal(result.result, null);
    assert.equal(result.error, 'invalid_response');
    t.mock.restoreAll();
  }
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('private credential'); });
  const result = await runFinancialWorkflow({workflow: 'funding'});
  assert.equal(result.status, 'context_unavailable');
  assert.equal(result.error, 'request_failed');
  assert.equal(JSON.stringify(result).includes('private credential'), false);
});

test('the entire workflow obeys deadline and caller cancellation', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Promise(() => {}));
  assert.equal((await runFinancialWorkflow({workflow: 'funding'}, {timeoutMs: 15})).error, 'request_timeout');
  assert.equal((await runFinancialWorkflow({workflow: 'funding'}, {}, AbortSignal.abort())).error, 'request_aborted');
});

test('optional workflow tool participates in a real AI SDK model loop', async t => {
  t.mock.method(globalThis, 'fetch', async url => response(url.endsWith('/snapshot') ? context() : evidence()));
  const usage = {inputTokens: {total: 1, noCache: 1, cacheRead: 0, cacheWrite: 0},
    outputTokens: {total: 1, text: 1, reasoning: 0}};
  const reply = (content, reason) => ({content, finishReason: {unified: reason, raw: reason}, usage, warnings: []});
  const result = await generateText({model: new MockLanguageModelV4({doGenerate: [
    reply([{type: 'tool-call', toolCallId: 'review', toolName: 'financial_evidence_workflow', input: '{"workflow":"funding"}'}], 'tool-calls'),
    reply([{type: 'text', text: 'Review the source gaps.'}], 'stop'),
  ]}), tools: {financial_evidence_workflow: financialEvidenceWorkflowTool({synthetic: true})},
  prompt: 'Prepare a funding research review.', stopWhen: isStepCount(2)});
  assert.equal(result.steps[0].toolResults[0].output.status, 'ready_for_review');
  assert.deepEqual(result.steps[0].toolResults[0].output.result, evidence());
});
