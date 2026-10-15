"""Install and execute the packed piece in an isolated official Activepieces host.

Requires Docker. Creates only a disposable local host, account and draft flows.
Uses the same installation and step-test APIs as the editor; it does not certify
browser interactions, npm publication or marketplace acceptance.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import tarfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

IMAGE = 'activepieces/activepieces@sha256:4b719ac8cb9a235beb59f9beae322c9447ee532264ff08af9094926240b721e8'
RELEASE = '0.92.3'
ROOT = Path(__file__).resolve().parents[1]


def command(*args, timeout=120):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stderr[-1500:]}')
    return result.stdout.strip()


def multipart(fields, archive):
    boundary = 'financial-evidence-' + secrets.token_hex(12)
    chunks = []
    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="pieceArchive"; filename="piece.tgz"\r\nContent-Type: application/gzip\r\n\r\n'.encode())
    chunks += [archive.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()]
    return b''.join(chunks), f'multipart/form-data; boundary={boundary}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    package = json.loads((ROOT / 'package.json').read_text())
    packed = json.loads(command('npm', 'pack', '--json', '--pack-destination', str(evidence)))[0]
    archive = evidence / packed['filename']
    with tarfile.open(archive) as handle:
        shipped = json.load(handle.extractfile('package/package.json'))
    if (shipped['name'], shipped['version']) != (package['name'], package['version']):
        raise RuntimeError('Packed package identity mismatch')
    receipt = {
        'schema': 'financial-evidence.activepieces-native.v1',
        'started_at': datetime.now(timezone.utc).isoformat(),
        'status': 'running', 'image': IMAGE, 'release': RELEASE,
        'source_commit': command('git', 'rev-parse', 'HEAD'),
        'package': package['name'], 'version': package['version'],
        'filename': archive.name, 'bytes': archive.stat().st_size,
        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'installation': 'archive_via_native_install_api',
        'execution': 'native_worker_via_editor_step_test_api',
        'browser_interaction': 'not_tested', 'npm_published': False,
        'upstream_submission': 'paused_by_upstream_policy',
        'independent_adoption_verified': False, 'runs': [],
    }
    container = 'financial-evidence-qualification-' + secrets.token_hex(6)
    token = None
    password = secrets.token_urlsafe(30)
    started = False

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
            for sensitive in (token, password):
                if sensitive:
                    detail = detail.replace(sensitive, '[redacted]')
            raise RuntimeError(f'{method} {path}: HTTP {error.code}: {detail}') from None

    try:
        command('docker', 'pull', IMAGE, timeout=600)
        command('docker', 'run', '-d', '--name', container, '--memory', '3g', '--cpus', '2',
                '-p', '127.0.0.1::80', '-e', 'AP_DB_TYPE=PGLITE',
                '-e', 'AP_REDIS_TYPE=MEMORY', '-e', 'AP_FRONTEND_URL=http://localhost',
                '-e', 'AP_TELEMETRY_ENABLED=false', '-e', 'AP_EXECUTION_MODE=UNSANDBOXED',
                '-e', 'AP_LOG_LEVEL=warn', IMAGE)
        started = True
        base = 'http://' + command('docker', 'port', container, '80/tcp')
        deadline = time.monotonic() + 240
        while True:
            try:
                flags = api('GET', 'flags')
                break
            except (OSError, RuntimeError):
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
        body, mime = multipart({
            'packageType': 'ARCHIVE', 'scope': 'PLATFORM',
            'pieceName': package['name'], 'pieceVersion': package['version'],
        }, archive)
        metadata = api('POST', 'pieces', body, mime)
        metadata = api('GET', 'pieces/' + package['name'] + '?' + urlencode({
            'version': package['version'], 'projectId': project,
        }))
        if metadata['name'] != package['name'] or metadata['version'] != package['version']:
            raise RuntimeError('Installed metadata identity mismatch')
        if set(metadata['actions']) != {'list_research_datasets', 'get_evidence_page'}:
            raise RuntimeError('Installed actions mismatch')
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
        receipt['error'] = str(error)
        if started:
            logs = command('docker', 'logs', '--tail', '70', container)
            for sensitive in (token, password):
                if sensitive:
                    logs = logs.replace(sensitive, '[redacted]')
            (evidence / 'runtime-diagnostic.txt').write_text(logs)
        raise
    finally:
        if started:
            command('docker', 'rm', '-f', container)
        receipt['completed_at'] = datetime.now(timezone.utc).isoformat()
        (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
