"""Public-edition navigation and feed consistency, without network access."""
import importlib.util
from datetime import timezone
from email.utils import format_datetime
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "docs/media"
SPEC = importlib.util.spec_from_file_location("media_catalog", ROOT / "scripts/build_media_catalog.py")
catalog_builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog_builder)


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
        actual = {item.findtext("link") for item in feed.findall("channel/item") if item.findtext("category") == "edition"}
        self.assertEqual(expected, actual)
        self.assertGreaterEqual(len(expected), 2)
        for item in feed.findall("channel/item"):
            self.assertEqual(item.findtext("guid"), item.findtext("link"))
            self.assertTrue(item.findtext("pubDate"))
        event_links = {item["url"] for item in catalog["corrections"]}
        self.assertEqual(event_links, {item.findtext("link") for item in feed.findall("channel/item") if item.findtext("category") != "edition"})

    def test_catalog_reproduces_retained_metadata(self):
        published = json.loads((MEDIA / "catalog.json").read_text())
        self.assertEqual(published["editions"], catalog_builder.editions())
        self.assertEqual(published["corrections"], catalog_builder.corrections(published["editions"])[1])

    def test_hub_retains_chart_previews_and_reuse_route(self):
        page = (MEDIA / "index.html").read_text()
        self.assertEqual(page.count('class="edition-preview"'), len(catalog_builder.editions()))
        self.assertIn('href="reuse/"', page)


class CorrectionFeedTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.media = Path(temporary.name) / "media"
        shutil.copytree(MEDIA, self.media)
        replacement = patch.object(catalog_builder, "MEDIA", self.media)
        replacement.start()
        self.addCleanup(replacement.stop)
        self.items = catalog_builder.editions()
        self.edition = next(item for item in self.items if item['id'] == '2026-10-11-dollar-funding')
        self.event = {
            "id": "2026-10-12-funding-unit",
            "edition_id": self.edition["id"],
            "kind": "correction",
            "published_at": "2026-10-12T10:00:00Z",
            "summary": "Synthetic test correction: units & <labels> are literal text.",
            "notice_anchor": "correction-unit",
        }
        self.page = self.media / "briefs" / self.edition["id"] / "index.html"
        self.page.write_text(self.page.read_text().replace('</main>', '<aside id="correction-unit">Synthetic test notice.</aside></main>'))

    def write_log(self, entries, **changes):
        log = {"schema": "liquilens.media.corrections.v1", "updated_at": "2026-10-13", "records": entries, **changes}
        (self.media / "corrections.json").write_text(json.dumps(log))

    def outputs(self):
        return {name: (self.media / name).read_bytes() for name in ("catalog.json", "feed.xml", "corrections.html", "index.html")}

    def test_correction_has_distinct_identity_without_redating_the_edition(self):
        self.write_log([self.event])
        original_page = self.page.read_bytes()
        catalog_builder.build()
        built = json.loads((self.media / "catalog.json").read_text())
        self.assertEqual(built["editions"], self.items)
        self.assertEqual(self.page.read_bytes(), original_page)
        feed = ET.parse(self.media / "feed.xml").findall("channel/item")
        editions = {node.findtext("link"): node for node in feed if node.findtext("category") == "edition"}
        for edition in self.items:
            self.assertEqual(editions[edition["url"]].findtext("pubDate"), format_datetime(catalog_builder.timestamp(edition["published_at"]).astimezone(timezone.utc)))
            self.assertEqual(editions[edition["url"]].findtext("guid"), edition["url"])
        event = feed[0]
        expected_url = catalog_builder.BASE + "corrections.html#" + self.event["id"]
        self.assertEqual(event.findtext("category"), "correction")
        self.assertEqual(event.findtext("guid"), expected_url)
        self.assertEqual(event.findtext("link"), expected_url)
        self.assertEqual(event.findtext("pubDate"), "Mon, 12 Oct 2026 10:00:00 +0000")
        self.assertNotIn(expected_url, editions)
        self.assertIn("&lt;labels&gt;", event.findtext("description"))
        self.assertIn(self.edition["url"] + "#correction-unit", event.findtext("description"))
        page = (self.media / "corrections.html").read_text()
        parsed = Links()
        parsed.feed(page)
        self.assertIn(self.event["id"], parsed.ids)
        self.assertNotIn("No corrections have been recorded", page)
        self.assertNotIn("<labels>", page)

    def test_multiple_notices_for_same_edition_are_distinct_and_rebuilds_are_stable(self):
        revision = {**self.event, "id": "2026-10-13-publisher-revision", "kind": "source_revision", "published_at": "2026-10-13T10:00:00+01:00"}
        self.write_log([self.event, revision])
        retained_log = (self.media / "corrections.json").read_bytes()
        catalog_builder.build()
        first = self.outputs()
        catalog_builder.build()
        self.assertEqual(first, self.outputs())
        self.assertEqual(retained_log, (self.media / "corrections.json").read_bytes())
        feed = ET.parse(self.media / "feed.xml").findall("channel/item")
        self.assertEqual(len(feed), len(self.items) + 2)
        self.assertEqual(len({item.findtext("guid") for item in feed}), len(feed))
        self.assertEqual(feed[0].findtext("category"), "source_revision")
        self.assertTrue(feed[0].findtext("title").startswith("Source revision: "))
        self.assertEqual(feed[0].findtext("pubDate"), "Tue, 13 Oct 2026 09:00:00 +0000")

    def test_empty_log_has_no_synthetic_correction_events(self):
        self.write_log([])
        catalog_builder.build()
        feed = ET.parse(self.media / "feed.xml").findall("channel/item")
        self.assertEqual(len(feed), len(self.items))
        self.assertEqual({item.findtext("category") for item in feed}, {"edition"})
        self.assertIn("No corrections have been recorded as of 13 October 2026", (self.media / "corrections.html").read_text())

    def test_invalid_event_fails_before_any_generated_output_changes(self):
        changes = [
            {"id": "../escape"}, {"id": "bad#fragment"}, {"id": "MixedCase"}, {"id": None}, {"id": "main"},
            {"edition_id": "not-a-published-edition"}, {"edition_id": "../escape"},
            {"kind": "new_capture"}, {"kind": "new_period"}, {"kind": []},
            {"published_at": "2026-10-12"}, {"published_at": "2026-10-12T10:00:00"},
            {"published_at": "2026-10-12T99:00:00Z"}, {"published_at": "2026-10-10T10:00:00Z"},
            {"published_at": "2026-10-14T10:00:00Z"},
            {"summary": "  "}, {"summary": None}, {"summary": "Invalid\x00text"},
            {"notice_anchor": "missing-notice"}, {"notice_anchor": "../escape"},
        ]
        before = self.outputs()
        for change in changes:
            with self.subTest(change=change):
                self.write_log([{**self.event, **change}])
                with self.assertRaises(ValueError):
                    catalog_builder.build()
                self.assertEqual(before, self.outputs())

    def test_duplicate_event_ids_are_rejected(self):
        self.write_log([self.event, self.event])
        with self.assertRaisesRegex(ValueError, "Duplicate correction ID"):
            catalog_builder.build()

    def test_invalid_log_structure_is_rejected(self):
        for change in ({"schema": "unknown"}, {"updated_at": "today"}, {"updated_at": "2026-99-99"}, {"records": {}}, {"records": [None]}):
            with self.subTest(change=change):
                self.write_log([], **change)
                with self.assertRaises(ValueError):
                    catalog_builder.build()

    def test_invalid_edition_identifier_is_rejected(self):
        metadata = self.page.parent / "brief.json"
        item = json.loads(metadata.read_text())
        item["id"] = "../outside"
        metadata.write_text(json.dumps(item))
        with self.assertRaisesRegex(ValueError, "Invalid edition ID"):
            catalog_builder.build()


if __name__ == "__main__":
    unittest.main()
