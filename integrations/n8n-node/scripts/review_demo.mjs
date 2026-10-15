#!/usr/bin/env node
/** A real, continuous n8n UI recording. No mocked model or network responses. */
import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdir, readFile, writeFile, readdir, copyFile, rm } from 'node:fs/promises';
import { openSync, closeSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createConnection } from 'node:net';

export const PIN = Object.freeze({
  n8n: '2.42.6', package: 'n8n-nodes-financial-evidence', version: '0.1.0',
  archiveSha256: '9d2fa6ba3950c41a68e025ea6f5c57922697c0b311ef6d77ce52412267b392ae',
  model: 'qwen3:1.7b',
  modelDigest: '8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7',
  ollama: '0.40.2', playwright: '1.64.0',
});
const BASE = 'http://127.0.0.1:5687';
const OLLAMA = 'http://127.0.0.1:11435';
const DATASETS = ['money_markets', 'bank_risk', 'market_liquidity'];
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const sleep = ms => new Promise(done => setTimeout(done, ms));
const MANIFEST_NORMALIZATION = 'n8n-2.42.6-community-package-manifest';

export function installedFileProjection(name, published, installed) {
  let expected = published;
  if (name === 'package.json') {
    // Exact n8n 2.42.6 behavior: community-packages.service.ts:1014-1029,
    // commit 34ab9c7bf3d0c6d2ec3422e12e0b970aea5717c7. No other fields may change.
    const { devDependencies, peerDependencies, optionalDependencies, ...manifest } = JSON.parse(published.toString('utf8'));
    expected = Buffer.from(JSON.stringify(manifest, null, 2));
  }
  assert.deepEqual(installed, expected, `Installed ${name} differs from its expected published content`);
  return {
    path: name, published_sha256: sha(published), installed_sha256: sha(installed),
    byte_identical: installed.equals(published),
    verification: name === 'package.json' ? MANIFEST_NORMALIZATION : 'exact_bytes',
    expected_sha256: sha(expected), verified: true,
  };
}

export function safeEnvironment(privateDir) {
  // No inherited credentials, N8N_*, DB_*, hooks, npm auth or model API keys.
  const env = Object.fromEntries(['HOME', 'PATH', 'LANG', 'LC_ALL', 'LD_LIBRARY_PATH'].filter(k => process.env[k]).map(k => [k, process.env[k]]));
  return {
    ...env, TMPDIR: join(privateDir, 'tmp'),
    N8N_USER_FOLDER: join(privateDir, 'profile'), DB_TYPE: 'sqlite',
    N8N_HOST: '127.0.0.1', N8N_LISTEN_ADDRESS: '127.0.0.1', N8N_PORT: '5687',
    N8N_PROTOCOL: 'http', N8N_EDITOR_BASE_URL: BASE, N8N_SECURE_COOKIE: 'false',
    N8N_DIAGNOSTICS_ENABLED: 'false', N8N_VERSION_NOTIFICATIONS_ENABLED: 'false',
    N8N_TEMPLATES_ENABLED: 'false', N8N_PERSONALIZATION_ENABLED: 'false',
    N8N_HIRING_BANNER_ENABLED: 'false', N8N_AI_ENABLED: 'false',
    N8N_COMMUNITY_PACKAGES_ENABLED: 'true', N8N_UNVERIFIED_PACKAGES_ENABLED: 'true',
    N8N_COMMUNITY_PACKAGES_PREVENT_LOADING: 'false',
    N8N_RUNNERS_MODE: 'internal', N8N_RUNNERS_BROKER_PORT: '5688',
    N8N_RUNNERS_BROKER_LISTEN_ADDRESS: '127.0.0.1', N8N_RUNNERS_MAX_CONCURRENCY: '1',
    N8N_RUNNERS_MAX_OLD_SPACE_SIZE: '256',
    N8N_LOG_LEVEL: 'warn', EXECUTIONS_DATA_SAVE_ON_SUCCESS: 'all',
    EXECUTIONS_DATA_SAVE_ON_ERROR: 'all', EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS: 'true',
    OLLAMA_HOST: '127.0.0.1:11435', OLLAMA_MODELS: join(privateDir, 'models'),
    OLLAMA_NO_CLOUD: '1', OLLAMA_NUM_PARALLEL: '1', OLLAMA_MAX_LOADED_MODELS: '1',
    OLLAMA_KEEP_ALIVE: '15m', CUDA_VISIBLE_DEVICES: '',
    npm_config_userconfig: join(privateDir, 'empty-npmrc'),
    npm_config_cache: join(privateDir, 'npm-cache'), npm_config_registry: 'https://registry.npmjs.org',
    NODE_OPTIONS: '--max-old-space-size=3072',
  };
}

