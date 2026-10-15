import test from 'node:test';
import assert from 'node:assert/strict';
import { generateText, isStepCount } from 'ai';
import { MockLanguageModelV4 } from 'ai/test';
import { financialEvidenceTools } from '../dist/index.js';

const usage = {inputTokens: {total: 1, noCache: 1, cacheRead: 0, cacheWrite: 0},
  outputTokens: {total: 1, text: 1, reasoning: 0}};
const reply = (content, reason) => ({content, finishReason: {unified: reason, raw: reason}, usage, warnings: []});

test('native AI SDK generateText executes all three tools and sends unchanged evidence to next model step', async t => {
  const now = Date.now();
  const fixture = {
    datasets: [{id: 'money_markets', name: 'Money markets', description: 'Published observations', maximum_limit: 2000}],
    query: {schema: 'financial-evidence.agent-result.v1', dataset: 'money_markets',
      financial_authority: 'none', transport_status: 'partial', sources: [{source_url: 'https://example.test/source'}],
      results: [{value: null, as_of: '2026-01-01', unit: 'percent'}, {value: 0, rights_status: 'review_required'}]},
    context: {schema: 'seiche-agent-network.context.v1', scope: 'source_status_metadata',
      execution_authority: 'none', coverage_complete: false,
      stream_id: 'a'.repeat(32), revision: 'b'.repeat(64), sequence: 1, products: [],
      source_monitor: {status: 'current', current: true, max_age_seconds: 900,
        evaluated_at: new Date(now - 1000).toISOString(), valid_until: new Date(now + 899000).toISOString()},
      input_eligibility: 'not_evaluated'},
  };
  const requests = [];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    requests.push(url);
    assert.equal(new URL(url).origin, 'https://agents.seiche.info');
    assert.equal(init.headers['X-Financial-Evidence-Traffic-Class'], 'synthetic');
    const value = url.endsWith('/datasets') ? fixture.datasets
      : url.includes('/agent-query?') ? fixture.query
      : url.endsWith('/context/snapshot') ? fixture.context : assert.fail('Unexpected network call');
    return new Response(JSON.stringify(value), {headers: {'content-type': 'application/json'}});
  });
  const toolCalls = [
    ['financial_evidence_datasets', {}],
    ['financial_evidence_query', {dataset: 'money_markets', limit: 2}],
    ['financial_evidence_context', {}],
  ];
  const model = new MockLanguageModelV4({doGenerate: [
    reply(toolCalls.map(([toolName, input], i) => ({type: 'tool-call', toolCallId: String(i), toolName, input: JSON.stringify(input)})), 'tool-calls'),
    reply([{type: 'text', text: 'Published evidence is partial; missing values remain unavailable.'}], 'stop'),
  ]});
  const result = await generateText({
    model,
    tools: financialEvidenceTools({synthetic: true}),
    prompt: 'Discover coverage and inspect two funding rows with source-status metadata.',
    stopWhen: isStepCount(2),
    maxRetries: 0,
  });
  assert.equal(result.steps.length, 2);
  assert.equal(requests.length, 3);
  assert.equal(result.steps[0].toolResults.length, 3);
  const queryResult = result.steps[0].toolResults.find(item => item.toolName === 'financial_evidence_query');
  assert.deepEqual(queryResult.output, fixture.query);
  const contextResult = result.steps[0].toolResults.find(item => item.toolName === 'financial_evidence_context');
  assert.equal(contextResult.output.client_monitor_current, true);
  assert.equal(contextResult.output.execution_authority, 'none');
  const forwarded = model.doGenerateCalls[1].prompt.find(message => message.role === 'tool').content;
  assert.deepEqual(forwarded.find(item => item.toolName === 'financial_evidence_query').output.value, fixture.query);
  assert.equal(result.text, 'Published evidence is partial; missing values remain unavailable.');
});

