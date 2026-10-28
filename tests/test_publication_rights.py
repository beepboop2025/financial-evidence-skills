"""Reviewed source policy must hold for packets and legacy table inputs."""
import copy
import hashlib
import json
import sys
import unittest
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
