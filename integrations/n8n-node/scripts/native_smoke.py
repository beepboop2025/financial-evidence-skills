#!/usr/bin/env python3
"""Run the packed node in an isolated, real n8n CLI against three public pages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n8n-bin', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    # Refuse reuse: an old database or receipt must never pass as this run.
    evidence.mkdir(parents=True, exist_ok=False)
    package = Path(__file__).resolve().parents[1]
    n8n = args.n8n_bin.resolve(strict=True)
    packed = subprocess.run(['npm', 'pack', '--json', '--pack-destination', str(evidence)],
                            cwd=package, check=True, capture_output=True, text=True)
    archive = evidence / json.loads(packed.stdout)[0]['filename']
    unpacked = evidence / 'unpacked'
    with tarfile.open(archive) as contents:
        contents.extractall(unpacked, filter='data')
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
           'NODE_OPTIONS': '--max-old-space-size=768'}

    def run(label, *arguments):
        result = subprocess.run([str(n8n), *arguments], env=env, cwd=package,
                                capture_output=True, text=True, timeout=240)
        (evidence / f'{label}.stdout').write_text(result.stdout)
        (evidence / f'{label}.stderr').write_text(result.stderr)
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
    run('import', 'import:workflow', '--input', str(path))
    stdout = run('execute', 'execute', '--id', workflow['id'], '--rawOutput')
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
               'loader': 'native_custom_extension_from_npm_tarball', 'pages': pages,
               'npm_published': False, 'n8n_verified': False, 'independent_adoption_proven': False}
    (evidence / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
