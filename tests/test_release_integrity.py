"""Release artifacts remain citable, attestable, and reproducible."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseIntegrityTests(unittest.TestCase):
    def test_citation_metadata_tracks_the_candidate_release(self):
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn("cff-version: 1.2.0", citation)
        self.assertIn("version: 0.1.5", citation)
        self.assertIn("date-released: '2026-08-26'", citation)
        self.assertIn("releases/tag/v0.1.5", citation)

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
