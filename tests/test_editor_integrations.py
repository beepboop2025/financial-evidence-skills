import base64
from html import unescape
import json
from pathlib import Path
import re
import shlex
import unittest
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SERVER_NAME = "financial-evidence"
REPOSITORY = "https://github.com/beepboop2025/financial-evidence-skills.git"


def _json(path: str):
    return json.loads((ROOT / path).read_text())


def _package_version() -> str:
    source = (ROOT / "src/financial_evidence/__init__.py").read_text()
    match = re.search(r'^__version__ = "([^"]+)"$', source, re.MULTILINE)
    if not match:
        raise AssertionError("package version is missing")
    return match.group(1)


class EditorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.version = _package_version()
        self.canonical = _json("integrations/mcp-config.json")
        self.config = self.canonical["mcpServers"][SERVER_NAME]
        self.named_config = {"name": SERVER_NAME, **self.config}
        manifest = _json("docs/integrations.json")
        self.interfaces = {item["name"]: item for item in manifest["interfaces"]}

    def test_workspace_configs_share_one_exact_stdio_contract(self):
        expected = {
            "type": "stdio",
            "command": "uvx",
            "args": [
                "--from",
                f"git+{REPOSITORY}@v{self.version}",
                "financial-evidence-mcp",
            ],
        }
        self.assertEqual(self.config, expected)
        self.assertEqual(_json(".cursor/mcp.json"), self.canonical)
        self.assertEqual(
            _json(".vscode/mcp.json"),
            {"servers": self.canonical["mcpServers"]},
        )

    def test_root_plugin_mcp_uses_the_public_remote(self):
        self.assertEqual(
            _json(".mcp.json"),
            {
                "mcpServers": {
                    SERVER_NAME: {
                        "type": "http",
                        "url": "https://liquilens.in/mcp/financial-evidence",
                    }
                }
            },
        )

    def test_vscode_install_url_and_cli_decode_to_named_config(self):
        integration = self.interfaces["Visual Studio Code"]
        install_url = integration["install_url"]
        self.assertTrue(install_url.startswith("vscode:mcp/install?"))
        encoded = install_url.split("?", 1)[1]
        self.assertEqual(json.loads(unquote(encoded)), self.named_config)

        command = shlex.split(integration["cli_install"])
        self.assertEqual(command[:2], ["code", "--add-mcp"])
        self.assertEqual(len(command), 3)
        self.assertEqual(json.loads(command[2]), self.named_config)

    def test_cursor_deeplink_decodes_to_unnamed_transport_config(self):
        install_url = self.interfaces["Cursor"]["install_url"]
        parsed = urlparse(install_url)
        self.assertEqual(parsed.scheme, "cursor")
        self.assertEqual(parsed.netloc, "anysphere.cursor-deeplink")
        self.assertEqual(parsed.path, "/mcp/install")
        query = parse_qs(parsed.query, strict_parsing=True)
        self.assertEqual(query["name"], [SERVER_NAME])
        self.assertEqual(len(query["config"]), 1)
        decoded = base64.b64decode(query["config"][0], validate=True)
        self.assertEqual(json.loads(decoded), self.config)

    def test_install_routes_are_documented_with_review_boundaries(self):
        vscode = self.interfaces["Visual Studio Code"]
        cursor = self.interfaces["Cursor"]
        self.assertTrue(vscode["review_before_start"])
        self.assertTrue(cursor["review_before_start"])
        for integration in (vscode, cursor):
            self.assertEqual(integration["published_version"], self.version)
            self.assertEqual(
                integration["status"],
                "self-installable-not-vendor-listing",
            )

        readme = (ROOT / "README.md").read_text()
        llms = (ROOT / "docs/llms.txt").read_text()
        page = unescape((ROOT / "docs/index.html").read_text())
        for document in (readme, llms, page):
            self.assertIn(vscode["install_url"], document)
            self.assertIn(cursor["install_url"], document)
        self.assertIn(vscode["cli_install"], readme)
        self.assertIn(vscode["cli_install"], llms)
        self.assertIn(vscode["cli_install"], page)
        self.assertIn("not claims of a VS Code or Cursor marketplace listing", readme)

    def test_release_surfaces_are_pinned_to_package_version(self):
        self.assertEqual(self.version, "0.1.4")
        self.assertEqual(_json("manifest.json")["version"], self.version)
        server = _json("server.json")
        self.assertEqual(server["version"], self.version)
        self.assertEqual(
            server["packages"][0]["identifier"],
            f"ghcr.io/beepboop2025/financial-evidence-skills:{self.version}",
        )
        self.assertEqual(
            server["remotes"],
            [
                {
                    "type": "streamable-http",
                    "url": "https://liquilens.in/mcp/financial-evidence",
                }
            ],
        )
        self.assertEqual(
            _json("integrations/fdc3/appd-record.json")["version"], self.version
        )
        self.assertEqual(_json("docs/integrations.json")["version"], self.version)
        homebrew = self.interfaces["Homebrew"]
        self.assertEqual(homebrew["published_version"], self.version)
        self.assertEqual(homebrew["status"], "public")
        mcp_interface = self.interfaces["Model Context Protocol"]
        self.assertTrue(mcp_interface["portable_agent_host"])
        self.assertTrue(mcp_interface["config"].endswith("/.mcp.json"))
        self.assertEqual(mcp_interface["published_version"], self.version)
        self.assertEqual(mcp_interface["status"], "official-registry-active")
        bundle = self.interfaces["MCP Bundle"]
        self.assertEqual(bundle["published_version"], self.version)
        self.assertEqual(bundle["status"], "public")

        pyproject = (ROOT / "pyproject.toml").read_text()
        self.assertIn(f'version = "{self.version}"', pyproject)
        release_surfaces = [
            "README.md",
            "gemini-extension.json",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
            ".agents/plugins/marketplace.json",
            "docs/index.html",
            "docs/integrations.json",
            "docs/llms.txt",
            "integrations/mcp-config.json",
            ".mcp.json",
            ".vscode/mcp.json",
            ".cursor/mcp.json",
        ]
        for path in release_surfaces:
            text = (ROOT / path).read_text()
            self.assertNotIn("0.1.1", text, path)

    def test_release_checksums_use_download_basenames(self):
        workflow = (ROOT / ".github/workflows/release-container.yml").read_text()
        self.assertNotIn("sha256sum dist/*", workflow)
        self.assertIn("(cd dist && sha256sum -- *)", workflow)

    def test_gemini_extension_uses_bounded_public_remote_mcp(self):
        extension = _json("gemini-extension.json")
        self.assertEqual(extension["name"], SERVER_NAME)
        self.assertEqual(extension["version"], self.version)
        remote = extension["mcpServers"][SERVER_NAME]
        self.assertEqual(
            remote["httpUrl"],
            "https://liquilens.in/mcp/financial-evidence",
        )
        self.assertEqual(remote["timeout"], 30000)
        self.assertNotIn("trust", remote)
        self.assertEqual(
            remote["includeTools"],
            [
                "financial_evidence_topics",
                "financial_evidence_route",
                "financial_evidence_fetch",
            ],
        )
        integration = self.interfaces["Gemini CLI"]
        self.assertIn(f"--ref v{self.version}", integration["install"])
        self.assertNotIn("--consent", integration["install"])

    def test_claude_plugin_and_marketplace_are_self_hosted(self):
        plugin = _json(".claude-plugin/plugin.json")
        marketplace = _json(".claude-plugin/marketplace.json")
        self.assertEqual(plugin["name"], SERVER_NAME)
        self.assertEqual(plugin["version"], self.version)
        self.assertEqual(marketplace["name"], "liquidity-lab")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], SERVER_NAME)
        self.assertEqual(entry["source"], ".")
        self.assertEqual(entry["version"], self.version)
        self.assertEqual(plugin["version"], entry["version"])
        integration = self.interfaces["Claude Code"]
        self.assertIn("plugin marketplace add", integration["install"])
        self.assertIn(
            "financial-evidence@liquidity-lab", integration["install"]
        )

    def test_openai_plugin_is_repo_installable_and_review_bounded(self):
        plugin = _json(".codex-plugin/plugin.json")
        marketplace = _json(".agents/plugins/marketplace.json")
        self.assertEqual(plugin["name"], SERVER_NAME)
        self.assertEqual(plugin["version"], self.version)
        self.assertEqual(plugin["skills"], "./skills/")
        self.assertEqual(plugin["mcpServers"], "./.mcp.json")
        self.assertEqual(
            _json(plugin["mcpServers"])["mcpServers"][SERVER_NAME]["url"],
            "https://liquilens.in/mcp/financial-evidence",
        )
        self.assertEqual(
            plugin["interface"]["privacyPolicyURL"],
            "https://beepboop2025.github.io/financial-evidence-skills/privacy/",
        )
        self.assertEqual(
            plugin["interface"]["termsOfServiceURL"],
            "https://beepboop2025.github.io/financial-evidence-skills/terms/",
        )
        self.assertEqual(
            plugin["interface"]["supportURL"],
            "https://beepboop2025.github.io/financial-evidence-skills/support/",
        )
        self.assertEqual(
            plugin["interface"]["logo"],
            "./assets/logo.svg",
        )
        self.assertTrue((ROOT / plugin["interface"]["logo"]).is_file())
        self.assertEqual(
            plugin["interface"]["composerIcon"],
            "./assets/logo-400.png",
        )
        self.assertTrue((ROOT / plugin["interface"]["composerIcon"]).is_file())
        self.assertLessEqual(len(plugin["interface"]["shortDescription"]), 30)
        self.assertEqual(marketplace["name"], "liquidity-lab")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], SERVER_NAME)
        self.assertEqual(entry["source"]["source"], "url")
        self.assertEqual(entry["source"]["ref"], "main")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")

        integration = self.interfaces["Codex plugin and ChatGPT submission"]
        self.assertEqual(integration["kind"], "openai-plugin")
        self.assertEqual(
            integration["remote_mcp"],
            "https://liquilens.in/mcp/financial-evidence",
        )
        self.assertEqual(
            integration["status"],
            "codex-repo-installable-chatgpt-submission-not-started",
        )
        self.assertIn("codex plugin marketplace add", integration["install"])
        self.assertIn("codex plugin add", integration["install"])
        self.assertEqual(integration["codex_status"], "repo-installable")
        self.assertEqual(
            integration["chatgpt_status"], "submission-not-started"
        )

        packet = (ROOT / "OPENAI_PLUGIN_SUBMISSION.md").read_text()
        self.assertIn(
            "has not been submitted, approved, listed, or published by OpenAI",
            packet.replace("\n", " "),
        )
        self.assertIn("five positive and three negative tests", packet)
        self.assertIn("openai-apps-challenge", packet)
        self.assertIn("Short description:", packet)
        self.assertIn("Long description:", packet)
        self.assertIn("Support: https://", packet)
        self.assertIn("## Release notes", packet)
        self.assertIn("Availability:", packet)
        self.assertIn("Demo recording: not yet recorded", packet)
        self.assertEqual(packet.count("`readOnlyHint` justification:"), 3)
        self.assertEqual(packet.count("`openWorldHint` justification:"), 3)
        self.assertEqual(packet.count("`destructiveHint` justification:"), 3)
        self.assertEqual(packet.count("Fixture or account data:"), 5)
        self.assertEqual(packet.count("Why it must not complete the action:"), 3)

    def test_glama_metadata_is_minimal_and_owner_scoped(self):
        self.assertEqual(
            _json("glama.json"),
            {
                "$schema": "https://glama.ai/mcp/schemas/server.json",
                "maintainers": ["beepboop2025"],
            },
        )

    def test_agent_skill_layouts_are_byte_identical(self):
        for relative in (
            "SKILL.md",
            "references/routing.md",
            "scripts/fetch_evidence.py",
        ):
            canonical = ROOT / "financial-evidence" / relative
            extension = ROOT / "skills" / "financial-evidence" / relative
            self.assertEqual(extension.read_bytes(), canonical.read_bytes(), relative)


if __name__ == "__main__":
    unittest.main()
