import importlib.util
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("product_plugins", ROOT / "scripts/build_product_plugins.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ProductPluginTests(unittest.TestCase):
    def test_every_published_connection_has_one_plugin(self):
        connections = json.loads((ROOT / "docs/connect/native-connections.json").read_text())
        required = {p["id"] for p in connections["products"]}
        for path in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            catalog = json.loads((ROOT / path).read_text())
            names = [p["name"] for p in catalog["plugins"]]
            self.assertEqual(len(names), len(set(names)))
            self.assertEqual(set(names), required | {"market-brief"})

    def test_downloads_resolve_all_runtime_files_and_exact_endpoints(self):
        catalog = json.loads((ROOT / "docs/plugins/catalog.json").read_text())
        for product in catalog["products"]:
            for platform, download in product["downloads"].items():
                data = (ROOT / "docs/plugins" / download["url"]).read_bytes()
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    names = archive.namelist()
                    self.assertEqual(len(names), len(set(names)))
                    self.assertFalse(any(Path(n).is_absolute() or ".." in Path(n).parts for n in names))
                    self.assertIn(f"skills/{product['id']}/SKILL.md", names)
                    self.assertIn("LICENSE", names)
                    if platform == "openai":
                        plugin = json.loads(archive.read(".codex-plugin/plugin.json"))
                        self.assertEqual(plugin["name"], product["id"])
                        for key in ("logo", "composerIcon"):
                            self.assertIn(plugin["interface"][key].removeprefix("./"), names)
                        mcp = json.loads(archive.read(plugin["mcpServers"].removeprefix("./")))
                        self.assertEqual(mcp, {"mcpServers": {product["id"]: {"type": "http", "url": product["mcp_url"]}}})
                    else:
                        manifest = json.loads(archive.read("gemini-extension.json"))
                        self.assertEqual(set(manifest["mcpServers"]), {product["id"]})
                        server = manifest["mcpServers"][product["id"]]
                        self.assertEqual(server["httpUrl"], product["mcp_url"])
                        self.assertNotIn("trust", server)

    def test_catalog_paths_resolve_without_cross_plugin_dependencies(self):
        catalog = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        for entry in catalog["plugins"][2:]:
            root = ROOT / entry["source"]["path"]
            plugin = json.loads((root / ".codex-plugin/plugin.json").read_text())
            self.assertEqual(plugin["name"], entry["name"])
            self.assertTrue((root / plugin["mcpServers"]).is_file())
            self.assertTrue((root / plugin["skills"]).is_dir())
            self.assertFalse(any(p.is_symlink() for p in root.rglob("*")))

    def test_generated_files_are_reproducible(self):
        for name, expected in builder.build().items():
            self.assertEqual((ROOT / name).read_bytes(), expected, name)


if __name__ == "__main__":
    unittest.main()
