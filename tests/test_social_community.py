"""Public community clients remain explicit, bounded and portable to stdlib CI."""
import importlib.util
import json
import unittest
from unittest.mock import patch

from financial_evidence.trading.network import (
    NetworkClient, NetworkDeliveryError, SOCIAL_POLICY_VERSION, create_mcp,
)

HAS_HTTPX = importlib.util.find_spec("httpx") is not None
HAS_MCP = importlib.util.find_spec("mcp") is not None
HAS_NETWORK = importlib.util.find_spec("seiche_agent_network") is not None
AGENT = "12345678-1234-4123-8123-123456789abc"
EVENT = "22345678-1234-4123-8123-123456789abc"
GRANT = "abcdef01-2345-4234-9234-123456789abc"
PROFILE = dict(display_name="Synthetic research agent", bio="A test profile", role="finance_research",
               topics=["funding"], policy_version=SOCIAL_POLICY_VERSION, acknowledged=True, traffic_class="synthetic")
POST = dict(event_id=EVENT, grant_id=GRANT, topic="funding", kind="research_note",
            text="Synthetic research note", source_urls=["https://example.org/evidence"], parent_id=None)


def response(value, status=200):
    import httpx
    return httpx.Response(status, headers={"content-type": "application/json"},
                          stream=httpx.ByteStream(json.dumps(value).encode()))


def client(handler=None):
    options = {}
    if handler is not None:
        import httpx
        options["transport"] = httpx.MockTransport(handler)
    return NetworkClient("https://platform.example", "private-provisioned-token", **options)


class CommunityValidationTests(unittest.TestCase):
    def test_publication_requires_owner_notice_and_declared_fields(self):
        network = client()
        with patch.object(network, "request") as request:
            for changes in ({"acknowledged": False}, {"acknowledged": 1}, {"policy_version": "old"},
                            {"display_name": "x" * 81}, {"bio": "x" * 601}, {"topics": ["funding"] * 5},
                            {"topics": ["private_plan"]}, {"role": "verified_human"},
                            {"website_url": "http://example.org"}, {"website_url": "https://127.0.0.1"},
                            {"traffic_class": "verified"}, {"private_prompt": "do not share"}):
                with self.subTest(changes=changes):
                    with self.assertRaises((ValueError, TypeError)):
                        network.publish_social_profile(AGENT, **(PROFILE | changes))
            request.assert_not_called()

    def test_posts_require_current_retry_identity_and_bounded_authorized_content(self):
        network = client()
        changes = ({"event_id": True}, {"grant_id": GRANT.upper()}, {"text": " "}, {"text": "x" * 2001},
                   {"source_urls": []}, {"source_urls": ["https://example.org"] * 4},
                   {"source_urls": ["https://user:secret@example.org"]},
                   {"source_urls": ["https://example.org/#fragment"]}, {"source_urls": ["https://[::1]"]},
                   {"source_urls": ["https://192.168.1.1/path"]}, {"source_urls": ["https://localhost/"]},
                   {"source_urls": ["https://0x7f.0.0.1/"]}, {"source_urls": ["https://0177.0.0.1/"]},
                   {"source_urls": ["https://2130706433/"]},
                   {"source_urls": ["https://example.org/\nsecret"]}, {"topic": "private_plan"},
                   {"kind": "execute_trade"}, {"kind": "reply", "parent_id": None},
                   {"parent_id": EVENT}, {"prompt": "do not share"})
        with patch.object(network, "request") as request:
            for change in changes:
                with self.subTest(changes=change):
                    with self.assertRaises((ValueError, TypeError)):
                        network.create_social_post(**(POST | change))
            request.assert_not_called()

    def test_search_and_report_bounds_validate_without_optional_dependencies(self):
        network = client()
        with patch.object(network, "request") as request:
            for kwargs in ({"limit": True}, {"limit": 51}, {"cursor": "x" * 257}, {"q": "x" * 81},
                           {"include_synthetic": "true"}, {"role": "unknown"}):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(ValueError):
                        network.social_profiles(**kwargs)
            for kwargs in ({"limit": 0}, {"agent_id": "../private"}, {"parent_id": True}, {"kind": "execute"}):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(ValueError):
                        network.social_feed(**kwargs)
            with self.assertRaises(ValueError):
                network.report_social_post(EVENT, reason="x" * 1001)
            request.assert_not_called()


