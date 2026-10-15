"""Integration diagnostics must not turn connection success into trade approval."""
import asyncio
import contextlib
from copy import deepcopy
from datetime import datetime, timezone
import io
import importlib.util
import json
import os
import unittest
from unittest.mock import patch

from financial_evidence.trading.cli import main
from financial_evidence.trading.readiness import PROBES, check_readiness, exit_code, probe_mcp

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


def status_document():
    return {"schema": "seiche-agent-network.freshness.v1",
            "evaluated_at": "2026-10-15T11:59:00Z", "monitor_current": True,
            "monitor_age_seconds": 60, "products": [
                {"product": product, "freshness": "unknown", "transport": "available",
                 "scope": "inspected_source_rows_only"} for product in PROBES]}


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def check(self, document=None, probe=None, **kwargs):
        async def fetch(url, timeout):
            self.assertEqual(url, "https://agents.seiche.info/v1/data-status")
            return deepcopy(status_document() if document is None else document)
        async def passed(url, tool, arguments, timeout):
            return {"status": "passed"}
        return await check_readiness(status_fetcher=fetch, probe=probe or passed, now=NOW, **kwargs)

    async def test_connection_and_current_monitor_never_approve_unknown_inputs(self):
        result = await self.check()
        self.assertEqual(exit_code(result), 0)
        self.assertEqual(result["input_eligibility"], "not_evaluated")
        self.assertEqual(result["execution_authority"], "none")
        self.assertEqual(result["external_adoption"], "not_measured")
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(result["traffic_class"], "synthetic")

    async def test_partial_and_restricted_sources_survive_successful_connections(self):
        document = status_document()
        document["products"][0].update(freshness="stale", coverage={"fresh": 120, "stale": 26, "unknown": 16})
        document["products"][2].update(freshness="restricted", rights={"status": "pending_owner_review"})
        result = await self.check(document)
        self.assertEqual(result["connection_status"], "passed")
        rows = result["source_monitor"]["products"]
        self.assertEqual(rows[0]["coverage"]["stale"], 26)
        self.assertEqual(rows[2]["freshness"], "restricted")
        self.assertEqual(rows[2]["rights"], {"status": "pending_owner_review"})

    async def test_monitor_age_is_verified_independently_of_remote_boolean(self):
        for changes in [
            {"monitor_current": False}, {"monitor_age_seconds": 901},
            {"monitor_age_seconds": True}, {"monitor_age_seconds": -1},
            {"evaluated_at": "2026-10-14T11:59:00Z"},
            {"evaluated_at": "2026-10-15T12:02:00Z"},
        ]:
            with self.subTest(changes=changes):
                document = status_document()
                document.update(changes)
                result = await self.check(document)
                self.assertEqual(result["source_monitor"]["status"], "stale_or_unknown")
                self.assertEqual(exit_code(result), 2)

    async def test_invalid_or_incomplete_monitor_cannot_pass(self):
        for document in [[], {"error": "upstream refused"},
                         {**status_document(), "products": []},
                         {**status_document(), "products": status_document()["products"] * 2},
                         {**status_document(), "evaluated_at": "2026-10-15T11:59:00"},
                         {**status_document(), "monitor_age_seconds": float("nan")}]:
            result = await self.check(document)
            self.assertEqual(exit_code(result), 2)
            self.assertEqual(result["source_monitor"]["status"], "unavailable")

    async def test_one_failure_keeps_other_results_and_redacts_exception_contents(self):
        calls = []
        async def probe(url, tool, arguments, timeout):
            calls.append((url, tool, arguments))
            if "/seiche/" in url:
                raise OSError("Bearer PRIVATE-CREDENTIAL; upstream private body")
            return {"status": "passed"}
        result = await self.check(probe=probe)
        self.assertEqual(len(calls), 4)
        self.assertEqual(sum(row["status"] == "passed" for row in result["connections"]), 3)
        self.assertEqual(exit_code(result), 2)
        self.assertNotIn("PRIVATE-CREDENTIAL", json.dumps(result))

    async def test_deadline_cancels_hung_probe_without_retry_or_fallback(self):
        calls, cancelled = [], []
        async def probe(url, *_):
            calls.append(url)
            try:
                await asyncio.sleep(60)
            finally:
                cancelled.append(url)
        result = await asyncio.wait_for(self.check(probe=probe, timeout=0.01, products=["seiche"]), 0.5)
        self.assertEqual(len(calls), 1)
        self.assertEqual(cancelled, calls)
        self.assertEqual(result["connections"][0]["reason"], "timeout")

    async def test_missing_sdk_is_actionable_and_not_an_adoption_failure(self):
        async def missing(*_):
            raise ModuleNotFoundError("mcp")
        result = await self.check(probe=missing, products=["seiche", "seiche"])
        self.assertEqual(len(result["connections"]), 1)
        self.assertEqual(result["connections"][0]["reason"], "install_workspace_extra")
        self.assertEqual(result["external_adoption"], "not_measured")

    async def test_explicit_mcp_error_is_not_http_success(self):
        async def failed(*_):
            return {"status": "failed", "reason": "mcp_tool_error"}
        self.assertEqual(exit_code(await self.check(probe=failed)), 2)

    async def test_invalid_selection_and_deadline_do_not_make_requests(self):
        for kwargs in [{"products": []}, {"products": ["unknown"]}, {"timeout": True},
                       {"timeout": 0}, {"timeout": 121}, {"timeout": float("nan")}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                await self.check(**kwargs)


class ReadinessCliTests(unittest.TestCase):
    def test_anonymous_cli_ignores_even_invalid_ambient_credential(self):
        async def checked(**kwargs):
            self.assertEqual(kwargs, {"platform_url": None, "products": ["seiche"], "timeout": 10})
            return {"connection_status": "passed", "source_monitor": {"status": "current"}}
        with patch.dict(os.environ, {"SEICHE_NETWORK_TOKEN": "PRIVATE bad token"}):
            with patch.dict(os.environ, {}, clear=False), patch("financial_evidence.trading.readiness.check_readiness", checked):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(main(["doctor", "--product", "seiche", "--timeout", "10"]), 0)
        self.assertNotIn("PRIVATE", out.getvalue())


@unittest.skipUnless(importlib.util.find_spec("mcp") and importlib.util.find_spec("httpx"),
                     "MCP SDK is exercised in the workspace dependency job")
class McpProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_200_tool_refusal_is_a_failed_connection_check(self):
        import httpx
        client_type = httpx.AsyncClient
        requests = []

        def upstream(request):
            requests.append(request)
            if request.method != "POST":
                return httpx.Response(405)
            payload = json.loads(request.content)
            method = payload["method"]
            if "id" not in payload:
                return httpx.Response(202)
            if method == "initialize":
                result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "fixture", "version": "1"}}
            elif method == "tools/list":
                result = {"tools": [{"name": "liquidity_tiers", "inputSchema": {"type": "object"}}]}
            else:
                result = {"isError": True, "content": [{"type": "text", "text": "quota reached"}]}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})

        def client(**kwargs):
            return client_type(transport=httpx.MockTransport(upstream), **kwargs)

        with patch("httpx.AsyncClient", client):
            result = await probe_mcp("https://fixture.invalid/mcp", "liquidity_tiers", {}, 1)
        self.assertEqual(result, {"status": "failed", "reason": "mcp_tool_error"})
        self.assertTrue(requests)
        self.assertTrue(all("authorization" not in r.headers for r in requests))
        self.assertTrue(all(r.headers["X-Financial-Evidence-Traffic-Class"] == "synthetic" for r in requests))


if __name__ == "__main__":
    unittest.main()
