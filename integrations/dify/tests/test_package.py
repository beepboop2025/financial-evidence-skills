import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.verify_package import FILES, verify


class PackageTests(unittest.TestCase):
    def test_package_rejects_private_files_and_changed_source(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'plugin.difypkg'
            with ZipFile(archive, 'w') as package:
                for name in FILES:
                    package.write(source / name, name)
            self.assertEqual(verify(archive, source)['status'], 'passed')
            with ZipFile(archive, 'a') as package:
                package.writestr('.env.local', 'PRIVATE_DEBUG_KEY=never-ship')
            with self.assertRaisesRegex(ValueError, 'Unexpected package contents'):
                verify(archive, source)
            with ZipFile(archive, 'w') as package:
                for name in FILES:
                    package.writestr(name, b'changed' if name == 'main.py' else (source / name).read_bytes())
            with self.assertRaisesRegex(ValueError, 'Packaged source differs: main.py'):
                verify(archive, source)
