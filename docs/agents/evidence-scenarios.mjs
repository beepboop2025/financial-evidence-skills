// Authored examples, never a feed or a statement about current product health.
// Mirrors the selected paper profile's illustrated limits, not its full validator.
export const PAPER_PROFILE = Object.freeze({
  id:'liquilens.paper-funding-exit.v1', source_age_seconds:691200,
  undertow_age_seconds:300, max_exit_cost_bps:25, max_venue_spread_bps:15,
});
const base = {
  id:'eligible', label:'Eligible illustration', synthetic:true,
  evaluated_at:'2026-10-08T12:00:00Z',
  seiche:{observed_at:'2026-10-07T00:00:00Z', retrieved_at:'2026-10-08T11:59:50Z',
    sofr_minus_iorb_bp:3, effr_minus_iorb_bp:-2},
  liquilens:{spread_observed_at:'2026-10-07T00:00:00Z',
    rollover_observed_at:'2026-10-07T00:00:00Z', retrieved_at:'2026-10-08T11:59:51Z'},
  undertow:{observed_at:'2026-10-08T11:59:40Z', retrieved_at:'2026-10-08T11:59:52Z',
    rights_status:'approved_in_example_only', worst_sell_cost_bps:12, venue_spread_bps:4,
    side:'sell', executable_quote:false},
};
const examples = [base,
  {...base, id:'funding-pressure', label:'Seiche: funding pressure',
    seiche:{...base.seiche, sofr_minus_iorb_bp:18}},
  {...base, id:'stale-cp', label:'LiquiLens: stale CP observation',
    liquilens:{...base.liquilens, rollover_observed_at:'2026-09-30T00:00:00Z'}},
  {...base, id:'missing-rights', label:'Undertow: missing permissions',
    undertow:{...base.undertow, rights_status:'unknown'}},
  {...base, id:'expensive-exit', label:'Undertow: expensive SELL liquidation',
    undertow:{...base.undertow, worst_sell_cost_bps:38}},
];
export function scenarios() { return examples.map(({id,label}) => ({id,label})); }
export function getScenario(id) {
  const found = examples.find(example => example.id === id);
  if (!found) throw new Error('Unknown synthetic evidence scenario.');
  return structuredClone(found);
}
export function fundingRegime(pressure) {
  return ['CALM','EROSION','STRAIN','STRESS'][[5,15,25].filter(limit => pressure > limit).length];
}
export function evaluateEvidence(evidence) {
  const now = Date.parse(evidence.evaluated_at);
  const unavailable = [], holds = [], limits = [];
  const clockValid = (stamp, maximum) => {
    const age = (now - Date.parse(stamp))/1000;
    return Number.isFinite(age) && age >= 0 && age < maximum;
  };
  const seiche = evidence.seiche, cp = evidence.liquilens, exit = evidence.undertow;
  const pressure = Math.max(seiche.sofr_minus_iorb_bp, Math.abs(seiche.effr_minus_iorb_bp));
  const regime = fundingRegime(pressure);
  if (![seiche.sofr_minus_iorb_bp,seiche.effr_minus_iorb_bp].every(Number.isFinite)) unavailable.push('seiche_funding_inputs_unavailable');
  if (!clockValid(seiche.observed_at, PAPER_PROFILE.source_age_seconds)) unavailable.push('seiche_observation_unavailable');
  if (['STRAIN','STRESS'].includes(regime)) holds.push(`seiche_regime_${regime.toLowerCase()}_held_by_policy`);
  if (![cp.spread_observed_at, cp.rollover_observed_at].every(stamp => clockValid(stamp, PAPER_PROFILE.source_age_seconds))) unavailable.push('liquilens_cp_observation_stale_or_invalid');
  if (exit.rights_status !== 'approved_in_example_only') unavailable.push('undertow_rights_manifest_not_approved');
  if (!clockValid(exit.observed_at, PAPER_PROFILE.undertow_age_seconds)) unavailable.push('undertow_observation_stale_or_invalid');
  for (const [product, section] of Object.entries({seiche,liquilens:cp,undertow:exit})) {
    const retrieved = Date.parse(section.retrieved_at);
    const observations = product === 'liquilens' ? [cp.spread_observed_at,cp.rollover_observed_at] : [section.observed_at];
    if (!Number.isFinite(retrieved) || retrieved > now || observations.some(stamp => Date.parse(stamp) > retrieved)) unavailable.push(`${product}_retrieval_unavailable`);
  }
  if (![exit.worst_sell_cost_bps,exit.venue_spread_bps].every(Number.isFinite)) unavailable.push('undertow_cost_measurements_unavailable');
  if (exit.side !== 'sell' || exit.executable_quote !== false) unavailable.push('undertow_hypothetical_sell_scope_invalid');
  if (exit.worst_sell_cost_bps > PAPER_PROFILE.max_exit_cost_bps) limits.push('max_exit_cost_bps_exceeded');
  if (exit.venue_spread_bps > PAPER_PROFILE.max_venue_spread_bps) limits.push('max_venue_spread_bps_exceeded');
  const outcome = unavailable.length ? 'unavailable' : holds.length ? 'hold' : limits.length ? 'limit' : 'pass';
  return {outcome, reason_codes:[...unavailable,...holds,...limits].length ? [...unavailable,...holds,...limits] : ['operator_policy_satisfied'],
    pressure_bp:pressure, regime, profile_id:PAPER_PROFILE.id, simulated:true,
    execution_authority:false, summary:{
      pass:'The illustrated evidence checks pass. Preview a proposal to check the simulated account before submitting.',
      unavailable:'Required evidence is unavailable. This proposal cannot be submitted.',
      hold:'An experimental operator funding rule holds this proposal.',
      limit:'The hypothetical SELL liquidation exceeds an operator limit. No automatic resizing.',
    }[outcome]};
}
