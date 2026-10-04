"""Financial semantics, bounded projections and shared-cache behavior."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from financial_evidence import core
from financial_evidence import mcp
from financial_evidence.service import EvidenceService
from financial_evidence.tables import query_packet


MONEY = {
    "schema": "seiche.global-money-markets.v1",
    "generated_at": "2026-09-28T00:00:00Z",
    "markets": [
        {
            "market_id": "US-USD",
            "display_name": "US dollar",
            "benchmark": {
                "mnemonic": "SOFR",
                "value": 0,
                "unit": "%",
                "availability": "AVAILABLE",
                "status": "FRESH",
                "asof": "2026-09-24",
                "redistribution_status": "allowed",
                "published_at": "2026-09-25",
                "knowledge_time": "2026-09-26",
                "history": [
                    ["2026-09-22", 4.5],
                    ["2026-09-23", None],
                    ["2026-09-24", 0],
                ],
            },
        },
        {
            "market_id": "XX-XXX",
            "benchmark": {
                "availability": "RESTRICTED",
                "value": 99,
                "history": [["2026-09-24", 99]],
            },
        },
    ],
}


def source_result(source, document=None, ok=True):
    document = copy.deepcopy(MONEY if document is None else document)
    raw = json.dumps(document).encode()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    result = {
        "product": source.product,
        "source_url": source.url,
        "retrieved_at": "2026-09-28T01:00:00Z",
        "ok": ok,
        "financial_authority": "none",
        "carrier_state": "not_published",
    }
    if ok:
        result.update(
            document=document,
            content_sha256=digest,
            bytes=len(raw),
            source_reported=core.source_reported_metadata(
                source, document, content_sha256=digest
            ),
        )
    else:
        result["error"] = "upstream unavailable"
    return result


def packet(topic, document=None, ok=True):
    return {
        "transport_status": "complete" if ok else "unavailable",
        "absence_policy": core.ABSENCE_POLICY,
        "sources": [
            {"topic": topic, **source_result(core.ROUTES[topic][0], document, ok)}
        ],
    }


class ProjectionTests(unittest.TestCase):
    def test_current_filings_preserve_zero_null_citations_and_knowledge_clock(self):
        doc = {"rows": [], "current_disclosures": {
            "schema": "liquilens.current-bank-filings.v1", "score_authority": False,
            "rows": [{"slug": "jana-sfb", "name": "Jana Small Finance Bank", "status": "observed",
                "period_end": "2026-06-30", "publication_date": "2026-07-30", "available_at": "2026-09-24",
                "sources": ["https://bank.example/filing.pdf"], "source_documents": [{"sha256": "a" * 64}],
                "metrics": {"gnpa_pct": {"value": 0, "unit": "percent", "status": "observed"},
                            "nnpa_pct": {"value": None, "unit": "percent", "status": "not_disclosed"}}}]}}
        rows = query_packet(packet("bank-risk", doc), "bank_risk")["results"]
        self.assertEqual(rows[0]["value"], 0)
        self.assertIsNone(rows[1]["value"])
        self.assertEqual(rows[0]["source_field"], "/current_disclosures/rows/0/metrics/gnpa_pct/value")
        self.assertEqual(rows[0]["as_of"], "2026-06-30")
        self.assertEqual(rows[0]["knowledge_time"], "2026-09-24")
        self.assertEqual(rows[0]["observation_url"], "https://bank.example/filing.pdf")
        self.assertFalse(json.loads(rows[0]["context"])["score_authority"])
        for mutation in ({"status": "stale"}, {"rights_status": "restricted"}):
            amended = copy.deepcopy(doc)
            amended["current_disclosures"]["rows"][0].update(mutation)
            output = query_packet(packet("bank-risk", amended), "bank_risk")["results"]
            self.assertTrue(all(row["value"] is None for row in output))

    def test_malformed_mcp_params_and_unknown_arguments_do_not_crash_or_fetch(self):
        result = mcp.dispatch(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": []}
        )
        self.assertEqual(result["error"]["code"], -32602)
        result = mcp.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "financial_evidence_route",
                    "arguments": {
                        "topics": ["money-market"],
                        "url": "https://example.org",
                    },
                },
            }
        )
        self.assertTrue(result["result"]["isError"])
        self.assertIn("unknown arguments", result["result"]["content"][0]["text"])

    def test_nonfinite_source_numbers_fail_as_transport_errors(self):
        from test_package import Response

        source = core.ROUTES["money-market"][0]
        for raw in (
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":-Infinity}',
            b'{"value":1e999}',
            b'{"value":-1e999}',
        ):
            result = core.fetch_source(
                source,
                max_bytes=1024,
                timeout=1,
                opener=lambda request, timeout, body=raw: Response(
                    request.full_url, body
                ),
            )
            self.assertFalse(result["ok"])
            self.assertNotIn("document", result)

    def test_unrepresentable_numeric_value_is_unavailable(self):
        doc = copy.deepcopy(MONEY)
        doc["markets"][0]["benchmark"]["value"] = 10**400
        row = query_packet(packet("money-market", doc), "money_markets")["results"][0]
        self.assertIsNone(row["value"])
        self.assertEqual(row["availability"], "unavailable")

    def test_actual_zero_remains_zero_and_restricted_numbers_are_not_published(self):
        result = query_packet(packet("money-market"), "money_markets")
        self.assertEqual(result["results"][0]["value"], 0)
        self.assertIsNone(result["results"][1]["value"])
        self.assertEqual(result["results"][0]["as_of"], "2026-09-24")
        self.assertNotEqual(
            result["results"][0]["as_of"], result["results"][0]["retrieved_at"]
        )
        self.assertEqual(
            result["results"][0]["source_field"], "/markets/0/benchmark/value"
        )

    def test_history_filters_pagination_and_null_gaps(self):
        result = query_packet(
            packet("money-market"),
            "money_market_history",
            entity="usd",
            start_date="2026-09-23",
            end_date="2026-09-24",
            limit=1,
        )
        self.assertEqual(result["total_rows"], 2)
        self.assertEqual(result["next_offset"], 1)
        self.assertIsNone(result["results"][0]["value"])
        self.assertIsNone(result["results"][0]["published_at"])
        tail = query_packet(
            packet("money-market"),
            "money_market_history",
            entity="usd",
            start_date="2026-09-23",
            limit=1,
            offset=1,
        )
        self.assertEqual(tail["results"][0]["value"], 0)
        self.assertIsNone(tail["next_offset"])
        restricted = query_packet(
            packet("money-market"), "money_market_history", entity="XX"
        )
        self.assertTrue(all(row["value"] is None for row in restricted["results"]))

    def test_capital_prices_keep_child_clock_and_native_units(self):
        doc = {
            "schema": "seiche.world-markets.v1",
            "as_of": "2099-01-01",
            "capital_markets": {
                "status": "derived",
                "risk_context": {
                    "market_prices": {
                        "vix": {
                            "value": 14.2,
                            "status": "observed",
                            "as_of": "2026-09-22",
                        },
                        "high_yield_oas": {"value": None, "status": "unavailable"},
                    }
                },
            },
        }
        rows = query_packet(packet("capital-market", doc), "capital_markets")["results"]
        self.assertEqual(rows[0]["as_of"], "2026-09-22")
        self.assertEqual(rows[0]["unit"], "index_points")
        self.assertIsNone(rows[1]["value"])
        self.assertIsNone(rows[1]["as_of"])

    def test_parent_restrictions_suppress_capital_values(self):
        original = {
            "schema": "seiche.world-markets.v1",
            "capital_markets": {
                "risk_context": {
                    "market_prices": {
                        "vix": {"value": 14.2},
                        "high_yield_oas": {"value": 3.1},
                    }
                }
            },
        }
        for path in (
            (),
            ("capital_markets",),
            ("capital_markets", "risk_context"),
            ("capital_markets", "risk_context", "market_prices"),
        ):
            with self.subTest(restriction_path=path):
                doc = copy.deepcopy(original)
                parent = doc
                for key in path:
                    parent = parent[key]
                parent["publication_allowed"] = False
                rows = query_packet(packet("capital-market", doc), "capital_markets")[
                    "results"
                ]
                self.assertEqual(len(rows), 2)
                self.assertTrue(all(row["value"] is None for row in rows))
                self.assertTrue(all(row["availability"] != "published" for row in rows))

    def test_restricted_history_has_explicit_unavailable_status(self):
        doc = copy.deepcopy(MONEY)
        doc["publication_allowed"] = False
        rows = query_packet(packet("money-market", doc), "money_market_history")[
            "results"
        ]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["value"] is None for row in rows))
        self.assertTrue(
            all(row["availability"] == "restricted_or_unavailable" for row in rows)
        )

    def test_bank_diagnostics_keep_probability_scale_and_eligibility_limits(self):
        doc = {
            "as_of": "2026-09-28",
            "historical_evidence": {
                "status": "CONSTRUCTION_PIT",
                "real_money_eligible": False,
            },
            "rows": [
                {
                    "slug": "example-bank",
                    "name": "Example Bank",
                    "as_of": "2025-09-30",
                    "score": 66,
                    "hazard": {"pd_12m": 0.0042, "validated_backtest": False},
                }
            ],
        }
        rows = query_packet(packet("bank-risk", doc), "bank_risk")["results"]
        self.assertEqual(rows[1]["value"], 0.0042)
        self.assertEqual(rows[1]["unit"], "ratio")
        self.assertEqual(rows[1]["as_of"], "2025-09-30")
        self.assertIn('"real_money_eligible": false', rows[0]["context"])
        self.assertNotIn("grade", rows[0])

    def test_withheld_percentile_is_not_reconstructed_from_segment_score(self):
        doc = {
            "segment_reports": [
                {
                    "segment": "UST",
                    "score": 90,
                    "n_qualifying": 2,
                    "coverage": {"validation_scope": "retrospective replay"},
                    "observations": [
                        {"measure": "A", "stress_pctl": 0.3, "asof": "2026-09-23"},
                        {
                            "measure": "B",
                            "stress_pctl": 0.7,
                            "stress_pctl_withheld": True,
                        },
                    ],
                }
            ]
        }
        rows = query_packet(packet("market-liquidity", doc), "market_liquidity")[
            "results"
        ]
        self.assertEqual(rows[0]["value"], 0.3)
        self.assertIsNone(rows[1]["value"])
        self.assertEqual(rows[1]["availability"], "withheld")
        self.assertIn("retrospective replay", rows[1]["context"])

    def test_segment_restriction_suppresses_liquidity_observations(self):
        doc = {
            "segment_reports": [
                {
                    "segment": "UST",
                    "publication_allowed": False,
                    "observations": [{"measure": "A", "stress_pctl": 0.3}],
                }
            ]
        }
        rows = query_packet(packet("market-liquidity", doc), "market_liquidity")[
            "results"
        ]
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["value"])
        self.assertNotEqual(rows[0]["availability"], "published")

    def test_china_is_metadata_only_even_when_source_contains_values(self):
        doc = {
            "status": "restricted",
            "availability": "unavailable",
            "publication_allowed": False,
            "value": 99,
            "counts": {"published_records": 0, "restricted_records": 200},
            "reason": "policy denies publication",
        }
        result = query_packet(packet("china-economy", doc), "china_economy")
        self.assertIsNone(result["results"][0]["value"])
        self.assertIsNone(result["results"][0]["as_of"])
        self.assertEqual(result["results"][0]["rights_status"], "restricted")
        self.assertIn("policy denies publication", result["results"][0]["context"])

    def test_filtered_transport_failure_stays_in_diagnostics(self):
        result = query_packet(
            packet("money-market", ok=False), "money_markets", entity="US-USD"
        )
        self.assertEqual(result["results"], [])
        self.assertEqual(result["transport_status"], "unavailable")
        self.assertEqual(result["diagnostics"][0]["availability"], "source_unavailable")
        self.assertIn("error", result["sources"][0])

    def test_schema_drift_is_visible_not_successful_empty_data(self):
        for document in (
            {"schema": "new-format", "markets": []},
            {"schema": "seiche.global-money-markets.v1", "markets": None},
        ):
            result = query_packet(packet("money-market", document), "money_markets")
            self.assertEqual(
                result["diagnostics"][0]["availability"], "schema_unavailable"
            )
            self.assertIsNone(result["results"][0]["value"])

    def test_bad_queries_fail_before_network_access(self):
        calls = []
        service = EvidenceService(fetcher=lambda *a, **k: calls.append(a))
        self.addCleanup(service.close)
        for kwargs in (
            {"dataset": "arbitrary-url"},
            {"limit": 0},
            {"limit": True},
            {"offset": -1},
            {"entity": "x" * 101},
            {"start_date": "20260901"},
            {"start_date": "2026-02-30"},
            {"start_date": "2026-09-28", "end_date": "2026-09-01"},
        ):
            with self.assertRaises(ValueError):
                service.query(**{"dataset": "money_markets", **kwargs})
        self.assertEqual(calls, [])

    def test_every_published_numeric_row_resolves_to_original_document(self):
        source_packet = packet("money-market")
        for dataset in ("money_markets", "money_market_history"):
            for row in query_packet(source_packet, dataset)["results"]:
                if row["value"] is None:
                    continue
                original = source_packet["sources"][0]["document"]
                for part in row["source_field"].split("/")[1:]:
                    original = (
                        original[int(part)]
                        if isinstance(original, list)
                        else original[part]
                    )
                self.assertEqual(row["value"], original)


class CacheTests(unittest.TestCase):
    def test_concurrent_callers_share_one_request_and_cannot_mutate_cache(self):
        entered, release = threading.Event(), threading.Event()
        calls = []

        def fetcher(source, **kwargs):
            calls.append(source.url)
            entered.set()
            if not release.wait(5):
                raise TimeoutError("test did not release fetch")
            return source_result(source)

        service = EvidenceService(fetcher=fetcher)
        self.addCleanup(service.close)
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = [pool.submit(service.query, "money_markets") for _ in range(12)]
            self.assertTrue(entered.wait(5))
            release.set()
            results = [future.result(timeout=5) for future in futures]
        self.assertEqual(len(calls), 1)
        results[0]["results"][0]["value"] = 999
        self.assertEqual(service.query("money_markets")["results"][0]["value"], 0)
        self.assertEqual(
            results[1]["sources"][0]["retrieved_at"], "2026-09-28T01:00:00Z"
        )

    def test_expiry_does_not_silently_serve_old_success_after_failure(self):
        clock = [0]
        calls = []

        def fetcher(source, **kwargs):
            calls.append(source.url)
            return source_result(source, ok=len(calls) == 1)

        service = EvidenceService(
            fetcher=fetcher, clock=lambda: clock[0], ttl=60, error_ttl=5
        )
        self.addCleanup(service.close)
        self.assertEqual(service.query("money_markets")["transport_status"], "complete")
        clock[0] = 59
        self.assertEqual(
            service.query("money_markets")["sources"][0]["cache"]["age_seconds"], 59
        )
        clock[0] = 60
        result = service.query("money_markets")
        self.assertEqual(result["transport_status"], "unavailable")
        self.assertIsNone(result["results"][0]["value"])
        clock[0] = 64
        service.query("money_markets")
        self.assertEqual(len(calls), 2)
        clock[0] = 65
        service.query("money_markets")
        self.assertEqual(len(calls), 3)

    def test_all_sources_run_with_a_four_worker_bound_and_stable_order(self):
        lock = threading.Lock()
        four = threading.Event()
        release = threading.Event()
        active = [0, 0]

        def fetcher(source, **kwargs):
            with lock:
                active[0] += 1
                active[1] = max(active)
                if active[0] == 4:
                    four.set()
            release.wait(5)
            with lock:
                active[0] -= 1
            return source_result(source)

        service = EvidenceService(fetcher=fetcher)
        self.addCleanup(service.close)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(service.packet, list(core.ROUTES))
            self.assertTrue(four.wait(5))
            release.set()
            result = pending.result(timeout=5)
        self.assertEqual(active[1], 4)
        self.assertEqual(
            [row["source_url"] for row in result["sources"]],
            [s.url for routes in core.ROUTES.values() for s in routes],
        )
        self.assertEqual(len(service._cache), 8)


if __name__ == "__main__":
    unittest.main()
