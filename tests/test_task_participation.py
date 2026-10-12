"""Participation is explicit, bounded and tied to the permission used at submission."""
import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from financial_evidence.trading.network import (
    NetworkClient, NetworkDeliveryError, TASK_POLICY_VERSION, create_mcp,
)

EVENT_ID = "12345678-1234-4123-8123-123456789abc"
GRANT_ID = "abcdef01-2345-4234-9234-123456789abc"
REPORT = {"event_id": EVENT_ID, "grant_id": GRANT_ID, "goal": "compare",
          "topic": "market_liquidity", "stage": "comparing", "outcome": "unknown", "traffic_class": "real"}


def response(value, status=200):
    return httpx.Response(status, headers={"content-type": "application/json"},
                          stream=httpx.ByteStream(json.dumps(value).encode()))


def client(handler):
    return NetworkClient("https://platform.example", "private-provisioned-token", transport=httpx.MockTransport(handler))


def test_explicit_owner_helpers_and_agent_report_have_distinct_routes():
    seen = []

    def handle(request):
        seen.append((request.method, request.url.path, json.loads(request.content) if request.content else None))
        return response({"ok": True})

    network = client(handle)
    assert seen == []
    network.participation_contract()
    network.participation_status()
    network.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=True)
    network.report_task(**REPORT)
    network.task_summary()
    network.withdraw_task_sharing()
    assert seen == [
        ("GET", "/v1/participation/contract", None),
        ("GET", "/v1/participation", None),
        ("PATCH", "/v1/participation", {"enabled": True, "policy_version": TASK_POLICY_VERSION,
                                         "data_notice_acknowledged": True}),
        ("POST", "/v1/participation/events", REPORT),
        ("GET", "/v1/participation/summary", None),
        ("DELETE", "/v1/participation", None),
    ]


def test_no_enable_without_strict_acknowledgment_and_exact_policy():
    seen = []
    network = client(lambda request: seen.append(request) or response({}))
    for acknowledgment in (False, 1, "true", None):
        with pytest.raises(ValueError, match="acknowledgment"):
            network.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=acknowledgment)
    with pytest.raises(ValueError, match="policy"):
        network.enable_task_sharing(policy_version="old-policy", acknowledge_data_notice=True)
    assert seen == []


@pytest.mark.parametrize("changes", [
    {"event_id": "contains-private-information"}, {"grant_id": 123}, {"grant_id": GRANT_ID.upper()},
    {"goal": "buy a private item"}, {"topic": "private-client-project"}, {"stage": "paid"},
    {"outcome": True}, {"traffic_class": "verified"}, {"prompt": "private prompt"},
])
def test_sdk_rejects_undeclared_fields_before_transport(changes):
    seen = []
    network = client(lambda request: seen.append(request) or response({}))
    with pytest.raises((ValueError, TypeError)):
        network.report_task(**(REPORT | changes))
    assert seen == []


def test_uncertain_receipt_does_not_retry_or_refresh_grant():
    seen = []

    def handle(request):
        seen.append(json.loads(request.content))
        raise httpx.ReadTimeout("private upstream detail")

    network = client(handle)
    with pytest.raises(NetworkDeliveryError, match="receipt not confirmed") as error:
        network.report_task(**REPORT)
    assert "private upstream detail" not in str(error.value)
    assert seen == [REPORT]


def test_mcp_schemas_reject_private_fields_and_expose_no_owner_enable_tool():
    from mcp.server.fastmcp.exceptions import ToolError
    seen = []

    def handle(request):
        seen.append((request.method, request.url.path, json.loads(request.content) if request.content else None))
        return response({"status": "accepted", "event_id": EVENT_ID, "evidence_kind": "self_reported"})

    async def run():
        server = create_mcp(client(handle))
        inventory = {tool.name: tool for tool in await server.list_tools()}
        participation = {name for name in inventory if "participation" in name or name in {
            "seiche_network_task_contract", "seiche_network_task_summary", "seiche_network_report_task"}}
        assert participation == {"seiche_network_task_contract", "seiche_network_participation",
                                  "seiche_network_task_summary", "seiche_network_report_task"}
        report = inventory["seiche_network_report_task"]
        assert report.annotations.idempotentHint and not report.annotations.readOnlyHint
        assert set(report.inputSchema["properties"]) == set(REPORT)
        for changes in ({"prompt": "private prompt"}, {"goal": "trade"}, {"grant_id": 123},
                        {"stage": "paid"}, {"event_id": EVENT_ID + "\n"}, {"outcome": False}):
            with pytest.raises(ToolError, match="invalid_request") as error:
                await server.call_tool("seiche_network_report_task", REPORT | changes)
            assert "private prompt" not in str(error.value)
        assert seen == []
        for name, path in (("seiche_network_task_contract", "/v1/participation/contract"),
                           ("seiche_network_participation", "/v1/participation"),
                           ("seiche_network_task_summary", "/v1/participation/summary")):
            assert inventory[name].annotations.readOnlyHint
            await server.call_tool(name, {})
            assert seen[-1] == ("GET", path, None)
        await server.call_tool("seiche_network_report_task", REPORT)
        assert seen[-1] == ("POST", "/v1/participation/events", REPORT)

    asyncio.run(run())


def test_real_api_owner_grant_withdrawal_and_reenable_do_not_revive_old_report(tmp_path):
    pytest.importorskip("seiche_agent_network")
    from fastapi.testclient import TestClient
    from seiche_agent_network.api import create_app
    from seiche_agent_network.crypto import generate_keys
    from seiche_agent_network.store import Store

    store = Store(tmp_path / "network.db", **generate_keys())
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
            assert agent_client.participation_status()["enabled"] is False
            with pytest.raises(NetworkDeliveryError):
                agent_client.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=True)
            grant = owner_client.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=True)
            assert grant["shared_training"] is False and grant["data_resale_permission"] is False
            report = REPORT | {"grant_id": grant["grant_id"], "traffic_class": "synthetic"}
            assert agent_client.report_task(**report)["status"] == "accepted"
            assert agent_client.report_task(**report)["status"] == "duplicate"
            owner_client.withdraw_task_sharing()
            assert agent_client.participation_status()["enabled"] is False
            fresh = owner_client.enable_task_sharing(policy_version=TASK_POLICY_VERSION, acknowledge_data_notice=True)
            assert fresh["grant_id"] != grant["grant_id"]
            with pytest.raises(NetworkDeliveryError):
                agent_client.report_task(**report)
            current = report | {"event_id": str(uuid4()), "grant_id": fresh["grant_id"]}
            assert agent_client.report_task(**current)["status"] == "accepted"
    finally:
        store.close()
