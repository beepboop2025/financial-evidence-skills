"""Exercise Workspace manifests, REST and real SDK MCP wire responses."""

import asyncio
import importlib.util
import unittest
from unittest.mock import patch

from test_openbb_tables import MONEY, source_result
from financial_evidence.service import EvidenceService
from financial_evidence.tables import DATASETS
from financial_evidence.workspace_config import apps, widgets

HAS_WORKSPACE = all(
    importlib.util.find_spec(name) for name in ("fastapi", "mcp", "httpx")
)
HAS_OPENBB = importlib.util.find_spec("openbb_core") is not None


class ManifestTests(unittest.TestCase):
    def test_layout_references_real_widgets_and_valid_default_parameters(self):
        definitions = widgets()
        self.assertEqual(len(definitions), 8)
        app = apps("http://localhost:6900")[0]
        self.assertEqual(app["mcp_servers"][0]["url"], "http://localhost:6900/mcp")
        for tab in app["tabs"].values():
            for placed in tab["layout"]:
                widget = definitions[placed["i"]]
                if widget["type"] == "table":
                    self.assertEqual(widget["data"]["dataKey"], "results")
                    self.assertEqual(
                        widget["mcp_tool"]["mcp_server"], app["mcp_servers"][0]["name"]
                    )
                    self.assertIn(placed["state"]["params"]["dataset"], DATASETS)
                    declared = {param["paramName"] for param in widget["params"]}
                    self.assertTrue(set(placed["state"]["params"]).issubset(declared))
        history = definitions["evidence_money_market_history"]["data"]["table"]
        self.assertTrue(history["chartView"]["enabled"])
        self.assertEqual(
            history["chartView"]["cellRangeCols"]["line"], ["as_of", "value"]
        )


