import copy
import importlib.util
import json
import struct
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "integrations/copilot-studio"
spec = importlib.util.spec_from_file_location("copilot_studio", ROOT / "scripts/build_copilot_studio_connectors.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def _json(path):
    return json.loads(Path(path).read_text())


class CopilotStudioConnectorTests(unittest.TestCase):
    def setUp(self):
        self.catalog = _json(BASE / "connectors.json")
        self.receipt = _json(BASE / self.catalog["verification_receipt"])
        self.observed = {row["id"]: row for row in self.receipt["connectors"]}

    def test_generated_files_are_reproducible(self):
        for name, expected in builder.build().items():
            self.assertEqual((ROOT / name).read_bytes(), expected, name)

    def test_each_definition_is_one_anonymous_streamable_mcp_operation(self):
        for entry in self.catalog["connectors"]:
            folder = BASE / entry["id"]
            swagger = _json(folder / "apiDefinition.swagger.json")
            properties = _json(folder / "apiProperties.json")["properties"]
            remote = urlsplit(entry["remote_url"])
            self.assertEqual(swagger["swagger"], "2.0")
            self.assertEqual(swagger["schemes"], ["https"])
            self.assertEqual((swagger["host"], swagger["basePath"]), (remote.hostname, "/"))
            self.assertEqual(list(swagger["paths"]), [remote.path])
            operations = swagger["paths"][remote.path]
            self.assertEqual(list(operations), ["post"])
            operation = operations["post"]
            self.assertEqual(operation["x-ms-agentic-protocol"], "mcp-streamable-1.0")
            self.assertEqual(operation["operationId"], "InvokeMCP")
            self.assertIn(operation["x-ms-visibility"], {"important", "advanced", "internal"})
            self.assertEqual(swagger["securityDefinitions"], {})
            self.assertEqual(swagger["security"], [])
            self.assertEqual(properties["connectionParameters"], {})
            self.assertNotIn("stackOwner", properties)
            self.assertNotIn(properties["iconBrandColor"].lower(), {"#ffffff", "#007ee5"})
            accept = operation["parameters"][0]
            self.assertEqual((accept["name"], accept["in"], accept["x-ms-visibility"]),
                             ("Accept", "header", "internal"))
            self.assertIn("text/event-stream", accept["default"])
            text = json.dumps(swagger) + json.dumps(properties)
            for marker in ("api_key", "apiKey", "Authorization", "Bearer", "token", "secret"):
                self.assertNotIn(marker, text, entry["id"])

    def test_text_meets_connector_certification_limits(self):
        for entry in self.catalog["connectors"]:
            operation = next(iter(_json(BASE / entry["id"] / "apiDefinition.swagger.json")["paths"].values()))["post"]
            builder.validate_text(entry["title"], entry["description"], operation["summary"], operation["description"])
        good = self.catalog["connectors"][0]
        for field, value in (("title", "LiquiLens API"), ("title", "x" * 31), ("title", "Seiche MCP."),
                             ("description", "Too short."), ("description", "Use in Power Automate. " * 3),
                             ("description", "x" * 500), ("description", ("Research " + chr(0x2014) + " not advice. ") * 3)):
            candidate = copy.deepcopy(good)
            candidate[field] = value
            with self.subTest(field=field, value=value[:20]), self.assertRaises(ValueError):
                builder.validate_text(candidate["title"], candidate["description"], "LiquiLens MCP server",
                                      "Sends messages.")
        with self.assertRaises(ValueError):
            builder.validate_text(good["title"], good["description"], "LiquiLens MCP server - v1", "Sends messages.")
        with self.assertRaises(ValueError):
            builder.validate_text(good["title"], good["description"], "LiquiLens MCP server", "No final punctuation")

    def test_every_connector_matches_the_dated_registry_and_live_check(self):
        self.assertEqual({entry["id"] for entry in self.catalog["connectors"]}, set(self.observed))
        self.assertFalse(self.receipt["copilot_studio_tenant_import_tested"])
        for entry in self.catalog["connectors"]:
            row = self.observed[entry["id"]]
            self.assertEqual(row["status"], "ok")
            self.assertEqual(row["url"], entry["remote_url"])
            self.assertEqual(row["http_status"], 200)
            self.assertEqual(row["registry"]["name"], entry["registry_name"])
            self.assertEqual(row["registry"]["remote_url"], entry["remote_url"])
            self.assertEqual(row["registry"]["remote_type"], "streamable-http")
            self.assertTrue(row["registry"]["is_latest"])
            self.assertTrue(row["tools"])
            self.assertTrue(set(row["copilot_studio_schema_findings"]) <= set(row["tools"]))

    def test_documented_limitations_match_the_receipt(self):
        findings = {key: row["copilot_studio_schema_findings"] for key, row in self.observed.items()}
        bounded = [tool for tool, issues in findings["noisefloor"].items()
                   if any(issue.startswith("integer exclusive") for issue in issues)]
        self.assertEqual((len(bounded), len(self.observed["noisefloor"]["tools"])), (9, 10))
        self.assertEqual(sorted(set(self.observed["noisefloor"]["tools"]) - set(bounded)), ["dyson_reference"])
        self.assertEqual([tool for tool, issues in findings["undertow"].items()
                          if "integer exclusiveMinimum" in issues], ["exit_cost"])
        groundcheck = next(e for e in self.catalog["connectors"] if e["id"] == "groundcheck")
        paid = ("check_citations", "resolve_instrument", "extract_claims", "attest_delivery")
        self.assertEqual(set(paid) | {"verify_claim"}, set(self.observed["groundcheck"]["tools"]))
        self.assertTrue(all(name in groundcheck["limitations"][0] for name in paid))

    def test_claude_direct_remote_plugins_use_the_same_registry_remote(self):
        remotes = {entry["id"]: entry["remote_url"] for entry in self.catalog["connectors"]}
        marketplace = {p["name"]: p for p in _json(ROOT / ".claude-plugin/marketplace.json")["plugins"]}
        for slug in ("groundcheck", "data-breach-detector"):
            root = ROOT / "plugins" / slug
            self.assertEqual(_json(root / ".mcp.json"),
                             {"mcpServers": {slug: {"type": "http", "url": remotes[slug]}}})
            manifest = _json(root / ".claude-plugin/plugin.json")
            self.assertEqual(manifest["name"], slug)
            self.assertEqual(marketplace[slug]["source"], f"./plugins/{slug}")
            self.assertEqual(marketplace[slug]["version"], manifest["version"])
            skill = (root / "skills" / slug / "SKILL.md").read_text()
            self.assertIn(remotes[slug], skill)
            gemini = _json(root / "gemini-extension.json")
            self.assertEqual((gemini["name"], gemini["version"]), (slug, manifest["version"]))
            self.assertEqual(gemini["mcpServers"][slug]["httpUrl"], remotes[slug])
            self.assertEqual(gemini["mcpServers"][slug]["includeTools"], self.observed[slug]["tools"])
            self.assertNotIn("trust", gemini["mcpServers"][slug])
            self.assertFalse((root / ".codex-plugin").exists())
            self.assertFalse(any(p.is_symlink() for p in root.rglob("*")))
        self.assertIn("Never pay", (ROOT / "plugins/groundcheck/skills/groundcheck/SKILL.md").read_text())

    def test_claude_guide_lists_every_registry_remote(self):
        guide = (ROOT / "docs/platforms/claude-connectors.md").read_text()
        readme = (BASE / "README.md").read_text()
        for entry in self.catalog["connectors"]:
            self.assertIn(f"`{entry['remote_url']}`", guide)
            self.assertIn(f"`{entry['remote_url']}`", readme)
        self.assertNotIn("riptide", guide.lower())

    def test_shared_icon_meets_certification_dimensions(self):
        data = (BASE / self.catalog["icon"]).read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height, _, color_type = struct.unpack(">IIBB", data[16:26])
        self.assertEqual(width, height)
        self.assertTrue(100 <= width <= 230)
        self.assertEqual(color_type, 2)  # RGB without alpha: no transparent background

    def test_packaged_text_has_no_en_or_em_dashes(self):
        paths = [ROOT / "docs/platforms/claude-connectors.md", ROOT / "scripts/build_copilot_studio_connectors.py"]
        paths += [p for p in BASE.rglob("*") if p.suffix in {".md", ".json"}]
        for slug in ("groundcheck", "data-breach-detector"):
            paths += [p for p in (ROOT / "plugins" / slug).rglob("*") if p.suffix in {".md", ".json"}]
        for path in paths:
            text = path.read_text()
            self.assertNotIn(chr(0x2014), text, path)
            self.assertNotIn(chr(0x2013), text, path)


if __name__ == "__main__":
    unittest.main()
