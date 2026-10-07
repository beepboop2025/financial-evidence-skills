const {test, afterEach} = require('node:test');
const assert = require('node:assert/strict');
const nock = require('nock');
const app = require('../index');
const tester = require('zapier-platform-core').createAppTester(app);
const perform = app.creates.evidence_page.operation.perform;
const page = {schema: 'liquidity-lab.openbb-table.v1', dataset: 'bank_risk', results: [{value: null, as_of: '2025-03-31', availability: 'restricted'}], diagnostics: [{availability: 'unavailable'}], sources: [{rights_status: 'unknown'}], next_offset: null, transport_status: 'partial'};
nock.disableNetConnect();
afterEach(() => { assert.ok(nock.isDone(), 'expected request was not performed'); nock.cleanAll(); });
test('actual Zapier runtime preserves missing data and the full research page', async () => {
  nock('https://api.seiche.info').get('/openbb/api/v1/query').query({dataset: 'bank_risk', entity: '', limit: 25, offset: 0}).reply(200, page);
  assert.deepEqual(await tester(perform, {inputData: {dataset: 'bank_risk'}}), page);
});
test('HTTP failure cannot become a completed research action', async () => {
  nock('https://api.seiche.info').get('/openbb/api/v1/query').query(true).reply(503, {error: 'unavailable'});
  await assert.rejects(tester(perform, {inputData: {dataset: 'bank_risk'}}));
});
test('rejects the wrong dataset even with HTTP 200', async () => {
  nock('https://api.seiche.info').get('/openbb/api/v1/query').query(true).reply(200, {...page, dataset: 'money_markets'});
  await assert.rejects(tester(perform, {inputData: {dataset: 'bank_risk'}}), /Unexpected research response/);
});
test('out-of-range pagination fails before requesting data', async () => {
  await assert.rejects(tester(perform, {inputData: {dataset: 'bank_risk', limit: 2000}}), /limit 1–100/);
});
