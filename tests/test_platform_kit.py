"""The offline platform guide must include the public receipts it links."""
import hashlib
import importlib.util
import io
from pathlib import Path
import re
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_platform_hub", ROOT / "scripts/build_platform_hub.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class PlatformKitTests(unittest.TestCase):
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
