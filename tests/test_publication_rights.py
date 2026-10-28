"""Reviewed source policy must hold for packets and legacy table inputs."""
import copy
import hashlib
import json
import sys
import unittest
import importlib.util
import tempfile
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from financial_evidence import core
from financial_evidence.tables import query_packet
from test_package import Response


def capital_document():
    return {
        "schema": "seiche.world-markets.v1",
        "capital_markets": {
            "risk_context": {
                "as_of": "2026-10-26",
                "funding_stress": {"value": 777.123, "regime": "SECRET-DERIVED"},
                "market_vs_plumbing": {"components": {"value": 777.123}, "reading": "SECRET-DERIVED"},
                "market_prices": {
                    "vix": {"value": 777.123, "as_of": "2026-10-26", "source_registry_ids": ["cboe_vix", "fred"]},
                    "high_yield_oas": {"value": 777.123, "as_of": "2026-10-26", "source_registry_ids": ["fred"]},
                },
            },
            "positioning": [
                {"id": "officialbid", "as_of": "2026-10-26", "value": 777.123, "reading": "SECRET-DERIVED"},
                {"id": "rvxray", "value": 0, "source_registry_ids": ["cftc"]},
            ],
            "primary_market": [{"id": "auctions", "value": 0, "source_registry_ids": ["treasury"]}],
        },
    }



def forex_document():
    return {
        "schema": "seiche.world-markets.v1",
        "generated_at": "2026-10-28T00:00:00Z",
        "selection": "forex",
        "summary": {"reading": "SECRET-DERIVED 777.123"},
        "forex": {
            "as_of": "2026-10-26",
            "headline": {"fx_pressure": 777.123, "verdict": "SECRET-DERIVED"},
            "currencies": [{"currency": "EUR", "value": 777.123}],
            "harbors": [{"reading": "SECRET-DERIVED"}],
            "new_unreviewed_field": {"history": [777.123]},
        },
    }


def money_document():
    metric = {"id": "US.NYFED.SOFR", "mnemonic": "SOFR", "value": 777.123,
              "source_url": "https://fred.stlouisfed.org/", "redistribution_status": "allowed",
              "asof": "2026-10-26", "unit": "%", "history": [["2026-10-26", 777.123]],
              "change_5d": 777.123, "reading": "SECRET-DERIVED"}
    direct = {"id": "EA.ECB.ESTR", "value": 0, "source_url": "https://data.ecb.europa.eu/",
              "asof": "2026-10-26", "history": [["2026-10-26", 0]], "redistribution_status": "allowed"}
    return {"schema": "seiche.global-money-markets.v1", "markets": [
        {"market_id": "US-USD", "benchmark": metric, "policy_anchor": copy.deepcopy(metric),
         "derived_benchmark": copy.deepcopy(metric), "metrics": [copy.deepcopy(metric), direct],
         "policy_relative_spread": {"value": 777.123}, "quant_read": "SECRET-DERIVED",
         "plain_language": "SECRET-DERIVED", "countercase": "SECRET-DERIVED"},
        {"market_id": "EA-EUR", "benchmark": direct},
    ]}


def packet(topic, document):
    return {"transport_status": "complete", "absence_policy": core.ABSENCE_POLICY, "sources": [{
        "source_url": core.ROUTES[topic][0].url, "product": core.ROUTES[topic][0].product, "topic": topic, "ok": True,
        "document": document, "retrieved_at": "2026-10-28T00:00:00Z",
    }]}











