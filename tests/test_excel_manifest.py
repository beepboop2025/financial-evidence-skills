import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("excel_build", ROOT / "scripts/build_excel_office_addin.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)
NS = {"app": "http://schemas.microsoft.com/office/appforoffice/1.1"}


class VerificationManifestTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "docs/office/excel/manifest.xml").read_bytes()

    def test_verification_is_separate_and_preserves_production_capabilities(self):
        data = BUILD.operator_manifest(self.source)
        production, verification = ET.fromstring(self.source), ET.fromstring(data)
        self.assertNotEqual(production.findtext("app:Id", namespaces=NS),
                            verification.findtext("app:Id", namespaces=NS))
        for name in ("Version", "Permissions", "Hosts", "Requirements", "AppDomains"):
            self.assertEqual(ET.tostring(production.find("app:" + name, NS)),
                             ET.tostring(verification.find("app:" + name, NS)))
        self.assertEqual(data.count(b"?operator=1"), 2)
        self.assertNotIn(b"operator=1", self.source)
        self.assertEqual(data, BUILD.operator_manifest(self.source))

    def test_divergent_ribbon_location_cannot_silently_send_real_traffic(self):
        bad = self.source.replace(b'id="Review.TaskpaneUrl" DefaultValue="https:',
                                  b'id="Review.TaskpaneUrl" DefaultValue="http:')
        with self.assertRaises(ValueError):
            BUILD.operator_manifest(bad)

    def test_preexisting_query_is_rejected(self):
        with self.assertRaises(ValueError):
            BUILD.operator_manifest(self.source.replace(b'taskpane.html"', b'taskpane.html?unexpected=1"'))

    def test_unrecognized_id_format_cannot_reuse_production_identity(self):
        with self.assertRaises(ValueError):
            BUILD.operator_manifest(self.source.replace(b"<Id>", b"<Id >"))


if __name__ == "__main__":
    unittest.main()
