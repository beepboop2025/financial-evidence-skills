"""Real MCP SDK transports, bounded native bridging and remote network controls."""

import asyncio
from contextlib import asynccontextmanager
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from financial_evidence.trading.client import PRODUCTS
from financial_evidence.trading.network import NetworkClient, NetworkDeliveryError, create_mcp
from financial_evidence.trading.product_mcp import BridgeError, MAX_RESPONSE_BYTES, create_server

HAS_MCP = importlib.util.find_spec("mcp") is not None
HAS_NETWORK = importlib.util.find_spec("seiche_agent_network") is not None

INPUT_SCHEMA = {"type": "object", "properties": {"country": {"type": "string", "enum": ["US", "CN"]},
                "options": {"type": "object", "properties": {"vintage": {"type": "integer", "minimum": 1}}}},
                "required": ["country"], "additionalProperties": False}
OUTPUT_SCHEMA = {"type": "object", "properties": {"rows": {"type": "array", "items": {"type": "number"}}}, "required": ["rows"]}


def native_tool(name="funding_stress_now"):
    from mcp.types import Tool, ToolAnnotations
    return Tool(name=name, title="Native funding", description="Original native schema", inputSchema=INPUT_SCHEMA,
                outputSchema=OUTPUT_SCHEMA, annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
                _meta={"revision": "synthetic-schema-v1"})


def native_result(error=False):
    from mcp.types import CallToolResult, TextContent
    return CallToolResult(content=[TextContent(type="text", text="Native structured result: Δ")],
                          structuredContent={"rows": [1.25, 2.5]}, isError=error, _meta={"source_revision": "test-only"})


def unpack(value):
    if isinstance(value, tuple):
        structured = value[1]
        return structured.get("result", structured)
    return json.loads(value[0].text)