@unittest.skipUnless(
    HAS_WORKSPACE, "Install .[workspace] for REST/MCP integration tests"
)
class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from financial_evidence.workspace import create_app

        self.calls = []

        def fetcher(source, **kwargs):
            self.calls.append(source.url)
            return source_result(source, MONEY)

        self.service = EvidenceService(fetcher=fetcher)
        self.addCleanup(self.service.close)
        self.app = create_app(service=self.service, base_url="http://localhost:6900")
        self.client = TestClient(self.app, base_url="http://localhost:6900")
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def rpc(self, method, params=None):
        response = self.client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
            headers={
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-11-25",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_rest_query_is_typed_cited_and_paginated(self):
        response = self.client.get(
            "/api/v1/query",
            params={"dataset": "money_market_history", "entity": "usd", "limit": 1},
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["schema"], "liquidity-lab.openbb-table.v1")
        self.assertEqual(result["next_offset"], 1)
        self.assertEqual(result["results"][0]["value"], 4.5)
        schema = self.client.get("/openapi.json").json()
        self.assertIn("EvidenceRow", schema["components"]["schemas"])
        self.assertEqual(
            schema["paths"]["/api/v1/query"]["get"]["responses"]["200"]["content"][
                "application/json"
            ]["schema"]["$ref"],
            "#/components/schemas/QueryResult",
        )

    def test_bad_parameters_fail_before_upstream_requests(self):
        for params in (
            {"dataset": "bad"},
            {"dataset": "money_markets", "limit": 2001},
            {"dataset": "money_markets", "start_date": "wrong"},
        ):
            self.assertEqual(
                self.client.get("/api/v1/query", params=params).status_code, 422
            )
        self.assertEqual(self.calls, [])

    def test_health_does_not_claim_upstream_readiness(self):
        self.assertEqual(
            self.client.get("/healthz").json()["upstream_status"], "not_checked"
        )
        self.assertEqual(self.calls, [])

    def test_unknown_host_and_untrusted_browser_origin_are_rejected(self):
        self.assertEqual(
            self.client.get("/healthz", headers={"Host": "evil.example"}).status_code,
            400,
        )
        for origin, expected in (
            ("https://pro.openbb.co", 200),
            ("https://evil.example", 400),
        ):
            result = self.client.options(
                "/mcp",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,mcp-protocol-version",
                },
            )
            self.assertEqual(result.status_code, expected)
        result = self.client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={
                "Origin": "https://evil.example",
                "Accept": "application/json, text/event-stream",
            },
        )
        self.assertIn(result.status_code, (400, 403))

    def test_mcp_initialization_discovery_output_schema_and_query_match_rest(self):
        initialized = self.rpc(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        )
        self.assertEqual(
            initialized["result"]["serverInfo"]["name"], "Financial Evidence Workspace"
        )
        tools = self.rpc("tools/list")["result"]["tools"]
        self.assertEqual(len(tools), 5)
        for tool in tools:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["destructiveHint"])
        query_tool = next(
            tool for tool in tools if tool["name"] == "financial_evidence_query"
        )
        self.assertIn("outputSchema", query_tool)
        self.assertEqual(
            query_tool["inputSchema"]["properties"]["limit"]["maximum"], 2000
        )
        result = self.rpc(
            "tools/call",
            {
                "name": "financial_evidence_query",
                "arguments": {"dataset": "money_markets", "entity": "usd"},
            },
        )
        self.assertFalse(result["result"].get("isError"), result)
        rest = self.client.get(
            "/api/v1/query", params={"dataset": "money_markets", "entity": "usd"}
        ).json()
        structured = result["result"]["structuredContent"]
        self.assertEqual(structured["results"], rest["results"])
        self.assertEqual(structured["schema"], rest["schema"])
        self.assertEqual(len(self.calls), 1)

    def test_mcp_rejects_invalid_input_and_exposes_prompts_and_resources(self):
        result = self.rpc(
            "tools/call",
            {
                "name": "financial_evidence_query",
                "arguments": {"dataset": "money_markets", "limit": 9000},
            },
        )
        self.assertTrue(result["result"]["isError"])
        self.assertEqual(self.calls, [])
        self.assertEqual(len(self.rpc("resources/list")["result"]["resources"]), 2)
        self.assertEqual(len(self.rpc("prompts/list")["result"]["prompts"]), 2)

    def test_real_widget_queries_resolve_and_mcp_url_is_same_backend(self):
        self.assertEqual(
            self.client.get("/apps.json").json()[0]["mcp_servers"][0]["url"],
            "http://localhost:6900/mcp",
        )
        for widget in self.client.get("/widgets.json").json().values():
            if widget["type"] != "table":
                continue
            response = self.client.get(
                "/" + widget["endpoint"],
                params={
                    param["paramName"]: param["value"] for param in widget["params"]
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIsInstance(response.json()[widget["data"]["dataKey"]], list)


@unittest.skipUnless(HAS_OPENBB, "Install .[openbb] for OpenBB integration tests")
class OpenBBTests(unittest.TestCase):
    def test_generated_commands_preserve_evidence_with_execution_metadata(self):
        from openbb_core.app.command_runner import CommandRunner, ExecutionContext
        from openbb_core.app.model.user_settings import UserSettings
        from openbb_core.app.router import CommandMap, Router
        from openbb_core.app.static.package_builder import ModuleBuilder, PathHandler
        from financial_evidence.openbb_router import router

        root = Router()
        root.include_router(router, prefix="/financial_evidence")
        routes = {route.path: route for route in root.api_router.routes}
        with (
            patch.object(PathHandler, "build_route_map", return_value=routes),
            patch.object(PathHandler, "get_router_dependencies", return_value=[]),
        ):
            generated = ModuleBuilder.build("/financial_evidence")
        namespace = {"__name__": "generated_financial_evidence"}
        exec(compile(generated, "generated_financial_evidence.py", "exec"), namespace)
        generated_router = namespace["ROUTER_financial_evidence"]
        for command in ("datasets", "query", "sources", "routes", "fetch"):
            self.assertTrue(callable(getattr(generated_router, command)))
        settings = UserSettings()
        settings.preferences.metadata = True
        runner = CommandRunner(
            command_map=CommandMap(router=root), user_settings=settings
        )
        service = EvidenceService(
            fetcher=lambda source, **kwargs: source_result(source)
        )
        self.addCleanup(service.close)
        with (
            patch.object(ExecutionContext, "_route_map", routes),
            patch("financial_evidence.openbb_router._service", return_value=service),
        ):
            interface = generated_router(runner)
            self.assertEqual(len(interface.datasets().to_df()), 7)
            result = interface.query(dataset="money_markets", entity="usd")
        self.assertEqual(result.to_df().iloc[0]["value"], 0)
        self.assertEqual(result.extra["financial_evidence"]["total_rows"], 1)
        self.assertEqual(result.extra["metadata"].route, "/financial_evidence/query")

    def test_query_returns_dataframe_with_metadata_and_shared_semantics(self):
        from financial_evidence.openbb_router import query

        service = EvidenceService(
            fetcher=lambda source, **kwargs: source_result(source)
        )
        self.addCleanup(service.close)
        with patch("financial_evidence.openbb_router._service", return_value=service):
            result = asyncio.run(query(dataset="money_markets", entity="usd"))
        dataframe = result.to_df()
        self.assertEqual(dataframe.iloc[0]["value"], 0)
        self.assertEqual(dataframe.iloc[0]["as_of"], "2026-09-24")
        self.assertEqual(result.extra["financial_evidence"]["total_rows"], 1)
        self.assertEqual(
            result.extra["financial_evidence"]["evidence_status"], "not_evaluated"
        )


if __name__ == "__main__":
    unittest.main()
