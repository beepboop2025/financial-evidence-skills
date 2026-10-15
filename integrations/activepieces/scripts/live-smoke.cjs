const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { financialEvidence } = require('../dist');

(async () => {
  const catalog = await financialEvidence.getAction('list_research_datasets').run({ propsValue: {} });
  const pages = [];
  for (const dataset of ['money_markets', 'bank_risk', 'market_liquidity']) {
    const result = await financialEvidence.getAction('get_evidence_page').run({ propsValue: { dataset, limit: 1, offset: 0 } });
    assert.equal(result.results.length, 1, `Expected one ${dataset} observation`);
    assert.ok(result.sources.length > 0, `Missing ${dataset} source metadata`);
    pages.push({
      dataset, returned_rows: result.results.length, next_offset: result.next_offset,
      response_sha256: createHash('sha256').update(JSON.stringify(result)).digest('hex'),
      observations: result.results.map(({ as_of, availability, source_status, unit, rights_status }) => ({ as_of, availability, source_status, unit, rights_status })),
      sources: result.sources.map(({ source_url, source_reported }) => ({ source_url, source_reported })),
      diagnostics: result.diagnostics,
    });
  }
  console.log(JSON.stringify({
    observed_at: new Date().toISOString(), node: process.version,
    pieces_framework: require('@activepieces/pieces-framework/package.json').version,
    package_version: require('../package.json').version,
    status: 'sdk_actions_live_read_passed',
    native_editor_installation: 'not_tested', upstream_submission: 'not_submitted',
    catalog_ids: catalog.map(({ id }) => id), pages,
  }, null, 2));
})().catch((error) => { console.error(error); process.exitCode = 1; });
