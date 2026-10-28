import importlib.util
import io
import copy
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

    def test_review_cases_match_discovered_tools_and_packaged_manifests(self):
        metadata = json.loads((ROOT / "integrations/openai/product-review.json").read_text())["products"]
        inventory = {row["id"]: row for row in json.loads(
            (ROOT / "docs/plugins/review-tool-inventory-20261028.json").read_text()
        )["products"]}
        for slug in metadata:
            item = builder.review_metadata(slug, metadata, inventory)
            manifest = json.loads((ROOT / f"plugins/{slug}/.codex-plugin/plugin.json").read_text())
            self.assertEqual(manifest["version"], "1.0.2")
            self.assertEqual(manifest["interface"]["defaultPrompt"], item["defaultPrompt"])
            review = manifest["extensions"]["com.openai"]["review"]
            self.assertEqual(review["test_cases"], {"positive": item["positive"], "negative": item["negative"]})
            self.assertFalse(review["commerce"])
            self.assertNotIn("demo_recording_url", review)
            self.assertNotIn("review", manifest["interface"])

    def test_invalid_review_counts_and_undiscovered_tools_fail_the_build(self):
        metadata = json.loads((ROOT / "integrations/openai/product-review.json").read_text())["products"]
        inventory = {row["id"]: row for row in json.loads(
            (ROOT / "docs/plugins/review-tool-inventory-20261028.json").read_text()
        )["products"]}
        invalid = copy.deepcopy(metadata)
        invalid["seiche"]["positive"][0]["tools_triggered"] = "place_private_order"
        with self.assertRaisesRegex(ValueError, "Undiscovered review tool"):
            builder.review_metadata("seiche", invalid, inventory)
        invalid = copy.deepcopy(metadata)
        invalid["seiche"]["negative"].pop()
        with self.assertRaisesRegex(ValueError, "five positive and three negative"):
            builder.review_metadata("seiche", invalid, inventory)
        invalid = copy.deepcopy(metadata)
        invalid["seiche"]["positive"][0]["expected_behavior"] = ""
        with self.assertRaisesRegex(ValueError, "Empty positive review field"):
            builder.review_metadata("seiche", invalid, inventory)

    def test_metadata_only_review_does_not_invent_app_access_or_assessment_inputs(self):
        metadata = json.loads((ROOT / "integrations/openai/product-review.json").read_text())["products"]
        app_tools = {case["tools_triggered"] for case in metadata["myquant-app"]["positive"]}
        self.assertLessEqual(app_tools, {"list_capabilities", "get_health"})
        sandbox_tools = {case["tools_triggered"] for case in metadata["trade-safety"]["positive"]}
        self.assertEqual(sandbox_tools, {"trade_safety_capabilities"})

    def test_every_generated_manifest_meets_public_submission_limits(self):
        generated = builder.build()
        for path, body in generated.items():
            if path.endswith("/.codex-plugin/plugin.json"):
                manifest = json.loads(body)
                builder.validate_submission_metadata(manifest)
                self.assertLessEqual(len(manifest["interface"]["shortDescription"]), 30)

    def test_public_listing_text_boundaries_are_enforced(self):
        manifest = json.loads((ROOT / "plugins/liquilens/.codex-plugin/plugin.json").read_text())
        for field, maximum in (("displayName", 30), ("shortDescription", 30),
                               ("longDescription", 4000), ("developerName", 80)):
            with self.subTest(field=field):
                candidate = copy.deepcopy(manifest)
                candidate["interface"][field] = "x" * maximum
                builder.validate_submission_metadata(candidate)
                candidate["interface"][field] += "x"
                with self.assertRaisesRegex(ValueError, field):
                    builder.validate_submission_metadata(candidate)
        candidate = copy.deepcopy(manifest)
        candidate["interface"]["defaultPrompt"] = ["x" * 128]
        builder.validate_submission_metadata(candidate)
        candidate["interface"]["defaultPrompt"] = ["x" * 129]
        with self.assertRaisesRegex(ValueError, "defaultPrompt"):
            builder.validate_submission_metadata(candidate)

    def test_listing_links_and_prompt_rules_fail_before_archive_generation(self):
        manifest = json.loads((ROOT / "plugins/liquilens/.codex-plugin/plugin.json").read_text())
        for field in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
            candidate = copy.deepcopy(manifest)
            candidate["interface"][field] = "https://name:secret@example.com"
            with self.assertRaisesRegex(ValueError, field):
                builder.validate_submission_metadata(candidate)
        for prompts in (["same", "same"], ["one", "two", "three", "four"], ["Ask @example"]):
            candidate = copy.deepcopy(manifest)
            candidate["interface"]["defaultPrompt"] = prompts
            with self.assertRaisesRegex(ValueError, "defaultPrompt"):
                builder.validate_submission_metadata(candidate)


if __name__ == "__main__":
    unittest.main()
