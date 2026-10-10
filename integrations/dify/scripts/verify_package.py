#!/usr/bin/env python3
"""Verify the official CLI package contains exactly the intended source files."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

FILES = {'manifest.yaml', 'main.py', 'requirements.txt', 'README.md', 'PRIVACY.md',
         '_assets/icon.svg', 'provider/financial_evidence.yaml', 'provider/financial_evidence.py',
         'tools/evidence_page.yaml', 'tools/evidence_page.py'}


def verify(archive: Path, source: Path) -> dict:
    with zipfile.ZipFile(archive) as package:
        names = [item.filename for item in package.infolist() if not item.is_dir()]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate package paths')
        if set(names) != FILES:
            raise ValueError(f'Unexpected package contents: {sorted(set(names) ^ FILES)}')
        hashes = {}
        for name in sorted(FILES):
            body = package.read(name)
            if body != (source / name).read_bytes():
                raise ValueError(f'Packaged source differs: {name}')
            hashes[name] = hashlib.sha256(body).hexdigest()
    return {'schema': 'financial-evidence.dify-package.v1', 'status': 'passed',
            'package': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'files': hashes, 'native_remote_debug_passed': False, 'marketplace_published': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, args.source), indent=2))
