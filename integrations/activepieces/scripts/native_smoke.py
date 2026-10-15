"""Install and execute a candidate archive or approved npm release in an isolated host.

Requires Docker. Creates only a disposable local host, account and draft flows.
Uses the same installation and step-test APIs as the editor; it does not certify
browser interactions or marketplace acceptance. A disposable engine preload
attests reviewed package files and the CommonJS sources compiled during each test.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import subprocess
import tarfile
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

IMAGE = 'activepieces/activepieces@sha256:4b719ac8cb9a235beb59f9beae322c9447ee532264ff08af9094926240b721e8'
RELEASE = '0.92.3'
ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT.parents[1] / 'docs/platforms/activepieces-publication-20261015.json'
ACTIONS = {'list_research_datasets', 'get_evidence_page'}
LOADER_REFERENCE = {
    'release': RELEASE, 'source_commit': '2fc7f8dcaa84400f9db53fb0de7fc4340d055c62',
    'path': 'packages/server/engine/src/lib/helper/piece-loader.ts',
    'sha256': 'be7b524038d9864e58bfe72b8d1feadc143c8b693bd30d9c03ddc0d82c793a8d',
    'source_to_image_build_provenance_verified': False,
}
PROBE_MOUNT = '/opt/financial-evidence-attestation'
EVENTS_MOUNT = '/opt/financial-evidence-attestation-events'
ATTESTATION_LIMIT = 1024 * 1024

# 0.92.3 bundles piece-loader into the cached engine main.js. Observe its actual
# createRequire(__filename)(piecePath), rather than guessing an install folder.
# Only a named disposable test phase is recorded; no arguments/results/env dump.
WORKER_PRELOAD = r"""'use strict';
const fs = require('node:fs'), path = require('node:path');
const crypto = require('node:crypto'), Module = require('node:module');
const base = process.env.FE_QUALIFICATION_DIR;
if (base && process.env.SANDBOX_ID) {
  const config = JSON.parse(fs.readFileSync(path.join(base, 'config.json'), 'utf8'));
  const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
  const real = value => fs.realpathSync(value);
  const engine = real(process.argv[1]);
  const alias = config.package + '-' + config.version;
  // Match the official helper exactly, including its prerelease alias semantics.
  const trimmed = alias.split('-').slice(0, -1).join('-');
  const originalLoad = Module._load, originalCompile = Module.prototype._compile;
  let active;
  function append(record) {
    const encoded = JSON.stringify(record) + '\n';
    const prior = fs.existsSync(config.events_file) ? fs.statSync(config.events_file).size : 0;
    if (prior + Buffer.byteLength(encoded) > 1048576) throw new Error('Attestation output limit');
    fs.appendFileSync(config.events_file, encoded);
  }
  function mainEntry(directory) {
    let main;
    try { main = JSON.parse(fs.readFileSync(path.join(directory, 'package.json'), 'utf8')).main; }
    catch { /* The official loader falls back when package metadata cannot resolve main. */ }
    if (typeof main === 'string' && fs.existsSync(path.join(directory, main))) return path.join(directory, main);
    return path.join(directory, 'src/index.js');
  }
  function installedEntry(folder) {
    const nested = path.join(folder, 'node_modules', trimmed);
    if (fs.existsSync(nested)) return {entry: mainEntry(nested), root: nested, layout: 'nested_node_modules'};
    if (fs.existsSync(path.join(folder, 'package.json'))) {
      const entry = mainEntry(folder);
      if (fs.existsSync(entry)) return {entry, root: folder, layout: 'archive_root'};
    }
  }
  function loaderEntry() {
    for (const custom of (process.env.AP_CUSTOM_PIECES_PATHS || '').split(':').filter(Boolean)) {
      const found = installedEntry(path.resolve(custom, 'pieces', alias));
      if (found) return found;
    }
    let current = path.dirname(engine);
    for (;;) {
      const found = installedEntry(path.resolve(current, 'pieces', alias));
      if (found) return found;
      const parent = path.dirname(current);
      if (parent === current) break;
      current = parent;
    }
  }
  function ownRelative(filename, root) {
    const relative = path.relative(root, real(filename));
    if (relative.startsWith('..') || path.isAbsolute(relative) || relative.split(path.sep).includes('node_modules')) return null;
    return relative.split(path.sep).join('/');
  }
  function inspectFiles(root, files) {
    for (const [name, wanted] of Object.entries(config.files)) {
      const filename = path.join(root, name);
      if (ownRelative(filename, root) !== name) throw new Error('Attestation package file escaped root');
      const stat = fs.statSync(filename);
      if (!stat.isFile() || stat.size > 1048576) throw new Error('Attestation package file bound');
      const bytes = fs.readFileSync(filename);
      files[name] = {bytes: bytes.length, sha256: hash(bytes)};
      if (files[name].bytes !== wanted.bytes || files[name].sha256 !== wanted.sha256) {
        throw new Error('Attestation package bytes mismatch: ' + name);
      }
    }
    return files;
  }
  Module.prototype._compile = function(content, filename) {
    if (active) {
      const name = ownRelative(filename, active.package_root);
      if (name !== null) {
        const sha256 = hash(Buffer.from(content, 'utf8'));
        active.compiled_files[name] = {sha256, bytes: Buffer.byteLength(content)};
        const wanted = config.files[name];
        if (!wanted || sha256 !== wanted.sha256 || Buffer.byteLength(content) !== wanted.bytes) {
          throw new Error('Attestation compiled source mismatch: ' + name);
        }
      }
    }
    return originalCompile.call(this, content, filename);
  };
  Module._load = function(request, parent, isMain) {
    if (!path.isAbsolute(request) || !request.includes(alias) || !parent?.filename || real(parent.filename) !== engine) {
      return originalLoad.apply(this, arguments);
    }
    const phaseFile = path.join(base, 'phase.json');
    const phase = fs.existsSync(phaseFile) ? JSON.parse(fs.readFileSync(phaseFile, 'utf8')) : null;
    if (!phase || !config.actions.includes(phase.action) || !/^[a-f0-9]{32}$/.test(phase.nonce)) {
      return originalLoad.apply(this, arguments);
    }
    const record = {schema: 'financial-evidence.activepieces-worker-load.v1',
      action: phase.action, phase_nonce: phase.nonce, pid: process.pid, ppid: process.ppid,
      sandbox_id_sha256: hash(process.env.SANDBOX_ID), engine_entry: engine,
      engine_entry_sha256: hash(fs.readFileSync(engine)), loader_parent: real(parent.filename),
      loader_request: request, package: config.package, version: config.version,
      compiled_files: {}, successful_load: false};
    try {
      const found = loaderEntry();
      if (!found || path.resolve(request) !== path.resolve(found.entry)) throw new Error('Attestation loader resolution differs');
      const resolved = Module._resolveFilename(request, parent, isMain);
      record.resolved_entry = real(resolved);
      record.package_root = real(found.root);
      record.layout = found.layout;
      record.entry_relative = ownRelative(record.resolved_entry, record.package_root);
      record.cached_before = Boolean(Module._cache[resolved]);
      record.files = {};
      inspectFiles(record.package_root, record.files);
      active = record;
      const result = originalLoad.apply(this, arguments);
      active = undefined;
      // Recheck after evaluation, so a source modified during loading cannot pass.
      record.files_after_load = {};
      inspectFiles(record.package_root, record.files_after_load);
      record.successful_load = true;
      return result;
    } catch (error) {
      record.error = String(error.message).slice(0, 300);
      throw error;
    } finally {
      active = undefined;
      append(record);
    }
  };
}
"""


def reviewed_files(archive, package):
    """Hash only bounded regular package members; never extract archive paths."""
    files, total = {}, 0
    with tarfile.open(archive) as handle:
        for member in handle:
            if member.isdir():
                continue
            name = member.name.removeprefix('package/')
            path = PurePosixPath(name)
            if (not member.name.startswith('package/') or not member.isfile() or name in files
                    or path.is_absolute() or '..' in path.parts or '\\' in name
                    or str(path) != name or member.size > 1024 * 1024 or len(files) >= 128):
                raise RuntimeError('Invalid or unbounded package member for worker attestation')
            total += member.size
            if total > 10 * 1024 * 1024:
                raise RuntimeError('Package attestation exceeds byte bound')
            raw = handle.extractfile(member).read()
            files[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if 'package.json' not in files:
            raise RuntimeError('Worker attestation requires package manifest')
    shipped_identity(archive, package)
    return files


def prepare_attestation(evidence, archive, package):
    files = reviewed_files(archive, package)
    probe = evidence / 'worker-probe'
    events = evidence / 'worker-events'
    probe.mkdir()
    events.mkdir(mode=0o777)
    events.chmod(0o777)  # The disposable container may use a different UID.
    (probe / 'preload.cjs').write_text(WORKER_PRELOAD)
    (probe / 'config.json').write_text(json.dumps({
        'package': package['name'], 'version': package['version'], 'files': files,
        'actions': sorted(ACTIONS), 'events_file': EVENTS_MOUNT + '/events.ndjson',
    }))
    return probe, events, files


def read_attestations(events):
    trace = events / 'events.ndjson'
    if not trace.exists():
        return []
    if trace.stat().st_size > ATTESTATION_LIMIT:
        raise RuntimeError('Worker attestation response exceeds byte bound')
    observations = [json.loads(line) for line in trace.read_text().splitlines() if line]
    if len(observations) > 32 or any(not isinstance(item, dict) for item in observations):
        raise RuntimeError('Invalid worker attestation records')
    return observations


def verify_worker_phase(observations, phase, files, package):
    matches = [item for item in observations if item.get('phase_nonce') == phase['nonce']]
    if not matches:
        raise RuntimeError('No actual engine piece-loader observation for native action')
    fresh = []
    for item in matches:
        if (item.get('schema') != 'financial-evidence.activepieces-worker-load.v1'
                or item.get('action') != phase['action'] or item.get('package') != package['name']
                or item.get('version') != package['version'] or item.get('successful_load') is not True
                or item.get('loader_parent') != item.get('engine_entry')
                or item.get('files') != files or item.get('files_after_load') != files
                or item.get('layout') not in ('nested_node_modules', 'archive_root')
                or item.get('entry_relative') not in files):
            raise RuntimeError('Worker loaded package does not match reviewed archive')
        compiled = item.get('compiled_files')
        if not isinstance(compiled, dict) or any(files.get(name) != digest for name, digest in compiled.items()):
            raise RuntimeError('Worker compiled sources do not match reviewed archive')
        if item.get('cached_before') is False and item['entry_relative'] in compiled:
            fresh.append(item)
    if not fresh:
        raise RuntimeError('Native action lacks a fresh matching CommonJS compilation')
    return {'phase_nonce': phase['nonce'], 'observations': len(matches),
            'fresh_compilations': len(fresh), 'compiled_files_verified': sorted({name for item in fresh for name in item['compiled_files']})}


def command(*args, timeout=120, env=None):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stderr[-1500:]}')
    return result.stdout.strip()


def multipart(fields, archive=None):
    boundary = 'financial-evidence-' + secrets.token_hex(12)
    chunks = []
    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    if archive is not None:
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="pieceArchive"; filename="piece.tgz"\r\nContent-Type: application/gzip\r\n\r\n'.encode())
        chunks += [archive.read_bytes(), b'\r\n']
    chunks.append(f'--{boundary}--\r\n'.encode())
    return b''.join(chunks), f'multipart/form-data; boundary={boundary}'


def registry_url(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != 'registry.npmjs.org' or parsed.fragment:
        raise RuntimeError('Expected an HTTPS public npm registry URL')
    return url


def public_read(url, limit):
    # Explicit anonymous requests: no npm config, publisher credentials or tokens.
    request = Request(registry_url(url), headers={'User-Agent': 'financial-evidence-native-qualification/1.0'})
    with urlopen(request, timeout=60) as response:
        registry_url(response.geturl())
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise RuntimeError('Registry response exceeds evidence bound')
    return raw


def shipped_identity(archive, package):
    with tarfile.open(archive) as handle:
        member = handle.getmember('package/package.json')
        if not member.isfile() or member.size > 1024 * 1024:
            raise RuntimeError('Invalid packed package manifest')
        shipped = json.load(handle.extractfile(member))
    if (shipped['name'], shipped['version']) != (package['name'], package['version']):
        raise RuntimeError('Packed package identity mismatch')


def published_archive(evidence, publication_path=PUBLICATION):
    publication_raw = publication_path.read_bytes()
    publication = json.loads(publication_raw)
    native_name = publication['native_receipt']
    if Path(native_name).name != native_name:
        raise RuntimeError('Native qualification receipt must be adjacent to publication receipt')
    native_raw = (publication_path.parent / native_name).read_bytes()
    native = json.loads(native_raw)
    if (publication.get('schema') != 'financial-evidence.activepieces-publication.v1'
            or publication.get('status') != 'published_bytes_verified'
            or publication.get('anonymous_registry_readback') is not True
            or native.get('status') != 'passed'
            or native.get('installation') != 'archive_via_native_install_api'
            or native.get('source_commit') != publication.get('native_source_commit')
            or any(publication.get(k) != native.get(k) for k in ('package', 'version', 'sha256', 'bytes'))
            or {run['action'] for run in native.get('runs', []) if run.get('status') == 'SUCCEEDED'} != ACTIONS):
        raise RuntimeError('Publication is not bound to a passed native archive qualification')
    package = {'name': publication['package'], 'version': publication['version']}
    metadata_url = 'https://registry.npmjs.org/' + quote(package['name'], safe='@') + '/' + quote(package['version'], safe='')
    metadata_raw = public_read(metadata_url, 1024 * 1024)
    (evidence / 'registry-version-metadata.json').write_bytes(metadata_raw)
    metadata = json.loads(metadata_raw)
    if (metadata.get('name'), metadata.get('version')) != (package['name'], package['version']):
        raise RuntimeError('Registry metadata identity mismatch')
    dist = metadata['dist']
    if dist.get('tarball') != publication['tarball_url'] or dist.get('integrity') != publication['integrity']:
        raise RuntimeError('Registry distribution metadata differs from approved publication')
    raw = public_read(dist['tarball'], 10 * 1024 * 1024)
    if len(raw) != publication['bytes'] or hashlib.sha256(raw).hexdigest() != publication['sha256']:
        raise RuntimeError('Registry tarball bytes differ from native-qualified publication')
    integrity = 'sha512-' + base64.b64encode(hashlib.sha512(raw).digest()).decode('ascii')
    if integrity != publication['integrity']:
        raise RuntimeError('Registry tarball SHA-512 integrity mismatch')
    filename = native['filename']
    if Path(filename).name != filename or not filename.endswith('.tgz'):
        raise RuntimeError('Invalid native-qualified archive filename')
    archive = evidence / filename
    archive.write_bytes(raw)
    shipped_identity(archive, package)
    return package, archive, {
        'metadata_url': metadata_url, 'metadata_sha256': hashlib.sha256(metadata_raw).hexdigest(),
        'tarball_url': dist['tarball'], 'integrity': integrity,
        'publication_receipt': publication_path.name,
        'publication_receipt_sha256': hashlib.sha256(publication_raw).hexdigest(),
        'native_archive_receipt': native_name,
        'native_archive_receipt_sha256': hashlib.sha256(native_raw).hexdigest(),
        'native_archive_source_commit': native['source_commit'],
        'anonymous_readback': True, 'public_artifact_bytes_verified': True,
        'worker_artifact_bytes_verified': False,
        'registry_signature_verification': 'not_repeated_by_this_run',
    }


def install_piece(api, package, installation, archive, project):
    body, mime = multipart({
        'packageType': installation.upper(), 'scope': 'PLATFORM',
        'pieceName': package['name'], 'pieceVersion': package['version'],
    }, archive if installation == 'archive' else None)
    api('POST', 'pieces', body, mime)
    metadata = api('GET', 'pieces/' + package['name'] + '?' + urlencode({
        'version': package['version'], 'projectId': project,
    }))
    if metadata['name'] != package['name'] or metadata['version'] != package['version']:
        raise RuntimeError('Installed metadata identity mismatch')
    if metadata.get('packageType') != installation.upper():
        raise RuntimeError('Installed metadata package type mismatch')
    if set(metadata['actions']) != ACTIONS:
        raise RuntimeError('Installed actions mismatch')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--installation', choices=('archive', 'registry'), default='archive')
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    candidate = json.loads((ROOT / 'package.json').read_text())
    source_commit = command('git', 'rev-parse', 'HEAD')
    receipt = {
        'schema': 'financial-evidence.activepieces-native.v1',
        'started_at': datetime.now(timezone.utc).isoformat(),
        'status': 'running', 'image': IMAGE, 'release': RELEASE,
        'source_commit': source_commit,
        'source_commit_role': 'qualification_harness_and_candidate_checkout',
        'candidate': {'package': candidate['name'], 'version': candidate['version']},
        'installation_mode': args.installation,
        'installation': args.installation + '_via_native_install_api',
        'artifact_source': 'candidate_checkout' if args.installation == 'archive' else 'approved_publication_receipt',
        'execution': 'native_worker_via_editor_step_test_api',
        'browser_interaction': 'not_tested', 'npm_published': False,
        'npm_publication_verification': 'not_checked_for_candidate_archive' if args.installation == 'archive' else 'pending',
        'worker_artifact_bytes_verified': False,
        'upstream_submission': 'paused_by_upstream_policy',
        'independent_adoption_verified': False, 'runs': [],
    }
    container = 'financial-evidence-qualification-' + secrets.token_hex(6)
    token = None
    password = secrets.token_urlsafe(30)
    host_secrets = {'AP_JWT_SECRET': secrets.token_hex(32), 'AP_ENCRYPTION_KEY': secrets.token_hex(16)}
    started = False
    probe = events = None
    files = {}

    def redact(value):
        for sensitive in (token, password, *host_secrets.values()):
            if sensitive:
                value = value.replace(sensitive, '[redacted]')
        return re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[redacted-jwt]', value)

    def api(method, path, body=None, content_type='application/json'):
        headers = {'Accept': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if body is not None:
            headers['Content-Type'] = content_type
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
        else:
            data = None
        request = Request(base + '/api/v1/' + path, method=method, headers=headers, data=data)
        try:
            with urlopen(request, timeout=180) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise RuntimeError('Native response exceeds evidence bound')
                return json.loads(raw)
        except HTTPError as error:
            detail = error.read(2000).decode(errors='replace')
            raise RuntimeError(f'{method} {path}: HTTP {error.code}: {redact(detail)}') from None

    try:
        if args.installation == 'registry':
            package, archive, verification = published_archive(evidence)
            receipt['registry_verification'] = verification
            receipt['npm_published'] = True
            receipt['npm_publication_verification'] = 'approved_public_bytes_verified'
        else:
            package = candidate
            packed = json.loads(command('npm', 'pack', '--json', '--pack-destination', str(evidence)))[0]
            archive = evidence / packed['filename']
            shipped_identity(archive, package)
        receipt.update({
            'package': package['name'], 'version': package['version'],
            'filename': archive.name, 'bytes': archive.stat().st_size,
            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        })
        probe, events, files = prepare_attestation(evidence, archive, package)
        command('docker', 'pull', IMAGE, timeout=600)
        command('docker', 'run', '-d', '--name', container, '--memory', '3g', '--cpus', '2',
                '-p', '127.0.0.1::80', '-e', 'AP_DB_TYPE=PGLITE',
                '-e', 'AP_REDIS_TYPE=MEMORY', '-e', 'AP_FRONTEND_URL=http://localhost',
                '-e', 'AP_TELEMETRY_ENABLED=false', '-e', 'AP_EXECUTION_MODE=UNSANDBOXED',
                '-e', 'AP_REUSE_SANDBOX=false', '-e', 'AP_WORKER_CONCURRENCY=1',
                '-e', 'AP_PREWARM_CACHE_ON_STARTUP=false',
                '-e', 'AP_SANDBOX_PROPAGATED_ENV_VARS=NODE_OPTIONS,FE_QUALIFICATION_DIR',
                '-e', 'NODE_OPTIONS=--require=' + PROBE_MOUNT + '/preload.cjs',
                '-e', 'FE_QUALIFICATION_DIR=' + PROBE_MOUNT,
                '--mount', f'type=bind,src={probe},dst={PROBE_MOUNT},readonly',
                '--mount', f'type=bind,src={events},dst={EVENTS_MOUNT}',
                '-e', 'AP_LOG_LEVEL=warn', '-e', 'AP_JWT_SECRET', '-e', 'AP_ENCRYPTION_KEY',
                IMAGE, env={**os.environ, **host_secrets})
        started = True
        base = 'http://' + command('docker', 'port', container, '80/tcp')
        deadline = time.monotonic() + 240
        while True:
            try:
                flags = api('GET', 'flags')
                break
            except (OSError, RuntimeError):
                state = json.loads(command('docker', 'inspect', '--format', '{{json .State}}', container))
                if not state['Running']:
                    raise RuntimeError(f"Isolated host exited: code={state['ExitCode']}, oom={state['OOMKilled']}") from None
                if time.monotonic() >= deadline:
                    raise RuntimeError('Isolated Activepieces host did not become ready')
                time.sleep(3)
        receipt['flags_sha256'] = hashlib.sha256(json.dumps(flags, sort_keys=True).encode()).hexdigest()
        session = api('POST', 'authentication/sign-up', {
            'email': 'qualification@financial-evidence.invalid', 'password': password,
            'firstName': 'Financial', 'lastName': 'Evidence',
            'trackEvents': False, 'newsLetter': False,
        })
        token = session['token']
        project = session['projectId']
        metadata = install_piece(api, package, args.installation, archive, project)
        receipt['metadata'] = {k: metadata.get(k) for k in ('name', 'version', 'displayName', 'minimumSupportedRelease', 'packageType', 'pieceType')}
        for action_name, inputs in [
            ('list_research_datasets', {}),
            ('get_evidence_page', {'dataset': 'money_markets', 'limit': 1, 'offset': 0}),
        ]:
            flow = api('POST', 'flows', {'displayName': 'Qualification: ' + action_name, 'projectId': project})
            flow = api('POST', 'flows/' + flow['id'], {'type': 'ADD_ACTION', 'request': {
                'parentStep': flow['version']['trigger']['name'], 'stepLocationRelativeToParent': 'AFTER',
                'action': {'name': 'step_1', 'displayName': action_name, 'type': 'PIECE', 'valid': True,
                           'settings': {'pieceName': package['name'], 'pieceVersion': package['version'],
                                        'actionName': action_name, 'input': inputs, 'propertySettings': {},
                                        'errorHandlingOptions': {}}},
            }})
            phase = {'action': action_name, 'nonce': secrets.token_hex(16)}
            (probe / 'phase.new').write_text(json.dumps(phase))
            (probe / 'phase.new').replace(probe / 'phase.json')
            run = api('POST', 'sample-data/test-step', {
                'projectId': project, 'flowVersionId': flow['version']['id'], 'stepName': 'step_1',
            })
            deadline = time.monotonic() + 180
            while run['status'] in ('QUEUED', 'RUNNING') and time.monotonic() < deadline:
                time.sleep(2)
                run = api('GET', 'flow-runs/' + run['id'])
            if run['status'] != 'SUCCEEDED':
                raise RuntimeError(f"Native {action_name} returned {run['status']}: {json.dumps(run.get('steps', {}))[:1400]}")
            output = run['steps']['step_1']['output']
            if action_name == 'list_research_datasets':
                if not isinstance(output, list) or not any(r.get('id') == 'money_markets' for r in output):
                    raise RuntimeError('Native catalog output has the wrong shape')
                detail = {'dataset_ids': [r['id'] for r in output]}
            else:
                if (output.get('schema') != 'liquidity-lab.openbb-table.v1' or output.get('dataset') != 'money_markets'
                        or len(output['results']) != 1 or not output['sources'] or not isinstance(output['diagnostics'], list)):
                    raise RuntimeError('Native evidence output lost its contract')
                detail = {'rows': len(output['results']), 'source_count': len(output['sources']),
                          'observations': [{k: r.get(k) for k in ('as_of', 'unit', 'availability', 'source_status', 'rights_status')} for r in output['results']],
                          'diagnostics_preserved': True}
            receipt['runs'].append({'action': action_name, 'status': run['status'],
                                    'worker_attestation': verify_worker_phase(read_attestations(events), phase, files, package),
                                    'output_sha256': hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest(), **detail})
            (probe / 'phase.json').unlink()
        receipt['worker_artifact_bytes_verified'] = True
        if args.installation == 'registry':
            receipt['registry_verification']['worker_artifact_bytes_verified'] = True
        receipt['status'] = 'passed'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['error'] = redact(str(error))
        if started:
            logs = subprocess.run(['docker', 'logs', '--tail', '70', container],
                                  capture_output=True, text=True, timeout=30)
            (evidence / 'runtime-diagnostic.txt').write_text(redact(logs.stdout + logs.stderr))
        raise
    finally:
        if events is not None:
            try:
                attestation = {
                    'schema': 'financial-evidence.activepieces-worker-attestation.v1',
                    'verified': receipt['worker_artifact_bytes_verified'],
                    'scope': 'reviewed_package_files_and_commonjs_sources_compiled_by_native_engine',
                    'external_dependencies_attested': False,
                    'loader_reference': LOADER_REFERENCE,
                    'preload_sha256': hashlib.sha256(WORKER_PRELOAD.encode()).hexdigest(),
                    'archive_sha256': receipt['sha256'], 'reviewed_files': files,
                    'observations': read_attestations(events),
                }
                retained = json.dumps(attestation, indent=2).encode() + b'\n'
                (evidence / 'worker-attestation.json').write_bytes(retained)
                receipt['worker_attestation'] = {'filename': 'worker-attestation.json',
                                               'sha256': hashlib.sha256(retained).hexdigest()}
            except Exception as error:
                receipt['attestation_error'] = redact(str(error))
                receipt['worker_artifact_bytes_verified'] = False
                if 'registry_verification' in receipt:
                    receipt['registry_verification']['worker_artifact_bytes_verified'] = False
                receipt['status'] = 'failed'
        if started:
            try:
                command('docker', 'rm', '-f', container)
            except Exception as error:
                # Preserve the original qualification failure and its receipt even
                # when cleanup also fails. A passed run must fail if cleanup fails.
                receipt['cleanup_error'] = redact(str(error))
                if receipt['status'] == 'passed':
                    receipt['status'] = 'failed'
                    receipt['error'] = 'Isolated host cleanup failed'
        receipt['completed_at'] = datetime.now(timezone.utc).isoformat()
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if receipt.get('cleanup_error'):
        raise RuntimeError('Isolated host cleanup failed; see retained receipt')
    if receipt.get('attestation_error'):
        raise RuntimeError('Worker attestation retention failed; see retained receipt')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
