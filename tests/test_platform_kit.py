"""The offline platform guide must include the public receipts it links."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_platform_hub", ROOT / "scripts/build_platform_hub.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class PlatformKitTests(unittest.TestCase):
    def test_dify_app_contains_the_signed_dependency_and_the_downloadable_workflow(self):
        assets = builder.assets()
        receipt_path = "docs/distribution/dify-marketplace-archive-20261029.json"
        workflow = assets["dify/first-evidence.yml"]
        package = assets["dify/first-evidence.ifpkg"]
        with zipfile.ZipFile(io.BytesIO(assets["finance-platform-kit.zip"])) as kit:
            self.assertEqual(kit.read("docs/platforms/dify/first-evidence.ifpkg"), package)
            self.assertEqual(kit.read("docs/platforms/dify/first-evidence.yml"), workflow)
            native = json.loads(kit.read("docs/platforms/dify/native-check-20261119.json"))
            self.assertEqual(native["workflow_yaml_sha256"], hashlib.sha256(workflow).hexdigest())
            self.assertEqual(native["workflow_ifpkg_sha256"], hashlib.sha256(package).hexdigest())
            identifier = json.loads(kit.read(receipt_path))["marketplace_identifier"]
            self.assertIn("marketplace_plugin_unique_identifier: " + identifier, workflow.decode())
        with zipfile.ZipFile(io.BytesIO(package)) as app:
            self.assertEqual(set(app.namelist()), {"app.yaml", "manifest.yaml"})
            self.assertEqual(app.read("app.yaml"), workflow)
            manifest = app.read("manifest.yaml").decode()
            self.assertIn("size: " + str(len(workflow)), manifest)
            self.assertIn("sha256: " + hashlib.sha256(workflow).hexdigest(), manifest)

    def test_activepieces_guide_receipts_are_usable_inside_downloaded_kit(self):
        assets = builder.assets()
        with zipfile.ZipFile(io.BytesIO(assets["finance-platform-kit.zip"])) as archive:
            guide = archive.read("docs/platforms/activepieces.md").decode()
            receipts = {target for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", guide)
                        if target.endswith(".json") and ":" not in target and "/" not in target}
            self.assertIn("activepieces-worker-attestation-20261015.json", receipts)
            for name in receipts:
                with self.subTest(receipt=name):
                    expected = (ROOT / "docs/platforms" / name).read_bytes()
                    self.assertEqual(archive.read("docs/platforms/" + name), expected)
            worker = "activepieces-worker-attestation-20261015.json"
            self.assertIn(hashlib.sha256(archive.read("docs/platforms/" + worker)).hexdigest()
                          + "  " + worker + "\n", assets["SHA256SUMS"].decode())


if __name__ == "__main__":
    unittest.main()