@unittest.skipUnless(HAS_HTTPX, "optional HTTP transport dependency required")
class CommunityTransportTests(unittest.TestCase):
    def test_explicit_routes_keep_publication_separate_from_posting(self):
        seen = []

        def handle(request):
            seen.append((request.method, request.url.path, dict(request.url.params),
                         json.loads(request.content) if request.content else None))
            return response({"status": "accepted"})

        network = client(handle)
        self.assertEqual(seen, [])
        network.social_contract()
        network.social_profiles(topic="funding", q="research", limit=2)
        network.social_profile(AGENT)
        network.social_me()
        network.publish_social_profile(AGENT, **PROFILE)
        self.assertEqual(seen[-1][0:2], ("PUT", "/v1/social/profiles/" + AGENT))
        self.assertEqual(seen[-1][3], PROFILE | {"website_url": None})
        network.create_social_post(**POST)
        self.assertEqual(seen[-1], ("POST", "/v1/social/posts", {}, POST))
        network.social_feed(parent_id=EVENT, include_synthetic=True)
        self.assertEqual(seen[-1][2], {"parent_id": EVENT, "limit": "20", "include_synthetic": "true"})
        network.social_post(EVENT)
        network.report_social_post(EVENT, reason="Synthetic review")
        self.assertEqual(seen[-1], ("POST", "/v1/social/posts/" + EVENT + "/report", {}, {"reason": "Synthetic review"}))
        network.delete_social_post(EVENT)
        network.withdraw_social_profile(AGENT)
        self.assertEqual(seen[-1][0:2], ("DELETE", "/v1/social/profiles/" + AGENT))
        self.assertEqual(len(seen), 11)

    def test_uncertain_receipt_keeps_old_grant_and_credentials_never_fall_back(self):
        import httpx
        seen = []

        def timeout(request):
            seen.append((request.method, request.url.path, json.loads(request.content)))
            raise httpx.ReadTimeout("private upstream detail")

        with self.assertRaisesRegex(NetworkDeliveryError, "receipt not confirmed") as error:
            client(timeout).create_social_post(**POST)
        self.assertNotIn("private upstream detail", str(error.exception))
        self.assertEqual(seen, [("POST", "/v1/social/posts", POST)])
        seen.clear()

        def unauthorized(request):
            seen.append(request.headers.get("authorization"))
            return response({"secret": "private rejection detail"}, 401)

        with self.assertRaisesRegex(NetworkDeliveryError, "HTTP 401"):
            client(unauthorized).social_feed()
        self.assertEqual(seen, ["Bearer private-provisioned-token"])


@unittest.skipUnless(HAS_HTTPX and HAS_MCP, "optional MCP and HTTP dependencies required")
class CommunityMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_are_bounded_and_never_publish_owner_profile(self):
        from mcp.server.fastmcp.exceptions import ToolError
        seen = []

        def handle(request):
            seen.append((request.method, request.url.path, json.loads(request.content) if request.content else None))
            return response({"status": "accepted", "post": {"id": EVENT, "evidence_kind": "agent_authored"}})

        server = create_mcp(client(handle))
        tools = {tool.name: tool for tool in await server.list_tools()}
        social = {name for name in tools if name.startswith("seiche_social_")}
        self.assertEqual(social, {"seiche_social_" + name for name in (
            "contract", "profiles", "profile", "me", "feed", "post", "create_post", "delete_post", "report_post")})
        self.assertTrue(tools["seiche_social_create_post"].annotations.idempotentHint)
        self.assertTrue(tools["seiche_social_delete_post"].annotations.destructiveHint)
        self.assertTrue(tools["seiche_social_feed"].annotations.readOnlyHint)
        for changes in ({"prompt": "private canary"}, {"grant_id": True}, {"source_urls": ["http://private"]},
                        {"text": "x" * 2001}, {"kind": "execute_trade"}):
            with self.subTest(changes=changes):
                with self.assertRaises(ToolError) as error:
                    await server.call_tool("seiche_social_create_post", POST | changes)
                self.assertNotIn("private canary", str(error.exception))
        for name, args in (("seiche_social_profiles", {"limit": True}), ("seiche_social_profiles", {"q": "x" * 81}),
                           ("seiche_social_feed", {"include_synthetic": "true"})):
            with self.assertRaises(ToolError):
                await server.call_tool(name, args)
        self.assertEqual(seen, [])
        await server.call_tool("seiche_social_create_post", POST)
        self.assertEqual(seen, [("POST", "/v1/social/posts", POST)])
        await server.call_tool("seiche_social_feed", {"parent_id": EVENT, "include_synthetic": True})
        self.assertEqual(seen[-1][0:2], ("GET", "/v1/social/posts"))


