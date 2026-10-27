"""Release artifacts remain citable, attestable, and reproducible."""

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseIntegrityTests(unittest.TestCase):
    def test_citation_metadata_tracks_the_package_release(self):
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn("cff-version: 1.2.0", citation)
        source = (ROOT / "src/financial_evidence/__init__.py").read_text()
        version = re.search(r'^__version__ = "([^"]+)"$', source, re.MULTILINE).group(1)
        self.assertIn(f"version: {version}", citation)
        manifest = json.loads((ROOT / "docs/integrations.json").read_text())
        if manifest["release_state"] == "candidate":
            self.assertNotRegex(citation, r"(?m)^date-released:")
            self.assertNotIn(f"releases/tag/v{version}", citation)
        else:
            self.assertRegex(citation, r"(?m)^date-released: '\d{4}-\d{2}-\d{2}'$")
            self.assertIn(f"releases/tag/v{version}", citation)

    def test_release_assets_are_sbomed_and_attested_by_immutable_actions(self):
        workflow = (
            ROOT / ".github/workflows/release-container.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("artifact-metadata: write", workflow)
        self.assertIn("attestations: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn(
            "anchore/sbom-action@e22c389904149dbc22b58101806040fa8d37a610",
            workflow,
        )
        self.assertIn(
            "actions/attest-build-provenance@"
            "0f67c3f4856b2e3261c31976d6725780e5e4c373",
            workflow,
        )
        self.assertIn("subject-checksums: SHA256SUMS", workflow)
        self.assertIn("financial-evidence-${{ github.ref_name }}.cdx.json", workflow)
        self.assertIn("upload-release-assets: false", workflow)


if __name__ == "__main__":
    unittest.main()