export function pageProjection(page, dataset) {
  assert.equal(page?.schema, 'liquidity-lab.openbb-table.v1');
  assert.equal(page.dataset, dataset);
  for (const key of ['results', 'sources', 'diagnostics']) assert.ok(Array.isArray(page[key]), key);
  assert.ok(page.results.length <= 1, 'The demo request must remain bounded');
  assert.ok(Object.hasOwn(page, 'next_offset'));
  // Explicit allowlist: never copy an execution, credential object or owner profile.
  return Object.fromEntries(['schema', 'dataset', 'results', 'sources', 'diagnostics', 'next_offset', 'transport_status'].filter(k => Object.hasOwn(page, k)).map(k => [k, page[k]]));
}

export function executionProjection(execution, dataset, { agent = false } = {}) {
  assert.equal(execution.status, 'success', 'HTTP 200 alone is not successful execution');
  assert.equal(execution.finished, true);
  const result = execution.data?.resultData;
  assert.ok(result && !result.error, 'Native execution error');
  const name = agent ? 'Financial Evidence Tool' : 'Financial Evidence';
  const runs = result.runData?.[name];
  assert.ok(Array.isArray(runs) && runs.length === 1, 'Exactly one real evidence-node invocation is required');
  assert.ok(!runs[0].error && runs[0].executionStatus !== 'error');
  const main = runs[0].data?.main ?? runs[0].data?.ai_tool;
  const page = main?.[0]?.[0]?.json;
  const output = { id: execution.id, status: execution.status, page: pageProjection(page, dataset) };
  if (agent) {
    const agentRun = result.runData?.['Research Agent']?.[0];
    assert.ok(agentRun && !agentRun.error);
    assert.ok(result.runData?.['Local Qwen3']?.length, 'Actual local language model invocation is required');
    const item = agentRun.data?.main?.[0]?.[0]?.json;
    assert.ok(typeof item?.output === 'string' && item.output.trim());
    assert.ok(Array.isArray(item.intermediateSteps) && item.intermediateSteps.length === 1, 'Agent must retain the real tool call');
    assert.match(item.intermediateSteps[0]?.action?.tool ?? '', /financial.*evidence/i);
    const observed = JSON.parse(item.intermediateSteps[0].observation);
    assert.ok(Array.isArray(observed) && observed.length === 1, 'Agent must observe exactly the executed tool page');
    assert.deepEqual(observed[0], page, 'The model observation must equal the native tool output');
    output.model_output = item.output;
    output.tool_calls = item.intermediateSteps.map(step => ({ tool: step.action.tool, tool_input: step.action.toolInput, observation: pageProjection(observed[0], dataset) }));
  }
  return output;
}

