const {test} = require('node:test');
const assert = require('node:assert/strict');
const {FinancialEvidence} = require('../dist/nodes/FinancialEvidence/FinancialEvidence.node');
const page = {schema: 'liquidity-lab.openbb-table.v1', dataset: 'bank_risk', results: [{value: null, as_of: null, availability: 'unavailable', rights_status: 'unknown'}], sources: [{status: 'restricted'}], diagnostics: [{availability: 'unavailable'}], next_offset: 25, transport_status: 'partial'};
function context(data, options = {}) {
  return {
    getInputData: () => [{}], getNode: () => ({name: 'test', type: 'financialEvidence', typeVersion: 1, position: [0,0], parameters: {}}),
    getNodeParameter: key => ({dataset: 'bank_risk', entity: '', limit: 25, offset: 0, ...options}[key]),
    continueOnFail: () => false,
    helpers: {httpRequest: async req => { assert.equal(req.method, 'GET'); assert.equal(req.url, 'https://api.seiche.info/openbb/api/v1/query'); return data; }},
  };
}
test('retains nulls, restrictions, diagnostics, next page and item identity', async () => {
  const result = await new FinancialEvidence().execute.call(context(page));
  assert.deepEqual(result, [[{json: page, pairedItem: {item: 0}}]]);
});
test('rejects an HTML/error-shaped response and wrong dataset', async () => {
  for (const bad of ['<html>down</html>', {error: 'down'}, {...page, dataset: 'money_markets'}]) {
    await assert.rejects(new FinancialEvidence().execute.call(context(bad)), /Unexpected research response/);
  }
});
test('bounds expression-driven parameters before network access', async () => {
  const ctx = context(page, {limit: 10000});
  ctx.helpers.httpRequest = () => { throw Error('network must not run'); };
  await assert.rejects(new FinancialEvidence().execute.call(ctx), /limit 1–100/);
});
test('continues errors only when explicitly configured, without fake research data', async () => {
  const ctx = context(page); ctx.continueOnFail = () => true;
  ctx.helpers.httpRequest = async () => {throw Error('HTTP 503');};
  assert.deepEqual(await new FinancialEvidence().execute.call(ctx), [[{json: {error: 'HTTP 503'}, pairedItem: {item: 0}}]]);
});
