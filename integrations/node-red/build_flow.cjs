#!/usr/bin/env node
// Generate an importable core-node flow and the identical public download.
const fs = require('node:fs');
const path = require('node:path');
const base = __dirname;
const tab = 'a43b6cb01e714321';
const prepare = 'a43b6cb01e714325';
const http = 'a43b6cb01e714326';
const validate = 'a43b6cb01e714327';
const evidence = 'a43b6cb01e714328';
const failure = 'a43b6cb01e714329';
const tasks = [
  ['a43b6cb01e714322', 'USD money-market preview', 'money_markets', 'USD', 160],
  ['a43b6cb01e714323', 'AU SFB filing preview', 'bank_risk', 'au-sfb', 240],
  ['a43b6cb01e714324', 'BTC indicative liquidity preview', 'market_liquidity', 'BTC', 320]
];
const flow = [
  {id: tab, type: 'tab', label: 'Financial Evidence research previews', disabled: false, info: 'Click one Inject button, then inspect the Debug sidebar. Each click makes one bounded public GET. No timer, credentials, model, outbound message or trading action. Edit each Inject payload to choose a supported dataset, entity substring and limit (1–200). Synthetic is false for your research and must be true for operator/CI tests. Keep the full table with its sources, clocks, units, rights, missingness and partial state. MIT flow code does not grant source-data rights.'},
  {id: 'a43b6cb01e714330', type: 'comment', z: tab, name: '1. Click one task • 2. Inspect evidence + warnings in Debug', info: 'Deploy does not fetch anything. Each manual click requests one page, never auto-follows pagination. The default bank is one currently covered institution, not universal bank coverage. BTC rows are indicative public research measures, not executable quotes or a validated composite.', x: 400, y: 60, wires: []},
  ...tasks.map(([id, name, dataset, entity, y]) => ({id, type: 'inject', z: tab, name, props: [{p: 'payload'}], repeat: '', crontab: '', once: false, onceDelay: 0.1, topic: '', payload: JSON.stringify({dataset, entity, limit: 25, synthetic: false}), payloadType: 'json', x: 190, y, wires: [[prepare]]})),
  {id: prepare, type: 'function', z: tab, name: 'Validate task + bounded GET', func: fs.readFileSync(path.join(base, 'functions/prepare.js'), 'utf8'), outputs: 2, timeout: 0, noerr: 0, initialize: '', finalize: '', libs: [], x: 500, y: 240, wires: [[http], [failure]]},
  {id: http, type: 'http request', z: tab, name: 'Public research table (20s)', method: 'GET', ret: 'txt', paytoqs: 'ignore', url: '', tls: '', persist: false, proxy: '', insecureHTTPParser: false, authType: '', senderr: false, headers: [], x: 780, y: 240, wires: [[validate]]},
  {id: validate, type: 'function', z: tab, name: 'Keep provenance + partial state', func: fs.readFileSync(path.join(base, 'functions/validate.js'), 'utf8'), outputs: 2, timeout: 0, noerr: 0, initialize: '', finalize: '', libs: [], x: 1080, y: 240, wires: [[evidence], [failure]]},
  {id: evidence, type: 'debug', z: tab, name: 'Evidence preview — expand table + warnings', active: true, tosidebar: true, console: false, tostatus: false, complete: 'payload', targetType: 'msg', statusVal: '', statusType: 'auto', x: 1110, y: 140, wires: []},
  {id: 'a43b6cb01e714331', type: 'catch', z: tab, name: 'Transport / runtime errors', scope: [prepare, http, validate], uncaught: false, x: 500, y: 400, wires: [['a43b6cb01e714332']]},
  {id: 'a43b6cb01e714332', type: 'function', z: tab, name: 'Readable failure (no raw payload)', func: 'return {payload: {status: "request_failed", detail: msg.error && msg.error.message || "Network or processing error", task: msg.task || null, financial_authority: "none"}};', outputs: 1, timeout: 0, noerr: 0, initialize: '', finalize: '', libs: [], x: 820, y: 400, wires: [[failure]]},
  {id: failure, type: 'debug', z: tab, name: 'Research request needs attention', active: true, tosidebar: true, console: false, tostatus: false, complete: 'payload', targetType: 'msg', statusVal: '', statusType: 'auto', x: 1110, y: 480, wires: []}
];
const text = JSON.stringify(flow, null, 2) + '\n';
const outputs = ['financial-evidence.flow.json', '../../docs/automations/node-red/financial-evidence.flow.json'];
const check = process.argv.includes('--check');
for (const name of outputs) {
  const filename = path.join(base, name);
  if (check) {
    if (!fs.existsSync(filename) || fs.readFileSync(filename, 'utf8') !== text) {
      throw new Error(`Generated Node-RED flow differs: ${name}`);
    }
  } else {
    fs.writeFileSync(filename, text);
  }
}
console.log(`${check ? 'Verified' : 'Generated'} ${flow.length} core nodes; both flow files are identical.`);