export function agentWorkflow(credentialId, toolType = `${PIN.package}.financialEvidenceTool`) {
  assert.match(credentialId, /^[a-zA-Z0-9_-]+$/);
  return {
    name: 'Review demo - real local AI tool call', active: false,
    settings: { executionOrder: 'v1', saveManualExecutions: true },
    nodes: [
      { id: 'start', name: 'Manual Trigger', type: 'n8n-nodes-base.manualTrigger', typeVersion: 1, position: [160, 260], parameters: {} },
      { id: 'agent', name: 'Research Agent', type: '@n8n/n8n-nodes-langchain.agent', typeVersion: 3.1, position: [420, 260], parameters: {
        promptType: 'define', text: 'Use the Financial Evidence Tool exactly once now. Then report the first returned money-market entity, rate, unit and as_of date. Mention any PARTIAL or unavailable source state. Use only the tool response. Keep the answer under 65 words.',
        options: { systemMessage: 'You are demonstrating a financial research tool. You must call the available Financial Evidence Tool once before answering. Do not answer from memory. Do not call it more than once. After the result, give a concise factual research summary with its source date. This is research, not trading advice.', maxIterations: 3, returnIntermediateSteps: true, enableStreaming: false, forceToolCallOnFirstIteration: false },
      } },
      { id: 'model', name: 'Local Qwen3', type: '@n8n/n8n-nodes-langchain.lmChatOllama', typeVersion: 1, position: [320, 500], parameters: { model: PIN.model, options: { think: false, numCtx: 8192, numPredict: 220, numThread: 2, numGpu: 0, temperature: 0 } }, credentials: { ollamaApi: { id: credentialId, name: 'Local Ollama - no API key' } } },
      { id: 'tool', name: 'Financial Evidence Tool', type: toolType, typeVersion: 1, position: [660, 500], parameters: { descriptionType: 'manual', toolDescription: 'Fetch one bounded page of public source-cited money-market evidence. Call once before answering. Takes no arguments.', dataset: 'money_markets', entity: '', limit: 1, offset: 0 } },
      { id: 'note', name: 'Demo context', type: 'n8n-nodes-base.stickyNote', typeVersion: 1, position: [100, 30], parameters: { height: 160, width: 820, content: '## Financial Evidence 0.1.0 - review demonstration\nPublic research node: no API credential required. One bounded page per call.\nAI example: real local Qwen3 1.7B through Ollama; no paid model API.\nRetain source dates, diagnostics, PARTIAL status and unavailable/null values.\nEphemeral local self-hosted demo; no Creator/Cloud account created.' } },
    ],
    connections: {
      'Manual Trigger': { main: [[{ node: 'Research Agent', type: 'main', index: 0 }]] },
      'Local Qwen3': { ai_languageModel: [[{ node: 'Research Agent', type: 'ai_languageModel', index: 0 }]] },
      'Financial Evidence Tool': { ai_tool: [[{ node: 'Research Agent', type: 'ai_tool', index: 0 }]] },
    },
  };
}

export function validatePublishable(receipt) {
  assert.equal(receipt.status, 'passed');
  assert.equal(receipt.package.sha256, PIN.archiveSha256);
  assert.equal(receipt.package.name, PIN.package);
  assert.equal(receipt.package.version, PIN.version);
  assert.equal(receipt.n8n_version, PIN.n8n);
  assert.equal(receipt.model.digest.replace(/^sha256:/, ''), PIN.modelDigest);
  assert.deepEqual(Object.keys(receipt.actions).sort(), [...DATASETS].sort());
  for (const dataset of DATASETS) {
    assert.equal(receipt.actions[dataset].status, 'success');
    pageProjection(receipt.actions[dataset].page, dataset);
  }
  assert.equal(receipt.agent.status, 'success');
  pageProjection(receipt.agent.page, 'money_markets');
  assert.equal(receipt.agent.tool_calls.length, 1);
  assert.deepEqual(receipt.agent.tool_calls[0].observation, receipt.agent.page);
  assert.equal(receipt.video.continuous, true);
  assert.equal(receipt.video.cuts, 0);
  assert.ok(receipt.video.duration_seconds > 0 && receipt.video.duration_seconds <= 300);
  assert.equal(receipt.ui_installed_package, true);
  assert.equal(receipt.ui_created_new_workflow, true);
  assert.equal(receipt.services_stopped, true);
  const files = receipt.installed_package_files;
  assert.ok(Array.isArray(files) && files.length > 1);
  assert.equal(new Set(files.map(file => file.path)).size, files.length);
  const manifest = files.filter(file => file.path === 'package.json');
  assert.equal(manifest.length, 1);
  assert.equal(manifest[0].verification, MANIFEST_NORMALIZATION);
  for (const file of files) {
    assert.equal(file.verified, true);
    assert.equal(file.installed_sha256, file.expected_sha256);
    assert.equal(file.byte_identical, file.installed_sha256 === file.published_sha256);
    if (file.path !== 'package.json') {
      assert.equal(file.verification, 'exact_bytes');
      assert.equal(file.byte_identical, true);
    }
  }
  assert.equal(receipt.installed_files_match_published_archive, files.every(file => file.byte_identical));
  assert.equal(receipt.installed_runtime_files_match_published_archive, true);
  assert.equal(receipt.installed_manifest_matches_n8n_normalization, true);
  assert.equal(receipt.model_is_real, true);
  assert.equal(receipt.external_model_api_used, false);
  assert.equal(receipt.online_account_created, false);
  assert.equal(receipt.n8n_verified, false);
  assert.equal(receipt.independent_adoption_proven, false);
}

