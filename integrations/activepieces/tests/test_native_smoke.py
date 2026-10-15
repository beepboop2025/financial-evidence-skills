"""Keep published identity, integrity failures and the native install route honest."""
import base64
from email import message_from_bytes
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/native_smoke.py'
SPEC = importlib.util.spec_from_file_location('activepieces_native_smoke', SCRIPT)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def archive_bytes(package):
    output = io.BytesIO()
    manifest = json.dumps(package).encode()
    with tarfile.open(fileobj=output, mode='w:gz') as handle:
        member = tarfile.TarInfo('package/package.json')
        member.size = len(manifest)
        handle.addfile(member, io.BytesIO(manifest))
    return output.getvalue()


def form_fields(body, content_type):
    message = message_from_bytes(('Content-Type: ' + content_type + '\r\n\r\n').encode() + body)
    return {part.get_param('name', header='content-disposition'): part.get_payload(decode=True)
            for part in message.get_payload()}


class PublishedArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        self.package = {'name': '@approved/piece-financial-evidence', 'version': '0.1.0'}
        self.raw = archive_bytes(self.package)
        self.publication = {
            'schema': 'financial-evidence.activepieces-publication.v1',
            'status': 'published_bytes_verified', 'anonymous_registry_readback': True,
            'package': self.package['name'], 'version': self.package['version'],
            'bytes': len(self.raw), 'sha256': hashlib.sha256(self.raw).hexdigest(),
            'integrity': 'sha512-' + base64.b64encode(hashlib.sha512(self.raw).digest()).decode(),
            'tarball_url': 'https://registry.npmjs.org/@approved/piece-financial-evidence/-/piece-financial-evidence-0.1.0.tgz',
            'native_receipt': 'native.json', 'native_source_commit': 'approved-source',
        }
        self.native = {
            **{k: self.publication[k] for k in ('package', 'version', 'bytes', 'sha256')},
            'status': 'passed', 'installation': 'archive_via_native_install_api',
            'source_commit': 'approved-source', 'filename': 'approved-piece-0.1.0.tgz',
            'runs': [{'action': action, 'status': 'SUCCEEDED'} for action in smoke.ACTIONS],
        }
        self.metadata = {**self.package, 'dist': {
            'tarball': self.publication['tarball_url'], 'integrity': self.publication['integrity'],
        }}
        self.write_receipts()

    def write_receipts(self):
        (self.root / 'publication.json').write_text(json.dumps(self.publication))
        (self.root / 'native.json').write_text(json.dumps(self.native))

    def fetch(self, url, limit):
        if url == self.publication['tarball_url']:
            return self.raw
        self.assertEqual(url, 'https://registry.npmjs.org/@approved%2Fpiece-financial-evidence/0.1.0')
        return json.dumps(self.metadata).encode()

    def resolve(self):
        return smoke.published_archive(self.evidence, self.root / 'publication.json')

    def test_binds_published_bytes_to_prior_native_qualification(self):
        with patch.object(smoke, 'public_read', side_effect=self.fetch):
            package, archive, facts = self.resolve()
        self.assertEqual(package, self.package)
        self.assertEqual(archive.read_bytes(), self.raw)
        self.assertTrue(facts['public_artifact_bytes_verified'])
        self.assertFalse(facts['worker_artifact_bytes_verified'])
        self.assertEqual(facts['native_archive_source_commit'], 'approved-source')
        self.assertTrue((self.evidence / 'registry-version-metadata.json').exists())

    def test_registry_target_remains_published_version_when_candidate_changes(self):
        (self.root / 'package.json').write_text(json.dumps({'name': '@future/piece', 'version': '9.9.9'}))
        with patch('sys.argv', ['native_smoke.py', '--installation', 'registry', '--evidence-dir', str(self.evidence)]), \
                patch.object(smoke, 'ROOT', self.root), \
                patch.object(smoke, 'public_read', side_effect=self.fetch), \
                patch.object(smoke, 'published_archive', side_effect=lambda evidence: self.resolve_pinned(evidence, self.root / 'publication.json')), \
                patch.object(smoke, 'command', side_effect=['harness-source', RuntimeError('Stop before native host')]) as command:
            with self.assertRaisesRegex(RuntimeError, 'Stop before native host'):
                smoke.main()
        self.assertEqual(command.call_count, 2)
        self.assertEqual(command.call_args.args[:2], ('docker', 'pull'))
        receipt = json.loads((self.evidence / 'receipt.json').read_text())
        self.assertEqual(receipt['candidate'], {'package': '@future/piece', 'version': '9.9.9'})
        self.assertEqual((receipt['package'], receipt['version']), (self.package['name'], '0.1.0'))
        self.assertEqual(receipt['artifact_source'], 'approved_publication_receipt')
        self.assertTrue(receipt['npm_published'])
        self.assertFalse(receipt['worker_artifact_bytes_verified'])

    # Capture the real function so the main-entry test can inject the fixture's
    # approved receipt without changing the production CLI's fixed target.
    resolve_pinned = staticmethod(smoke.published_archive)

    def test_refuses_receipt_identity_hash_and_native_action_mismatches_before_fetch(self):
        for key, wrong in [('version', '0.2.0'), ('sha256', '0' * 64), ('bytes', 0),
                           ('status', 'failed'), ('runs', [])]:
            with self.subTest(key=key):
                original = self.native[key]
                self.native[key] = wrong
                self.write_receipts()
                with patch.object(smoke, 'public_read') as fetch:
                    with self.assertRaisesRegex(RuntimeError, 'not bound'):
                        self.resolve()
                    fetch.assert_not_called()
                self.native[key] = original

    def test_refuses_registry_identity_mismatch(self):
        self.metadata['version'] = '0.2.0'
        with patch.object(smoke, 'public_read', side_effect=self.fetch):
            with self.assertRaisesRegex(RuntimeError, 'metadata identity mismatch'):
                self.resolve()

    def test_refuses_registry_distribution_metadata_mismatch_before_tarball_fetch(self):
        self.metadata['dist']['integrity'] = 'sha512-changed'
        with patch.object(smoke, 'public_read', side_effect=self.fetch) as fetch:
            with self.assertRaisesRegex(RuntimeError, 'distribution metadata differs'):
                self.resolve()
        self.assertEqual(fetch.call_count, 1)

    def test_refuses_same_length_tampered_tarball(self):
        self.raw = self.raw[:-1] + bytes([self.raw[-1] ^ 1])
        with patch.object(smoke, 'public_read', side_effect=self.fetch):
            with self.assertRaisesRegex(RuntimeError, 'tarball bytes differ'):
                self.resolve()

    def test_refuses_sri_mismatch_even_when_sha256_matches(self):
        self.publication['integrity'] = self.metadata['dist']['integrity'] = 'sha512-wrong'
        self.write_receipts()
        with patch.object(smoke, 'public_read', side_effect=self.fetch):
            with self.assertRaisesRegex(RuntimeError, 'SHA-512 integrity mismatch'):
                self.resolve()

    def test_refuses_embedded_package_identity_mismatch(self):
        self.raw = archive_bytes({**self.package, 'version': '9.9.9'})
        self.publication.update(bytes=len(self.raw), sha256=hashlib.sha256(self.raw).hexdigest(),
                                integrity='sha512-' + base64.b64encode(hashlib.sha512(self.raw).digest()).decode())
        self.native.update(bytes=self.publication['bytes'], sha256=self.publication['sha256'])
        self.metadata['dist']['integrity'] = self.publication['integrity']
        self.write_receipts()
        with patch.object(smoke, 'public_read', side_effect=self.fetch):
            with self.assertRaisesRegex(RuntimeError, 'Packed package identity mismatch'):
                self.resolve()

    def test_registry_urls_reject_other_hosts_credentials_and_plain_http(self):
        for url in ['http://registry.npmjs.org/piece', 'https://registry.npmjs.org.evil.test/piece',
                    'https://secret@registry.npmjs.org/piece', 'https://example.com/piece']:
            with self.subTest(url=url), self.assertRaisesRegex(RuntimeError, 'HTTPS public npm'):
                smoke.public_read(url, 1024)


