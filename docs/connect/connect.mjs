const $ = id => document.getElementById(id);
const clients = new Set(['mcp', 'api', 'python']);
const params = new URLSearchParams(globalThis.location?.search || '');
let client = clients.has(params.get('client')) ? params.get('client') : 'mcp';
let catalog, task, mcpConfig;

export function connectionText(kind, item, endpoint) {
  if (kind === 'api') return `curl --fail --show-error '${item.api_url}'`;
  if (kind === 'python') return `import json\nfrom urllib.request import urlopen\n\nurl = ${JSON.stringify(item.api_url)}\nwith urlopen(url, timeout=30) as response:\n    evidence = json.load(response)\nprint(json.dumps(evidence, indent=2))`;
  return endpoint;
}

export function mcpHandoffs(endpoint, config) {
  const entry = Object.entries(config?.mcpServers || {}).find(([, server]) => server.url === endpoint);
  if (!entry) throw new Error('No matching MCP configuration');
  const [name, server] = entry;
  const cursor = new URL('cursor://anysphere.cursor-deeplink/mcp/install');
  cursor.searchParams.set('name', name);
  cursor.searchParams.set('config', btoa(JSON.stringify({url: server.url})));
  const insomnia = new URL('https://app.insomnia.rest/run');
  insomnia.searchParams.set('mcp', server.url);
  return {cursor: cursor.href, insomnia: insomnia.href};
}

function render() {
  for (const button of document.querySelectorAll('[data-task]')) button.setAttribute('aria-pressed', String(button.dataset.task === task.id));
  for (const button of document.querySelectorAll('[data-client]')) button.setAttribute('aria-pressed', String(button.dataset.client === client));
  $('task-scope').textContent = task.scope;
  $('task-question').textContent = task.question;
  $('browser-start').href = task.browser_url;
  $('connection-code').value = connectionText(client, task, catalog.mcp_url);
  $('connection-code').rows = client === 'python' ? 9 : client === 'api' ? 4 : 3;
  $('code-label').textContent = {mcp: 'Remote MCP URL', api: 'Read-only API request', python: 'Python 3 / standard library'}[client];
  $('connection-instruction').textContent = {
    mcp: 'Add this URL as a remote Streamable HTTP MCP server in a compatible client. The server needs no credentials; your client may have its own account or plan requirements.',
    api: 'Run this request in your terminal. The JSON retains the original evidence, source URL and retrieval time. No API key is needed.',
    python: 'Run with Python 3. No extra packages or API key are needed. This prints the complete response so the source dates and unavailable values stay visible.'
  }[client];
  $('mcp-downloads').hidden = client !== 'mcp';
  $('mcp-handoff').hidden = true;
  if (client === 'mcp' && mcpConfig) {
    const links = mcpHandoffs(catalog.mcp_url, mcpConfig);
    $('open-cursor').href = links.cursor;
    $('open-insomnia').href = links.insomnia;
    $('mcp-handoff').hidden = false;
  }
  $('copy-status').textContent = '';
  $('copy-fallback').hidden = true;
  const next = new URL(location.href);
  next.searchParams.set('task', task.id); next.searchParams.set('client', client);
  history.replaceState(null, '', next);
}

async function copy(value, success) {
  try { await navigator.clipboard.writeText(value); $('copy-status').textContent = success; }
  catch { const fallback = $('copy-fallback'); fallback.value = value; fallback.hidden = false; fallback.focus(); fallback.select(); $('copy-status').textContent = 'Select and copy the text below.'; }
}

if (typeof document !== 'undefined') try {
  const response = await fetch('catalog.json', {cache: 'no-cache'});
  if (!response.ok) throw new Error('Catalog unavailable');
  catalog = await response.json();
  if (catalog.schema !== 'financial-evidence.start.v1' || !Array.isArray(catalog.tasks)) throw new Error('Catalog unavailable');
  try {
    const configResponse = await fetch('mcp.json', {cache: 'no-cache'});
    if (!configResponse.ok) throw new Error('Client configuration unavailable');
    const config = await configResponse.json();
    mcpHandoffs(catalog.mcp_url, config);
    mcpConfig = config;
  } catch { /* Copyable setup remains available if optional client links cannot load. */ }
  task = catalog.tasks.find(item => item.id === params.get('task')) || catalog.tasks[0];
  render();
  for (const button of document.querySelectorAll('[data-task]')) button.addEventListener('click', () => { task = catalog.tasks.find(item => item.id === button.dataset.task); render(); });
  for (const button of document.querySelectorAll('[data-client]')) button.addEventListener('click', () => { client = button.dataset.client; render(); });
  $('copy-connection').hidden = false; $('copy-prompt').hidden = false;
  $('copy-connection').addEventListener('click', () => copy($('connection-code').value, 'Connection copied. Paste it into your client.'));
  $('copy-prompt').addEventListener('click', () => copy(`${task.question} Keep sources, observation dates, units and missing values with the answer. ${task.scope}`, 'Research prompt copied.'));
} catch {
  $('copy-status').textContent = 'Interactive setup is unavailable. Copy the MCP URL above, or open the Research Desk and API guide.';
  for (const button of document.querySelectorAll('[data-task], [data-client]')) button.disabled = true;
}
