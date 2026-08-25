from contextlib import redirect_stdout
from email.message import Message
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


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
    def test_legacy_three_argument_source_constructor_remains_compatible(self):
        source = core.Source("Example", "https://example.com/data.json", "observed")
        self.assertEqual(source.human_scope_url, "")
        self.assertEqual(source.financial_authority, "none")
        self.assertEqual(source.carrier_state, "not_published")

    def test_packaged_routes_match_the_immutable_skill_helper(self):
        helper = load_legacy_helper()
        packaged = {
            topic: [
                (
                    row.product,
                    row.url,
                    row.evidence_class,
                    row.human_scope_url,
                    row.financial_authority,
                    row.carrier_state,
                )
                for row in rows
            ]
            for topic, rows in core.ROUTES.items()
        }
        legacy = {
            topic: [
                (
                    row.product,
                    row.url,
                    row.evidence_class,
                    row.human_scope_url,
                    row.financial_authority,
                    row.carrier_state,
                )
                for row in rows
            ]
            for topic, rows in helper.ROUTES.items()
        }
        self.assertEqual(packaged, legacy)
        self.assertEqual(core.ALIASES, helper.ALIASES)
        packaged_adapters = {
            url: (
                adapter.name,
                [(field.name, field.path) for field in adapter.states],
                [(field.name, field.path) for field in adapter.clocks],
            )
            for url, adapter in core.SOURCE_ADAPTERS.items()
        }
        helper_adapters = {
            url: (
                adapter.name,
                [(field.name, field.path) for field in adapter.states],
                [(field.name, field.path) for field in adapter.clocks],
            )
            for url, adapter in helper.SOURCE_ADAPTERS.items()
        }
        self.assertEqual(packaged_adapters, helper_adapters)

    def test_route_manifest_is_offline_and_machine_readable(self):
        manifest = core.route_manifest(["china", "funding"])
        self.assertEqual(list(manifest["topics"]), ["china-economy", "money-market"])
        self.assertEqual(
            [row["product"] for row in manifest["topics"]["china-economy"]],
            ["Palimpsest", "Seiche"],
        )
        self.assertIn("never converted to zero", manifest["absence_policy"])
        for sources in manifest["topics"].values():
            for source in sources:
                self.assertEqual(source["financial_authority"], "none")
                self.assertEqual(source["carrier_state"], "not_published")
                self.assertNotIn("carrier_url", source)
                self.assertTrue(source["human_scope_url"].startswith("https://"))

    def test_packet_preserves_documents_hashes_and_explicit_clocks(self):
        def opener(request, *, timeout):
            self.assertEqual(timeout, 2.5)
            return Response(request.full_url, b'{"status":"structural"}')

        packet = core.build_packet(
            ["china"], max_bytes=1024, timeout=2.5, opener=opener
        )
        self.assertEqual(packet["status"], "complete")
        self.assertEqual(packet["transport_status"], "complete")
        self.assertEqual(packet["status_semantics"], "transport_only")
        self.assertEqual(packet["evidence_status"], "not_evaluated")
        self.assertEqual(packet["carrier_verification"], "not_performed")
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
        self.assertTrue(all("carrier_url" not in row for row in packet["sources"]))


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

    def test_route_table_exposes_boundary_metadata_without_carrier_url(self):
        status, output = self.run_cli(
            ["route", "--topic", "money-market", "--format", "table"]
        )
        self.assertEqual(status, 0)
        header = output.splitlines()[0]
        for field in (
            "human_scope_url",
            "financial_authority",
            "carrier_state",
        ):
            self.assertIn(field, header)
        self.assertNotIn("carrier_url", header)

    def test_completion_is_data_not_shell_execution(self):
        status, output = self.run_cli(["completion", "zsh"])
        self.assertEqual(status, 0)
        self.assertIn("#compdef financial-evidence", output)
        self.assertNotIn("eval ", output)

    def test_legacy_exit_codes_follow_transport_status(self):
        for transport_status, expected in (
            ("complete", 0),
            ("partial", 1),
            ("unavailable", 2),
        ):
            packet = {
                "status": transport_status,
                "transport_status": transport_status,
                "status_semantics": "transport_only",
                "evidence_status": "not_evaluated",
                "carrier_verification": "not_performed",
                "sources": [],
            }
            with patch("financial_evidence.cli.build_packet", return_value=packet):
                status, output = self.run_cli(
                    ["fetch", "--topic", "money-market", "--format", "json"]
                )
            self.assertEqual(status, expected)
            self.assertEqual(json.loads(output)["status"], transport_status)

    def test_row_formats_repeat_packet_semantic_guardrails(self):
        packet = {
            "status": "complete",
            "transport_status": "complete",
            "status_semantics": "transport_only",
            "evidence_status": "not_evaluated",
            "carrier_verification": "not_performed",
            "sources": [
                {
                    "topic": "money-market",
                    "product": "Seiche",
                    "ok": True,
                    "source_reported": {
                        "adapter": "seiche_money_markets_v1",
                        "state": "not_reported",
                        "clocks": "not_reported",
                    },
                    "document": {"status": "PARTIAL"},
                }
            ],
        }
        with patch("financial_evidence.cli.build_packet", return_value=packet):
            status, output = self.run_cli(
                ["fetch", "--topic", "money-market", "--format", "ndjson"]
            )
        self.assertEqual(status, 0)
        row = json.loads(output)
        self.assertEqual(row["status"], row["transport_status"])
        self.assertEqual(row["status_semantics"], "transport_only")
        self.assertEqual(row["evidence_status"], "not_evaluated")
        self.assertEqual(row["carrier_verification"], "not_performed")
        self.assertEqual(
            json.loads(row["source_reported"])["adapter"],
            "seiche_money_markets_v1",
        )


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
        common = {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        }
        self.assertEqual(
            {tool["name"]: tool["annotations"] for tool in tools},
            {
                "financial_evidence_topics": {
                    **common,
                    "openWorldHint": False,
                },
                "financial_evidence_route": {
                    **common,
                    "openWorldHint": False,
                },
                "financial_evidence_fetch": {
                    **common,
                    "openWorldHint": True,
                },
            },
        )
        for tool in tools[1:]:
            topics = tool["inputSchema"]["properties"]["topics"]
            self.assertEqual(topics["minItems"], 1)
            self.assertEqual(topics["maxItems"], 5)
            self.assertTrue(topics["uniqueItems"])
        contract = json.loads(
            (ROOT / "integrations" / "financial-evidence-mcp-v0.1.5.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(contract["serverInfo"], mcp.SERVER_INFO)
        self.assertEqual(contract["tools"], tools)
        canonical_tools = json.dumps(
            tools, sort_keys=True, separators=(",", ":")
        ).encode()
        self.assertEqual(
            hashlib.sha256(canonical_tools).hexdigest(),
            contract["toolsSha256"],
        )
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {tool["name"]: tool["description"] for tool in manifest["tools"]},
            {tool["name"]: tool["description"] for tool in tools},
        )

    def test_mcp_enforces_the_five_topic_boundary(self):
        canonical_topics = list(core.ROUTES)
        accepted = mcp.call_tool(
            "financial_evidence_route",
            {"topics": canonical_topics},
        )
        self.assertFalse(accepted["isError"])
        self.assertEqual(
            list(accepted["structuredContent"]["topics"]),
            canonical_topics,
        )

        rejected = mcp.dispatch(
            {
                "jsonrpc": "2.0",
                "id": "too-many",
                "method": "tools/call",
                "params": {
                    "name": "financial_evidence_route",
                    "arguments": {
                        "topics": [*canonical_topics, canonical_topics[0]],
                    },
                },
            }
        )
        self.assertTrue(rejected["result"]["isError"])
        self.assertIn("between 1 and 5", rejected["result"]["content"][0]["text"])

        duplicate = mcp.dispatch(
            {
                "jsonrpc": "2.0",
                "id": "duplicate",
                "method": "tools/call",
                "params": {
                    "name": "financial_evidence_fetch",
                    "arguments": {"topics": [canonical_topics[0]] * 2},
                },
            }
        )
        self.assertTrue(duplicate["result"]["isError"])
        self.assertIn("unique", duplicate["result"]["content"][0]["text"])

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

    def test_fetch_tool_error_semantics_follow_transport_only(self):
        packet = {
            "status": "unavailable",
            "transport_status": "unavailable",
            "status_semantics": "transport_only",
            "evidence_status": "not_evaluated",
            "carrier_verification": "not_performed",
            "sources": [],
        }
        with patch("financial_evidence.mcp.build_packet", return_value=packet):
            response = mcp.call_tool(
                "financial_evidence_fetch",
                {"topics": ["money-market"]},
            )
        self.assertTrue(response["isError"])
        self.assertEqual(response["structuredContent"], packet)

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
