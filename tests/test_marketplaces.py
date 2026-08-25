import json
import re
import struct
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACES = ROOT / "docs" / "marketplaces.json"


def _package_version() -> str:
    source = (ROOT / "src/financial_evidence/__init__.py").read_text()
    match = re.search(r'^__version__ = "([^"]+)"$', source, re.MULTILINE)
    if not match:
        raise AssertionError("package version is missing")
    return match.group(1)


class MarketplaceLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = json.loads(MARKETPLACES.read_text())
        self.entries = self.ledger["entries"]
        self.by_id = {entry["id"]: entry for entry in self.entries}

    def test_release_and_observation_clock_are_explicit(self):
        self.assertEqual(self.ledger["version"], _package_version())
        self.assertEqual(self.ledger["release_state"], "candidate")
        self.assertEqual(self.ledger["last_verified_release"], "0.1.4")
        checked_at = self.ledger["checked_at"]
        self.assertTrue(checked_at.endswith("Z"))
        datetime.fromisoformat(checked_at.removesuffix("Z") + "+00:00")

    def test_ids_are_unique_and_states_are_defined(self):
        ids = [entry["id"] for entry in self.entries]
        self.assertEqual(len(ids), len(set(ids)))
        states = set(self.ledger["state_definitions"])
        for entry in self.entries:
            self.assertIn(entry["state"], states)
            self.assertTrue(entry["detail"])
            self.assertTrue(entry["next_action"])
            self.assertTrue(entry["cost"])

    def test_urls_and_receipt_boundaries(self):
        for entry in self.entries:
            urls = [
                entry[key]
                for key in ("listing_url", "submission_url")
                if key in entry
            ]
            self.assertTrue(urls, entry["id"])
            for url in urls:
                parsed = urlparse(url)
                self.assertEqual(parsed.scheme, "https", url)
                self.assertTrue(parsed.netloc, url)
            if entry["state"] in {"live", "listed_incomplete"}:
                self.assertIn("listing_url", entry)
            if entry["state"] == "submitted":
                self.assertIn("submission_url", entry)

    def test_key_channels_preserve_truthful_states(self):
        self.assertEqual(self.by_id["official-mcp-registry"]["state"], "live")
        self.assertEqual(self.by_id["skills-sh"]["state"], "live")
        self.assertEqual(self.by_id["glama"]["state"], "listed_incomplete")
        self.assertEqual(self.by_id["awesome-openbb"]["state"], "submitted")
        self.assertEqual(
            self.by_id["awesome-copilot"]["state"],
            "closed_unmerged",
        )
        self.assertEqual(
            self.by_id["openai-plugin-directory"]["state"],
            "release_gated_owner_action",
        )
        self.assertEqual(
            self.by_id["gemini-cli-extension-gallery"]["state"],
            "eligible_automatic",
        )
        self.assertEqual(self.by_id["mcp-so"]["state"], "skipped_paid")

    def test_marketplace_assets_exist(self):
        self.assertTrue((ROOT / "llms-install.md").is_file())
        self.assertTrue((ROOT / "assets" / "logo.svg").is_file())
        self.assertTrue((ROOT / "assets" / "logo-400.png").is_file())

        logo = (ROOT / "assets" / "logo-400.png").read_bytes()
        self.assertEqual(logo[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", logo[16:24])
        self.assertEqual((width, height), (400, 400))

    def test_openai_owner_gates_remain_explicit(self):
        packet = (ROOT / "OPENAI_PLUGIN_SUBMISSION.md").read_text()
        demo = (ROOT / "OPENAI_DEMO_RECORDING.md").read_text()
        privacy = (ROOT / "docs" / "privacy" / "index.html").read_text()

        self.assertIn("Demo recording: not yet recorded", packet)
        self.assertIn("public logo and release URL are release-gated", packet)
        self.assertIn("both ChatGPT and Codex", demo)
        self.assertIn("does not persist topic request bodies", privacy)
        self.assertIn("no later than 30 days", privacy)


if __name__ == "__main__":
    unittest.main()