@unittest.skipUnless(HAS_MCP, "optional official MCP SDK required")
class ProductBridgeTests(unittest.IsolatedAsyncioTestCase):
    def factory(self, *, result=None, pages=None, delay=0):
        from mcp.types import ListToolsResult
        calls = []

        class Upstream:
            async def list_tools(self, cursor=None):
                calls.append(("list", cursor))
                if delay:
                    await asyncio.sleep(delay)
                if pages:
                    return pages[cursor]
                return ListToolsResult(tools=[native_tool(), native_tool("unreviewed_write")])

            async def call_tool(self, name, arguments):
                calls.append(("call", name, arguments))
                if delay:
                    await asyncio.sleep(delay)
                if isinstance(result, Exception):
                    raise result
                return result if result is not None else native_result()

        @asynccontextmanager
        async def factory(endpoint, credential):
            calls.append(("session", endpoint, credential))
            yield Upstream()

        return factory, calls

    async def inventory(self, server):
        from mcp.types import ListToolsRequest
        return (await server.request_handlers[ListToolsRequest](ListToolsRequest(method="tools/list"))).root

    async def call(self, server, name="funding_stress_now", arguments=None):
        from mcp.types import CallToolRequest, CallToolRequestParams
        return (await server.request_handlers[CallToolRequest](CallToolRequest(method="tools/call", params=CallToolRequestParams(name=name, arguments=arguments or {"country": "US"})))).root

    async def test_native_schema_and_result_preserved_exactly(self):
        for error in (False, True):
            factory, calls = self.factory(result=native_result(error))
            server = create_server("seiche", PRODUCTS["seiche"][1], session_factory=factory)
            listed = await self.inventory(server)
            self.assertEqual([tool.model_dump(mode="json") for tool in listed.tools], [native_tool().model_dump(mode="json")])
            result = await self.call(server)
            self.assertEqual(result.model_dump(mode="json"), native_result(error).model_dump(mode="json"))
            self.assertEqual([call[2] for call in calls if call[0] == "session"], [None, None])

    async def test_unreviewed_call_never_reaches_upstream_and_private_errors_redacted(self):
        factory, calls = self.factory(result=RuntimeError("private-upstream-secret"))
        server = create_server("seiche", PRODUCTS["seiche"][1], session_factory=factory)
        denied = await self.call(server, "unreviewed_write")
        self.assertTrue(denied.isError)
        self.assertFalse(any(item[0] == "call" for item in calls))
        failure = await self.call(server)
        self.assertTrue(failure.isError)
        self.assertNotIn("private-upstream-secret", failure.model_dump_json())

    async def test_argument_response_and_pagination_limits(self):
        from mcp.types import CallToolResult, ListToolsResult, TextContent
        factory, calls = self.factory()
        server = create_server("seiche", PRODUCTS["seiche"][1], session_factory=factory)
        oversized = await self.call(server, arguments={"country": "x" * 17000})
        self.assertTrue(oversized.isError)
        self.assertFalse(any(item[0] == "call" for item in calls))
        factory, _ = self.factory(result=CallToolResult(content=[TextContent(type="text", text="x" * MAX_RESPONSE_BYTES)]))
        self.assertTrue((await self.call(create_server("seiche", PRODUCTS["seiche"][1], session_factory=factory))).isError)
        pages = {None: ListToolsResult(tools=[native_tool()], nextCursor="repeated"),
                 "repeated": ListToolsResult(tools=[], nextCursor="repeated")}
        factory, _ = self.factory(pages=pages)
        with self.assertRaises(BridgeError):
            await self.inventory(create_server("seiche", PRODUCTS["seiche"][1], session_factory=factory))

    async def test_deadline_and_configured_credential_destination(self):
        factory, calls = self.factory(delay=.05)
        server = create_server("seiche", PRODUCTS["seiche"][1], session_factory=factory, timeout=.01)
        with self.assertRaises(BridgeError):
            await self.inventory(server)
        for endpoint, platform in (("https://api.seiche.info/mcp", None), ("https://other.example/products/seiche/mcp", "https://approved.example")):
            with self.assertRaises(ValueError):
                create_server("seiche", endpoint, "private-provisioned-token", platform_url=platform, session_factory=factory)
        factory, calls = self.factory()
        server = create_server("seiche", "https://approved.example/products/seiche/mcp", "private-provisioned-token",
                               platform_url="https://approved.example", session_factory=factory)
        await self.inventory(server)
        self.assertEqual(calls[0], ("session", "https://approved.example/products/seiche/mcp", "private-provisioned-token"))

    async def test_real_stdio_handshake_and_native_tool_result(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        script = r'''
import asyncio
from contextlib import asynccontextmanager
from mcp.types import Tool, ToolAnnotations, ListToolsResult, CallToolResult, TextContent
from financial_evidence.trading import product_mcp
INPUT = INPUT_LITERAL
OUTPUT = OUTPUT_LITERAL
class Upstream:
    async def list_tools(self, cursor=None):
        return ListToolsResult(tools=[Tool(name="funding_stress_now", title="Native funding", description="Original native schema", inputSchema=INPUT, outputSchema=OUTPUT, annotations=ToolAnnotations(readOnlyHint=True,idempotentHint=True), _meta={"revision":"synthetic-schema-v1"})])
    async def call_tool(self, name, arguments):
        return CallToolResult(content=[TextContent(type="text",text="Native structured result: Δ")],structuredContent={"rows":[1.25,2.5]},isError=False,_meta={"source_revision":"test-only"})
@asynccontextmanager
async def factory(endpoint, credential):
    assert endpoint == "https://agents.seiche.info/products/seiche/mcp"
    assert credential == "secret-not-for-public-product", "only the configured central gateway receives the token"
    yield Upstream()
product_mcp.create_server.__kwdefaults__["session_factory"] = factory
product_mcp.main(["--product","seiche"])
'''.replace("INPUT_LITERAL", repr(INPUT_SCHEMA)).replace("OUTPUT_LITERAL", repr(OUTPUT_SCHEMA))
        params = StdioServerParameters(command=sys.executable, args=["-c", script],
                 env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"), "SEICHE_NETWORK_TOKEN": "secret-not-for-public-product"})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                self.assertEqual(initialized.serverInfo.name, "Seiche")
                inventory = await session.list_tools()
                self.assertEqual(inventory.tools[0].model_dump(mode="json"), native_tool().model_dump(mode="json"))
                result = await session.call_tool("funding_stress_now", {"country": "US"})
                self.assertEqual(result.model_dump(mode="json"), native_result().model_dump(mode="json"))


@unittest.skipUnless(HAS_MCP, "optional workspace dependencies required")
class RemoteNetworkTests(unittest.IsolatedAsyncioTestCase):
    def client(self, handler, timeout=1):
        import httpx
        return NetworkClient("https://platform.example", "private-provisioned-token", timeout=timeout, transport=httpx.MockTransport(handler))

    def response(self, value, status=200, headers=None):
        import httpx
        return httpx.Response(status, stream=httpx.ByteStream(json.dumps(value).encode()), headers=headers or {"content-type": "application/json"})

    async def test_cursor_contact_membership_and_completion_schemas(self):
        seen = []
        def handler(request):
            seen.append((request.method, request.url.path, dict(request.url.params), json.loads(request.content) if request.content else None))
            self.assertEqual(request.headers["user-agent"], "Seiche-Agent-Network/0.1")
            if request.url.path == "/v1/rooms":
                return self.response([{"id": "room-1", "members": [{"agent_id": "agent-2", "status": "active"}]}])
            if request.url.path.endswith("/messages") and request.method == "GET":
                return self.response([])
            return self.response({"id": "test-only", "next_cursor": 13})
        server = create_mcp(self.client(handler))
        inventory = {tool.name: tool for tool in await server.list_tools()}
        self.assertEqual(len(inventory), 38)
        self.assertTrue(inventory["seiche_network_revoke_contact"].annotations.destructiveHint)
        self.assertTrue(inventory["seiche_network_messages"].annotations.readOnlyHint)
        await server.call_tool("seiche_network_inbox", {"after": 12, "limit": 2})
        self.assertEqual(seen[-1], ("GET", "/v1/inbox", {"after": "12", "limit": "2"}, None))
        members = unpack(await server.call_tool("seiche_network_members", {"room_id": "room-1"}))
        self.assertEqual(members, [{"agent_id": "agent-2", "status": "active"}])
        for tool, args, method, path, body in (
            ("seiche_network_revoke_contact", {"contact_id": "contact-1"}, "POST", "/v1/contacts/contact-1/revoke", {}),
            ("seiche_network_block", {"target_agent_id": "agent-2"}, "POST", "/v1/blocks", {"target_agent_id": "agent-2"}),
            ("seiche_network_remove_member", {"room_id": "room-1", "agent_id": "agent-2"}, "DELETE", "/v1/rooms/room-1/members/agent-2", None),
            ("seiche_network_cancel_task", {"message_id": "message-1"}, "POST", "/v1/tasks/message-1/cancel", {}),
            ("seiche_network_usefulness", {"message_id": "message-1", "useful": True}, "POST", "/v1/tasks/message-1/complete", {"useful": True}),
        ):
            await server.call_tool(tool, args)
            self.assertEqual(seen[-1], (method, path, {}, body))

    async def test_invalid_fields_redacted_and_redirects_do_not_forward_tokens(self):
        from mcp.server.fastmcp.exceptions import ToolError
        seen = []
        def handler(request):
            seen.append(str(request.url))
            self.assertEqual(request.headers["authorization"], "Bearer private-provisioned-token")
            return self.response({}, status=302, headers={"location": "https://other.example/steal"})
        client = self.client(handler)
        server = create_mcp(client)
        for args in ({"after": True}, {"limit": 101}, {"private": "secret-private-value"}):
            with self.assertRaises(ToolError) as caught:
                await server.call_tool("seiche_network_inbox", args)
            self.assertNotIn("secret-private-value", str(caught.exception))
        self.assertEqual(seen, [])
        with self.assertRaises(ToolError) as caught:
            await server.call_tool("seiche_network_identity", {})
        self.assertIn("HTTP 302", str(caught.exception))
        self.assertEqual(seen, ["https://platform.example/v1/me"])
        self.assertNotIn("private-provisioned-token", str(caught.exception))
        for path in ("/v1/../me", "/v1/rooms/a%2Fb/messages", "https://other.example/v1/me", "/v1/inbox?q=secret"):
            with self.assertRaises(ValueError):
                client.request("GET", path)

    async def test_response_bytes_and_total_deadline_bounded(self):
        import httpx
        client = self.client(lambda request: httpx.Response(200, stream=httpx.ByteStream(b"x" * (MAX_RESPONSE_BYTES + 1))))
        with self.assertRaises(NetworkDeliveryError):
            client.request("GET", "/v1/me")
        class Slow(httpx.SyncByteStream):
            def __iter__(self):
                time.sleep(.02)
                yield b"{}"
        client = self.client(lambda request: httpx.Response(200, stream=Slow()), timeout=.01)
        with self.assertRaises(NetworkDeliveryError):
            client.request("GET", "/v1/me")


@unittest.skipUnless(HAS_MCP and HAS_NETWORK, "separate Seiche service source required for optional integration")
class ActualNetworkIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_mcp_to_real_local_api_delivery_and_usefulness(self):
        import httpx
        from fastapi.testclient import TestClient
        from seiche_agent_network.api import create_app
        from seiche_agent_network.crypto import generate_keys
        from seiche_agent_network.store import Store
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "network.db", **generate_keys())
            self.addCleanup(store.close)
            people = []
            for label in ("Synthetic A", "Synthetic B"):
                owner = store.bootstrap_org(label)
                principal = store.authenticate(owner["owner_token"])
                agent = store.register_agent(principal, label, public=True)
                people.append(agent)
            a, b = people
            with TestClient(create_app(store, purge_interval=0)) as local:
                def dispatch(request):
                    response = local.request(request.method, request.url.raw_path.decode(), content=request.content, headers=dict(request.headers))
                    return httpx.Response(response.status_code, headers=dict(response.headers), stream=httpx.ByteStream(response.content))
                def remote(agent):
                    return create_mcp(NetworkClient("http://127.0.0.1:8765", agent["token"], transport=httpx.MockTransport(dispatch)))
                first, second = remote(a), remote(b)
                contact = unpack(await first.call_tool("seiche_network_invite", {"target_agent_id": b["agent"]["id"]}))
                await second.call_tool("seiche_network_accept_contact", {"contact_id": contact["id"]})
                room = unpack(await first.call_tool("seiche_network_create_room", {"label": "Synthetic private room", "participant_ids": [b["agent"]["id"]]}))
                await second.call_tool("seiche_network_accept_room", {"room_id": room["id"]})
                message = unpack(await first.call_tool("seiche_network_send", {"room_id": room["id"], "kind": "question", "text": "Synthetic evidence request", "idempotency_key": "test-1"}))
                inbox = unpack(await second.call_tool("seiche_network_inbox", {"after": 0, "limit": 1}))
                self.assertEqual(inbox["items"][0]["message"]["id"], message["id"])
                receipt = unpack(await second.call_tool("seiche_network_ack", {"message_id": message["id"]}))
                self.assertEqual(receipt["meaning"], "receipt_only")
                await second.call_tool("seiche_network_status", {"message_id": message["id"], "status": "completed"})
                feedback = unpack(await first.call_tool("seiche_network_usefulness", {"message_id": message["id"], "useful": True}))
                self.assertTrue(feedback["useful"])
                await first.call_tool("seiche_network_revoke_contact", {"contact_id": contact["id"]})
                self.assertEqual(unpack(await second.call_tool("seiche_network_rooms", {})), [])


if __name__ == "__main__":
    unittest.main()
