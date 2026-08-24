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
        self.assertEqual(len(manifest["interfaces"]), 8)

    def test_html_jsonld_fragments_and_local_links(self):
        parser = _PageParser()
        parser.feed((DOCS / "index.html").read_text())
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
                self.assertTrue((DOCS / parsed.path).is_file(), href)

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