test('native SDK validation rejects invented endpoint, invalid dates and oversized requests before fetch', async t => {
  let calls = 0;
  t.mock.method(globalThis, 'fetch', async () => { calls++; throw new Error('Must not execute'); });
  for (const input of [
    {dataset: 'money_markets', url: 'https://attacker.test'},
    {dataset: 'money_markets', start_date: '2026-02-30'},
    {dataset: 'money_markets', limit: 101},
  ]) {
    const model = new MockLanguageModelV4({doGenerate: reply([{
      type: 'tool-call', toolCallId: 'bad-input', toolName: 'financial_evidence_query', input: JSON.stringify(input),
    }], 'tool-calls')});
    const result = await generateText({model, tools: financialEvidenceTools(), prompt: 'Synthetic validation test', maxRetries: 0});
    assert.equal(calls, 0);
    assert.equal(result.steps[0].toolResults.length, 0);
    assert.ok(result.steps[0].content.some(item => item.type === 'tool-error'));
  }
});

test('native SDK retains failed reads as tool errors rather than empty successful evidence', async t => {
  let make;
  t.mock.method(globalThis, 'fetch', async () => make());
  for (const [factory, code] of [
    [() => new Response('<html>not JSON</html>'), 'invalid_response'],
    [() => new Response('[]', {headers: {'content-type': 'application/json', 'content-length': '999999999'}}), 'response_too_large'],
    [() => new Response(new ReadableStream(), {headers: {'content-type': 'application/json'}}), 'request_timeout'],
  ]) {
    make = factory;
    const model = new MockLanguageModelV4({doGenerate: reply([{
      type: 'tool-call', toolCallId: 'failed-read', toolName: 'financial_evidence_datasets', input: '{}',
    }], 'tool-calls')});
    const result = await generateText({model, tools: financialEvidenceTools({timeoutMs: 25}), prompt: 'Synthetic failure test', maxRetries: 0});
    assert.equal(result.steps[0].toolResults.length, 0);
    assert.equal(result.steps[0].content.find(item => item.type === 'tool-error').error.code, code);
  }
});

test('native SDK receives a stale context with original source fields and blocked eligibility', async t => {
  const evaluated = Date.now() - 1000000;
  const fixture = {schema: 'seiche-agent-network.context.v1', scope: 'source_status_metadata',
    execution_authority: 'none', coverage_complete: false,
    stream_id: 'c'.repeat(32), revision: 'd'.repeat(64), sequence: 1,
    products: [{product: 'seiche', source_timestamp: null, status: 'unavailable', source_url: 'https://example.test/evidence'}],
    source_monitor: {status: 'current', current: true, max_age_seconds: 900,
      evaluated_at: new Date(evaluated).toISOString(), valid_until: new Date(evaluated + 900000).toISOString()},
    input_eligibility: 'not_evaluated'};
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify(fixture), {headers: {'content-type': 'application/json'}}));
  const model = new MockLanguageModelV4({doGenerate: reply([{
    type: 'tool-call', toolCallId: 'stale-context', toolName: 'financial_evidence_context', input: '{}',
  }], 'tool-calls')});
  const result = await generateText({model, tools: financialEvidenceTools(), prompt: 'Synthetic stale context test', maxRetries: 0});
  const value = result.steps[0].toolResults[0].output;
  assert.equal(value.client_monitor_status, 'stale');
  assert.equal(value.input_eligibility, 'blocked_monitor');
  assert.deepEqual(value.products, fixture.products);
  assert.deepEqual(value.source_monitor, fixture.source_monitor);
});

test('native SDK propagates operation abort to the active evidence request', async t => {
  let notify;
  const entered = new Promise(resolve => { notify = resolve; });
  let requestSignal;
  t.mock.method(globalThis, 'fetch', async (_url, init) => {
    requestSignal = init.signal;
    notify();
    return new Promise(() => {});
  });
  const controller = new AbortController();
  const model = new MockLanguageModelV4({doGenerate: reply([{
    type: 'tool-call', toolCallId: 'cancelled-read', toolName: 'financial_evidence_datasets', input: '{}',
  }], 'tool-calls')});
  const pending = generateText({model, tools: financialEvidenceTools(), prompt: 'Synthetic cancellation test',
    abortSignal: controller.signal, maxRetries: 0});
  await entered;
  controller.abort(new DOMException('Cancelled test', 'AbortError'));
  const result = await pending;
  assert.equal(result.steps[0].toolResults.length, 0);
  assert.equal(result.steps[0].content.find(item => item.type === 'tool-error').error.code, 'request_aborted');
  assert.equal(requestSignal.aborted, true);
});
