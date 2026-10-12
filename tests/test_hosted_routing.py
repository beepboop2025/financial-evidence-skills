"""Production entrypoints converge on hosted data without losing source identity."""
import asyncio
from contextlib import redirect_stdout
from email.message import Message
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import urllib.error
from unittest.mock import patch

import importlib.util
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from financial_evidence import cli, core, mcp, workflows
from financial_evidence.agents import EvidenceAgentClient, tool_functions
from financial_evidence.hosted import PLATFORM_URL, SOURCE_DATASETS, platform_base, source_endpoint
from financial_evidence.learning.contracts import tool_event
from financial_evidence.runtime import worker
from financial_evidence.runtime.contracts import presets
from financial_evidence.service import EvidenceService
from financial_evidence.trading.client import ProductClient, PRODUCTS, product_catalog
from financial_evidence.trading.cli import main as trading_cli
from test_openbb_tables import MONEY, source_result


class Response(io.BytesIO):
    def __init__(self, request_url, body, headers=None):
        super().__init__(body)
        self.url = request_url
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def geturl(self):
        return self.url


class HostedRoutingTests(unittest.TestCase):
    def test_fixed_raw_catalog_preserves_original_bytes_clocks_and_source_identity(self):
        calls = []
        body = json.dumps(MONEY).encode()
        sources = {source.url: source for group in core.ROUTES.values() for source in group}
        assert set(sources) == set(SOURCE_DATASETS)
        for original, source in sources.items():
            def opener(request, **kwargs):
                calls.append(request.full_url)
                assert request.data is None and request.get_method() == "GET"
                assert request.get_header("Authorization") is None
                return Response(request.full_url, body, {"X-Source-URL": original, "X-Dataset-ID": SOURCE_DATASETS[original]})
            result = core.fetch_source(source, max_bytes=100000, timeout=1, opener=opener)
            assert result["ok"] and result["source_url"] == original
            assert result["resolved_url"] == source_endpoint(original)
            assert result["dataset_id"] == SOURCE_DATASETS[original]
            assert result["content_sha256"] == "sha256:" + hashlib.sha256(body).hexdigest()
            assert result["document"] == MONEY and result["financial_authority"] == "none"
            assert result["transport_mode"] == "hosted"
        assert all(url.startswith(PLATFORM_URL + "/v1/data/") and "?" not in url for url in calls)


    def test_raw_failure_never_retries_anonymously_or_at_native_origin(self):
        for status in (401, 403, 429, 502):
            with self.subTest(status=status):
                calls = []
                def unavailable(request, **kwargs):
                    calls.append(request.full_url)
                    raise urllib.error.HTTPError(request.full_url, status, "private-error-token", {}, None)
                source = core.ROUTES["money-market"][0]
                result = core.fetch_source(source, max_bytes=1024, timeout=1, opener=unavailable)
                assert not result["ok"] and "document" not in result
                assert calls == [source_endpoint(source.url)]
                assert "private-error-token" not in json.dumps(result)


    def test_unreviewed_source_and_mismatched_gateway_identity_fail_closed(self):
        calls = []
        def opener(request, **kwargs):
            calls.append(request.full_url)
            return Response(request.full_url, b"{}", {"X-Dataset-ID": "wrong.dataset"})
        for url in ("https://attacker.example/data", "https://api.seiche.info/api/v2/money-markets?extra=private", "file:///etc/passwd"):
            assert not core.fetch_source(core.Source("Seiche", url, "unknown"), max_bytes=1024, timeout=1, opener=opener)["ok"]
        assert not calls
        assert not core.fetch_source(core.ROUTES["money-market"][0], max_bytes=1024, timeout=1, opener=opener)["ok"]
        assert len(calls) == 1


    def test_legacy_cli_mcp_service_framework_and_runtime_use_the_same_hosted_route(self):
        calls = []
        def opener(request, **kwargs):
            calls.append(request)
            return Response(request.full_url, json.dumps(MONEY).encode())
        with patch.dict(core.fetch_source.__kwdefaults__, {"opener": opener}), patch.dict(core.build_packet.__kwdefaults__, {"opener": opener}):
            output = io.StringIO()
            with redirect_stdout(output):
                assert cli.main(["fetch", "--topic", "money-market"]) == 0
            assert not mcp.call_tool("financial_evidence_fetch", {"topics": ["money-market"]})["isError"]
            with EvidenceAgentClient() as client:
                result = tool_functions(client)[1]("money_markets")
                assert result["results"][0]["value"] == 0
            output_bytes = io.BytesIO()
            with patch.object(worker, "FIXED_ROUTE_OPENER", opener), patch.object(worker.sys, "argv", ["worker", "--traffic-class", "synthetic"]), patch.object(worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(presets()[0]).encode()))), patch.object(worker.sys, "stdout", SimpleNamespace(buffer=output_bytes)):
                worker.main()
            assert json.loads(output_bytes.getvalue())["results"][0]["value"] == 0
        assert len(calls) == 4
        assert all(request.full_url == PLATFORM_URL + "/v1/data/seiche.money_markets" for request in calls)
        assert calls[-1].get_header("X-financial-evidence-traffic-class") == "synthetic"


    def test_sequential_default_reads_request_hosted_data_and_do_not_reuse_failures(self):
        calls = []
        def opener(request, **kwargs):
            calls.append(request.full_url)
            if len(calls) == 2:
                raise OSError("gateway unavailable")
            return Response(request.full_url, json.dumps(MONEY).encode())
        with patch.dict(core.fetch_source.__kwdefaults__, {"opener": opener}):
            service = EvidenceService()
            self.addCleanup(service.close)
            states = [service.packet(["money-market"])["transport_status"] for _ in range(3)]
        self.assertEqual(states, ["complete", "unavailable", "complete"])
        self.assertEqual(calls, [PLATFORM_URL + "/v1/data/seiche.money_markets"] * 3)
        self.assertEqual((service.ttl, service.error_ttl), (0, 0))

    def test_one_packet_shares_a_source_even_when_the_zero_ttl_fetch_is_finished(self):
        from concurrent.futures import Future
        calls = []
        class CompletedPool:
            def submit(self, fn, source):
                calls.append(source.url)
                future = Future()
                future.set_result(fn(source))
                return future
        service = EvidenceService(fetcher=lambda source, **kwargs: source_result(source))
        self.addCleanup(service.close)
        with patch.object(service, "_pool", CompletedPool()):
            packet = service.packet(["gift-city", "gold"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(packet["sources"]), 2)

    def test_all_product_defaults_and_download_config_are_hosted_without_credentials(self):
        environment = patch.dict(os.environ, {key: value for key, value in os.environ.items() if key not in {"SEICHE_AGENT_PLATFORM_URL", "SEICHE_NETWORK_TOKEN"}}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        output = io.StringIO()
        with redirect_stdout(output):
            assert trading_cli(["mcp-config"]) == 0
        configured = json.loads(output.getvalue())["mcpServers"]
        assert set(configured) == set(PRODUCTS)
        assert all(row["mcp_url"] == PLATFORM_URL + "/products/" + row["id"] + "/mcp" for row in product_catalog())
        assert all(row["url"] == PLATFORM_URL + "/products/" + key + "/mcp" for key, row in configured.items())
        assert all(row["hosted_operational_measurement"] and row["optional_learning_default"] == "off" for row in product_catalog())


    def test_malicious_or_ambiguous_platform_urls_rejected(self):
        for value in ("", "http://remote.example", "https://user:secret@example.test", "https://example.test/?private=1", "https://example.test/../escape", "https://example.test/%2e", "https://example.test\\evil", "https://example.test\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                platform_base(value)


    def test_custom_transport_and_platform_are_explicit_and_failure_is_single_attempt(self):
        calls = []
        async def unavailable(endpoint, *args):
            calls.append(endpoint)
            raise RuntimeError("unavailable")
        client = ProductClient(platform_url="http://127.0.0.1:1234/test", transport=unavailable)
        with self.assertRaises(RuntimeError):
            asyncio.run(client.call("seiche", "funding_stress_now"))
        assert calls == ["http://127.0.0.1:1234/test/products/seiche/mcp"]


    @unittest.skipUnless(importlib.util.find_spec("httpx"), "Install workflow HTTP dependencies")
    def test_workflow_fetches_bounded_central_routes_preserving_native_receipts(self):
        import httpx
        seen = []
        def stream(method, url, **kwargs):
            seen.append((method, url, kwargs))
            return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"schema": "liquilens.institution-monitoring.v1", "rows": []}))).stream(method, url, headers=kwargs["headers"])
        with patch.object(httpx, "stream", stream):
            result = workflows.run(None, "institutions", "au-sfb", synthetic=True)
            assert result["source_url"] == workflows.MONITOR + "?slugs=au-sfb"
            with self.assertRaises(ValueError):
                workflows.fetch_document("https://attacker.example/?slugs=au-sfb")
        assert len(seen) == 1 and seen[0][1] == PLATFORM_URL + "/v1/data/liquilens.institution_watchlist?slugs=au-sfb"
        assert seen[0][2]["follow_redirects"] is False
        assert seen[0][2]["headers"]["X-Financial-Evidence-Traffic-Class"] == "synthetic"


    def test_wake_is_an_admitted_optional_learning_product(self):
        event = {"id": "wake-request", "product": "wake", "tool": "wake_economy_now", "task": "research", "occurred_at": 100, "duration_ms": 1, "status": "success", "mode": "test"}
        assert tool_event(event, 100)["product"] == "wake"


    def test_every_catalog_product_is_admitted_to_optional_learning_with_separate_scopes(self):
        for product, entry in PRODUCTS.items():
            event = {"id": "request", "product": product, "tool": entry[2], "task": "research", "occurred_at": 100, "duration_ms": 1, "status": "success", "mode": "test"}
            assert tool_event(event, 100)["product"] == product
        catalog = {entry["id"]: entry for entry in product_catalog()}
        assert catalog["myquant-app"]["kind"] == "metadata_only"
        assert catalog["financial-evidence"]["kind"] == "research_wrapper"
        assert catalog["trade-safety"]["kind"] == "read_only_sandbox"
        assert not any(entry["nested_requests_are_additive"] for entry in catalog.values())


    def test_current_download_catalog_and_editor_configs_use_only_central_endpoints(self):
        root = Path(__file__).resolve().parents[1]
        for name in (".mcp.json", ".cursor/mcp.json", ".vscode/mcp.json", "integrations/mcp-config.json", "docs/connect/all-products.mcp.json", "docs/agents/mcp.remote.json", "docs/agents/mcp.vscode.json"):
            value = json.loads((root / name).read_text())
            servers = value.get("mcpServers", value.get("servers"))
            assert all(entry == {"type": "http", "url": PLATFORM_URL + f"/products/{key}/mcp"} for key, entry in servers.items()), name
        configured = json.loads((root / "docs/connect/all-products.mcp.json").read_text())["mcpServers"]
        assert set(configured) == set(PRODUCTS)


    def test_research_notebook_setup_accepts_the_adjacent_current_helper_without_network(self):
        root = Path(__file__).resolve().parents[1] / "docs/tools"
        notebook = json.loads((root / "research_desk.ipynb").read_text())
        setup = next("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code" and "CLIENT_SHA256" in "".join(cell["source"]))
        original_directory = os.getcwd()
        self.addCleanup(os.chdir, original_directory)
        os.chdir(root)
        namespace = {}
        with patch("urllib.request.urlopen", side_effect=AssertionError("adjacent kit must not download code")), redirect_stdout(io.StringIO()):
            exec(compile(setup, "notebook-setup", "exec"), namespace)
        assert namespace["research_client"].BASE_URL == PLATFORM_URL + "/v1/research"


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("mcp", "pydantic")), "Install workspace MCP dependencies")
class HostedWorkspaceDispatchTests(unittest.TestCase):
    def test_current_plugin_allowlist_dispatches_the_native_workspace_contract(self):
        from financial_evidence.workspace_mcp import create_mcp
        root = Path(__file__).resolve().parents[1]
        configured = json.loads((root / "gemini-extension.json").read_text())["mcpServers"]["financial-evidence"]
        fetched = []
        def fetcher(source, **kwargs):
            fetched.append(source.url)
            return source_result(source)
        service = EvidenceService(fetcher=fetcher)
        self.addCleanup(service.close)
        server = create_mcp(service)
        async def dispatch():
            names = {tool.name for tool in await server.list_tools()}
            self.assertEqual(names, set(configured["includeTools"]))
            self.assertEqual(configured["httpUrl"], PLATFORM_URL + "/products/financial-evidence/mcp")
            self.assertNotIn("financial_evidence_fetch", names)
            results = {}
            for name, arguments in (
                ("financial_evidence_datasets", {}),
                ("financial_evidence_agent_query", {"dataset": "money_markets", "limit": 1}),
                ("financial_evidence_review", {"limit": 1}),
                ("financial_evidence_packet", {"topics": ["money-market"]}),
            ):
                reply = await server.call_tool(name, arguments)
                results[name] = reply[1] if isinstance(reply, tuple) else json.loads(reply[0].text)
            return results
        results = asyncio.run(dispatch())
        self.assertTrue(results["financial_evidence_datasets"]["datasets"])
        query = results["financial_evidence_agent_query"]
        self.assertEqual(query["results"][0]["value"], 0)
        self.assertEqual(query["results"][0]["source_url"], core.ROUTES["money-market"][0].url)
        self.assertTrue(results["financial_evidence_review"]["sections"])
        self.assertEqual(results["financial_evidence_packet"]["transport_status"], "complete")
        self.assertTrue(fetched)


if __name__ == "__main__":
    unittest.main()
