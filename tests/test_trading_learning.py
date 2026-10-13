"""Direct-product SDK integration: opt-in metadata, private captures, MCP schema."""

import asyncio
import importlib.util
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from financial_evidence.learning import LearningStore
from financial_evidence.trading.client import ProductClient
from financial_evidence.trading.journal import save_receipt
from financial_evidence.trading.network import NetworkClient, create_mcp

NOW = 1_800_000_000


class TradingLearningTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LearningStore(Path(self.temp.name) / "learning", clock=lambda: NOW)
        enrollment = self.store.enroll(purposes=["measurement", "private_evidence"], policy_version="v1", expires_at=NOW + 86400)
        self.token = enrollment["credential"]
        self.calls = []

        async def transport(endpoint, tool, arguments, timeout):
            self.calls.append((endpoint, tool, arguments))
            return {"server": {"name": "synthetic-test"}, "result": {"structuredContent": {"private_value": "do-not-measure-result"}, "isError": False}}
        self.transport = transport

    def sink(self, event):
        self.store.record_tool(self.token, event)

    async def test_no_measurement_by_default_even_when_sink_supplied(self):
        client = ProductClient(transport=self.transport, event_sink=lambda event: self.fail("default must not emit"), clock=lambda: NOW)
        result = await client.call("seiche", "funding_stress_now", {"private_query": "do-not-measure-input"})
        self.assertEqual(result["product"], "seiche")
        self.assertEqual(self.store.report(self.token)["requests"], 0)

    async def test_enrolled_metadata_excludes_inputs_outputs_and_counts_cached_use(self):
        client = ProductClient(transport=self.transport, measurement=True, event_sink=self.sink,
                               mode="shadow", clock=lambda: NOW, cache_seconds=30)
        first = await client.call("seiche", "funding_stress_now", {"private_query": "do-not-measure-input"}, task="funding_review", workflow_id="review-1")
        second = await client.call("seiche", "funding_stress_now", {"private_query": "do-not-measure-input"}, task="funding_review", workflow_id="review-1")
        self.assertEqual(client.measurement_failures, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(second["cache_hit"])
        for identifier in (first["call_id"], second["call_id"]):
            event = self.store.get_record(self.token, "tool", identifier)["record"]
            self.assertNotIn("do-not-measure", json.dumps(event))
            self.assertNotIn("arguments", event)
            self.assertNotIn("payload", event)
        self.assertEqual(self.store.report(self.token)["requests"], 2)
        self.assertEqual(self.store.report(self.token)["cache_hits"], 1)

    async def test_default_task_and_starter_workflow_are_measurable(self):
        client = ProductClient(transport=self.transport, measurement=True, event_sink=self.sink, mode="shadow", clock=lambda: NOW)
        await client.call("seiche", "funding_stress_now")
        await client.funding_china_review()
        self.assertEqual(client.measurement_failures, 0)
        self.assertEqual(self.store.report(self.token)["requests"], 5)

    async def test_measurement_revocation_does_not_break_free_product_access(self):
        client = ProductClient(transport=self.transport, measurement=True, event_sink=self.sink, mode="shadow", clock=lambda: NOW)
        self.store.withdraw(self.token, purposes=["measurement"])
        result = await client.call("seiche", "funding_stress_now", task="funding_review")
        self.assertEqual(result["product"], "seiche")
        self.assertEqual(client.measurement_failures, 1)
        self.assertEqual(self.store.report(self.token)["requests"], 0)

    async def test_central_endpoints_and_private_receipt_projection(self):
        client = ProductClient(transport=self.transport, platform_url="https://platform.example", credential="private-platform-token", clock=lambda: NOW)
        receipt = await client.call("seiche", "funding_stress_now", task="funding_review")
        self.assertEqual(self.calls[0][0], "https://platform.example/products/seiche/mcp")
        self.assertNotIn("private-platform-token", json.dumps(receipt))
        captured = save_receipt(Path(self.temp.name) / "receipts", receipt)
        exact_ref = {key: captured[key] for key in ("kind", "product", "receipt_id", "sha256")}
        feature = {"value": 1, "observed_at": NOW - 10, "available_at": NOW - 1, "source": "test-source", "revision": "r1"}
        result = self.store.record_decision(self.token, {"id": "exact-decision", "decided_at": NOW, "target": "funding_next_release_change",
                 "entity": "US-USD", "horizon_seconds": 60, "mode": "test", "evidence_refs": [exact_ref],
                 "data_features": {"current_rate": feature}, "usage_features": {}})
        self.assertTrue(result["created"])
        self.assertEqual(self.store.report(self.token)["requests"], 0)


@unittest.skipUnless(importlib.util.find_spec("mcp"), "optional MCP SDK required")
class NetworkSDKTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_central_config_uses_environment_without_token_embedding(self):
        from financial_evidence.trading.cli import main
        output = io.StringIO()
        with patch.dict(os.environ, {"SEICHE_NETWORK_TOKEN": "private-test-token-never-print"}), redirect_stdout(output):
            self.assertEqual(main(["--platform-url", "https://platform.example", "mcp-config"]), 0)
        value = json.loads(output.getvalue())
        self.assertNotIn("private-test-token-never-print", output.getvalue())
        self.assertEqual(value["mcpServers"]["seiche"], {"command": "financial-evidence-product-mcp", "args": ["--product", "seiche", "--platform-url", "https://platform.example"]})

    async def test_actual_sdk_schemas_and_remote_request_shapes(self):
        calls = []

        class StubRemote:
            def request(self, method, path, body=None):
                calls.append((method, path, body))
                if path in {"/v1/directory", "/v1/contacts"}:
                    return []
                return {"id": "synthetic-test", "status": "submitted"}

        server = create_mcp(StubRemote())
        inventory = {tool.name: tool for tool in await server.list_tools()}
        self.assertIn("seiche_network_send", inventory)
        self.assertIn("seiche_network_inbox", inventory)
        schema = inventory["seiche_network_send"].inputSchema
        self.assertTrue({"room_id", "kind", "text", "idempotency_key"} <= set(schema["required"]))
        await server.call_tool("seiche_network_send", {"room_id": "room-1", "kind": "question", "text": "test-only", "idempotency_key": "retry-1"})
        self.assertEqual(calls[-1], ("POST", "/v1/rooms/room-1/messages", {"kind": "question", "payload": {"text": "test-only"}, "idempotency_key": "retry-1", "expires_in": 86400}))
        await server.call_tool("seiche_network_create_room", {"label": "Private room", "participant_ids": ["agent-2"]})
        self.assertEqual(calls[-1][2], {"label": "Private room", "participant_ids": ["agent-2"]})
        await server.call_tool("seiche_network_status", {"message_id": "message-1", "status": "completed"})
        self.assertEqual(calls[-1], ("POST", "/v1/tasks/message-1/status", {"status": "completed"}))

    async def test_network_url_validation_prevents_plaintext_remote_credentials(self):
        for url in ("http://remote.example", "https://user:pass@example.test", "https://example.test/?private=1", "https://example.test/../escape"):
            with self.assertRaises(ValueError):
                NetworkClient(url, "x" * 43)


if __name__ == "__main__":
    unittest.main()
