const {test} = require('node:test');
const assert = require('node:assert/strict');
const https = require('node:https');

test('native test instrumentation labels only the reviewed hosted request', () => {
  const original = https.request;
  const calls = [];
  https.request = (options) => ({path: options.path, getHeader: () => options.host,
    setHeader: (name, value) => calls.push({name, value, host: options.host, path: options.path})});
  try {
    require('../scripts/synthetic_traffic.cjs');
    for (const options of [
      {host: 'agents.seiche.info', path: '/v1/research/api/v1/query?dataset=money_markets'},
      {host: 'agents.seiche.info.evil', path: '/v1/research/api/v1/query'},
      {host: 'api.seiche.info', path: '/openbb/api/v1/query'},
      {host: 'agents.seiche.info', path: '/v1/private'},
    ]) https.request(options);
    assert.deepEqual(calls, [{name: 'X-Financial-Evidence-Traffic-Class', value: 'synthetic',
      host: 'agents.seiche.info', path: '/v1/research/api/v1/query?dataset=money_markets'}]);
  } finally { https.request = original; }
});
