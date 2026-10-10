// Build saved Agentflow V2 definitions from the installed native node metadata.
// Numeric MCP arguments must remain JSON numbers: Tool does not coerce strings.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const [runtime, output] = process.argv.slice(2);
if (!runtime || !output) throw new Error('Usage: node build_workflows.cjs RUNTIME OUTPUT');
const modules = path.resolve(runtime, 'node_modules');
const components = path.join(modules, 'flowise-components');
const files = {
  start: 'dist/nodes/agentflow/Start/Start.js',
  tool: 'dist/nodes/agentflow/Tool/Tool.js',
  custom_mcp: 'dist/nodes/tools/MCP/CustomMCP/CustomMCP.js',
  mcp_transport: 'dist/nodes/tools/MCP/core.js',
};
const sha256 = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const versions = Object.fromEntries(['flowise', 'flowise-components', 'flowise-ui'].map(name => {
  const pkg = JSON.parse(fs.readFileSync(path.join(modules, name, 'package.json')));
  if (pkg.version !== '3.1.4') throw new Error(`Unexpected ${name} version ${pkg.version}`);
  return [name, pkg.version];
}));
function nativeNode(key, id, inputs, x) {
  const Native = require(path.join(components, files[key])).nodeClass;
  const metadata = JSON.parse(JSON.stringify(new Native()));
  const params = metadata.inputs || [];
  delete metadata.inputs;
  delete metadata.loadMethods;
  return {
    id, type: 'agentFlow', position: {x, y: 50},
    data: {...metadata, id,
      inputParams: params.map(p => ({...p, id: `${id}-input-${p.name}-${p.type}`, display: true})),
      inputAnchors: [], inputs,
      outputAnchors: [{id: `${id}-output-${metadata.name}`, label: metadata.label, name: metadata.name}],
      outputs: {}, selected: false},
    width: 190, height: 66, selected: false, dragging: false,
  };
}
fs.mkdirSync(output, {recursive: true, mode: 0o700});
for (const dataset of ['money_markets', 'bank_risk', 'market_liquidity']) {
  const start = nativeNode('start', 'startAgentflow_0', {
    startInputType: 'chatInput', startEphemeralMemory: true, startState: [], startPersistState: false,
  }, 100);
  const tool = nativeNode('tool', 'toolAgentflow_0', {
    toolAgentflowSelectedTool: 'customMCP',
    toolAgentflowSelectedToolConfig: {
      mcpServerConfig: JSON.stringify({url: 'https://api.seiche.info/openbb/mcp', headers: {
        'X-Liquilens-Traffic-Class': 'synthetic',
        'User-Agent': 'Financial-Evidence-Flowise-Native-Acceptance/1.0',
      }}),
      mcpActions: ['financial_evidence_query'], toolAgentflowSelectedTool: 'customMCP',
    },
    toolInputArgs: [
      {inputArgName: 'dataset', inputArgValue: dataset},
      {inputArgName: 'limit', inputArgValue: 1},
      {inputArgName: 'offset', inputArgValue: 0},
    ], toolUpdateState: [],
  }, 420);
  const flow = {nodes: [start, tool], edges: [{
    source: start.id, sourceHandle: `${start.id}-output-startAgentflow`,
    target: tool.id, targetHandle: tool.id,
    data: {sourceColor: '#7EE787', targetColor: '#d4a373', isHumanInput: false},
    type: 'agentFlow', id: `${start.id}-to-${tool.id}`,
  }], viewport: {x: 0, y: 0, zoom: 1}};
  fs.writeFileSync(path.join(output, `${dataset}.json`), JSON.stringify(flow, null, 2) + '\n');
  if (dataset === 'money_markets') {
    const candidate = structuredClone(flow);
    candidate.nodes[1].data.label = 'Financial evidence page';
    candidate.nodes[1].data.inputs.toolAgentflowSelectedToolConfig.mcpServerConfig = JSON.stringify({url: 'https://api.seiche.info/openbb/mcp'});
    Object.assign(candidate, JSON.parse(fs.readFileSync(path.join(__dirname, 'marketplace_metadata.json'))));
    fs.writeFileSync(path.join(output, 'marketplace-candidate.json'), JSON.stringify(candidate, null, 2) + '\n');
  }
}
const lockfile = path.join(runtime, 'package-lock.json');
const lock = JSON.parse(fs.readFileSync(lockfile));
const identity = {
  node: process.version, packages: versions,
  package_integrities: Object.fromEntries(Object.keys(versions).map(name => [name, lock.packages[`node_modules/${name}`].integrity])),
  package_lock_sha256: sha256(lockfile),
  component_sha256: Object.fromEntries(Object.entries(files).map(([key, file]) => [key, sha256(path.join(components, file))])),
};
fs.writeFileSync(path.join(output, 'runtime-identity.json'), JSON.stringify(identity, null, 2) + '\n');
