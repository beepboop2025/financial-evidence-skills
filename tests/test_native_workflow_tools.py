"""Real SDK wire contracts for explicit read-only research operations."""
import importlib.util
import unittest
from unittest.mock import patch

HAS_WORKSPACE = all(importlib.util.find_spec(name) for name in ("fastapi", "mcp", "httpx"))

@unittest.skipUnless(HAS_WORKSPACE, "Install workspace dependencies")
class ExplicitWorkflowToolsTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from financial_evidence.service import EvidenceService
        from financial_evidence.workspace import create_app
        self.service = EvidenceService(fetcher=lambda *a, **k: self.fail("Unexpected upstream access"))
        self.addCleanup(self.service.close)
        self.client = TestClient(create_app(service=self.service, base_url="http://localhost:6900"), base_url="http://localhost:6900")
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def rpc(self, method, params=None, protocol="2025-11-25"):
        response = self.client.post("/mcp", headers={
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": protocol,
            "X-Financial-Evidence-Traffic-Class": "synthetic",
            "X-Liquilens-Traffic-Class": "synthetic",
        }, json={"jsonrpc": "2.0", "id": 7, "method": method, "params": params or {}})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"]

    def call(self, name, arguments):
        return self.rpc("tools/call", {"name": name, "arguments": arguments})

    def test_every_operation_is_discovered_with_bounded_schema_and_annotations(self):
        for protocol in ("2025-06-18", "2025-11-25"):
            with self.subTest(protocol=protocol):
                tools = {tool["name"]: tool for tool in self.rpc("tools/list", protocol=protocol)["tools"]}
                for suffix in ("funding", "institutions", "exit"):
                    tool = tools[f"financial_evidence_{suffix}_workflow"]
                    self.assertNotIn("workflow", tool["inputSchema"]["properties"])
                    self.assertNotIn("ctx", tool["inputSchema"]["properties"])
                    for key, value in {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}.items():
                        self.assertIs(tool["annotations"][key], value)
                self.assertEqual(tools["financial_evidence_workflow"]["inputSchema"]["properties"]["workflow"]["enum"], ["funding", "institutions", "exit"])
                self.assertEqual(tools["financial_evidence_institutions_workflow"]["inputSchema"]["properties"]["institution_ids"]["maxItems"], 5)
                amounts = tools["financial_evidence_exit_workflow"]["inputSchema"]["properties"]["sizes_usd"]
                self.assertEqual(amounts["maxItems"], 4)
                self.assertEqual(amounts["items"]["maximum"], 1000000)
                self.assertEqual(amounts["items"]["multipleOf"], 0.01)

    def test_explicit_and_compatibility_tools_use_identical_bounded_operations(self):
        for workflow, arguments, selection in (
            ("funding", {"currency": "INR"}, "INR"),
            ("institutions", {"institution_ids": ["au-sfb", "hdfc-bank"]}, "au-sfb,hdfc-bank"),
            ("exit", {"sizes_usd": [0.01, 1000000]}, "0.01,1000000"),
        ):
            evidence = {"workflow": workflow, "selection": selection, "prepared_response": False,
                        "evidence": {"value": None, "rights_status": "restricted", "asof": "2026-10-27", "unit": "%"}}
            with patch("financial_evidence.workflows.run", return_value=evidence) as run:
                explicit = self.call(f"financial_evidence_{workflow}_workflow", arguments)
                legacy = self.call("financial_evidence_workflow", {"workflow": workflow, "selection": selection})
                self.assertFalse(explicit.get("isError", False))
                self.assertEqual(explicit["structuredContent"], legacy["structuredContent"])
                self.assertEqual(explicit["structuredContent"], evidence)
                self.assertEqual(run.call_count, 2)
                for call in run.call_args_list:
                    self.assertEqual(call.args[1:], (workflow, selection))
                    self.assertTrue(call.kwargs["synthetic"])

    def test_defaults_preserve_the_published_workflow_selections(self):
        from financial_evidence.workflows import DEFAULTS
        for workflow, selection in DEFAULTS.items():
            with patch("financial_evidence.workflows.run", return_value={"prepared_response": False}) as run:
                result = self.call(f"financial_evidence_{workflow}_workflow", {})
                self.assertFalse(result.get("isError", False))
                self.assertEqual(run.call_args.args[1:], (workflow, selection))

    def test_invalid_input_cannot_reach_any_operation(self):
        cases = [
            ("funding", {"currency": "USD,EUR"}),
            ("institutions", {"institution_ids": []}),
            ("institutions", {"institution_ids": ["au-sfb"] * 6}),
            ("institutions", {"institution_ids": ["au-sfb,other"]}),
            ("institutions", {"institution_ids": ["a" * 100, "b" * 100]}),
            ("exit", {"sizes_usd": []}),
            ("exit", {"sizes_usd": [0]}),
            ("exit", {"sizes_usd": [-1]}),
            ("exit", {"sizes_usd": [1000000.01]}),
            ("exit", {"sizes_usd": [1.001]}),
            ("exit", {"sizes_usd": [True]}),
            ("exit", {"sizes_usd": ["10000"]}),
            ("exit", {"sizes_usd": [1, 2, 3, 4, 5]}),
        ]
        with patch("financial_evidence.workflows.run") as run:
            for workflow, arguments in cases:
                with self.subTest(workflow=workflow, arguments=arguments):
                    self.assertTrue(self.call(f"financial_evidence_{workflow}_workflow", arguments)["isError"])
            run.assert_not_called()

    def test_upstream_failure_keeps_an_explicit_retryable_gap(self):
        with patch("financial_evidence.workflows.run", side_effect=OSError("private diagnostic must not leak")):
            for workflow in ("funding", "institutions", "exit"):
                result = self.call(f"financial_evidence_{workflow}_workflow", {})
                self.assertTrue(result["isError"])
                self.assertIn("Retry later", result["content"][0]["text"])
                self.assertNotIn("private diagnostic", result["content"][0]["text"])
