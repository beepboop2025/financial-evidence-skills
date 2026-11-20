import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import qualify_private_runtime_release as provenance


@unittest.skipUnless(shutil.which('ssh-keygen') and shutil.which('git'), 'SSH-enabled Git required')
class AdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'gpg.format', 'ssh')
        self.git('config', 'gpg.ssh.program', shutil.which('ssh-keygen'))
        self.git('config', 'commit.gpgsign', 'false')
        self.key = self.root / 'synthetic-key'
        self.generate_key(self.key)
        self.git('config', 'user.signingkey', str(self.key))
        signers = self.root / provenance.SIGNERS
        signers.parent.mkdir(parents=True)
        pub = self.key.with_suffix('.pub').read_text().split()
        signers.write_text('test namespaces="git" ' + ' '.join(pub[:2]) + '\n')
        self.policy = provenance.sha(signers)
        self.git('add', provenance.SIGNERS)
        self.git('commit', '-q', '-m', 'build source')
        self.head = self.git('rev-parse', 'HEAD')
        self.document = {key: 'e' * 64 for key in provenance.DIGEST_KEYS}
        self.document.update(schema=provenance.SCHEMA, build_source_commit=self.head,
                             runtime_source_commit='a' * 40, acceptance={'rehearsal': 'b' * 64})
        self.raw = json.dumps(self.document).encode()
        blob = self.git('hash-object', '-w', '--stdin', data=self.raw)
        self.tree = self.git('mktree', data=f'100644 blob {blob}\tadmission.json\n'.encode())

    def generate_key(self, path):
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)], check=True)

    def git(self, *args, data=None):
        return provenance.git(self.root, *args, data=data)

    def sign(self, tree=None, parent=None):
        oid = self.git('commit-tree', '-S', tree or self.tree, '-p', parent or self.head, '-m', 'admit')
        return subprocess.check_output(['git', 'cat-file', 'commit', oid], cwd=self.root)

    def verify(self, signed, raw=None):
        return provenance.verify_admission(self.root, raw or self.raw, signed, self.head, self.policy)

    def test_detached_signed_admission_and_mutated_artifact_digest(self):
        signed = self.sign()
        self.assertEqual(self.verify(signed), self.git('hash-object', '-t', 'commit', '--stdin', data=signed))
        altered = dict(self.document, wheel_sha256='b' * 64)
        with self.assertRaisesRegex(ValueError, 'signed commit'):
            self.verify(signed, json.dumps(altered).encode())

    def test_reject_unsigned_foreign_key_and_wrong_parent(self):
        with self.assertRaisesRegex(ValueError, 'SSH-signed'):
            self.verify(subprocess.check_output(['git', 'cat-file', 'commit', self.head], cwd=self.root))
        parent = self.git('commit-tree', self.tree, '-p', self.head, '-m', 'other')
        with self.assertRaisesRegex(ValueError, 'directly follow'):
            self.verify(self.sign(parent=parent))
        other_key = self.root / 'other-key'
        self.generate_key(other_key)
        self.git('config', 'user.signingkey', str(other_key))
        with self.assertRaises(subprocess.CalledProcessError):
            self.verify(self.sign())

    def test_reject_mismatched_policy_and_non_digest_fields(self):
        with self.assertRaisesRegex(ValueError, 'signer policy'):
            provenance.verify_admission(self.root, self.raw, self.sign(), self.head, 'f' * 64)
        for acceptance in ({}, {'absolute/path': 'd' * 64}, {'test': 'contents'}):
            with self.subTest(acceptance=acceptance), self.assertRaises(ValueError):
                provenance.validate_admission(dict(self.document, acceptance=acceptance))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            provenance.unique_fields([('schema', 'one'), ('schema', 'two')])
        with mock.patch.dict('os.environ', {'ADMISSION_B64': 'x' * 12_001}):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                provenance.input_bytes('ADMISSION_B64')
