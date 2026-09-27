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
    endpoint = 'https://api.seiche.info/mcp'; tool = 'funding_stress_now';
    if (evidence.schema !== 'seiche.public.v2' || !object(evidence.data_quality) || !object(evidence.conclusion)) {
      throw new Error('Unexpected Seiche funding contract');
    }
    sourceClock = evidence.generated_at;
    state = clockState(sourceClock);
    const counts = evidence.data_quality.status_counts;
    if (!object(counts) || !['fresh', 'aging', 'dead', 'unknown'].every(k => Number.isInteger(counts[k]) && counts[k] >= 0)) {
      throw new Error('Funding source-quality counts are missing');
    }
    const c = evidence.conclusion;
    const regime = typeof c.regime === 'string' && /^[A-Z_ -]{1,40}$/.test(c.regime) ? c.regime : null;
    if (!regime || !number(c.value) || !number(c.coverage_pct)) throw new Error('Funding conclusion is incomplete');
    const timely = state === 'WITHIN_SNAPSHOT_AGE_LIMIT';
    if (timely) state = counts.aging + counts.dead + counts.unknown > 0 || c.coverage_pct < 100 ? 'DATA_GAPS' : 'SOURCE_REPORTED';
    lines = [`Seiche funding review — ${state}`, `Board generated: ${sourceClock}`];
    if (timely) lines.push(`Source-reported regime: ${regime}; gauge ${c.value}/100; coverage ${c.coverage_pct}%.`);
    else lines.push('Snapshot is outside the configured age window; current reading withheld.');
    lines.push(`Sources: ${counts.fresh} fresh, ${counts.aging} aging, ${counts.dead} dead, ${counts.unknown} unknown.`);
    lines.push('Board generation time is not the date of every observation. Inspect headline_ages and proof limits in the retained evidence.');
    lines.push('https://seiche.info/');
  } else if (product === 'liquilens') {
    endpoint = 'https://api.liquilens.in/mcp'; tool = 'bank_asset_quality_review';
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
    endpoint = 'https://api.seiche.info/undertow/mcp'; tool = 'exit_cost';
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
