"""Historical context, reusable snippets and package identity; no network access."""
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("newsroom_reuse", ROOT / "scripts/build_newsroom_reuse_kit.py")
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.labels, self.copies, self.textareas = [], set(), set(), [], {}
        self.active_textarea = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "label":
            self.labels.add(values.get("for"))
        if tag == "button" and values.get("data-copy"):
            self.copies.append(values["data-copy"])
        if tag == "textarea":
            self.active_textarea = values["id"]
            self.textareas[self.active_textarea] = ""
        for name in ("href", "src"):
            if values.get(name):
                self.links.append(values[name])

    def handle_endtag(self, tag):
        if tag == "textarea":
            self.active_textarea = None

    def handle_data(self, value):
        if self.active_textarea:
            self.textareas[self.active_textarea] += value


class ReuseKitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix=".reuse-tests-", dir=ROOT)
        cls.output = Path(cls.temp.name) / "output"
        cls.result = kit.build(output=cls.output)
        cls.manifest = json.loads((cls.output / "manifest.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def fixture_repo(self):
        target = Path(self.temp.name) / self._testMethodName
        for relative in ("docs/media/briefs",):
            shutil.copytree(ROOT / relative, target / relative)
        for relative in ("docs/media/rights.html", "docs/media/corrections.html", "docs/media/corrections.json", "docs/funding/sources.md"):
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, dest)
        return target

    def test_archive_is_repeatable_and_every_retained_asset_matches(self):
        other = Path(self.temp.name) / "second"
        second = kit.build(output=other)
        self.assertEqual(self.result["zip_sha256"], second["zip_sha256"])
        bundle = (self.output / kit.KIT_NAME).read_bytes()
        self.assertEqual(hashlib.sha256(bundle).hexdigest(), self.manifest["archive"]["sha256"])
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            self.assertIsNone(archive.testzip())
            checksums = json.loads(archive.read("newsroom-kit/checksums.json"))
            self.assertEqual(set(archive.namelist()), {"newsroom-kit/" + p for p in checksums} | {"newsroom-kit/checksums.json"})
            for name, checksum in checksums.items():
                self.assertEqual(hashlib.sha256(archive.read("newsroom-kit/" + name)).hexdigest(), checksum)
            for edition in self.manifest["editions"]:
                for asset in edition["assets"]:
                    raw = (ROOT / "docs/media/briefs" / edition["id"] / asset["filename"]).read_bytes()
                    self.assertEqual(archive.read("newsroom-kit/" + asset["archive_path"]), raw)
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), asset["sha256"])
                    self.assertTrue(asset["reuse_scope"])

    def test_copyable_fields_exactly_match_the_downloadable_files(self):
        parsed = Page()
        parsed.feed((self.output / "index.html").read_text())
        self.assertEqual(len(parsed.copies), 4)
        self.assertTrue(set(parsed.copies).issubset(parsed.labels))
        for edition in self.manifest["editions"]:
            ident = edition["id"]
            self.assertEqual(parsed.textareas[ident + "-caption"], (self.output / ident / "CAPTION.txt").read_text())
            self.assertEqual(parsed.textareas[ident + "-embed"], (self.output / ident / "embed.html").read_text())
            self.assertIn(edition["published_at"], edition["caption"])
            self.assertIn(edition["source_notice"], edition["caption"])
            self.assertIn("corrections.html", edition["embed"])
            self.assertIn("width=", edition["embed"])
            self.assertIn("height=", edition["embed"])
            self.assertIn("alt=", edition["embed"])

    def test_historical_limits_and_specific_source_notices_survive(self):
        funding, bank = self.manifest["editions"]
        self.assertIn("8 October 2026", funding["caption"])
        self.assertIn("weekly-average reserves dated 7 October", funding["caption"])
        self.assertIn("DTCC Solutions LLC", funding["caption"])
        self.assertIn("not a current market reading", funding["caption"])
        self.assertIn("31 March and 30 June 2026", bank["caption"])
        self.assertIn("31 July 2026", bank["caption"])
        self.assertIn("hash was not independently verified", bank["caption"])
        self.assertIn("No original issuer PDF", bank["caption"])
        self.assertFalse(self.manifest["market_data_refreshed"])

    def test_all_generated_local_and_owned_public_links_resolve(self):
        generated = set(self.result["files_written"])
        for relative in generated:
            if not relative.endswith(".html"):
                continue
            parsed = Page()
            parsed.feed((self.output / relative).read_text())
            for href in parsed.links:
                url = urlparse(href)
                if href.startswith(kit.BASE):
                    path = ROOT / "docs" / unquote(url.path.removeprefix("/financial-evidence-skills/"))
                elif url.scheme or url.netloc:
                    continue
                else:
                    # Resolve in the eventual docs location; generated files may be in temp.
                    path = ROOT / "docs/media/reuse" / Path(relative).parent / unquote(url.path)
                    if not url.path:
                        path = ROOT / "docs/media/reuse" / relative
                path = path.resolve()
                try:
                    generated_relative = str(path.relative_to((ROOT / "docs/media/reuse").resolve()))
                except ValueError:
                    generated_relative = None
                if generated_relative in generated:
                    path = self.output / generated_relative
                if path.is_dir():
                    path /= "index.html"
                with self.subTest(page=relative, target=href):
                    self.assertTrue(path.is_file(), str(path))
                    if url.fragment and path.suffix == ".html":
                        target = Page()
                        target.feed(path.read_text())
                        self.assertIn(unquote(url.fragment), target.ids)

    def test_rejects_external_or_escaping_assets_before_writing(self):
        folder = ROOT / "docs/media/briefs/2026-10-11-dollar-funding"
        for value in ("../rights.html", "https://example.com/data.csv", "%2e%2e/data.csv", "data.json?fresh=1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                kit.local_download(folder, value)

    def test_changed_dates_require_a_caption_review(self):
        repo = self.fixture_repo()
        path = repo / "docs/media/briefs/2026-10-11-dollar-funding/brief.json"
        brief = json.loads(path.read_text())
        brief["observation_dates"] = ["2026-10-10"]
        path.write_text(json.dumps(brief))
        output = repo / "output"
        with self.assertRaisesRegex(ValueError, "caption review"):
            kit.build(repo, output)
        self.assertFalse(output.exists())

    def test_missing_notices_fail_before_writing(self):
        repo = self.fixture_repo()
        (repo / "docs/funding/sources.md").write_text("Missing notice")
        output = repo / "output"
        with self.assertRaisesRegex(ValueError, "source notices"):
            kit.build(repo, output)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
