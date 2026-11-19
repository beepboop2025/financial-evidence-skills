'use strict';

// Embedded in the downloadable workflows by scripts/build_task_workflows.py.
// Keep the source result intact; only the small notification is summarized.
function formatTaskResponse(product, response, settings, now = new Date()) {
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const number = value => typeof value === 'number' && Number.isFinite(value);
  const nonnegative = value => number(value) && value >= 0;
  if (!object(response) || response.error !== undefined || response.isError === true) {
    throw new Error('MCP tool failed; no completed research result is available');
  }
  let evidence = response.structuredContent;
  if (evidence === undefined) {
    const text = response.content?.find(item => item.type === 'text')?.text;
    evidence = typeof text === 'string' ? JSON.parse(text) : text;
  }
  if (!object(evidence)) throw new Error('Expected structured evidence');
  if (!object(settings) || !object(settings.toolInput)) throw new Error('Missing task settings');
  const retrievedAt = now.toISOString();
  let state, sourceClock, lines, endpoint, tool;
  const clockState = timestamp => {
    const time = typeof timestamp === 'string' ? Date.parse(timestamp) : NaN;
    if (!Number.isFinite(time)) throw new Error('Missing or invalid source generation clock');
    if (!number(settings.maxAgeSeconds) || settings.maxAgeSeconds <= 0) throw new Error('Invalid freshness limit');
    const age = (now.getTime() - time) / 1000;
    return age < -300 ? 'FUTURE_SOURCE_CLOCK' : age > settings.maxAgeSeconds ? 'STALE_SNAPSHOT' : 'WITHIN_SNAPSHOT_AGE_LIMIT';
  };
  if (product === 'seiche') {
    endpoint = 'https://agents.seiche.info/products/seiche/mcp'; tool = 'money_market_context';
    const short = (value, limit = 120) => typeof value === 'string' && value.length > 0 && value.length <= limit && !/[\r\n]/.test(value) ? value : null;
    const projection = evidence.publication_projection;
    const withheld = evidence.ok === false || evidence.available === false ||
      (object(projection) && projection.status !== 'public') ||
      ['unavailable', 'withheld', 'restricted', 'denied'].includes(String(evidence.status ?? '').toLowerCase());
    if (withheld) {
      sourceClock = short(evidence.snapshot_generated_at, 40);
      state = 'UNAVAILABLE';
      const reason = short(evidence.reason ?? (object(projection) ? projection.reason : null), 300);
      lines = [`Seiche money-market desk: ${state}`, `Reason given: ${reason ?? 'not supplied'}`,
        'No reading has been substituted for the unavailable evidence. Inspect the retained evidence.', 'https://seiche.info/money-markets/'];
    } else {
      if (evidence.schema !== 'seiche.money-market-desk.v1' || evidence.selection !== settings.toolInput.section ||
          !object(evidence.freshness) || !object(evidence.coverage)) {
        throw new Error('Unexpected Seiche money-market contract');
      }
      sourceClock = evidence.snapshot_generated_at;
      state = clockState(sourceClock);
      const counts = evidence.freshness.status_counts;
      if (!object(counts) || !['fresh', 'aging', 'stale', 'unavailable'].every(k => Number.isInteger(counts[k]) && counts[k] >= 0)) {
        throw new Error('Funding source freshness counts are missing');
      }
      const cov = evidence.coverage;
      if (!Number.isInteger(cov.available_metrics) || !Number.isInteger(cov.total_metrics) || cov.available_metrics < 0 || cov.total_metrics < cov.available_metrics) {
        throw new Error('Funding metric coverage is missing');
      }
      const signals = [['Most stretched channel', evidence.strongest_signal], ['Countercase', evidence.countercase]];
      const reading = x => {
        if (!object(x)) return 'not supplied';
        const value = number(x.value) ? `${x.value}${short(x.unit, 20) ? ` ${x.unit}` : ''}` : 'unavailable';
        const pct = v => number(v) ? v : 'not supplied';
        return `${short(x.label) ?? 'unlabelled channel'}: ${value}, observed ${short(x.asof, 40) ?? 'not supplied'} (${short(x.freshness, 20) ?? 'freshness not supplied'}); ` +
          `three-year percentile ${pct(x.empirical_percentile_3y)}, adjusted across ${pct(x.familywise_hypotheses)} channels ${pct(x.bonferroni_adjusted_stress_percentile)}.`;
      };
      const timely = state === 'WITHIN_SNAPSHOT_AGE_LIMIT';
      if (timely) {
        const gaps = counts.aging + counts.stale + counts.unavailable > 0 || cov.available_metrics < cov.total_metrics ||
          signals.some(([, x]) => !object(x) || !number(x.value));
        state = gaps ? 'DATA_GAPS' : 'SOURCE_REPORTED';
      }
      lines = [`Seiche money-market desk: ${state}`, `Snapshot generated: ${sourceClock}`,
        `Desk observations through ${short(evidence.asof, 40) ?? 'not supplied'}; evaluated on ${short(evidence.freshness.evaluation_asof, 40) ?? 'not supplied'}.`];
      if (timely) for (const [label, x] of signals) lines.push(`${label}: ${reading(x)}`);
      else lines.push('Snapshot is outside the configured age window; current readings withheld.');
      lines.push(`Sources: ${counts.fresh} fresh, ${counts.aging} aging, ${counts.stale} stale, ${counts.unavailable} unavailable. Metrics available: ${cov.available_metrics} of ${cov.total_metrics}.`);
      lines.push('Snapshot time is not the date of every observation. A three-year rank is descriptive context, not a forecast, probability or trade signal.');
      lines.push('The Seiche MCP does not serve its legacy stress score or forecasts while their source rights are qualified; this update does not reconstruct them.');
      lines.push('https://seiche.info/money-markets/');
    }
  } else if (product === 'liquilens') {
    endpoint = 'https://agents.seiche.info/products/liquilens/mcp'; tool = 'bank_asset_quality_review';
    if (evidence.schema !== 'liquilens.bank-specialisation.v1' || evidence.slug !== settings.toolInput.slug ||
        !['observed', 'stale', 'historical', 'unavailable'].includes(evidence.status) || evidence.scope !== 'research' ||
        evidence.score_authority !== false || evidence.can_authorize_credit !== false) {
      throw new Error('Unexpected bank identity, status or research contract');
    }
    sourceClock = evidence.period_end ?? null;
    state = evidence.status.toUpperCase();
    const cited = Array.isArray(evidence.sources) && evidence.sources.some(s => typeof s === 'string' && s.startsWith('https://'));
    if (state === 'OBSERVED' && !cited) state = 'UNCITED';
    lines = [`LiquiLens bank filing review — ${state}`, `Institution: ${evidence.slug}`, `Filing period end: ${sourceClock ?? 'not supplied'}`];
    if (state === 'OBSERVED') {
      const metrics = evidence.metrics;
      if (!object(metrics)) throw new Error('Missing bank metrics contract');
      const ratio = key => {
        const m = metrics[key];
        return object(m) && m.status === 'observed' && number(m.value) && m.unit === 'percent' ? `${m.value}%` : 'not disclosed';
      };
      lines.push(`GNPA ${ratio('gnpa_pct')}; NNPA ${ratio('nnpa_pct')}.`);
      const annual = evidence.changes?.year;
      if (annual?.status === 'observed' && annual.unit === 'percentage_points' && number(annual.changes?.gnpa_pct)) {
        lines.push(`GNPA year change: ${annual.changes.gnpa_pct} percentage points (${annual.from_period} to ${annual.to_period}).`);
      }
      const m = evidence.npa_movement;
      if (m?.status === 'reconciled' && m.amount_unit === 'INR_crore' && object(m.reductions)) {
        for (const [key, label] of [['cash_recoveries', 'Cash recoveries'], ['write_offs', 'Write-offs'], ['upgrades', 'Upgrades']]) {
          if (nonnegative(m.reductions[key])) lines.push(`${label}: INR ${m.reductions[key]} crore.`);
        }
        lines.push('Reconciliation is arithmetic against the supplied statement; reductions are not all cash recoveries.');
      }
    } else lines.push('Current ratios withheld; inspect the retained evidence status and coverage gaps.');
    lines.push('Filing dates, cited PDF pages, PCR basis and missing disclosures remain in the full record.');
    lines.push('https://liquilens.in/banking/?institution=' + encodeURIComponent(evidence.slug));
  } else if (product === 'undertow') {
    endpoint = 'https://agents.seiche.info/products/undertow/mcp'; tool = 'exit_cost';
    if (evidence.asset !== 'BTC' || !number(settings.toolInput.size_usd) || settings.toolInput.size_usd <= 0 ||
        evidence.requested_size_usd !== settings.toolInput.size_usd || !number(evidence.published_rung_used_usd) ||
        evidence.published_rung_used_usd <= 0 || !object(evidence.sell_cost_bp_by_venue) ||
        typeof evidence.method !== 'string' || !Array.isArray(evidence.unable_at_observed_depth)) {
      throw new Error('Unexpected BTC size or exit-estimate contract');
    }
    sourceClock = evidence.generated_at;
    state = clockState(sourceClock);
    const timely = state === 'WITHIN_SNAPSHOT_AGE_LIMIT';
    const costs = Object.entries(evidence.sell_cost_bp_by_venue);
    if (costs.some(([venue, cost]) => !/^[a-z0-9_-]{1,40}$/i.test(venue) || (cost !== null && !nonnegative(cost)))) {
      throw new Error('Malformed venue cost');
    }
    if (timely) state = costs.length === 0 || costs.some(([,cost]) => cost === null) || evidence.unable_at_observed_depth.length > 0 ? 'DEPTH_GAPS' : 'ESTIMATE_AVAILABLE';
    lines = [`Undertow BTC exit — ${state}`, `Snapshot generated: ${sourceClock}`,
      `Requested: USD ${evidence.requested_size_usd}; published rung used: USD ${evidence.published_rung_used_usd}.`];
    if (timely) for (const [venue, cost] of costs) lines.push(`${venue}: ${cost === null ? 'unavailable' : `${cost} bp`}`);
    else lines.push('Snapshot is outside the configured age window; current costs withheld.');
    if (evidence.unable_at_observed_depth.length) lines.push(`Insufficient observed depth at ${evidence.unable_at_observed_depth.length} venue(s); see full evidence.`);
    lines.push('Depth-band interpolation; fees excluded. An estimate, not an executable quote or guaranteed fill.');
    lines.push('https://liquilens.in/start/?task=exit&size=' + encodeURIComponent(evidence.requested_size_usd));
  } else throw new Error('Unknown research task');
  return { schema: 'liquidity-lab.task-delivery.v1', product, endpoint, tool,
    retrieved_at: retrievedAt, source_status: state, source_clock: sourceClock,
    message_text: lines.join('\n'), evidence };
}

if (typeof module !== 'undefined') module.exports = { formatTaskResponse };