export function redactDiagnostic(text, secrets = []) {
  let clean = String(text);
  for (const secret of secrets.filter(Boolean)) clean = clean.split(secret).join('[redacted]');
  return clean.replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '[email redacted]')
    .replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, '[token redacted]').slice(0, 1600);
}

async function main() {
  assert.equal(process.env.GITHUB_ACTIONS, 'true', 'Owner setup is restricted to an ephemeral GitHub Actions runner');
  const [runtimeArg, ollamaArg, evidenceArg] = process.argv.slice(2);
  assert.ok(runtimeArg && ollamaArg && evidenceArg, 'usage: review_demo.mjs RUNTIME OLLAMA_BINARY NEW_EVIDENCE_DIR');
  const runtime = resolve(runtimeArg), ollamaBin = resolve(ollamaArg), evidence = resolve(evidenceArg);
  await mkdir(evidence, { mode: 0o700 }); // Refuse reuse of profiles or old videos.
  const privateDir = join(evidence, 'private'), output = join(evidence, 'review');
  await mkdir(privateDir, { mode: 0o700 });
  await mkdir(join(privateDir, 'tmp'), { mode: 0o700 });
  await writeFile(join(privateDir, 'empty-npmrc'), '', { mode: 0o600 });
  const env = safeEnvironment(privateDir);
  const require = createRequire(join(runtime, 'package.json'));
  const { chromium, selectors } = require('playwright');
  const { parse: unflatten } = require('flatted');
  selectors.setTestIdAttribute('data-test-id');
  const n8nBin = join(runtime, 'node_modules/n8n/bin/n8n');
  assert.equal(JSON.parse(await readFile(join(runtime, 'node_modules/n8n/package.json'))).version, PIN.n8n);
  assert.equal(require('playwright/package.json').version, PIN.playwright);
  const processes = [], logs = [];
  let browser, context, page, video, recordingStarted;
  let ownedModelState;
  let stage = 'preflight';
  const secrets = [];
  const receipt = { schema: 'financial-evidence.n8n-review-demo.v1', status: 'failed',
    source_revision: process.env.GITHUB_SHA ?? null, run_id: process.env.GITHUB_RUN_ID ?? null,
    observed_at: new Date().toISOString(), n8n_version: PIN.n8n, actions: {},
    browser_ui_observed: false, model_is_real: false, external_model_api_used: false,
    internal_demo: true, request_parameters: { datasets: DATASETS, limit: 1, offset: 0, entity: '' },
    online_account_created: false, owner_scope: 'ephemeral local self-hosted demo only',
    n8n_verified: false, independent_adoption_proven: false };
  const mark = label => { stage = label; console.log(`Demo stage: ${label}`); };
  const start = (label, command, args) => {
    const fd = openSync(join(privateDir, `${label}.log`), 'wx', 0o600); logs.push(fd);
    // Each task-owned service has its own process group, including model workers.
    const child = spawn(command, args, { env, stdio: ['ignore', fd, fd], detached: true });
    processes.push(child); return child;
  };
  const waitHTTP = async (url, timeout = 120000) => {
    const end = Date.now() + timeout;
    while (Date.now() < end) { try { const r = await fetch(url); if (r.ok) return; } catch {} await sleep(500); }
    throw new Error('Local service readiness deadline exceeded');
  };
  try {
    mark('isolate fresh runner model state');
    assert.ok(env.HOME && env.HOME === resolve(env.HOME), 'Runner HOME must be an absolute path');
    // Preserve HOME. Ollama 0.40.2 keeps its key here even with OLLAMA_MODELS set.
    // Exclusive creation refuses any existing key/config; failed mkdir grants no cleanup ownership.
    const modelState = join(env.HOME, '.ollama');
    await mkdir(modelState, { mode: 0o700 });
    ownedModelState = modelState;
    mark('verify anonymous npm bytes');
    const metadata = await (await fetch(`https://registry.npmjs.org/${PIN.package}/${PIN.version}`)).json();
    assert.equal(metadata.name, PIN.package); assert.equal(metadata.version, PIN.version);
    assert.ok(metadata.dist.tarball.startsWith('https://registry.npmjs.org/'));
    const archive = Buffer.from(await (await fetch(metadata.dist.tarball)).arrayBuffer());
    assert.equal(sha(archive), PIN.archiveSha256);
    receipt.package = { name: PIN.package, version: PIN.version, sha256: sha(archive), npm_tarball: metadata.dist.tarball };
    // This download checks identity; actual installation below is performed in the UI.
    await writeFile(join(privateDir, 'published.tgz'), archive, { mode: 0o600 });
    mark('start loopback services');
    for (const port of [5687, 5688, 11435]) {
      const occupied = await new Promise((done, reject) => {
        const socket = createConnection({ host: '127.0.0.1', port });
        socket.once('connect', () => { socket.destroy(); done(true); });
        socket.once('error', error => error.code === 'ECONNREFUSED' ? done(false) : reject(error));
      });
      assert.equal(occupied, false, 'Refuse to use an existing local service');
    }
    start('ollama', ollamaBin, ['serve']);
    start('n8n', process.execPath, [n8nBin, 'start']);
    await Promise.all([waitHTTP(`${OLLAMA}/api/version`), waitHTTP(`${BASE}/healthz/readiness`)]);
    assert.equal((await (await fetch(`${OLLAMA}/api/version`)).json()).version, PIN.ollama);
    mark('pull and prewarm real local model');
    const pull = await fetch(`${OLLAMA}/api/pull`, { method: 'POST', body: JSON.stringify({ model: PIN.model, stream: false }), signal: AbortSignal.timeout(600000) });
    assert.ok(pull.ok); assert.equal((await pull.json()).status, 'success');
    const models = await (await fetch(`${OLLAMA}/api/tags`)).json();
    const model = models.models.find(item => item.name === PIN.model);
    assert.equal(model?.digest.replace(/^sha256:/, ''), PIN.modelDigest);
    receipt.model = { name: model.name, digest: model.digest, size: model.size, details: model.details, ollama_version: PIN.ollama, cpu_only: true };
    const warm = await fetch(`${OLLAMA}/api/chat`, { method: 'POST', body: JSON.stringify({ model: PIN.model, stream: false, think: false, messages: [{ role: 'user', content: 'Reply with Ready.' }], options: { num_ctx: 8192, num_predict: 12, num_thread: 2, num_gpu: 0, temperature: 0 } }), signal: AbortSignal.timeout(240000) });
    assert.ok(warm.ok); assert.ok((await warm.json()).done);
    receipt.model_is_real = true;
    assert.ok(processes.every(child => child.exitCode === null && child.signalCode === null), 'A local service exited before recording');
    await waitHTTP(`${BASE}/rest/settings`, 15000);
    mark('prepare ephemeral local owner and model connection off camera');
    browser = await chromium.launch({ headless: true });
    const setup = await browser.newContext({ baseURL: BASE });
    const password = `Demo-${randomBytes(24).toString('base64url')}9aA`;
    secrets.push(password);
    const owner = await setup.request.post('/rest/owner/setup', { data: { email: 'review-demo@example.invalid', firstName: 'Review', lastName: 'Demo', password } });
    assert.ok(owner.ok(), `Owner setup HTTP ${owner.status()}`);
    const credential = await setup.request.post('/rest/credentials', { data: { name: 'Local Ollama - no API key', type: 'ollamaApi', data: { baseUrl: OLLAMA } } });
    assert.ok(credential.ok(), `Local model connection HTTP ${credential.status()}`);
    const credentialId = (await credential.json()).data.id;
    const agentDefinition = agentWorkflow(credentialId);
    receipt.agent_workflow = {
      name: agentDefinition.name, active: false, settings: agentDefinition.settings,
      nodes: agentDefinition.nodes.map(({ credentials, ...node }) => node),
      connections: agentDefinition.connections,
      local_model_connection: { base_url: OLLAMA, api_key_required: false, credential_reference_omitted: true },
    };
    const created = await setup.request.post('/rest/workflows', { data: agentDefinition });
    assert.ok(created.ok(), `Prepare agent workflow HTTP ${created.status()}`);
    const agentId = (await created.json()).data.id;
    const state = await setup.storageState(); // In memory only, never uploaded.
    secrets.push(...state.cookies.map(cookie => cookie.value));
    await setup.close();

    mark('start continuous UI recording');
    context = await browser.newContext({ baseURL: BASE, storageState: state, viewport: { width: 1440, height: 1000 }, recordVideo: { dir: join(privateDir, 'raw-video'), size: { width: 1440, height: 1000 } } });
    page = await context.newPage(); video = page.video(); recordingStarted = Date.now();
    page.setDefaultTimeout(20000);
    await page.goto('/settings/community-nodes');
    assert.equal(await page.locator('input[type=password]').count(), 0, 'Never record credential entry');
    receipt.browser_ui_observed = true;
    await page.getByRole('button', { name: /Install/i }).first().click();
    await page.getByTestId('communityPackageInstall-modal').locator('input').first().fill(`${PIN.package}@${PIN.version}`);
    await sleep(1800);
    await page.getByTestId('user-agreement-checkbox').click();
    const installedResponse = page.waitForResponse(r => r.url().includes('/rest/community-packages') && r.request().method() === 'POST', { timeout: 90000 });
    await page.getByTestId('install-community-package-button').click();
    assert.ok((await installedResponse).ok(), 'UI package installation failed');
    await page.getByTestId('communityPackageInstall-modal').waitFor({ state: 'hidden', timeout: 90000 });
    const card = page.getByTestId('community-package-card').filter({ hasText: PIN.package });
    await card.waitFor(); assert.match(await card.innerText(), /0\.1\.0/);
    receipt.ui_installed_package = true;
    await sleep(3000);

    mark('create workflow and insert published node in UI');
    await page.goto('/workflow/new');
    await page.getByTestId('canvas-plus-button').click();
    await page.getByTestId('node-creator-search-bar').fill('Manual Trigger');
    await page.getByTestId('node-creator-item-name').getByText('Manual Trigger', { exact: true }).click();
    if (await page.getByTestId('ndv-close-button').isVisible()) await page.getByTestId('ndv-close-button').click();
    await page.locator('[data-test-id="canvas-node-output-handle"] [data-test-id="canvas-handle-plus"]').first().click();
    await page.getByTestId('node-creator-search-bar').fill('Financial Evidence');
    await page.getByTestId('node-creator-item-name').getByText('Financial Evidence', { exact: true }).click();
    // n8n 2.42.6 opens community-package details before it creates the node.
    await page.getByText('Add to workflow', { exact: true }).click();
    await page.getByTestId('node-parameters').waitFor({ state: 'visible' });
    await page.getByTestId('parameter-input-limit').locator('input').fill('1');
    await page.getByTestId('parameter-input-limit').locator('input').press('Tab');
    assert.equal(await page.getByTestId('node-credentials-select').count(), 0, 'Research node requires no credential');
    receipt.ui_created_new_workflow = true;
    const executeUI = async (dataset, agent = false) => {
      const response = page.waitForResponse(r => /\/rest\/workflows\/[^/]+\/run(?:\?|$)/.test(r.url()) && r.request().method() === 'POST');
      await page.getByTestId(agent ? 'execute-workflow-button' : 'node-execute-button').click();
      const started = await response; assert.ok(started.ok());
      const id = (await started.json()).data.executionId;
      assert.ok(id);
      const end = Date.now() + (agent ? 155000 : 40000);
      while (Date.now() < end) {
        const result = await context.request.get(`/rest/executions/${id}`);
        if (result.ok()) {
          const execution = (await result.json()).data;
          if (execution && ['success', 'error', 'crashed', 'canceled'].includes(execution.status)) {
            if (typeof execution.data === 'string') execution.data = unflatten(execution.data);
            await writeFile(join(privateDir, `execution-${id}.json`), JSON.stringify(execution), { mode: 0o600 });
            return executionProjection(execution, dataset, { agent });
          }
        }
        await sleep(600);
      }
      throw new Error('Execution deadline exceeded');
    };
    for (const [dataset, label] of [['money_markets', 'Money Markets'], ['bank_risk', 'Bank Risk'], ['market_liquidity', 'Market Liquidity']]) {
      mark(`UI action ${dataset}`);
      if (dataset !== 'money_markets') {
        await page.getByTestId('parameter-input-dataset').click();
        await page.getByRole('option', { name: label, exact: true }).filter({ visible: true }).click();
      }
      await sleep(1200);
      receipt.actions[dataset] = await executeUI(dataset);
      await page.getByTestId('output-panel').getByTestId('radio-button-json').click();
      await sleep(2000);
      for (const key of ['as_of', 'availability', 'value', 'sources', 'diagnostics']) {
        const property = page.getByTestId('output-panel').locator('.json-data span').filter({ hasText: new RegExp(`^"${key}"$`) }).first();
        if (await property.count()) { await property.scrollIntoViewIfNeeded(); await sleep(1400); }
      }
    }
    await page.getByTestId('ndv-close-button').click();
    await sleep(1000);
    mark('run real AI Agent with published node as a tool');
    await page.goto(`/workflow/${agentId}`);
    await page.getByTestId('canvas-node').filter({ hasText: 'Research Agent' }).waitFor();
    await sleep(4500);
    receipt.agent = await executeUI('money_markets', true);
    await page.locator('[data-test-id="canvas-node"][data-node-name="Financial Evidence Tool"]').dblclick();
    await page.getByTestId('output-panel').getByTestId('radio-button-json').click();
    await sleep(4000);
    await page.getByTestId('ndv-close-button').click();
    await page.locator('[data-test-id="canvas-node"][data-node-name="Research Agent"]').dblclick();
    await sleep(5000);
    receipt.recording_wall_seconds = (Date.now() - recordingStarted) / 1000;
    assert.ok(receipt.recording_wall_seconds < 300, 'Uncut recording exceeded review limit');
    await context.close(); context = null;
    const videoPath = await video.path();
    mark('verify recording, runtime bytes and normalized package manifest');
    const installedPackage = join(privateDir, 'profile/.n8n/nodes/node_modules', PIN.package);
    assert.equal(JSON.parse(await readFile(join(installedPackage, 'package.json'))).version, PIN.version);
    const tarList = execFileSync('tar', ['tzf', join(privateDir, 'published.tgz')], { encoding: 'utf8' }).trim().split('\n');
    receipt.installed_package_files = [];
    for (const name of tarList) {
      assert.ok(name.startsWith('package/') && !name.includes('..'));
      if (name.endsWith('/')) continue;
      receipt.installed_package_files.push(installedFileProjection(name.slice(8),
        execFileSync('tar', ['xOzf', join(privateDir, 'published.tgz'), name]),
        await readFile(join(installedPackage, name.slice(8)))));
    }
    receipt.installed_files_match_published_archive = receipt.installed_package_files.every(file => file.byte_identical);
    receipt.installed_runtime_files_match_published_archive = receipt.installed_package_files.filter(file => file.path !== 'package.json').every(file => file.byte_identical);
    receipt.installed_manifest_matches_n8n_normalization = receipt.installed_package_files.some(file => file.path === 'package.json' && file.verified);
    const mp4 = join(privateDir, 'review-demo.mp4');
    // Whole-file format conversion only. No trim, splice, overlay, speed change or audio replacement.
    execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-i', videoPath, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart', mp4], { timeout: 120000 });
    const duration = path => Number(JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'json', path], { encoding: 'utf8' })).format.duration);
    const originalDuration = duration(videoPath), mp4Duration = duration(mp4);
    assert.ok(Math.abs(originalDuration - mp4Duration) < 0.15);
    receipt.video = { continuous: true, cuts: 0, duration_seconds: mp4Duration, original_duration_seconds: originalDuration, original_sha256: sha(await readFile(videoPath)), mp4_sha256: sha(await readFile(mp4)), transformation: 'whole recording WebM-to-MP4 format conversion only', audio: 'none; voiceover optional', viewport: [1440, 1000] };
    receipt.operator_controlled_demo_window = { started_at: new Date(recordingStarted).toISOString(), ended_at: new Date(recordingStarted + receipt.recording_wall_seconds * 1000).toISOString(), excluded_from_adoption: true };
    receipt.status = 'passed';
  } catch (error) {
    // No raw service log, request headers, cookies, DB, owner data or failed video uploaded.
    receipt.failure_stage = stage;
    receipt.failure_kind = error?.name ?? 'Error';
    receipt.failure_summary = redactDiagnostic(error?.message ?? 'Unknown failure', secrets);
    receipt.service_exit_codes = processes.map(child => ({ code: child.exitCode, signal: child.signalCode }));
    console.error(`Demo failed at ${stage} (${receipt.failure_kind}); raw details remain private.`);
    await writeFile(join(privateDir, 'failure.txt'), String(error?.stack ?? error), { mode: 0o600 });
    if (page && !page.isClosed()) {
      await page.screenshot({ path: join(privateDir, 'failure.png') }).catch(() => {});
      // DOM text contains only this isolated local UI; retained privately for diagnosis.
      await writeFile(join(privateDir, 'failure-dom.txt'), await page.locator('body').innerText().catch(() => ''), { mode: 0o600 });
    }
  } finally {
    if (context) await context.close().catch(() => {});
    if (browser) await browser.close().catch(() => {});
    const stopGroup = (child, signal) => { try { process.kill(-child.pid, signal); } catch (error) { if (error.code !== 'ESRCH') throw error; } };
    for (const child of processes) stopGroup(child, 'SIGTERM');
    await sleep(1000);
    for (const child of processes) stopGroup(child, 'SIGKILL');
    await sleep(500);
    const stoppedEndpoints = await Promise.all([BASE + '/healthz', 'http://127.0.0.1:5688/', OLLAMA + '/api/version'].map(async url => {
      try { await fetch(url, { signal: AbortSignal.timeout(1000) }); return false; } catch { return true; }
    }));
    receipt.services_stopped = processes.every(child => child.exitCode !== null || child.signalCode !== null) && stoppedEndpoints.every(Boolean);
    if (ownedModelState) await rm(ownedModelState, { recursive: true, force: true });
    for (const fd of logs) closeSync(fd);
    await mkdir(output, { mode: 0o700 });
    if (receipt.status === 'passed') {
      validatePublishable(receipt);
      await copyFile(join(privateDir, 'review-demo.mp4'), join(output, 'review-demo.mp4'));
      const original = (await readdir(join(privateDir, 'raw-video'))).filter(name => name.endsWith('.webm'));
      assert.equal(original.length, 1);
      await copyFile(join(privateDir, 'raw-video', original[0]), join(output, 'original-uncut.webm'));
    }
    await writeFile(join(output, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
    if (receipt.status !== 'passed') process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) await main();
