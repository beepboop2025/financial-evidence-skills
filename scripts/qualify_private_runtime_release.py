#!/usr/bin/env python3
"""Verify the release owner's signed admission and reproduce both private artifacts."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]
SIGNERS = 'ops/release/financial-evidence.allowed_signers'
SIGNERS_HASH = '53294bcc8be556a265458c079a7d2cb7c012378e3c47a8708b9082bfdcef9b31'
SCHEMA = 'financial-evidence.private-runtime-provenance.v1'
TRANSPORT_SCHEMA = 'financial-evidence.private-runtime-provenance.v2'
TRANSPORT_DIGEST_KEYS = {'base_service_sha256', 'service_sha256'}
DIGEST_KEYS = {'base_wheel_sha256', 'implementation_sha256', 'wheel_sha256', 'operations_sha256'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *args, data=None):
    return subprocess.check_output(['git', *args], cwd=root, input=data).decode().strip()


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate admission field')
        result[key] = value
    return result


def valid_hex(value, size):
    return isinstance(value, str) and re.fullmatch(f'[0-9a-f]{{{size}}}', value) is not None


def validate_admission(document):
    if not isinstance(document, dict) or document.get('schema') not in (SCHEMA, TRANSPORT_SCHEMA):
        raise ValueError('unexpected admission schema')
    digest_keys = DIGEST_KEYS
    source_keys = {'build_source_commit', 'runtime_source_commit'}
    if document['schema'] == TRANSPORT_SCHEMA:
        digest_keys = digest_keys | TRANSPORT_DIGEST_KEYS
        source_keys.add('transport_source_commit')
    if document.keys() != digest_keys | source_keys | {'schema', 'acceptance'}:
        raise ValueError('unexpected admission fields')
    if not all(valid_hex(document[key], 64) for key in digest_keys):
        raise ValueError('invalid artifact digest')
    if not all(valid_hex(document[key], 40) for key in source_keys):
        raise ValueError('invalid source commit')
    receipts = document['acceptance']
    if not isinstance(receipts, dict) or not 1 <= len(receipts) <= 32:
        raise ValueError('acceptance receipts required')
    if not all(re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', name) and valid_hex(digest, 64)
               for name, digest in receipts.items()):
        raise ValueError('invalid acceptance receipt')


def verify_admission(root, raw, signed, expected_head, signers_hash):
    document = json.loads(raw, object_pairs_hook=unique_fields)
    validate_admission(document)
    head = git(root, 'rev-parse', 'HEAD')
    if head != expected_head or head != document['build_source_commit']:
        raise ValueError('build source differs from dispatch checkout')
    if sha(root / SIGNERS) != signers_hash:
        raise ValueError('unexpected release signer policy')
    if b'\ngpgsig -----BEGIN SSH SIGNATURE-----\n' not in signed.partition(b'\n\n')[0]:
        raise ValueError('an SSH-signed Git commit is required')
    blob = git(root, 'hash-object', '-w', '--stdin', data=raw)
    tree = git(root, 'mktree', data=f'100644 blob {blob}\tadmission.json\n'.encode())
    commit = git(root, 'hash-object', '-w', '-t', 'commit', '--stdin', data=signed)
    if git(root, 'show', '-s', '--format=%T %P', commit) != f'{tree} {head}':
        raise ValueError('signed commit must contain only admission.json and directly follow the build source')
    git(root, '-c', 'gpg.format=ssh', '-c', f'gpg.ssh.allowedSignersFile={root / SIGNERS}', 'verify-commit', commit)
    return commit


def input_bytes(key):
    encoded = os.environ[key]
    if not 1 <= len(encoded) <= 12_000:
        raise ValueError('dispatch input exceeds its size limit')
    return base64.b64decode(encoded, validate=True)


def build(root, admission_file, base_wheel, output):
    admission = json.loads(admission_file.read_bytes(), object_pairs_hook=unique_fields)
    validate_admission(admission)
    if sha(base_wheel) != admission['base_wheel_sha256']:
        raise ValueError('baseline wheel digest mismatch')
    output.mkdir(exist_ok=False)
    wheel_dir = output / 'wheel'
    wheel_dir.mkdir()
    transport_profile = admission['schema'] == TRANSPORT_SCHEMA
    generation = 2 if transport_profile else 1
    package_version = f'0.1.7+successor.{generation}'
    ops_version = f'1.0.3+successor.{generation}'
    ops_name = 'financial-evidence-runtime-ops-' + ops_version
    wheel_path = wheel_dir / f'financial_evidence-{package_version}-py3-none-any.whl'
    wheel_args = ['--profile', '2'] if transport_profile else []
    ops_args = ['--private-successor', '2'] if transport_profile else ['--private-successor']
    wheel_receipt = json.loads(subprocess.check_output([
        sys.executable, 'scripts/build_runtime_successor_wheel.py',
        '--base-wheel', str(base_wheel), '--output', str(wheel_dir), *wheel_args], cwd=root))
    expected = {
        'base_wheel_sha256': admission['base_wheel_sha256'],
        'implementation_sha256': admission['implementation_sha256'],
        'wheel_sha256': admission['wheel_sha256'],
        'source_commit': admission['runtime_source_commit'],
        'package_version': package_version,
    }
    if transport_profile:
        expected.update({key: admission[key] for key in TRANSPORT_DIGEST_KEYS | {'transport_source_commit'}})
    if wheel_receipt != expected or sha(wheel_path) != expected['wheel_sha256']:
        raise ValueError('reconstructed wheel differs from signed admission')
    ops_dir = output / 'ops'
    subprocess.run([sys.executable, 'scripts/build_runtime_operations.py', *ops_args,
                    '--output', str(ops_dir)], cwd=root, check=True)
    archive = ops_dir / (ops_name + '.tar')
    if sha(archive) != admission['operations_sha256']:
        raise ValueError('reconstructed operations digest differs from signed admission')
    with tarfile.open(archive, 'r:') as reader:
        manifest = json.loads(reader.extractfile(ops_name + '/source.json').read())
    if (manifest['version'] != ops_version or manifest['source_commit'] != admission['build_source_commit']
            or any(manifest['runtime'].get(key) != value for key, value in expected.items())):
        raise ValueError('operations archive does not bind the admitted source and runtime')
    print('Verified private wheel', expected['wheel_sha256'])
    print('Verified private operations archive', admission['operations_sha256'])
    return wheel_path, archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    verify = commands.add_parser('admission')
    verify.add_argument('--output', type=Path, required=True)
    reproduce = commands.add_parser('build')
    reproduce.add_argument('--admission', type=Path, required=True)
    reproduce.add_argument('--base-wheel', type=Path, required=True)
    reproduce.add_argument('--output', type=Path, required=True)
    reproduce.add_argument('--github-output', type=Path)
    args = parser.parse_args()
    if args.command == 'admission':
        raw = input_bytes('ADMISSION_B64')
        commit = verify_admission(ROOT, raw, input_bytes('SIGNED_COMMIT_B64'), os.environ['GITHUB_SHA'], SIGNERS_HASH)
        with args.output.open('xb') as destination:
            destination.write(raw)
        print('Verified release-owner admission commit', commit)
    else:
        wheel, operations = build(ROOT, args.admission, args.base_wheel.resolve(), args.output.resolve())
        if args.github_output:
            with args.github_output.open('a', encoding='utf-8') as outputs:
                outputs.write(f'wheel={wheel}\noperations={operations}\n')


if __name__ == '__main__':
    main()
