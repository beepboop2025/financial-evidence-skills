// Node 22+ / modern fetch clients. Source metadata only; no execution authority.
const MAX = 16384, FRAME = 17408;

function options({baseUrl = 'https://agents.seiche.info', timeoutMs = 30000, synthetic = false, signal} = {}) {
  const base = new URL(baseUrl);
  if ((base.protocol !== 'https:' && !(base.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(base.hostname))) || base.username || base.password || base.search || base.hash || /[%\\]/.test(baseUrl)) throw new Error('Invalid platform URL');
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 120000 || typeof synthetic !== 'boolean') throw new Error('Invalid client options');
  return {baseUrl: base.href.replace(/\/$/, ''), redirect: 'error', signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(timeoutMs)]) : AbortSignal.timeout(timeoutMs), headers: {'X-Financial-Evidence-Traffic-Class': synthetic ? 'synthetic' : 'unknown'}};
}

function timestamp(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(value)) return null;
  const whole = value.slice(0, 19), milliseconds = Date.parse(whole + 'Z');
  if (!Number.isFinite(milliseconds) || new Date(milliseconds).toISOString().slice(0, 19) !== whole) return null;
  const fraction = /\.(\d+)/.exec(value);
  return milliseconds + (fraction ? Number('0.' + fraction[1]) * 1000 : 0);
}

// Revalidate retained snapshots before use; receipt-time validity is not a lease.
export function validateSnapshot(value, nowMs = Date.now()) {
  if (value?.schema !== 'seiche-agent-network.context.v1' || value.scope !== 'source_status_metadata' || value.execution_authority !== 'none' || value.coverage_complete !== false || !/^[a-f0-9]{32}$/.test(value.stream_id) || !/^[a-f0-9]{64}$/.test(value.revision) || !Number.isSafeInteger(value.sequence) || value.sequence < 1 || !Array.isArray(value.products) || !value.source_monitor || typeof value.source_monitor !== 'object' || Array.isArray(value.source_monitor)) throw new Error('Invalid context snapshot');
  if (!Number.isFinite(nowMs)) throw new Error('Invalid client clock');
  const monitor = value.source_monitor, evaluated = timestamp(monitor.evaluated_at), expires = timestamp(monitor.valid_until);
  let status;
  if (evaluated === null || expires === null || monitor.max_age_seconds !== 900 || expires !== evaluated + 900000) status = 'invalid_monitor';
  else if (evaluated > nowMs) status = 'future_clock';
  else if (nowMs >= expires) status = 'stale';
  else if (monitor.current !== true || monitor.status !== 'current') status = 'source_blocked';
  else status = 'current';
  return {...value, client_monitor_current: status === 'current', client_monitor_status: status,
    client_monitor_checked_at: new Date(nowMs).toISOString(),
    input_eligibility: status === 'current' && value.input_eligibility === 'not_evaluated' ? 'not_evaluated' : 'blocked_monitor'};
}

async function open(path, config, headers = {}) {
  const {baseUrl, ...init} = options(config);
  const response = await fetch(baseUrl + path, {...init, headers: {...init.headers, ...headers}});
  if (!response.ok || !response.body) {
    await response.body?.cancel();
    throw new Error(`Context unavailable (${response.status})`);
  }
  return response;
}

export async function contextSnapshot(config = {}) {
  const response = await open('/v1/context/snapshot', config);
  const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', {fatal: true});
  let size = 0, text = '';
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX) throw new Error('Snapshot too large');
      text += decoder.decode(value, {stream: true});
    }
    return validateSnapshot(JSON.parse(text + decoder.decode()));
  } finally { await reader.cancel(); reader.releaseLock(); }
}

export async function* contextEvents(config = {}) {
  const cursor = config.lastEventId;
  if (cursor !== undefined && (typeof cursor !== 'string' || !/^[a-f0-9]{32}:[1-9][0-9]{0,19}$/.test(cursor))) throw new Error('Invalid event cursor');
  const response = await open('/v1/context/events', config, {Accept: 'text/event-stream', ...(cursor ? {'Last-Event-ID': cursor} : {})});
  if (response.headers.get('content-type')?.split(';')[0] !== 'text/event-stream') {
    await response.body.cancel();
    throw new Error('Expected event stream');
  }
  const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', {fatal: true}), encoder = new TextEncoder();
  let buffer = '', previous;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) { buffer += decoder.decode(); if (buffer) throw new Error('Truncated stream'); break; }
      buffer += decoder.decode(value, {stream: true});
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        if (encoder.encode(frame).length > FRAME) throw new Error('Event too large');
        const fields = {}, data = [];
        for (const line of frame.split(/\r?\n/)) {
          if (line.startsWith(':')) continue;
          const colon = line.indexOf(':'); if (colon < 0) continue;
          const key = line.slice(0, colon), body = line.slice(colon + 1).replace(/^ /, '');
          if (key === 'data') data.push(body);
          else if (key === 'id' || key === 'event') { if (key in fields) throw new Error('Duplicate event field'); fields[key] = body; }
        }
        if (!data.length) continue;
        const event = {...fields, data: JSON.parse(data.join('\n'))};
        if (event.event === 'keepalive') {
          if (event.data.transport_only !== true || event.data.source_freshness_proof !== false) throw new Error('Invalid keepalive');
        } else {
          if (!['reset', 'snapshot'].includes(event.event)) throw new Error('Unknown event');
          const state = validateSnapshot(event.data);
          if (event.id !== `${state.stream_id}:${state.sequence}` || state.delivery?.replay_complete !== false) throw new Error('Invalid event envelope');
          if (!previous && event.event !== 'reset') throw new Error('Expected initial reset');
          if (previous && event.event !== 'reset' && (state.stream_id !== previous.stream_id || state.sequence <= previous.sequence)) throw new Error('Nonmonotonic event');
          previous = state;
          event.data = state;
        }
        yield event;
      }
      if (encoder.encode(buffer).length > FRAME) throw new Error('Event too large');
    }
  } finally { await reader.cancel(); reader.releaseLock(); }
}
