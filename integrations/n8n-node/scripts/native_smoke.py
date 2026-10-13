#!/usr/bin/env python3
"""Run the packed node in an isolated, real n8n CLI against three public pages."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone


def prepare_archive(package, evidence, existing=None, expected_sha256=None):
    """Validate an immutable candidate before a host can load any of its code."""
    if (existing is None) != (expected_sha256 is None):
        raise ValueError('--archive and --expected-sha256 must be supplied together')
    if existing is None:
        packed = subprocess.run(['npm', 'pack', '--json', '--pack-destination', str(evidence)],
                                cwd=package, check=True, capture_output=True, text=True)
        existing = evidence / json.loads(packed.stdout)[0]['filename']
        origin = 'fresh_pack'
    else:
        origin = 'existing_archive'
    raw = existing.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and (not re.fullmatch('[a-f0-9]{64}', expected_sha256)
                                        or digest != expected_sha256):
        raise ValueError('Reviewed archive SHA-256 mismatch')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as contents:
        for member in contents.getmembers():
            path = PurePosixPath(member.name)
            if (not member.isfile() or path.is_absolute() or '..' in path.parts
                    or path.parts[0] != 'package' or path.as_posix() != member.name
                    or member.name in files):
                raise ValueError(f'Unexpected archive member: {member.name}')
            files[member.name] = contents.extractfile(member).read()
    # Everything shipped, including README and metadata, must match the build.
    expected_files = {'package/package.json', 'package/LICENSE', 'package/README.md'}
    expected_files.update('package/' + path.relative_to(package).as_posix()
                          for path in (package / 'dist').rglob('*') if path.is_file())
    if set(files) != expected_files:
        raise ValueError('Archive file list differs from current package and build')
    readme_matches = files['package/README.md'] == (package / 'README.md').read_bytes()
    for name, data in files.items():
        if data != (package / name.removeprefix('package/')).read_bytes():
            raise ValueError(f'Archive differs from current source/build: {name}')
    manifest = json.loads(files['package/package.json'])
    if manifest['name'] != 'n8n-nodes-financial-evidence' or not re.fullmatch(
            r'\d+\.\d+\.\d+', manifest['version']):
        raise ValueError('Unexpected package identity')
    archive = evidence / f"{manifest['name']}-{manifest['version']}.tgz"
    archive.write_bytes(raw)  # Preserve the original tarball, including gzip metadata.
    unpacked = evidence / 'unpacked'
    for name, data in files.items():
        destination = unpacked / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    report = {'schema': 'financial-evidence.n8n-archive-check.v1', 'origin': origin,
              'name': manifest['name'], 'version': manifest['version'], 'sha256': digest,
              'runtime_and_metadata_match_current_build': True,
              'readme_matches_current_source': readme_matches,
              'archive_readme_sha256': hashlib.sha256(files['package/README.md']).hexdigest(),
              'source_readme_sha256': hashlib.sha256((package / 'README.md').read_bytes()).hexdigest()}
    (evidence / 'archive-check.json').write_text(json.dumps(report, indent=2) + '\n')
    return archive, unpacked, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n8n-bin', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--archive', type=Path, help='Test these existing bytes without npm pack')
    parser.add_argument('--expected-sha256', help='Required reviewed hash when --archive is supplied')
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    # Refuse reuse: an old database or receipt must never pass as this run.
    evidence.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).resolve().parents[1]
    n8n = args.n8n_bin.resolve(strict=True)
    archive, unpacked, archive_check = prepare_archive(
        package, evidence, args.archive, args.expected_sha256)
    # The custom loader uses the host's peer dependency, as an installed node does.
    (unpacked / 'package' / 'node_modules').symlink_to(n8n.parents[2], target_is_directory=True)
    # Do not inherit DB_*, N8N_* or external-hook settings from a real instance.
    inherited = {key: value for key, value in os.environ.items() if key in {
        'PATH', 'HOME', 'SHELL', 'TMPDIR', 'TEMP', 'TMP', 'LANG', 'LC_ALL',
        'SSL_CERT_FILE', 'SSL_CERT_DIR', 'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'CI'}}
    env = {**inherited, 'DB_TYPE': 'sqlite', 'DB_SQLITE_DATABASE': 'database.sqlite',
           'N8N_USER_FOLDER': str(evidence / 'user'),
           'N8N_CUSTOM_EXTENSIONS': str(unpacked / 'package' / 'dist'),
           'N8N_DIAGNOSTICS_ENABLED': 'false', 'N8N_VERSION_NOTIFICATIONS_ENABLED': 'false',
           'N8N_TEMPLATES_ENABLED': 'false', 'N8N_PERSONALIZATION_ENABLED': 'false',
           'N8N_COMMUNITY_PACKAGES_PREVENT_LOADING': 'false',
           # n8n routes --rawOutput through logger.info; error would hide the result.
           'N8N_RUNNERS_ENABLED': 'false', 'N8N_LOG_LEVEL': 'info',
           'NODE_OPTIONS': '--max-old-space-size=768 --require=' + str(package / 'scripts/synthetic_traffic.cjs')}

    def run(label, *arguments):
        result = subprocess.run([str(n8n), *arguments], env=env, cwd=package,
                                capture_output=True, text=True, timeout=240)
        for suffix, content in [('stdout', result.stdout), ('stderr', result.stderr)]:
            # Native logs and results can contain data; retain only identity and size.
            retained = json.dumps({'bytes': len(content.encode()),
                'sha256': hashlib.sha256(content.encode()).hexdigest(),
                'body_retained': False})
            (evidence / f'{label}.{suffix}').write_text(retained)
        result.check_returncode()
        return result.stdout

    version = run('version', '--version').strip()
    datasets = ['bank_risk', 'money_markets', 'market_liquidity']
    workflow = {'id': 'financialEvidenceSmoke', 'name': 'Financial Evidence native smoke',
                'active': False, 'settings': {'executionOrder': 'v1'},
                'nodes': [{'id': 'start', 'name': 'Start', 'type': 'n8n-nodes-base.manualTrigger',
                           'typeVersion': 1, 'position': [0, 0], 'parameters': {}}],
                'connections': {'Start': {'main': [[]]}}}
    for index, dataset in enumerate(datasets):
        workflow['nodes'].append({'id': dataset, 'name': dataset, 'type': 'CUSTOM.financialEvidence',
                                  'typeVersion': 1, 'position': [300, index * 200],
                                  'parameters': {'dataset': dataset, 'entity': '', 'limit': 1, 'offset': 0}})
        workflow['connections']['Start']['main'][0].append({'node': dataset, 'type': 'main', 'index': 0})
    path = evidence / 'workflow.json'
    path.write_text(json.dumps(workflow, indent=2) + '\n')
    try:
        run('import', 'import:workflow', '--input', str(path))
        stdout = run('execute', 'execute', '--id', workflow['id'], '--rawOutput')
    finally:
        # This path was reserved by this invocation; never touch another host.
        shutil.rmtree(evidence / 'user', ignore_errors=False) if (evidence / 'user').exists() else None
    # Some n8n versions print startup notices even with rawOutput enabled.
    decoder = json.JSONDecoder()
    execution = None
    for index, character in enumerate(stdout):
        if character == '{':
            try:
                candidate, _ = decoder.raw_decode(stdout[index:])
                if (isinstance(candidate, dict) and isinstance(candidate.get('data'), dict)
                        and 'resultData' in candidate['data']):
                    execution = candidate
                    break
            except json.JSONDecodeError:
                continue
    if execution is None:
        raise ValueError('n8n did not return an execution result')
    result = execution['data']['resultData']
    if result.get('error') or execution.get('finished') is not True:
        raise ValueError('n8n execution did not finish successfully')
    pages = {}
    for dataset in datasets:
        page = result['runData'][dataset][0]['data']['main'][0][0]['json']
        if (page.get('schema') != 'liquidity-lab.openbb-table.v1'
                or page.get('dataset') != dataset
                or not all(isinstance(page.get(key), list) for key in ['results', 'sources', 'diagnostics'])
                or len(page['results']) > 1 or 'next_offset' not in page):
            raise ValueError(f'Native output lost the evidence contract for {dataset}')
        pages[dataset] = {'rows': len(page['results']), 'sources': len(page['sources']),
                          'diagnostics': len(page['diagnostics']), 'next_offset': page['next_offset'],
                          'transport_status': page.get('transport_status')}
    receipt = {'schema': 'financial-evidence.n8n-native-smoke.v1',
               'observed_at': datetime.now(timezone.utc).isoformat(),
               'status': 'passed', 'n8n_version': version,
               'package': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
               'archive_check': archive_check,
               'loader': 'native_custom_extension_from_npm_tarball', 'pages': pages,
               'traffic_class': 'synthetic', 'measurement_instrumentation': 'isolated_https_request_header',
               'package_bytes_modified_by_instrumentation': False, 'temporary_runtime_state_retained': False,
               'npm_published': False, 'n8n_verified': False, 'independent_adoption_proven': False}
    (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
