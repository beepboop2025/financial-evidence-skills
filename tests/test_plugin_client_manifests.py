"""Every client manifest of the LiquiLens, Seiche and LiquiLens Undertow plugins against one table.

docs/plugins/client-manifests.json names each product's plugin version, its MCP Registry
URL (canonical on new surfaces) and its gateway alias (kept where a directory submission
uses it), and lists every manifest with the URL kind it must carry. These tests parse each
manifest, check its name, version and URL against that table, and hold each file to its
client's published format: Agent Plugins 1.0.0, Google Antigravity's plugin schema and the
Devin marketplace folder rules.
"""
from __future__ import annotations

import base64
import copy
import html
import importlib.util
import io
import json
import re
import unittest
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("product_plugins_clients", ROOT / "scripts/build_product_plugins.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

TABLE = json.loads((ROOT / "docs/plugins/client-manifests.json").read_text())
PRODUCTS = {row["id"]: row for row in TABLE["products"]}
SNAPSHOT = json.loads((ROOT / "docs/plugins" / TABLE["registry_snapshot"]).read_text())
DASHES = re.compile("[\u2013\u2014]")
INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
# Claim discipline for anything that ships (portfolio policy, section 6).
FORBIDDEN = re.compile(r"\bpredict(?:s|ed|ion)?\b|early warning|credit rating|\bpartner(?:s|ship)?\b|rbi approved", re.I)
# Undertow copy must not upsell where a marketplace forbids it: no plan or per-call prices.
PRICE = re.compile(r"(?:US)?\$\s?\d[\d,]*(?:\.\d+)?\s*(?:/|a |per )\s*(?:mo|month|yr|year|call)\b|\bRs\.?\s?\d", re.I)


def read_json(relative):
    return json.loads((ROOT / relative).read_text())


def package_paths(root):
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}


def manifest_url(fmt, manifest, mcp, slug):
    """The MCP URL a client of this format reads, and the server names it declares."""
    if fmt in {"claude", "codex"}:
        servers = mcp["mcpServers"]
        if fmt == "codex":
            assert manifest["mcpServers"] == "./.mcp.json"
        assert servers[slug]["type"] == "http"
        return servers[slug]["url"], set(servers)
    if fmt == "gemini":
        servers = manifest["mcpServers"]
        return servers[slug]["httpUrl"], set(servers)
    if fmt == "agent-plugins":
        servers = mcp["mcpServers"]
        assert servers[slug]["type"] == "streamable-http"
        return servers[slug]["url"], set(servers)
    if fmt == "antigravity":
        servers = mcp["mcpServers"]
        return servers[slug]["serverUrl"], set(servers)
    if fmt == "devin":
        servers = manifest["mcpServers"]
        return servers[slug]["url"], set(servers)
    raise AssertionError(f"Unknown manifest format {fmt}")


