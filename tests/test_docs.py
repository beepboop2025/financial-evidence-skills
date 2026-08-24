import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.hrefs: list[str] = []
        self.assets: list[str] = []
        self.jsonld: list[str] = []
        self._capture_jsonld = False

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            if element_id in self.ids:
                raise AssertionError(f"duplicate HTML id: {element_id}")
            self.ids.add(element_id)
        if tag == "a" and (href := attributes.get("href")):
            self.hrefs.append(href)
        if tag == "script" and (src := attributes.get("src")):
            self.assets.append(src)
        if tag == "link" and (href := attributes.get("href")):
            self.assets.append(href)
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._capture_jsonld = True
            self.jsonld.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._capture_jsonld = False

    def handle_data(self, data: str) -> None:
        if self._capture_jsonld:
            self.jsonld[-1] += data


def _package_version() -> str:
    source = (ROOT / "src/financial_evidence/__init__.py").read_text()
    match = re.search(r'^__version__ = "([^"]+)"$', source, re.MULTILINE)
    if not match:
        raise AssertionError("package version is missing")
    return match.group(1)


class DiscoveryDocsTests(unittest.TestCase):
    def test_machine_readable_manifest_tracks_release(self):
        manifest = json.loads((DOCS / "integrations.json").read_text())
        self.assertEqual(manifest["version"], _package_version())
        self.assertFalse(manifest["account_required"])
        self.assertFalse(manifest["api_key_required"])
        self.assertFalse(manifest["write_actions"])
        self.assertEqual(len(manifest["products"]), 4)
        self.assertEqual(len(manifest["topics"]), 5)
        self.assertEqual(len(manifest["interfaces"]), 11)
        agent_skill = next(
            interface
            for interface in manifest["interfaces"]
            if interface["kind"] == "agent-skill"
        )
        self.assertEqual(agent_skill["identifier"], "financial-evidence")
        self.assertEqual(agent_skill["activation_topics"], manifest["topics"])
        self.assertEqual(agent_skill["status"], "public")

    def test_html_jsonld_fragments_and_local_links(self):
        page = DOCS / "index.html"
        parser = _PageParser()
        parser.feed(page.read_text())
        self.assertEqual(len(parser.jsonld), 1)
        metadata = json.loads(parser.jsonld[0])
        self.assertEqual(metadata["@type"], "SoftwareApplication")
        self.assertEqual(metadata["softwareVersion"], _package_version())
        self.assertTrue(metadata["isAccessibleForFree"])

        for href in parser.hrefs:
            if href.startswith("#"):
                self.assertIn(href[1:], parser.ids)
                continue
            parsed = urlparse(href)
            if not parsed.scheme and not parsed.netloc:
                candidate = page.parent / parsed.path
                if candidate.is_dir():
                    candidate /= "index.html"
                self.assertTrue(candidate.is_file(), href)

    def test_fdc3_runtime_page_and_record(self):
        page = DOCS / "integrations" / "fdc3" / "evidence-inspector" / "index.html"
        parser = _PageParser()
        parser.feed(page.read_text())
        self.assertIn("inspector", parser.ids)
        self.assertIn("routes", parser.ids)
        self.assertIn("app.js", parser.assets)
        self.assertIn("styles.css", parser.assets)

        for reference in parser.hrefs + parser.assets:
            parsed = urlparse(reference)
            if parsed.scheme or parsed.netloc or reference.startswith("#"):
                continue
            candidate = page.parent / parsed.path
            if candidate.is_dir():
                candidate /= "index.html"
            self.assertTrue(candidate.is_file(), reference)

        canonical_record = ROOT / "integrations/fdc3/appd-record.json"
        published_record = DOCS / "integrations/fdc3/appd-record.json"
        self.assertEqual(published_record.read_bytes(), canonical_record.read_bytes())
        record = json.loads(canonical_record.read_text())
        self.assertEqual(record["appId"], "financial-evidence-inspector")
        self.assertEqual(record["name"], record["appId"])
        self.assertEqual(
            record["details"]["url"],
            "https://beepboop2025.github.io/financial-evidence-skills/integrations/fdc3/evidence-inspector/",
        )
        self.assertNotIn("publisher", record)
        self.assertEqual(
            record["interop"]["userChannels"]["broadcasts"],
            record["interop"]["userChannels"]["listensFor"],
        )
        self.assertEqual(
            record["interop"]["intents"]["listensFor"]["ViewInstrument"]["contexts"],
            ["fdc3.instrument"],
        )
        manifest = json.loads((DOCS / "integrations.json").read_text())
        fdc3 = next(
            interface for interface in manifest["interfaces"] if interface["kind"] == "fdc3-web-app"
        )
        self.assertEqual(
            fdc3["app_directory_record"],
            "https://beepboop2025.github.io/financial-evidence-skills/integrations/fdc3/appd-record.json",
        )

    def test_agent_discovery_files_state_boundaries(self):
        llms = (DOCS / "llms.txt").read_text()
        pricing = (DOCS / "pricing.md").read_text()
        robots = (DOCS / "robots.txt").read_text()
        for topic in (
            "money-market",
            "capital-market",
            "china-economy",
            "bank-risk",
            "market-liquidity",
        ):
            self.assertIn(topic, llms)
        self.assertIn("Price: USD 0", pricing)
        self.assertIn("source publishers retain rights", llms.lower())
        self.assertIn("npx skills add beepboop2025/financial-evidence-skills", llms)
        self.assertIn("Allow: /", robots)
        self.assertIn("sitemap.xml", robots)

    def test_indexnow_key_and_workflow_stay_synchronized(self):
        key = "82f75882dbd36fa818fdb25735425b6f"
        workflow = (ROOT / ".github/workflows/indexnow.yml").read_text()
        self.assertEqual((DOCS / f"{key}.txt").read_text().strip(), key)
        self.assertGreaterEqual(workflow.count(key), 2)
        self.assertIn("https://api.indexnow.org/indexnow", workflow)
        self.assertIn("keyLocation", workflow)


if __name__ == "__main__":
    unittest.main()
