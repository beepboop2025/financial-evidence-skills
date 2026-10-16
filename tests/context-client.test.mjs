import {test} from 'node:test';
import assert from 'node:assert/strict';
import {contextEvents, contextSnapshot, validateSnapshot} from '../docs/agents/context-client.mjs';

const state = (sequence = 1) => ({schema:'seiche-agent-network.context.v1',stream_id:'a'.repeat(32),revision:'b'.repeat(64),sequence,scope:'source_status_metadata',execution_authority:'none',coverage_complete:false,products:[],source_monitor:{current:false,status:'stale'},delivery:{replay_complete:false}});
const frame = (event = 'reset', sequence = 1) => `event: ${event}\nid: ${'a'.repeat(32)}:${sequence}\ndata: ${JSON.stringify(state(sequence))}\n\n`;

test('local expiry, future clocks and malformed validity windows fail closed', () => {
  const now = 1800000000000;
  const source = {...state(), input_eligibility:'not_evaluated', source_monitor:{status:'current',current:true,
    evaluated_at:new Date(now).toISOString(),valid_until:new Date(now+900000).toISOString(),max_age_seconds:900}};
  const original = structuredClone(source);
  for (const [clock, expected] of [[now,'current'],[now+899999,'current'],[now+900000,'stale'],[now-1,'future_clock']]) {
    const checked = validateSnapshot(source, clock);
    assert.equal(checked.client_monitor_status, expected);
    assert.equal(checked.client_monitor_current, expected === 'current');
    assert.equal(checked.input_eligibility, expected === 'current' ? 'not_evaluated' : 'blocked_monitor');
    assert.deepEqual(checked.source_monitor, original.source_monitor);
  }
  assert.deepEqual(source, original);
  for (const change of [{valid_until:new Date(now+901000).toISOString()},{max_age_seconds:true},{max_age_seconds:901},
    {evaluated_at:'2026-02-30T00:00:00Z'},{evaluated_at:'2026-01-01T00:00:00'},{valid_until:null}]) {
    const checked = validateSnapshot({...source,source_monitor:{...source.source_monitor,...change}}, now);
    assert.equal(checked.client_monitor_status, 'invalid_monitor');
    assert.equal(checked.input_eligibility, 'blocked_monitor');
  }
  assert.equal(validateSnapshot({...source,input_eligibility:'blocked_monitor'},now).input_eligibility,'blocked_monitor');
  assert.equal(validateSnapshot({...source,source_monitor:{...source.source_monitor,current:false}},now).client_monitor_status,'source_blocked');
});

test('snapshot remains stale; request never contains authorization', async t => {
  t.mock.method(globalThis, 'fetch', async (_, options) => {
    assert.equal(options.headers.Authorization, undefined);
    assert.equal(options.redirect, 'error');
    return new Response(JSON.stringify(state()));
  });
  assert.equal((await contextSnapshot()).source_monitor.current, false);
});

test('stream reset, coalesced update and bounded client cancellation', async t => {
  let cancelled = false;
  const bytes = new TextEncoder().encode(frame() + frame('snapshot', 3));
  t.mock.method(globalThis, 'fetch', async () => new Response(new ReadableStream({start(c) { c.enqueue(bytes); }, cancel() { cancelled = true; }}), {headers:{'Content-Type':'text/event-stream'}}));
  const events = [];
  for await (const event of contextEvents()) { events.push(event); if (events.length === 2) break; }
  assert.equal(events[1].data.sequence, 3);
  assert.equal(events[1].data.delivery.replay_complete, false);
  assert.equal(events[1].data.client_monitor_current, false);
  assert.equal(cancelled, true);
});

test('wrong content type and HTTP failure cancel response bodies', async t => {
  for (const [status, type] of [[200,'application/json'],[503,'text/event-stream']]) {
    let cancelled = false;
    t.mock.method(globalThis, 'fetch', async () => new Response(new ReadableStream({cancel() {cancelled=true;}}),
      {status,headers:{'Content-Type':type}}));
    await assert.rejects(async () => { for await (const event of contextEvents()) void event; });
    assert.equal(cancelled,true);
  }
});

test('unknown event, missing reset, oversized or truncated stream rejected', async t => {
  const heartbeat = 'event: keepalive\ndata: {"transport_only":true,"source_freshness_proof":false}\n\n';
  for (const body of [frame('snapshot'), frame('bad'), frame().slice(0,-1), 'data:' + 'x'.repeat(18000), heartbeat]) {
    t.mock.method(globalThis, 'fetch', async () => new Response(body, {headers:{'Content-Type':'text/event-stream'}}));
    await assert.rejects(async () => { for await (const event of contextEvents()) void event; });
  }
});

test('keepalive after reset remains transport-only', async t => {
  const heartbeat = 'event: keepalive\ndata: {"transport_only":true,"source_freshness_proof":false}\n\n';
  t.mock.method(globalThis, 'fetch', async () => new Response(frame() + heartbeat,
    {headers:{'Content-Type':'text/event-stream'}}));
  const events = [];
  for await (const event of contextEvents()) events.push(event);
  assert.equal(events.length, 2);
  assert.equal(events[1].data.source_freshness_proof, false);
});
