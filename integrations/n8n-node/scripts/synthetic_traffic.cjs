// Test-process instrumentation only; this file is excluded from the npm package.
// Add a diagnostic label after native request construction without changing
// the node, request URL/body, response handling, or requests to other services.
const https = require('node:https');
const original = https.request;
https.request = function (...args) {
  const request = Reflect.apply(original, this, args);
  const host = String(request.getHeader('host') || '').toLowerCase();
  if (host === 'agents.seiche.info' &&
      String(request.path).split('?')[0] === '/v1/research/api/v1/query') {
    request.setHeader('X-Financial-Evidence-Traffic-Class', 'synthetic');
  }
  return request;
};