@unittest.skipUnless(HAS_HTTPX and HAS_NETWORK, "separate network service and optional HTTP dependency required")
class CommunityIntegrationTests(unittest.TestCase):
    def test_real_api_sdk_publishes_only_with_owner_grant_and_deleted_posts_stay_deleted(self):
        import httpx
        from pathlib import Path
        import tempfile
        from fastapi.testclient import TestClient
        from seiche_agent_network.api import create_app
        from seiche_agent_network.crypto import generate_keys
        from seiche_agent_network.store import Store

        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "community.db", **generate_keys())
            try:
                owner = store.bootstrap_org("Synthetic SDK community")
                principal = store.authenticate(owner["owner_token"])
                agent = store.register_agent(principal, "Synthetic community agent")
                with TestClient(create_app(store, purge_interval=0)) as api:
                    def dispatch(request):
                        result = api.request(request.method, request.url.raw_path.decode(),
                                             content=request.content, headers=dict(request.headers))
                        return httpx.Response(result.status_code, headers=dict(result.headers), stream=httpx.ByteStream(result.content))

                    transport = httpx.MockTransport(dispatch)
                    owner_client = NetworkClient("http://127.0.0.1:8765", owner["owner_token"], transport=transport)
                    agent_client = NetworkClient("http://127.0.0.1:8765", agent["token"], transport=transport)
                    with self.assertRaises(NetworkDeliveryError):
                        agent_client.publish_social_profile(agent["agent"]["id"], **PROFILE)
                    grant = owner_client.publish_social_profile(agent["agent"]["id"], **PROFILE)
                    self.assertEqual(agent_client.social_me()["profiles"][0]["grant_id"], grant["grant_id"])
                    self.assertNotIn("grant_id", agent_client.social_profile(agent["agent"]["id"]))
                    self.assertEqual(agent_client.social_profiles()["profiles"], [])
                    self.assertEqual(len(agent_client.social_profiles(include_synthetic=True)["profiles"]), 1)
                    post = POST | {"grant_id": grant["grant_id"]}
                    first = agent_client.create_social_post(**post)
                    self.assertEqual(first["status"], "accepted")
                    self.assertEqual(agent_client.create_social_post(**post)["status"], "duplicate")
                    self.assertEqual(agent_client.social_feed()["posts"], [])
                    self.assertEqual(len(agent_client.social_feed(include_synthetic=True)["posts"]), 1)
                    receipt = owner_client.report_social_post(first["post"]["id"], reason="Synthetic SDK moderation report")
                    self.assertEqual(receipt["status"], "recorded")
                    self.assertFalse(receipt["reviewed"])
                    agent_client.delete_social_post(first["post"]["id"])
                    with self.assertRaises(NetworkDeliveryError):
                        agent_client.create_social_post(**post)
                    owner_client.withdraw_social_profile(agent["agent"]["id"])
                    with self.assertRaises(NetworkDeliveryError):
                        agent_client.social_profile(agent["agent"]["id"])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
