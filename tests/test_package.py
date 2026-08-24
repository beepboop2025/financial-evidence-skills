from contextlib import redirect_stdout
from email.message import Message
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from financial_evidence import cli, core, mcp  # noqa: E402


class Response:
    def __init__(self, url, body, content_type="application/json"):
        self.url = url
        self.body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def geturl(self):
        return self.url

    def read(self, size):
        return self.body[:size]


def load_legacy_helper():
    script = ROOT / "financial-evidence" / "scripts" / "fetch_evidence.py"
    spec = spec_from_file_location("legacy_financial_evidence_fetch", script)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CoreTests(unittest.TestCase):
    def test_packaged_routes_match_the_immutable_skill_helper(self):
        helper = load_legacy_helper()
        packaged = {
            topic: [(row.product, row.url, row.evidence_class) for row in rows]
            for topic, rows in core.ROUTES.items()
        }
        legacy = {
            topic: [(row.product, row.url, row.evidence_class) for row in rows]
            for topic, rows in helper.ROUTES.items()
        }
        self.assertEqual(packaged, legacy)
        self.assertEqual(core.ALIASES, helper.ALIASES)

    def test_route_manifest_is_offline_and_machine_readable(self):
        manifest = core.route_manifest(["china", "funding"])
        self.assertEqual(list(manifest["topics"]), ["china-economy", "money-market"])
        self.assertEqual(
            [row["product"] for row in manifest["topics"]["china-economy"]],
            ["Palimpsest", "Seiche"],
        )
        self.assertIn("never converted to zero", manifest["absence_policy"])

    def test_packet_preserves_documents_hashes_and_explicit_clocks(self):
        def opener(request, *, timeout):
            self.assertEqual(timeout, 2.5)
            return Response(request.full_url, b'{"status":"structural"}')

        packet = core.build_packet(
            ["china"], max_bytes=1024, timeout=2.5, opener=opener
        )
        self.assertEqual(packet["status"], "complete")
        self.assertEqual(len(packet["sources"]), 2)
        self.assertTrue(
            all(
                row["document"] == {"status": "structural"} for row in packet["sources"]
            )
        )
        self.assertTrue(
            all(row["retrieved_at"].endswith("Z") for row in packet["sources"])
        )
        self.assertTrue(
            all(len(row["content_sha256"]) == 71 for row in packet["sources"])
        )


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        output = StringIO()
        with redirect_stdout(output):
            status = cli.main(argv)
        return status, output.getvalue()

    def test_topics_json(self):
        status, output = self.run_cli(["topics", "--format", "json"])
        self.assertEqual(status, 0)
        payload = json.loads(output)
        self.assertEqual(len(payload["topics"]), 5)

    def test_route_ndjson_has_one_source_per_line(self):
        status, output = self.run_cli(
            ["route", "--topic", "china", "--format", "ndjson"]
        )
        self.assertEqual(status, 0)
        rows = [json.loads(line) for line in output.splitlines()]
        self.assertEqual([row["product"] for row in rows], ["Palimpsest", "Seiche"])

    def test_completion_is_data_not_shell_execution(self):
        status, output = self.run_cli(["completion", "zsh"])
        self.assertEqual(status, 0)
        self.assertIn("#compdef financial-evidence", output)
        self.assertNotIn("eval ", output)


class McpTests(unittest.TestCase):
    def test_legacy_initialize_and_modern_discovery(self):
        initialized = mcp.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-11-25"},
            }
        )
        self.assertEqual(initialized["result"]["protocolVersion"], "2025-11-25")
        discovered = mcp.dispatch(
            {"jsonrpc": "2.0", "id": 2, "method": "server/discover", "params": {}}
        )
        self.assertIn("2026-07-28", discovered["result"]["supportedVersions"])

    def test_tools_are_deterministic_and_read_only(self):
        response = mcp.dispatch(
            {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
        )
        tools = response["result"]["tools"]
        self.assertEqual(
            [tool["name"] for tool in tools],
            [
                "financial_evidence_topics",
                "financial_evidence_route",
                "financial_evidence_fetch",
            ],
        )
        self.assertTrue(all(tool["annotations"]["readOnlyHint"] for tool in tools))
        self.assertTrue(
            all(not tool["annotations"]["destructiveHint"] for tool in tools)
        )

    def test_route_tool_returns_structured_and_text_content(self):
        response = mcp.dispatch(
            {
                "jsonrpc": "2.0",
                "id": "route",
                "method": "tools/call",
                "params": {
                    "name": "financial_evidence_route",
                    "arguments": {"topics": ["china-economy"]},
                },
            }
        )
        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["content"][0]["type"], "text")
        self.assertIn("china-economy", result["structuredContent"]["topics"])

    def test_stdio_uses_one_json_message_per_line(self):
        source = StringIO(
            '{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}\n'
            '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n'
        )
        destination = StringIO()
        self.assertEqual(mcp.serve(source, destination), 0)
        messages = [json.loads(line) for line in destination.getvalue().splitlines()]
        self.assertEqual([message["id"] for message in messages], [1, 2])


if __name__ == "__main__":
    unittest.main()
