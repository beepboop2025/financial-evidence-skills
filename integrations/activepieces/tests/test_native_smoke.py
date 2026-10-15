"""Keep published identity, integrity failures and the native install route honest."""
import base64
from email import message_from_bytes
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
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


@unittest.skipUnless(shutil.which('node'), 'Node is required to exercise the actual CommonJS hooks')
class WorkerAttestationTests(unittest.TestCase):
    """Run real CommonJS loading without Docker, network or Activepieces secrets."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.package = {'name': '@approved/piece-financial-evidence', 'version': '0.1.0', 'main': 'dist/index.js'}
        self.phase = {'action': 'list_research_datasets', 'nonce': 'a' * 32}
        self.contents = {
            'package.json': json.dumps(self.package).encode(),
            'dist/index.js': b"module.exports = require('./helper.js');\n",
            'dist/helper.js': b'module.exports = {ok: true};\n',
            'README.md': b'Reviewed package documentation.\n',
        }
        self.archive = self.root / 'reviewed.tgz'
        self.write_archive()
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        self.probe, self.events, self.files = smoke.prepare_attestation(self.evidence, self.archive, self.package)
        config = json.loads((self.probe / 'config.json').read_text())
        config['events_file'] = str(self.events / 'events.ndjson')
        (self.probe / 'config.json').write_text(json.dumps(config))
        (self.probe / 'phase.json').write_text(json.dumps(self.phase))
        self.engine = self.root / 'cache/v15/common/main.js'
        self.engine.parent.mkdir(parents=True)
        self.folder = self.engine.parent / 'pieces' / (self.package['name'] + '-' + self.package['version'])

    def write_archive(self):
        with tarfile.open(self.archive, 'w:gz') as handle:
            for name, content in self.contents.items():
                member = tarfile.TarInfo('package/' + name)
                member.size = len(content)
                handle.addfile(member, io.BytesIO(content))

    def install(self, nested=True, linked=False):
        package_root = self.folder / 'node_modules' / self.package['name'] if nested else self.folder
        actual = self.root / 'bun-shared-store/package' if linked else package_root
        for name, content in self.contents.items():
            destination = actual / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        if linked:
            package_root.parent.mkdir(parents=True, exist_ok=True)
            package_root.symlink_to(actual, target_is_directory=True)
        return package_root

    def execute(self, package_root, prefix='', repeat=False, phase=True):
        entry = str(package_root / self.package['main'])
        self.engine.write_text(prefix + '\nconst load = require("node:module").createRequire(__filename);\n' +
                               f'load({json.dumps(entry)});\n' * (2 if repeat else 1))
        if not phase:
            (self.probe / 'phase.json').unlink()
        env = {**os.environ, 'NODE_OPTIONS': '--require=' + str(self.probe / 'preload.cjs'),
               'SANDBOX_ID': 'disposable-sandbox', 'FE_QUALIFICATION_DIR': str(self.probe)}
        env.pop('AP_CUSTOM_PIECES_PATHS', None)
        return subprocess.run(['node', str(self.engine)], env=env, capture_output=True, text=True, timeout=10)

    def test_actual_nested_loader_and_compiled_relative_module_match_archive(self):
        root = self.install()
        result = self.execute(root, repeat=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = smoke.read_attestations(self.events)
        facts = smoke.verify_worker_phase(observed, self.phase, self.files, self.package)
        self.assertEqual(facts['observations'], 2)
        self.assertEqual(facts['fresh_compilations'], 1)
        self.assertEqual(facts['compiled_files_verified'], ['dist/helper.js', 'dist/index.js'])
        self.assertEqual(observed[0]['resolved_entry'], str(root / 'dist/index.js'))
        self.assertEqual(observed[0]['engine_entry_sha256'], hashlib.sha256(self.engine.read_bytes()).hexdigest())
        self.assertNotIn('disposable-sandbox', json.dumps(observed))

    def test_archive_root_fallback_is_observed_not_assumed(self):
        result = self.execute(self.install(nested=False))
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = smoke.read_attestations(self.events)
        self.assertEqual(observed[0]['layout'], 'archive_root')
        smoke.verify_worker_phase(observed, self.phase, self.files, self.package)

    def test_bun_symlink_root_records_real_worker_file_paths(self):
        root = self.install(linked=True)
        result = self.execute(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = smoke.read_attestations(self.events)
        self.assertEqual(observed[0]['package_root'], str(root.resolve()))
        smoke.verify_worker_phase(observed, self.phase, self.files, self.package)

    def test_same_length_tampered_shipped_bytes_block_load(self):
        root = self.install()
        (root / 'README.md').write_bytes(b'X' * len(self.contents['README.md']))
        result = self.execute(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Attestation package bytes mismatch', result.stderr)
        observed = smoke.read_attestations(self.events)
        self.assertFalse(observed[0]['successful_load'])
        with self.assertRaisesRegex(RuntimeError, 'does not match'):
            smoke.verify_worker_phase(observed, self.phase, self.files, self.package)

    def test_compile_content_transformation_cannot_pass_disk_hash_check(self):
        root = self.install()
        prefix = """const M = require('node:module'), compile = M.prototype._compile;