class ClientManifestTableTests(unittest.TestCase):
    def test_table_urls_and_versions_match_their_sources(self):
        registry = {server["name"]: server for server in SNAPSHOT["servers"]}
        aliases = {p["id"]: p["mcp_url"] for p in read_json("docs/connect/native-connections.json")["products"]}
        self.assertEqual(set(PRODUCTS), {"liquilens", "seiche", "undertow"})
        for slug, row in PRODUCTS.items():
            with self.subTest(slug=slug):
                server = registry[row["registry_server"]]
                self.assertEqual(server["status"], "active")
                self.assertTrue(server["is_latest"])
                self.assertEqual([r["url"] for r in server["remotes"] if r["type"] == "streamable-http"],
                                 [row["canonical_mcp_url"]])
                self.assertEqual(row["alias_mcp_url"], aliases[slug])
                self.assertEqual(row["alias_mcp_url"], f"https://agents.seiche.info/products/{slug}/mcp")
                self.assertNotEqual(row["canonical_mcp_url"], row["alias_mcp_url"])
                self.assertEqual(row["plugin_version"], builder.PRODUCT_VERSIONS[slug])
        self.assertEqual(PRODUCTS["undertow"]["display_name"], "LiquiLens Undertow")

    def test_every_manifest_carries_the_table_name_version_and_url(self):
        formats = {row["format"] for row in TABLE["manifests"]}
        self.assertEqual(formats, {"claude", "codex", "gemini", "agent-plugins", "antigravity", "devin"})
        for slug, row in PRODUCTS.items():
            for entry in TABLE["manifests"]:
                with self.subTest(slug=slug, manifest=entry["format"]):
                    manifest = read_json(entry["path"].format(id=slug))
                    mcp = read_json(entry["mcp_path"].format(id=slug))
                    url, servers = manifest_url(entry["format"], manifest, mcp, slug)
                    self.assertEqual(servers, {slug})
                    self.assertEqual(manifest["name"], slug)
                    expected = row["canonical_mcp_url"] if entry["url"] == "canonical" else row["alias_mcp_url"]
                    self.assertEqual(url, expected)
                    if entry["format"] == "devin":
                        self.assertNotIn("version", manifest)
                    else:
                        self.assertEqual(manifest["version"], row["plugin_version"])
                    if entry["format"] in {"antigravity", "devin"}:
                        self.assertEqual(manifest["displayName"], row["display_name"])

    def test_marketplace_catalogs_and_plugin_catalog_carry_the_table_versions(self):
        claude = {p["name"]: p for p in read_json(".claude-plugin/marketplace.json")["plugins"]}
        catalog = {p["id"]: p for p in read_json("docs/plugins/catalog.json")["products"]}
        for slug, row in PRODUCTS.items():
            with self.subTest(slug=slug):
                self.assertEqual(claude[slug]["version"], row["plugin_version"])
                self.assertEqual(catalog[slug]["plugin_version"], row["plugin_version"])
                self.assertEqual(catalog[slug]["canonical_mcp_url"], row["canonical_mcp_url"])
                self.assertEqual(catalog[slug]["mcp_url"], row["alias_mcp_url"])
                self.assertEqual(catalog[slug]["client_manifests"],
                                 {m["format"]: m["path"].format(id=slug) for m in TABLE["manifests"]})

    def test_manifests_pass_their_format_validators(self):
        for slug in PRODUCTS:
            with self.subTest(slug=slug):
                folder = ROOT / "plugins" / slug
                paths = package_paths(folder)
                builder.validate_agent_plugin(read_json(f"plugins/{slug}/plugin.json"))
                builder.validate_agent_mcp(read_json(f"plugins/{slug}/mcp.json"))
                builder.validate_antigravity_plugin(read_json(f"plugins/{slug}/.antigravity-plugin/plugin.json"), paths)
                builder.validate_antigravity_mcp(read_json(f"plugins/{slug}/mcp_config.json"))
                devin_root = ROOT / "integrations/devin" / slug
                builder.validate_devin_plugin(read_json(f"integrations/devin/{slug}/.devin-plugin/plugin.json"),
                                              slug, package_paths(devin_root))
                builder.validate_submission_metadata(read_json(f"plugins/{slug}/.codex-plugin/plugin.json"))

    def test_agent_plugins_validator_rejects_what_the_closed_schema_rejects(self):
        manifest = read_json("plugins/liquilens/plugin.json")
        mcp = read_json("plugins/liquilens/mcp.json")
        for change in ({"logo": "assets/logo.svg"}, {"displayName": "LiquiLens"}, {"$schema": builder.ANTIGRAVITY_SCHEMA},
                       {"name": "LiquiLens"}, {"name": "liqui--lens"}, {"author": {"name": "x", "role": "y"}},
                       {"keywords": "india"}, {"extensions": {"com.example": True}}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    builder.validate_agent_plugin({**manifest, **change})
        bad_servers = ({"type": "http", "url": "https://api.liquilens.in/mcp"},
                       {"type": "streamable-http", "url": "http://api.liquilens.in/mcp"},
                       {"type": "streamable-http", "url": "https://user:pw@api.liquilens.in/mcp"},
                       {"type": "streamable-http", "url": "https://api.liquilens.in/mcp#frag"},
                       {"type": "streamable-http", "url": "https://api.liquilens.in/mcp", "timeout": 30})
        for server in bad_servers:
            with self.subTest(server=server):
                with self.assertRaises(ValueError):
                    builder.validate_agent_mcp({**mcp, "mcpServers": {"liquilens": server}})
        with self.assertRaises(ValueError):
            builder.validate_agent_mcp({**mcp, "extra": True})
        with self.assertRaises(ValueError):
            builder.validate_agent_mcp({**mcp, "$schema": builder.AGENT_PLUGINS_SCHEMA})

    def test_antigravity_validator_enforces_marketplace_rules(self):
        manifest = read_json("plugins/seiche/.antigravity-plugin/plugin.json")
        paths = package_paths(ROOT / "plugins/seiche")
        for change in ({"displayName": "Claude Seiche"}, {"displayName": "Gemini funding"},
                       {"suggestedPrompts": ["a", "b", "c", "d"]}, {"suggestedPrompts": ["same", "same"]},
                       {"logo": "assets/missing.svg"}, {"logo": "../logo.svg"}, {"logo": "LICENSE"},
                       {"keywords": ["Money Markets"]}, {"mcpServers": {}}, {"name": "seiche.info"},
                       {"author": {"name": "LIQUILENS PRIVATE LIMITED", "url": "http://liquilens.in/"}}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    builder.validate_antigravity_plugin({**manifest, **change}, paths)
        for field in builder.ANTIGRAVITY_MARKETPLACE_FIELDS:
            with self.subTest(missing=field):
                candidate = dict(manifest)
                del candidate[field]
                with self.assertRaises(ValueError):
                    builder.validate_antigravity_plugin(candidate, paths)
        for server in ({"httpUrl": "https://api.seiche.info/mcp"}, {"serverUrl": "http://api.seiche.info/mcp"},
                       {"serverUrl": "https://api.seiche.info/mcp", "type": "sse"}):
            with self.subTest(server=server):
                with self.assertRaises(ValueError):
                    builder.validate_antigravity_mcp({"mcpServers": {"seiche": server}})

    def test_devin_validator_enforces_marketplace_folder_rules(self):
        manifest = read_json("integrations/devin/undertow/.devin-plugin/plugin.json")
        paths = package_paths(ROOT / "integrations/devin/undertow")
        for change in ({"version": "1.0.4"}, {"name": "liquilens-undertow"}, {"description": manifest["description"] + "."},
                       {"description": "Too short"}, {"shortDescription": "x" * 41}, {"logo": "./logo.svg"},
                       {"logo": "missing.svg"}, {"displayName": " LiquiLens Undertow"},
                       {"mcpServers": {"undertow": {"url": "http://api.seiche.info/undertow/mcp"}}},
                       {"mcpServers": {"undertow": {"url": "https://api.seiche.info/undertow/mcp", "type": "http"}}},
                       {"mcpServers": {"undertow": {"command": "npx"}}}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    builder.validate_devin_plugin({**manifest, **change}, "undertow", paths)
        for shadow in builder.DEVIN_SHADOW_FILES:
            with self.subTest(shadow=shadow):
                with self.assertRaises(ValueError):
                    builder.validate_devin_plugin(manifest, "undertow", paths | {shadow})

    def test_devin_packages_are_self_contained(self):
        for slug in PRODUCTS:
            with self.subTest(slug=slug):
                root = ROOT / "integrations/devin" / slug
                self.assertEqual(package_paths(root), {".devin-plugin/plugin.json", "logo.svg", "README.md", "LICENSE",
                                                       f"skills/{slug}/SKILL.md"})
                self.assertFalse(any(path.is_symlink() for path in root.rglob("*")))
                self.assertEqual((root / f"skills/{slug}/SKILL.md").read_bytes(),
                                 (ROOT / f"plugins/{slug}/skills/{slug}/SKILL.md").read_bytes())
                self.assertEqual((root / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
                self.assertEqual((root / "logo.svg").read_bytes(), (ROOT / "assets/logo.svg").read_bytes())

    def test_submitted_bundles_keep_the_alias_and_leave_out_client_manifests(self):
        catalog = {p["id"]: p for p in read_json("docs/plugins/catalog.json")["products"]}
        for slug, row in PRODUCTS.items():
            codex = read_json(f"plugins/{slug}/.codex-plugin/plugin.json")
            publication = codex["extensions"]["com.openai"]["publication"]
            self.assertEqual(publication["countries"], [])
            self.assertNotIn("demo_recording_url", codex["extensions"]["com.openai"]["review"])
            for platform, download in catalog[slug]["downloads"].items():
                with self.subTest(slug=slug, platform=platform):
                    self.assertEqual(download["url"], f"downloads/{slug}-{platform}-{row['plugin_version']}.zip")
                    data = (ROOT / "docs/plugins" / download["url"]).read_bytes()
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        names = set(archive.namelist())
                        self.assertFalse(names & set(builder.CLIENT_ONLY_FILES))
                        self.assertFalse(any(name.startswith(".antigravity-plugin/") for name in names))
                        if platform == "openai":
                            mcp = json.loads(archive.read(".mcp.json"))
                            self.assertEqual(mcp["mcpServers"][slug]["url"], row["alias_mcp_url"])
                        else:
                            gemini = json.loads(archive.read("gemini-extension.json"))
                            self.assertEqual(gemini["mcpServers"][slug]["httpUrl"], row["alias_mcp_url"])

    def test_plugins_page_links_decode_to_the_table_urls(self):
        page = (ROOT / "docs/plugins/index.html").read_text()
        title = re.search(r"<title>(.*?)</title>", page).group(1)
        self.assertIsNone(DASHES.search(title))
        self.assertIsNone(DASHES.search(page))
        for slug, row in PRODUCTS.items():
            with self.subTest(slug=slug):
                cells = re.search(rf'<tr id="product-{slug}">(.*?)</tr>', page, re.S).group(1)
                links = [html.unescape(href) for href in re.findall(r'href="([^"]+)"', cells)]
                decoded = {}
                for link in links:
                    parts = urlsplit(link)
                    query = parse_qs(parts.query)
                    if link.startswith("cursor://"):
                        decoded["cursor"] = json.loads(base64.b64decode(query["config"][0]))["url"]
                    elif link.startswith("vscode:mcp/install?"):
                        decoded["vscode"] = json.loads(unquote(link.split("?", 1)[1]))["url"]
                    elif link.startswith("https://kiro.dev/launch/mcp/add?"):
                        decoded["kiro"] = json.loads(query["config"][0])["url"]
                        self.assertEqual(query["name"], [slug])
                    elif link.startswith("lmstudio://add_mcp?"):
                        decoded["lm-studio"] = json.loads(base64.b64decode(query["config"][0]))["url"]
                        self.assertEqual(query["name"], [slug])
                self.assertEqual(decoded, {key: row["canonical_mcp_url"] for key in ("cursor", "vscode", "kiro", "lm-studio")})
        riptide = re.search(r'<tr id="product-riptide">(.*?)</tr>', page, re.S).group(1)
        self.assertNotRegex(riptide, r"href=|cursor://|vscode:|kiro\.dev|lmstudio:|\.zip|<details>")
        self.assertIn("Record only", riptide)

    def test_no_riptide_client_install_entries(self):
        for path in ("plugins/riptide/plugin.json", "plugins/riptide/mcp.json", "plugins/riptide/mcp_config.json",
                     "plugins/riptide/.antigravity-plugin", "integrations/devin/riptide"):
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists())
        self.assertNotIn("riptide", PRODUCTS)
        connections = read_json("docs/connect/native-connections.json")
        riptide_table = copy.deepcopy(TABLE)
        riptide_table["products"].append({**TABLE["products"][0], "id": "riptide"})
        with self.assertRaisesRegex(ValueError, "Riptide"):
            builder.load_client_table(connections, riptide_table)

    def test_table_mismatches_fail_the_build(self):
        connections = read_json("docs/connect/native-connections.json")
        for field, value, message in (("canonical_mcp_url", "https://agents.seiche.info/products/liquilens/mcp", "registry snapshot"),
                                      ("alias_mcp_url", "https://api.liquilens.in/mcp", "native connection"),
                                      ("plugin_version", "9.9.9", "PRODUCT_VERSIONS"),
                                      ("registry_server", "io.github.example/missing", "registry entry")):
            with self.subTest(field=field):
                table = copy.deepcopy(TABLE)
                table["products"][0][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    builder.load_client_table(connections, table)

    def test_shipped_client_text_has_no_dashes_claims_or_undertow_prices(self):
        texts = {}
        for slug in PRODUCTS:
            for relative in (f"plugins/{slug}/plugin.json", f"plugins/{slug}/.antigravity-plugin/plugin.json",
                             f"plugins/{slug}/mcp.json", f"plugins/{slug}/mcp_config.json",
                             f"plugins/{slug}/README.md", f"plugins/{slug}/skills/{slug}/SKILL.md",
                             f"integrations/devin/{slug}/.devin-plugin/plugin.json", f"integrations/devin/{slug}/README.md"):
                texts[relative] = (ROOT / relative).read_text()
        readme = (ROOT / "README.md").read_text()
        texts["README.md block"] = readme[readme.index(builder.README_BEGIN):readme.index(builder.README_END)]
        page = (ROOT / "docs/plugins/index.html").read_text()
        texts["plugins page client section"] = page[page.index('id="client-manifests-heading"'):page.index("<h2>Other assistants</h2>")]
        texts["client table"] = (ROOT / "docs/plugins/client-manifests.json").read_text()
        for name, text in texts.items():
            with self.subTest(file=name):
                self.assertIsNone(DASHES.search(text))
                self.assertIsNone(INVISIBLE.search(text))
                self.assertIsNone(FORBIDDEN.search(text))
                if "undertow" in name:
                    self.assertIsNone(PRICE.search(text))

    def test_readme_rows_list_every_product_from_the_table(self):
        readme = (ROOT / "README.md").read_text()
        block = readme[readme.index(builder.README_BEGIN):readme.index(builder.README_END)]
        for row in PRODUCTS.values():
            with self.subTest(slug=row["id"]):
                self.assertIn(f"| {row['display_name']} | {row['plugin_version']} | `{row['canonical_mcp_url']}` | `{row['alias_mcp_url']}` |", block)
        self.assertEqual(readme.count(builder.README_BEGIN), 1)
        self.assertEqual(readme.count(builder.README_END), 1)


if __name__ == "__main__":
    unittest.main()