class PublicationRightsTests(unittest.TestCase):
    def test_capital_packet_withholds_raw_and_dependent_values_preserving_provenance(self):
        document = capital_document()
        original = copy.deepcopy(document)
        output, receipt = core.publication_projection(core.ROUTES["capital-market"][0].url, document)
        assert document == original
        assert "777.123" not in json.dumps(output)
        assert "SECRET-DERIVED" not in json.dumps(output)
        prices = output["capital_markets"]["risk_context"]["market_prices"]
        assert prices["vix"]["as_of"] == "2026-10-26"
        assert prices["vix"]["source_registry_ids"] == ["cboe_vix", "fred"]
        assert prices["high_yield_oas"]["rights_urls"][-1].endswith("/BAMLH0A0HYM2")
        assert output["capital_markets"]["positioning"][1]["value"] == 0
        assert output["capital_markets"]["primary_market"] == original["capital_markets"]["primary_market"]
        assert receipt["document_is_original"] is False
        assert core.publication_projection(core.ROUTES["capital-market"][0].url, output)[0] == output


    def test_forex_snapshot_is_metadata_only_while_independent_ecb_route_is_unchanged(self):
        original = forex_document()
        output, receipt = core.publication_projection(core.ROUTES["forex"][0].url, original)
        assert "777.123" not in json.dumps(output)
        assert "SECRET-DERIVED" not in json.dumps(output)
        assert output["forex"]["as_of"] == "2026-10-26"
        assert output["generated_at"] == original["generated_at"]
        assert output["forex"]["publication_allowed"] is False
        assert core._projection_receipt(output, [], "")["content_sha256"] == receipt["content_sha256"]
        assert core.publication_projection(core.ROUTES["forex"][0].url, output)[0] == output
        direct = {"schema": "seiche.gift-city.v1", "forex": {
            "provider": "ecb", "source_url": "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml",
            "rows": [{"value": 1.25}]}}
        for topic in ("gift-city", "gold"):
            assert core.publication_projection(core.ROUTES[topic][0].url, direct) == (direct, None)
        for malformed in ([777.123], {"schema": "changed", "forex": original["forex"]},
                          {"schema": original["schema"], "forex": "SECRET-DERIVED"}):
            restricted, proof = core.publication_projection(core.ROUTES["forex"][0].url, malformed)
            assert restricted["status"] == "unavailable"
            assert "777.123" not in json.dumps(restricted)
            assert proof["withheld_paths"] == ["/"]

    def test_capital_funding_narrative_is_withheld_but_treasury_demand_statistics_remain(self):
        original = capital_document()
        direct_statistics = [{"tenor": "10-Year", "latest_indirect_pct": 67.1,
                              "trend_pp_per_auction": 0.25, "verdict": "firming"}]
        original["capital_markets"]["primary_market"].append({
            "id": "reportcard", "status": "derived", "asof": "2026-10-26",
            "funding_asof": "2026-10-27", "n_cards": 8, "window_bd": [0, 1, 3, 5],
            "demand_fatigue": direct_statistics,
            "letter_line": "SECRET-DERIVED 777.123",
            "unreviewed_event_study": {"value": 777.123},
            "source_registry_ids": ["us_treasury_fiscaldata_api"]})
        projected, _ = core.publication_projection(core.ROUTES["capital-market"][0].url, original)
        assert "777.123" not in json.dumps(projected)
        assert "SECRET-DERIVED" not in json.dumps(projected)
        auction, report = projected["capital_markets"]["primary_market"]
        assert auction == original["capital_markets"]["primary_market"][0]
        assert report["demand_fatigue"] == direct_statistics
        assert report["n_cards"] == 8 and report["window_bd"] == [0, 1, 3, 5]
        assert report["letter_line"] is None
        assert report["funding_reading"]["publication_allowed"] is False
        assert report["funding_asof"] == "2026-10-27"
        assert core.publication_projection(core.ROUTES["capital-market"][0].url, projected)[0] == projected

    def test_legacy_table_input_cannot_bypass_publication_policy(self):
        for topic, dataset, document in (
            ("capital-market", "capital_markets", capital_document()),
            ("money-market", "money_markets", money_document()),
            ("money-market", "money_market_history", money_document()),
        ):
            result = query_packet(packet(topic, document), dataset)
            assert "777.123" not in json.dumps(result)
            assert "SECRET-DERIVED" not in json.dumps(result)
            restricted = [row for row in result["results"] if row["entity_id"] != "EA-EUR"]
            assert restricted and all(row["value"] is None for row in restricted)
            assert all(row["rights_status"] for row in restricted)


    def test_money_packet_preserves_direct_publisher_values_without_relabelling(self):
        output, _ = core.publication_projection(core.ROUTES["money-market"][0].url, money_document())
        assert "777.123" not in json.dumps(output)
        assert "SECRET-DERIVED" not in json.dumps(output)
        us, euro = output["markets"]
        assert us["benchmark"]["source_url"] == "https://fred.stlouisfed.org/"
        assert us["benchmark"]["value"] is None
        assert us["metrics"][1]["value"] == 0
        assert euro["benchmark"]["value"] == 0
        assert euro["benchmark"]["history"] == [["2026-10-26", 0]]


    def test_fetch_receipt_distinguishes_original_bytes_from_returned_projection(self):
        source = core.ROUTES["capital-market"][0]
        raw = json.dumps(capital_document()).encode()
        result = core.fetch_source(source, timeout=1, max_bytes=100000,
            opener=lambda request, timeout: Response(request.full_url, raw))
        assert result["ok"] is True
        assert result["content_sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
        projection = result["publication_projection"]
        canonical = json.dumps(result["document"], sort_keys=True, ensure_ascii=False,
                               separators=(",", ":"), allow_nan=False).encode()
        assert projection["content_sha256"] == "sha256:" + hashlib.sha256(canonical).hexdigest()
        assert projection["content_sha256"] != result["content_sha256"]
        assert projection["source_hash_scope"] == "original_retrieved_response_bytes"
        assert result["source_reported"] == core.source_reported_metadata(
            source, json.loads(raw), content_sha256=result["content_sha256"])


    def test_unrelated_routes_and_direct_publisher_contract_are_unchanged(self):
        doc = {"value": 0, "rights_status": "allowed", "source": "ECB"}
        output, receipt = core.publication_projection("https://data.ecb.europa.eu/", doc)
        assert output is doc
        assert receipt is None


    def test_protected_routes_fail_closed_on_unknown_schema_and_shape(self):
        for topic, dataset, valid in (
            ("capital-market", "capital_markets", capital_document()),
            ("money-market", "money_markets", money_document()),
        ):
            variants = [
                {"value": 777.123},
                {**valid, "schema": "future.schema", "value": 777.123},
                {"schema": valid["schema"], "value": 777.123},
                [{"value": 777.123}],
                {**valid, ("markets" if topic == "money-market" else "capital_markets"): 777.123},
                {**valid, "markets": [{"benchmark": 777.123}]} if topic == "money-market"
                else {**valid, "capital_markets": {"risk_context": 777.123}},
            ]
            for document in variants:
                with self.subTest(topic=topic, document=document):
                    source = core.ROUTES[topic][0]
                    raw = json.dumps(document).encode()
                    result = core.fetch_source(source, timeout=1, max_bytes=100000,
                        opener=lambda request, timeout: Response(request.full_url, raw))
                    assert result["ok"] is True
                    assert "777.123" not in json.dumps(result["document"])
                    assert result["document"]["status"] == "unavailable"
                    assert result["document"]["publication_allowed"] is False
                    assert result["publication_projection"]["withheld_paths"] == ["/"]
                    assert result["content_sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
                    table = query_packet(packet(topic, document), dataset)
                    assert all(row["value"] is None for row in table["results"])
                    assert all(row["availability"] != "published" for row in table["results"])

@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ("fastapi", "mcp", "httpx")),
                     "workspace dependencies required")