class InstallationRouteTests(unittest.TestCase):
    def test_registry_route_sends_exact_identity_without_archive(self):
        package = {'name': '@approved/piece', 'version': '0.1.0'}
        metadata = {**package, 'packageType': 'REGISTRY', 'actions': dict.fromkeys(smoke.ACTIONS)}
        calls = []

        def api(*args):
            calls.append(args)
            return metadata

        self.assertEqual(smoke.install_piece(api, package, 'registry', Path('/must-not-read'), 'project'), metadata)
        self.assertEqual(calls[0][:2], ('POST', 'pieces'))
        self.assertEqual(form_fields(*calls[0][2:]), {
            'packageType': b'REGISTRY', 'scope': b'PLATFORM',
            'pieceName': b'@approved/piece', 'pieceVersion': b'0.1.0',
        })
        self.assertEqual(calls[1], ('GET', 'pieces/@approved/piece?version=0.1.0&projectId=project'))

    def test_registry_route_refuses_archive_metadata(self):
        package = {'name': '@approved/piece', 'version': '0.1.0'}
        metadata = {**package, 'packageType': 'ARCHIVE', 'actions': dict.fromkeys(smoke.ACTIONS)}
        with self.assertRaisesRegex(RuntimeError, 'package type mismatch'):
            smoke.install_piece(lambda *args: metadata, package, 'registry', None, 'project')

    def test_archive_route_includes_the_candidate_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'candidate.tgz'
            archive.write_bytes(b'candidate archive')
            body, mime = smoke.multipart({'packageType': 'ARCHIVE'}, archive)
        self.assertEqual(form_fields(body, mime), {'packageType': b'ARCHIVE', 'pieceArchive': b'candidate archive'})

    def test_failed_registry_preflight_retains_failure_receipt_and_never_starts_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('sys.argv', ['native_smoke.py', '--installation', 'registry', '--evidence-dir', directory]), \
                    patch.object(smoke, 'command', return_value='harness-source') as command, \
                    patch.object(smoke, 'published_archive', side_effect=RuntimeError('Registry integrity mismatch')):
                with self.assertRaisesRegex(RuntimeError, 'Registry integrity mismatch'):
                    smoke.main()
            command.assert_called_once_with('git', 'rev-parse', 'HEAD')
            receipt = json.loads((Path(directory) / 'receipt.json').read_text())
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['installation_mode'], 'registry')
        self.assertFalse(receipt['npm_published'])
        self.assertEqual(receipt['runs'], [])

    def test_future_candidate_archive_does_not_require_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = {'name': '@future/piece', 'version': '9.9.9'}
            (root / 'package.json').write_text(json.dumps(candidate))
            evidence = root / 'evidence'
            evidence.mkdir()
            (evidence / 'candidate.tgz').write_bytes(archive_bytes(candidate))

            def command(*args, **kwargs):
                if args[0] == 'git':
                    return 'candidate-source'
                if args[:2] == ('npm', 'pack'):
                    return json.dumps([{'filename': 'candidate.tgz'}])
                raise RuntimeError('Stop before native host')

            with patch('sys.argv', ['native_smoke.py', '--evidence-dir', str(evidence)]), \
                    patch.object(smoke, 'ROOT', root), patch.object(smoke, 'command', side_effect=command), \
                    patch.object(smoke, 'published_archive') as published:
                with self.assertRaisesRegex(RuntimeError, 'Stop before native host'):
                    smoke.main()
                published.assert_not_called()
            receipt = json.loads((evidence / 'receipt.json').read_text())
        self.assertEqual((receipt['package'], receipt['version']), ('@future/piece', '9.9.9'))
        self.assertEqual(receipt['installation_mode'], 'archive')
        self.assertEqual(receipt['artifact_source'], 'candidate_checkout')


if __name__ == '__main__':
    unittest.main()
