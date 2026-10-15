#!/usr/bin/env node
// Usage: node native_acceptance.cjs /absolute/path/to/node-red /absolute/evidence-directory
// Dependencies live outside this repository. The runtime binds only to loopback.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const [modulePath, outputPath] = process.argv.slice(2);
if (!modulePath || !outputPath || !path.isAbsolute(modulePath) || !path.isAbsolute(outputPath)) throw Error('Provide absolute Node-RED module and output paths.');
fs.mkdirSync(outputPath, {recursive: true});
const RED = require(modulePath);
const express = require(require.resolve('express', {paths: [modulePath]}));
const version = JSON.parse(fs.readFileSync(path.join(modulePath, 'package.json'))).version;
if (version !== '5.0.8') throw Error('This acceptance run is pinned to Node-RED 5.0.8.');
const publicPath = path.join(__dirname, 'financial-evidence.flow.json');
const original = fs.readFileSync(publicPath);
const flow = JSON.parse(original);
const injects = flow.filter(n => n.type === 'inject');
for (const n of injects) {const payload = JSON.parse(n.payload); payload.synthetic = true; n.payload = JSON.stringify(payload);}
const userDir = fs.mkdtempSync(path.join(outputPath, 'isolated-runtime-'));
fs.writeFileSync(path.join(userDir, 'flows.json'), JSON.stringify(flow));
const app = express();
const server = http.createServer(app);
const log = [];
const receipt = {schema: 'financial-evidence.node-red-acceptance.v1', started_at: new Date().toISOString(), node_red: version, node: process.version, pid: process.pid, user_dir: userDir, public_flow_sha256: crypto.createHash('sha256').update(original).digest('hex'), synthetic: true, public_flow_changed: false, native_results: [], failures_checked: [], flow_library_accepted: false, external_user_verified: false};
let running = false;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, timeout=30000) {const start=Date.now(); while(!fn()) {if(Date.now()-start>timeout) throw Error('Timed out waiting for native result'); await delay(100);} return fn();}
(async () => {
 try {
  RED.init(server, {userDir, flowFile: 'flows.json', uiHost: '127.0.0.1', disableEditor: true, httpAdminRoot: '/admin', httpNodeRoot: false, credentialSecret: false, functionExternalModules: false, externalModules: {autoInstall: false}, editorTheme: {projects: {enabled: false}}, logging: {console: {level: 'off'}, capture: {level: 'info', metrics: false, audit: false, handler: () => entry => log.push(entry)}}});
  app.use('/admin', RED.httpAdmin);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  receipt.listen_address = server.address();
  fs.writeFileSync(path.join(outputPath, 'runtime-ownership.json'), JSON.stringify({pid: process.pid, userDir, address: server.address()}, null, 2)+'\n');
  await RED.start(); running = true;
  await until(() => RED.nodes.getNode('a43b6cb01e714328'));
  const successes = [], failures = [];
  RED.nodes.getNode('a43b6cb01e714328').on('input', msg => successes.push(structuredClone(msg.payload)));
  RED.nodes.getNode('a43b6cb01e714329').on('input', msg => failures.push(structuredClone(msg.payload)));
  await delay(500);
  assert.equal(successes.length + failures.length, 0, 'Import/deploy must not execute requests');
  receipt.no_automatic_execution = true;
  for (const n of injects) {
    const task = JSON.parse(n.payload), before = successes.length, failureCount = failures.length;
    const response = await fetch(`http://127.0.0.1:${server.address().port}/admin/inject/${n.id}`, {method: 'POST'});
    assert.equal(response.status, 200, 'Native manual inject endpoint');
    await until(() => successes.length > before || failures.length > failureCount);
    if (failures.length > failureCount) throw Error(JSON.stringify(failures.at(-1)));
    const preview = successes.at(-1);
    assert.equal(preview.task.dataset, task.dataset);
    assert.equal(preview.task.synthetic, true);
    assert.equal(preview.financial_authority, 'none');
    fs.writeFileSync(path.join(outputPath, task.dataset+'.native-preview.json'), JSON.stringify(preview, null, 2)+'\n');
    receipt.native_results.push({dataset: task.dataset, entity: task.entity, returned_rows: preview.table.returned_rows, total_rows: preview.table.total_rows, transport_complete: preview.transport_complete, pagination_complete: preview.pagination_complete, source_partial_reported: preview.source_partial_reported, sources_retained: preview.table.sources.length, warnings: preview.warnings});
  }
  let expected = failures.length + 1;
  RED.nodes.getNode('a43b6cb01e714325').receive({payload: {dataset: 'invalid', entity: 'USD', limit: 25, synthetic: true}});
  await until(() => failures.length === expected);
  assert.equal(failures.at(-1).status, 'request_rejected');
  receipt.failures_checked.push('Unsupported task rejected by native Function node before HTTP');
  expected++;
  RED.nodes.getNode('a43b6cb01e714327').receive({task: JSON.parse(injects[0].payload), statusCode: 200, headers: {'content-type': 'text/html'}, payload: '<html>challenge</html>'});
  await until(() => failures.length === expected);
  assert.equal(failures.at(-1).status, 'response_rejected');
  receipt.failures_checked.push('HTML challenge rejected by native Function node');
  assert.equal(fs.readFileSync(publicPath).equals(original), true);
  receipt.status = 'passed';
 } catch (error) {receipt.status = 'failed'; receipt.error = error.stack; process.exitCode = 1;}
 finally {
  if (running) await RED.stop();
  await new Promise(resolve => server.close(resolve));
  receipt.stopped_at = new Date().toISOString();
  receipt.runtime_stopped = true;
  fs.writeFileSync(path.join(outputPath, 'native-runtime-log.json'), JSON.stringify(log, null, 2)+'\n');
  fs.writeFileSync(path.join(outputPath, 'native-acceptance.json'), JSON.stringify(receipt, null, 2)+'\n');
  console.log(JSON.stringify(receipt, null, 2));
 }
})().catch(error => {console.error(error); process.exitCode=1;});
