'use strict';
const datasets = ['bank_risk', 'capital_markets', 'china_economy', 'market_liquidity', 'money_market_history', 'money_markets', 'source_health'];
const perform = async (z, bundle) => {
  const {dataset, entity = '', limit = 25, offset = 0} = bundle.inputData;
  if (!datasets.includes(dataset) || typeof entity !== 'string' || entity.length > 100 ||
      !Number.isInteger(Number(limit)) || Number(limit) < 1 || Number(limit) > 100 ||
      !Number.isInteger(Number(offset)) || Number(offset) < 0 || Number(offset) > 100000) {
    throw new z.errors.Error('Use a listed dataset, entity up to 100 characters, limit 1–100 and offset 0–100000.', 'InvalidInput');
  }
  const response = await z.request({
    url: 'https://api.seiche.info/openbb/api/v1/query', method: 'GET',
    params: {dataset, entity, limit, offset}, headers: {Accept: 'application/json'},
  });
  response.throwForStatus();
  const data = response.data;
  if (!data || data.schema !== 'liquidity-lab.openbb-table.v1' || data.dataset !== dataset ||
      !Array.isArray(data.results) || !Array.isArray(data.diagnostics) || !Array.isArray(data.sources) ||
      !Object.hasOwn(data, 'next_offset')) {
    throw new z.errors.Error('Unexpected research response. No result was produced.', 'ResponseContract');
  }
  return data;
};
module.exports = {
  version: require('./package.json').version,
  platformVersion: require('zapier-platform-core').version,
  flags: {cleanInputData: false},
  creates: {
    evidence_page: {
      key: 'evidence_page', noun: 'Evidence Page',
      display: {label: 'Get Evidence Page', description: 'Gets a research page with source links, observation dates, units, pagination and coverage diagnostics.'},
      operation: {
        inputFields: [
          {key: 'dataset', label: 'Dataset', required: true, choices: datasets},
          {key: 'entity', label: 'Entity', type: 'string', helpText: 'Optional entity ID or name filter, up to 100 characters.'},
          {key: 'limit', label: 'Limit', type: 'integer', default: '25', helpText: '1–100 rows per page.'},
          {key: 'offset', label: 'Offset', type: 'integer', default: '0', helpText: 'Map next_offset from a previous page. Null means no next page.'},
        ],
        perform,
        sample: {schema: 'liquidity-lab.openbb-table.v1', dataset: 'bank_risk', description: 'Synthetic unavailable example; not current financial evidence', results: [], total_rows: 0, returned_rows: 0, offset: 0, limit: 25, next_offset: null, transport_status: 'partial', evidence_status: 'not_evaluated', carrier_verification: 'not_verified', absence_policy: 'Missing is not zero', status_semantics: 'Transport only', diagnostics: [], sources: []},
        outputFields: [
          {key: 'dataset', type: 'string'}, {key: 'transport_status', type: 'string'},
          {key: 'evidence_status', type: 'string'}, {key: 'carrier_verification', type: 'string'},
          {key: 'returned_rows', type: 'integer'}, {key: 'next_offset', type: 'integer'},
          {key: 'results', list: true, children: [{key: 'entity_name'}, {key: 'value', type: 'number'}, {key: 'unit'}, {key: 'as_of'}, {key: 'availability'}, {key: 'source_url'}]},
        ],
      },
    },
  },
};