M.prototype._compile = function(source, filename) {
  return compile.call(this, filename.endsWith('/dist/helper.js') ? source + '// changed' : source, filename);
};"""
        result = self.execute(root, prefix)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Attestation compiled source mismatch', result.stderr)

    def test_metadata_without_action_phase_is_not_counted(self):
        result = self.execute(self.install(), phase=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(smoke.read_attestations(self.events), [])
        with self.assertRaisesRegex(RuntimeError, 'No actual engine'):
            smoke.verify_worker_phase([], self.phase, self.files, self.package)

    def test_cached_only_and_wrong_phase_cannot_count_as_action_proof(self):
        self.assertEqual(self.execute(self.install(), repeat=True).returncode, 0)
        observed = smoke.read_attestations(self.events)
        with self.assertRaisesRegex(RuntimeError, 'fresh matching'):
            smoke.verify_worker_phase(observed[1:], self.phase, self.files, self.package)
        with self.assertRaisesRegex(RuntimeError, 'No actual engine'):
            smoke.verify_worker_phase(observed, {**self.phase, 'nonce': 'b' * 32}, self.files, self.package)

    def test_nested_layout_wins_over_root_package(self):
        nested = self.install()
        self.install(nested=False)
        result = self.execute(nested)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(smoke.read_attestations(self.events)[0]['layout'], 'nested_node_modules')
        (self.events / 'events.ndjson').unlink()
        result = self.execute(self.folder)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('loader resolution differs', result.stderr)

    def test_external_dependencies_are_explicitly_outside_compiled_source_scope(self):
        self.contents['dist/index.js'] = b"module.exports = require('dependency');\n"
        self.write_archive()
        self.files = smoke.reviewed_files(self.archive, self.package)
        config = json.loads((self.probe / 'config.json').read_text())
        config['files'] = self.files
        (self.probe / 'config.json').write_text(json.dumps(config))
        root = self.install()
        dependency = root / 'node_modules/dependency/index.js'
        dependency.parent.mkdir(parents=True)
        dependency.write_text('module.exports = 42;')
        result = self.execute(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        facts = smoke.verify_worker_phase(smoke.read_attestations(self.events), self.phase, self.files, self.package)
        self.assertEqual(facts['compiled_files_verified'], ['dist/index.js'])

    def test_record_byte_and_count_limits(self):
        trace = self.events / 'events.ndjson'
        trace.write_bytes(b' ' * (smoke.ATTESTATION_LIMIT + 1))
        with self.assertRaisesRegex(RuntimeError, 'byte bound'):
            smoke.read_attestations(self.events)
        trace.write_text('{}\n' * 33)
        with self.assertRaisesRegex(RuntimeError, 'Invalid worker'):
            smoke.read_attestations(self.events)

    def test_archive_rejects_duplicate_traversal_symlink_and_oversize_members(self):
        for name, kind, size in [('package/package.json', 'file', 1),
                                 ('package/../escape.js', 'file', 1),
                                 ('package/link.js', 'link', 0),
                                 ('package/huge.js', 'file', 1024 * 1024 + 1)]:
            with self.subTest(name=name):
                self.write_archive()
                # Build an uncompressed fixture to append the invalid member.
                invalid = self.root / 'invalid.tar'
                with tarfile.open(self.archive) as source, tarfile.open(invalid, 'w') as target:
                    for member in source:
                        target.addfile(member, source.extractfile(member))
                    member = tarfile.TarInfo(name)
                    member.size = size
                    if kind == 'link':
                        member.type, member.linkname = tarfile.SYMTYPE, '../outside'
                    target.addfile(member, io.BytesIO(b'x' * size))
                with self.assertRaisesRegex(RuntimeError, 'Invalid or unbounded'):
                    smoke.reviewed_files(invalid, self.package)


if __name__ == '__main__':
    unittest.main()
