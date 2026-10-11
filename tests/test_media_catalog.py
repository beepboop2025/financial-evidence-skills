"""Public-edition navigation and feed consistency, without network access."""
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "docs/media"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.ids.add(values.get("id"))
        for field in ("href", "src"):
            if values.get(field):
                self.targets.append(values[field])


class MediaCatalogTests(unittest.TestCase):
    def test_every_local_download_and_link_resolves(self):
        for page in MEDIA.rglob("*.html"):
            parser = Links()
            parser.feed(page.read_text())
            for target in parser.targets:
                url = urlparse(target)
                if url.scheme or url.netloc:
                    continue
                path = page.parent / unquote(url.path) if url.path else page
                if path.is_dir():
                    path /= "index.html"
                with self.subTest(page=page.relative_to(ROOT), target=target):
                    self.assertTrue(path.is_file(), str(path))
                    if url.fragment and path.suffix == ".html":
                        destination = Links()
                        destination.feed(path.read_text())
                        self.assertIn(unquote(url.fragment), destination.ids)

    def test_feed_and_catalog_point_to_the_same_fixed_editions(self):
        catalog = json.loads((MEDIA / "catalog.json").read_text())
        feed = ET.parse(MEDIA / "feed.xml").getroot()
        expected = {item["url"] for item in catalog["editions"]}
        actual = {item.findtext("link") for item in feed.findall("channel/item")}
        self.assertEqual(expected, actual)
        self.assertGreaterEqual(len(expected), 2)
        for item in feed.findall("channel/item"):
            self.assertEqual(item.findtext("guid"), item.findtext("link"))
            self.assertTrue(item.findtext("pubDate"))
            self.assertIn("/media/briefs/", item.findtext("link"))

    def test_catalog_reproduces_retained_metadata(self):
        spec = importlib.util.spec_from_file_location("media_catalog", ROOT / "scripts/build_media_catalog.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        published = json.loads((MEDIA / "catalog.json").read_text())
        self.assertEqual(published["editions"], module.editions())


if __name__ == "__main__":
    unittest.main()
