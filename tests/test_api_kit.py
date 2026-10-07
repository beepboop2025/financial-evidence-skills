"""Protect the public import boundary and reproduce the downloadable API kit."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.parse import urlsplit
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "docs/api"


class ApiKitTests(unittest.TestCase):
    def test_imports_only_read_the_published_contract(self):
        spec = json.loads((API / "openapi.json").read_text())
        collection = json.loads((API / "financial-evidence.postman_collection.json").read_text())
        self.assertEqual(spec["servers"][0]["url"], "https://api.seiche.info/openbb")
        for item in collection["item"]:
            request = item["request"]
            self.assertEqual(request["method"], "GET")
            self.assertEqual(request["auth"]["type"], "noauth")
            path = urlsplit(request["url"].replace("{{base_url}}", "https://example.test")).path
            self.assertIn("get", spec["paths"][path])
            self.assertNotIn("body", request)
            self.assertNotIn("prerequest", [e["listen"] for e in item["event"]])
            self.assertLessEqual(int(dict(p.split("=") for p in urlsplit(request["url"]).query.split("&") if "=" in p).get("limit", "0")), 5)

    def test_download_manifest_matches_every_archived_asset(self):
        manifest = json.loads((API / "manifest.json").read_text())
        with ZipFile(API / "api-kit.zip") as archive:
            self.assertEqual(set(archive.namelist()), {*manifest["files"], "manifest.json"})
            for name, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((API / name).read_bytes()).hexdigest(), digest)
                self.assertEqual(archive.read(name), (API / name).read_bytes())

    def test_build_is_reproducible_and_rejects_wrong_origin(self):
        module_spec = importlib.util.spec_from_file_location("api_kit", ROOT / "scripts/build_api_kit.py")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for name in ("openapi.json", "README.md"):
                shutil.copyfile(API / name, out / name)
            module.build(out)
            self.assertEqual((out / "api-kit.zip").read_bytes(), (API / "api-kit.zip").read_bytes())
            spec = json.loads((out / "openapi.json").read_text())
            spec["servers"][0]["url"] = "/openbb"
            (out / "openapi.json").write_text(json.dumps(spec))
            with self.assertRaises(ValueError):
                module.build(out)
