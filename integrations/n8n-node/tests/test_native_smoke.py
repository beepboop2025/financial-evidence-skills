"""Check the publication artifact boundary without a registry or native host."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_smoke', PACKAGE / 'scripts/native_smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        # Local temporary files stay with the task checkout on the development SSD.
        self.temp = tempfile.TemporaryDirectory(prefix='.smoke-test-', dir=PACKAGE)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'source'
        self.package.mkdir()
        self.files = {
            'package.json': json.dumps({'name': 'n8n-nodes-financial-evidence', 'version': '0.1.0'}).encode(),
            'LICENSE': b'MIT\n', 'README.md': b'Original README\n',
            'dist/nodes/FinancialEvidence/FinancialEvidence.node.js': b'exports.FinancialEvidence = {};\n',
        }
        for name, data in self.files.items():
            path = self.package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()

    def archive(self, files=None, extra=None):
        target = self.root / 'candidate.tgz'
        with tarfile.open(target, 'w:gz') as archive:
            for name, data in (self.files if files is None else files).items():
                member = tarfile.TarInfo('package/' + name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
            if extra is not None:
                archive.addfile(extra, io.BytesIO(b'') if extra.isfile() else None)
        return target, hashlib.sha256(target.read_bytes()).hexdigest()

    def test_exact_archive_is_not_repacked_and_is_the_loaded_payload(self):
        original, digest = self.archive()
        raw = original.read_bytes()
        with patch.object(smoke.subprocess, 'run', side_effect=AssertionError('npm must not run')):
            archive, unpacked, report = smoke.prepare_archive(
                self.package, self.evidence, original, digest)
        self.assertEqual(archive.read_bytes(), raw)
        self.assertEqual(report['sha256'], digest)
        self.assertEqual(report['origin'], 'existing_archive')
        self.assertTrue(report['readme_matches_current_source'])
        for name, data in self.files.items():
            self.assertEqual((unpacked / 'package' / name).read_bytes(), data)

    def test_changed_archive_is_rejected_before_unpacking(self):
        original, digest = self.archive()
        original.write_bytes(original.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            smoke.prepare_archive(self.package, self.evidence, original, digest)
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_reviewed_hash_does_not_excuse_different_runtime_or_metadata(self):
        for name in ['dist/nodes/FinancialEvidence/FinancialEvidence.node.js', 'package.json']:
            with self.subTest(name=name):
                altered = {**self.files, name: self.files[name] + b' changed'}
                archive, digest = self.archive(altered)
                with self.assertRaisesRegex(ValueError, 'differs from current source/build'):
                    smoke.prepare_archive(self.package, self.evidence, archive, digest)

    def test_readme_difference_is_rejected_even_with_reviewed_archive_hash(self):
        archive, digest = self.archive()
        (self.package / 'README.md').write_text('Current publication instructions\n')
        with self.assertRaisesRegex(ValueError, 'README.md'):
            smoke.prepare_archive(self.package, self.evidence, archive, digest)
        self.assertEqual(list(self.evidence.iterdir()), [])

    def test_missing_and_extra_payload_files_are_rejected(self):
        for files in [{k: v for k, v in self.files.items() if k != 'LICENSE'},
                      {**self.files, 'surprise.js': b'not part of build'}]:
            archive, digest = self.archive(files)
            with self.assertRaisesRegex(ValueError, 'file list differs'):
                smoke.prepare_archive(self.package, self.evidence, archive, digest)

    def test_duplicate_traversal_and_link_members_are_rejected(self):
        link = tarfile.TarInfo('package/link')
        link.type = tarfile.SYMTYPE
        link.linkname = '../../outside'
        for member in [tarfile.TarInfo('package/LICENSE'), tarfile.TarInfo('package/../../outside'), link]:
            archive, digest = self.archive(extra=member)
            with self.assertRaisesRegex(ValueError, 'Unexpected archive member'):
                smoke.prepare_archive(self.package, self.evidence, archive, digest)
        self.assertFalse((self.root / 'outside').exists())

    def test_archive_mode_requires_reviewed_digest(self):
        archive, digest = self.archive()
        for candidate, sha in [(archive, None), (None, digest)]:
            with self.assertRaisesRegex(ValueError, 'supplied together'):
                smoke.prepare_archive(self.package, self.evidence, candidate, sha)
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            smoke.prepare_archive(self.package, self.evidence, archive, 'not-a-sha256')


if __name__ == '__main__':
    unittest.main(verbosity=2)
