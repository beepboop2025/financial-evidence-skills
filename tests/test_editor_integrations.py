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
        self.assertEqual(_json(".mcp.json"), self.canonical)
        self.assertEqual(_json(".cursor/mcp.json"), self.canonical)
        self.assertEqual(
            _json(".vscode/mcp.json"),
            {"servers": self.canonical["mcpServers"]},
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
        self.assertEqual(
            vscode["status"], "self-installable-not-vendor-listing"
        )
        self.assertEqual(cursor["status"], "self-installable-not-vendor-listing")

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
        self.assertEqual(self.version, "0.1.2")
        self.assertEqual(_json("manifest.json")["version"], self.version)
        server = _json("server.json")
        self.assertEqual(server["version"], self.version)
        self.assertEqual(
            server["packages"][0]["identifier"],
            f"ghcr.io/beepboop2025/financial-evidence-skills:{self.version}",
        )
        self.assertEqual(
            _json("integrations/fdc3/appd-record.json")["version"], self.version
        )
        self.assertEqual(_json("docs/integrations.json")["version"], self.version)
        mcp_interface = self.interfaces["Model Context Protocol"]
        self.assertTrue(mcp_interface["portable_agent_host"])
        self.assertTrue(mcp_interface["config"].endswith("/.mcp.json"))

        pyproject = (ROOT / "pyproject.toml").read_text()
        self.assertIn(f'version = "{self.version}"', pyproject)
        release_surfaces = [
            "README.md",
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


if __name__ == "__main__":
    unittest.main()
