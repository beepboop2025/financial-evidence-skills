"""The uploaded wheel must advertise its own supported installation and guide."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_pypi_metadata", ROOT / "scripts/verify_pypi_metadata.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class PyPIMetadataTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.project = {
            "name": "financial-evidence", "version": "0.1.12",
            "description": "Financial evidence for agents",
            "readme": "PYPI_README.md",
            "urls": {"Source": "https://github.com/beepboop2025/financial-evidence-skills"},
        }

    def verify(self, wheel):
        return verifier.verify_metadata(
            wheel, project=self.project, readme_path=self.root / "PYPI_README.md",
        )

    def wheel(self, description, *, readme=None, version="0.1.12"):
        (self.root / "PYPI_README.md").write_text(
            description if readme is None else readme, encoding="utf-8",
        )
        wheel = self.root / f"financial_evidence-{version}-py3-none-any.whl"
        metadata = (
            f"Metadata-Version: 2.4\nName: financial-evidence\nVersion: {version}\n"
            "Summary: Financial evidence for agents\nDescription-Content-Type: text/markdown\n\n"
            + description
        )
        with ZipFile(wheel, "w") as archive:
            archive.writestr(f"financial_evidence-{version}.dist-info/METADATA", metadata)
        return wheel

    def test_original_release_with_stale_self_install_is_rejected(self):
        for requirement in ("financial-evidence==0.1.11", "financial-evidence[workspace]==0.1.11"):
            with self.subTest(requirement=requirement):
                wheel = self.wheel(f"python3 -m pip install '{requirement}'\n")
                with self.assertRaisesRegex(ValueError, "installation pin 0.1.11.*0.1.12"):
                    self.verify(wheel)

    def test_old_current_package_guide_is_rejected(self):
        for base in (
            "https://github.com/beepboop2025/financial-evidence-skills/blob/",
            "https://raw.githubusercontent.com/beepboop2025/financial-evidence-skills/",
        ):
            with self.subTest(base=base):
                wheel = self.wheel(f"[First review]({base}v0.1.11/docs/agents/FIRST_REVIEW.md)\n")
                with self.assertRaisesRegex(ValueError, "guide version 0.1.11.*0.1.12"):
                    self.verify(wheel)

    def test_latest_and_matching_install_commands_are_valid(self):
        wheel = self.wheel("""# Financial Evidence — Python research
python3 -m pip install --upgrade financial-evidence
python3 -m pip install --upgrade 'financial-evidence[workspace]'
uvx --from financial-evidence financial-evidence mcp
python3 -m pip install financial-evidence==0.1.12
python3 -m pip install 'Financial_Evidence[workspace,openbb] == 0.1.12'
[Guide](https://github.com/beepboop2025/financial-evidence-skills/blob/v0.1.12/docs/agents/FIRST_REVIEW.md)
[Current](https://github.com/beepboop2025/financial-evidence-skills/blob/main/docs/start/agent-workflows.md)
""")
        result = self.verify(wheel)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["version"], "0.1.12")

    def test_other_packages_and_historical_release_notes_are_not_current_guides(self):
        wheel = self.wheel("""python3 -m pip install unrelated-financial-evidence==0.0.1
[History](https://github.com/beepboop2025/financial-evidence-skills/releases/tag/v0.1.11)
[Other guide](https://github.com/example/another-project/blob/v0.1.11/docs/start.md)
""")
        self.assertEqual(self.verify(wheel)["status"], "PASS")

    def test_wheel_must_contain_the_configured_readme(self):
        wheel = self.wheel("Old package description\n", readme="Corrected source description\n")
        with self.assertRaisesRegex(ValueError, "description differs from configured README"):
            self.verify(wheel)

    def test_metadata_serialization_can_normalize_line_endings(self):
        wheel = self.wheel("# Research\r\n\r\nSave evidence.\r\n", readme="# Research\n\nSave evidence.\n\n")
        self.assertEqual(self.verify(wheel)["status"], "PASS")

    def test_stale_wheel_cannot_be_checked_against_a_new_source_version(self):
        wheel = self.wheel("Install financial-evidence\n", version="0.1.11")
        with self.assertRaisesRegex(ValueError, "wheel Version differs"):
            self.verify(wheel)


if __name__ == "__main__":
    unittest.main()