class PublicToolRightsTests(unittest.TestCase):
    def test_all_native_tools_and_legacy_fetch_preserve_the_rights_gate(self):
        from fastapi.testclient import TestClient
        from financial_evidence.workspace import create_app
        from financial_evidence.service import EvidenceService
        from financial_evidence import mcp as legacy_mcp
        from financial_evidence import workspace_mcp

        def opener(request, **kwargs):
            document = (forex_document() if "forex" in request.full_url else
                        capital_document() if ("world" in request.full_url or "capital" in request.full_url)
                        else money_document())
            return Response(request.full_url, json.dumps(document).encode())

        with patch.dict(core.fetch_source.__kwdefaults__, {"opener": opener}), \
             patch.dict(core.build_packet.__kwdefaults__, {"opener": opener}), \
             patch.object(workspace_mcp, "read_review", return_value={"qualified_original_publisher_fixture": 0}), \
             tempfile.TemporaryDirectory() as usage_dir:
            service = EvidenceService()
            self.addCleanup(service.close)
            with TestClient(create_app(service=service, base_url="http://localhost:6900",
                                       usage_dir=usage_dir), base_url="http://localhost:6900") as client:
                def rpc(method, params=None):
                    response = client.post("/mcp", headers={"Accept": "application/json, text/event-stream"},
                        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
                    assert response.status_code == 200, response.text
                    return response.json()["result"]
                names = {tool["name"] for tool in rpc("tools/list")["tools"]}
                calls = [
                    ("financial_evidence_datasets", {}),
                    ("financial_evidence_route", {"topics": ["money-market", "capital-market"]}),
                    ("financial_evidence_funding_review", {}),
                    ("financial_evidence_sources", {}),
                    ("financial_evidence_query", {"dataset": "money_markets", "entity": "USD"}),
                    ("financial_evidence_query", {"dataset": "capital_markets"}),
                    ("financial_evidence_agent_query", {"dataset": "money_markets", "entity": "USD"}),
                    ("financial_evidence_agent_query", {"dataset": "capital_markets"}),
                    ("financial_evidence_review", {}),
                    ("financial_evidence_packet", {"topics": ["money-market", "capital-market"]}),
                    ("financial_evidence_workflow", {"workflow": "funding", "selection": "USD"}),
                    ("financial_evidence_funding_workflow", {"currency": "USD"}),
                ]
                # The two fixed-source workflow wrappers have separate wire parity tests;
                # their implementations do not read the core funding/forex opener.
                assert names == {name for name, _ in calls} | {
                    "financial_evidence_institutions_workflow", "financial_evidence_exit_workflow",
                }
                assert "financial_evidence_fetch" not in names
                for name, arguments in calls:
                    reply = rpc("tools/call", {"name": name, "arguments": arguments})
                    assert not reply.get("isError"), (name, reply)
                    assert "777.123" not in json.dumps(reply), name
                    assert "SECRET-DERIVED" not in json.dumps(reply), name
                    if name in ("financial_evidence_workflow", "financial_evidence_funding_workflow"):
                        result = reply["structuredContent"]
                        assert result["prepared_response"] is False
                        assert result["evidence"]["results"]
                        assert all(row["value"] is None for row in result["evidence"]["results"])
                    if name == "financial_evidence_funding_review":
                        assert reply["structuredContent"] == {"qualified_original_publisher_fixture": 0}
                forex = client.get("/api/v1/packet", params={"topics": "forex"}).json()
                assert forex["sources"][0]["document"]["forex"]["publication_allowed"] is False
                assert "777.123" not in json.dumps(forex)
                assert "SECRET-DERIVED" not in json.dumps(forex)
                rest = client.get("/api/v1/workflow", params={"workflow": "funding", "selection": "USD"}).json()
                assert rest["prepared_response"] is False
                assert "777.123" not in json.dumps(rest)
            legacy = legacy_mcp.call_tool("financial_evidence_fetch", {"topics": ["money-market", "capital-market", "forex"]})
            assert not legacy.get("isError")
            assert "777.123" not in json.dumps(legacy)
            assert "SECRET-DERIVED" not in json.dumps(legacy)
