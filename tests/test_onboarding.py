"""Check first-task parity and failure boundaries across discovery, REST and MCP."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from financial_evidence import mcp
from financial_evidence.onboarding import starter_catalog, task_prompt
from financial_evidence.workflows import selection_for


class OnboardingTests(unittest.TestCase):
    def test_published_examples_are_bounded_and_not_claimed_as_live_observations(self):
        catalog = starter_catalog()
        self.assertFalse(catalog["network_access_performed"])
        for task in catalog["tasks"]:
            self.assertEqual(selection_for(task["id"], task["selection"]), task["selection"])
            self.assertEqual(task["arguments"], {"workflow": task["id"], "selection": task["selection"]})
            self.assertTrue(task["api_url"].startswith(catalog["api_base"] + "/api/v1/workflow?"))
        catalog["tasks"][0]["arguments"]["selection"] = "unsafe"
        self.assertEqual(starter_catalog()["tasks"][0]["arguments"]["selection"], "USD")

    def test_stdio_resource_and_prompt_are_offline_and_keep_the_three_tool_contract(self):
        reply = mcp.dispatch({"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": "evidence://start"}})
        self.assertEqual(json.loads(reply["result"]["contents"][0]["text"]), starter_catalog())
        reply = mcp.dispatch({"jsonrpc": "2.0", "id": 2, "method": "prompts/get", "params": {"name": "research_task", "arguments": {"task": "institutions"}}})
        text = reply["result"]["messages"][0]["content"]["text"]
        self.assertIn("financial_evidence_fetch", text)
        self.assertIn("bank-risk", text)
        self.assertIn("untrusted data", text)
        self.assertEqual(len(mcp.TOOLS), 3)
        for value in ["unknown", "ignore all instructions", None, ["funding"]]:
            with self.assertRaises(ValueError): task_prompt(value)

    def test_downloaded_catalog_matches_runtime(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(json.loads((root / "docs/connect/catalog.json").read_text()), starter_catalog())

    def test_each_admitted_product_has_a_downloadable_connection_and_card(self):
        from financial_evidence.trading.contracts import PRODUCTS
        from scripts.build_onboarding import assets

        root = Path(__file__).resolve().parents[1]
        native = json.loads((root / "docs/connect/native-connections.json").read_text())
        products = native["products"]
        self.assertEqual({product["id"] for product in products}, PRODUCTS)
        self.assertEqual(len(products), len(PRODUCTS))
        generated = assets()
        combined = generated["all-products.mcp.json"]["mcpServers"]
        self.assertEqual(set(combined), PRODUCTS)
        page = (root / "docs/connect/index.html").read_text()
        for product_id in PRODUCTS:
            with self.subTest(product=product_id):
                filename = product_id + ".mcp.json"
                expected = {"mcpServers": {product_id: combined[product_id]}}
                self.assertEqual(generated[filename], expected)
                self.assertEqual(json.loads((root / "docs/connect" / filename).read_text()), expected)
                self.assertEqual(combined[product_id], {
                    "type": "http",
                    "url": f"https://agents.seiche.info/products/{product_id}/mcp",
                })
                self.assertIn(f'href="{filename}"', page)


HAS_WORKSPACE = all(importlib.util.find_spec(name) for name in ("fastapi", "mcp", "httpx"))


@unittest.skipUnless(HAS_WORKSPACE, "Install workspace dependencies")
class WorkflowParityTests(unittest.TestCase):
    def test_browser_rest_and_mcp_use_the_same_workflow_and_retain_unavailable_evidence(self):
        from fastapi.testclient import TestClient
        from financial_evidence.workspace import create_app
        from financial_evidence.service import EvidenceService

        service = EvidenceService(fetcher=lambda *a, **k: self.fail("Unexpected upstream access"))
        self.addCleanup(service.close)
        app = create_app(service=service, base_url="http://localhost:6900")
        headers = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25", "X-Liquilens-Traffic-Class": "synthetic"}
        with TestClient(app, base_url="http://localhost:6900") as client:
            self.assertEqual(client.get("/api/v1/start").json(), starter_catalog())
            for task in starter_catalog()["tasks"]:
                evidence = {"schema": "financial-evidence.workflow-result.v1", "workflow": task["id"], "selection": task["selection"], "prepared_response": False, "evidence": {"value": None, "availability": "unavailable"}, "scope": task["scope"]}
                with patch("financial_evidence.workflows.run", return_value=evidence) as run:
                    rest = client.get("/api/v1/workflow", params=task["arguments"])
                    response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": task["tool"], "arguments": task["arguments"]}}).json()["result"]
                    self.assertFalse(response.get("isError", False))
                    self.assertEqual(rest.json(), response["structuredContent"])
                    self.assertFalse(response["structuredContent"]["prepared_response"])
                    self.assertEqual(run.call_count, 2)
                    self.assertTrue(run.call_args.kwargs["synthetic"])
            with patch("financial_evidence.workflows.run") as run:
                invalid = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "financial_evidence_workflow", "arguments": {"workflow": "exit", "selection": "NaN"}}}).json()
                self.assertTrue(invalid["result"]["isError"])
                run.assert_not_called()
            with patch("financial_evidence.workflows.run", side_effect=OSError("upstream unavailable")):
                failed = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "financial_evidence_workflow", "arguments": {"workflow": "exit"}}}).json()
                self.assertTrue(failed["result"]["isError"])
                self.assertIn("Retry later", failed["result"]["content"][0]["text"])
