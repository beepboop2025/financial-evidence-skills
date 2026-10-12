"""Participation is explicit, bounded and tied to the permission used at submission."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from financial_evidence.trading.network import (
    NetworkClient, NetworkDeliveryError, TASK_POLICY_VERSION, create_mcp,
)

HAS_HTTPX = importlib.util.find_spec("httpx") is not None
HAS_MCP = importlib.util.find_spec("mcp") is not None
HAS_NETWORK = importlib.util.find_spec("seiche_agent_network") is not None
HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
EVENT_ID = "12345678-1234-4123-8123-123456789abc"
GRANT_ID = "abcdef01-2345-4234-9234-123456789abc"
REPORT = {"event_id": EVENT_ID, "grant_id": GRANT_ID, "goal": "compare",
          "topic": "market_liquidity", "stage": "comparing", "outcome": "unknown", "traffic_class": "real"}


def response(value, status=200):
    import httpx
    return httpx.Response(status, headers={"content-type": "application/json"},
                          stream=httpx.ByteStream(json.dumps(value).encode()))


def client(handler):
    import httpx
    return NetworkClient("https://platform.example", "private-provisioned-token", transport=httpx.MockTransport(handler))


class ParticipationValidationTests(unittest.TestCase):
    """Pure contract checks also run in the dependency-free CI job."""

    def test_no_enable_without_strict_acknowledgment_and_exact_policy(self):
        network = NetworkClient("https://platform.example", "private-provisioned-token")
        with patch.object(network, "request") as request:
            for acknowledgment in (False, 1, "true", None):
                with self.subTest(acknowledgment=acknowledgment):
                    with self.assertRaisesRegex(ValueError, "acknowledgment"):
                        network.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=acknowledgment)
            with self.assertRaisesRegex(ValueError, "policy"):
                network.enable_task_sharing(policy_version="old-policy", acknowledge_data_notice=True)
            request.assert_not_called()

    def test_sdk_rejects_undeclared_fields_before_transport(self):
        network = NetworkClient("https://platform.example", "private-provisioned-token")
        with patch.object(network, "request") as request:
            for changes in (
                {"event_id": "contains-private-information"}, {"grant_id": 123}, {"grant_id": GRANT_ID.upper()},
                {"goal": "buy a private item"}, {"topic": "private-client-project"}, {"stage": "paid"},
                {"outcome": True}, {"traffic_class": "verified"}, {"prompt": "private prompt"},
            ):
                with self.subTest(changes=changes):
                    with self.assertRaises((ValueError, TypeError)):
                        network.report_task(**(REPORT | changes))
            request.assert_not_called()


@unittest.skipUnless(HAS_HTTPX, "optional HTTP transport dependency required")
class ParticipationTransportTests(unittest.TestCase):
    def test_explicit_owner_helpers_and_agent_report_have_distinct_routes(self):
        seen = []

        def handle(request):
            seen.append((request.method, request.url.path, json.loads(request.content) if request.content else None))
            return response({"ok": True})

        network = client(handle)
        self.assertEqual(seen, [])
        network.participation_contract()
        network.participation_status()
        network.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=True)
        network.report_task(**REPORT)
        network.task_summary()
        network.withdraw_task_sharing()
        self.assertEqual(seen, [
            ("GET", "/v1/participation/contract", None),
            ("GET", "/v1/participation", None),
            ("PATCH", "/v1/participation", {"enabled": True, "policy_version": TASK_POLICY_VERSION,
                                             "data_notice_acknowledged": True}),
            ("POST", "/v1/participation/events", REPORT),
            ("GET", "/v1/participation/summary", None),
            ("DELETE", "/v1/participation", None),
        ])

    def test_uncertain_receipt_does_not_retry_or_refresh_grant(self):
        import httpx
        seen = []

        def handle(request):
            seen.append(json.loads(request.content))
            raise httpx.ReadTimeout("private upstream detail")

        network = client(handle)
        with self.assertRaisesRegex(NetworkDeliveryError, "receipt not confirmed") as error:
            network.report_task(**REPORT)
        self.assertNotIn("private upstream detail", str(error.exception))
        self.assertEqual(seen, [REPORT])


@unittest.skipUnless(HAS_HTTPX and HAS_MCP, "optional official MCP SDK and HTTP transport required")
class ParticipationMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_schemas_reject_private_fields_and_expose_no_owner_enable_tool(self):
        from mcp.server.fastmcp.exceptions import ToolError
        seen = []

        def handle(request):
            seen.append((request.method, request.url.path, json.loads(request.content) if request.content else None))
            return response({"status": "accepted", "event_id": EVENT_ID, "evidence_kind": "self_reported"})

        server = create_mcp(client(handle))
        inventory = {tool.name: tool for tool in await server.list_tools()}
        participation = {name for name in inventory if "participation" in name or name in {
            "seiche_network_task_contract", "seiche_network_task_summary", "seiche_network_report_task"}}
        self.assertEqual(participation, {"seiche_network_task_contract", "seiche_network_participation",
                                         "seiche_network_task_summary", "seiche_network_report_task"})
        report = inventory["seiche_network_report_task"]
        self.assertTrue(report.annotations.idempotentHint)
        self.assertFalse(report.annotations.readOnlyHint)
        self.assertEqual(set(report.inputSchema["properties"]), set(REPORT))
        for changes in ({"prompt": "private prompt"}, {"goal": "trade"}, {"grant_id": 123},
                        {"stage": "paid"}, {"event_id": EVENT_ID + "\n"}, {"outcome": False}):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ToolError, "invalid_request") as error:
                    await server.call_tool("seiche_network_report_task", REPORT | changes)
                self.assertNotIn("private prompt", str(error.exception))
        self.assertEqual(seen, [])
        for name, path in (("seiche_network_task_contract", "/v1/participation/contract"),
                           ("seiche_network_participation", "/v1/participation"),
                           ("seiche_network_task_summary", "/v1/participation/summary")):
            self.assertTrue(inventory[name].annotations.readOnlyHint)
            await server.call_tool(name, {})
            self.assertEqual(seen[-1], ("GET", path, None))
        await server.call_tool("seiche_network_report_task", REPORT)
        self.assertEqual(seen[-1], ("POST", "/v1/participation/events", REPORT))


@unittest.skipUnless(HAS_NETWORK and HAS_HTTPX and HAS_FASTAPI, "separate network service and optional workspace dependencies required")
class ParticipationIntegrationTests(unittest.TestCase):
    def test_real_api_owner_grant_withdrawal_and_reenable_do_not_revive_old_report(self):
        import httpx
        from fastapi.testclient import TestClient
        from seiche_agent_network.api import create_app
        from seiche_agent_network.crypto import generate_keys
        from seiche_agent_network.store import Store

        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "network.db", **generate_keys())
            try:
                owner = store.bootstrap_org("Synthetic participation integration")
                principal = store.authenticate(owner["owner_token"])
                agent = store.register_agent(principal, "Synthetic agent")
                with TestClient(create_app(store, purge_interval=0)) as api:
                    def dispatch(request):
                        result = api.request(request.method, request.url.raw_path.decode(),
                                             content=request.content, headers=dict(request.headers))
                        return httpx.Response(result.status_code, headers=dict(result.headers), stream=httpx.ByteStream(result.content))

                    transport = httpx.MockTransport(dispatch)
                    owner_client = NetworkClient("http://127.0.0.1:8765", owner["owner_token"], transport=transport)
                    agent_client = NetworkClient("http://127.0.0.1:8765", agent["token"], transport=transport)
                    self.assertFalse(agent_client.participation_status()["enabled"])
                    with self.assertRaises(NetworkDeliveryError):
                        agent_client.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=True)
                    grant = owner_client.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=True)
                    self.assertFalse(grant["shared_training"])
                    self.assertFalse(grant["data_resale_permission"])
                    report = REPORT | {"grant_id": grant["grant_id"], "traffic_class": "synthetic"}
                    self.assertEqual(agent_client.report_task(**report)["status"], "accepted")
                    self.assertEqual(agent_client.report_task(**report)["status"], "duplicate")
                    owner_client.withdraw_task_sharing()
                    self.assertFalse(agent_client.participation_status()["enabled"])
                    fresh = owner_client.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=True)
                    self.assertNotEqual(fresh["grant_id"], grant["grant_id"])
                    with self.assertRaises(NetworkDeliveryError):
                        agent_client.report_task(**report)
                    current = report | {"event_id": str(uuid4()), "grant_id": fresh["grant_id"]}
                    self.assertEqual(agent_client.report_task(**current)["status"], "accepted")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
