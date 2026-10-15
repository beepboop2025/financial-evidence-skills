"""Install and execute a candidate archive or approved npm release in an isolated host.

Requires Docker. Creates only a disposable local host, account and draft flows.
Uses the same installation and step-test APIs as the editor; it does not certify
browser interactions, worker filesystem bytes or marketplace acceptance.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
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
        command('docker', 'pull', IMAGE, timeout=600)
        command('docker', 'run', '-d', '--name', container, '--memory', '3g', '--cpus', '2',
                '-p', '127.0.0.1::80', '-e', 'AP_DB_TYPE=PGLITE',
                '-e', 'AP_REDIS_TYPE=MEMORY', '-e', 'AP_FRONTEND_URL=http://localhost',
                '-e', 'AP_TELEMETRY_ENABLED=false', '-e', 'AP_EXECUTION_MODE=UNSANDBOXED',
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
                                    'output_sha256': hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest(), **detail})
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
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
