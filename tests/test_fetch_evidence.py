from email.message import Message
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
import unittest
import urllib.error


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "financial-evidence" / "scripts" / "fetch_evidence.py"


def load_module():
    spec = spec_from_file_location("financial_evidence_fetch", SCRIPT)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Response:
    def __init__(self, url, body, content_type="application/json"):
        self.url = url
        self.body = body
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def geturl(self):
        return self.url

    def read(self, size):
        return self.body[:size]


class FetchEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_topics_dedupe_without_reordering(self):
        self.assertEqual(
            self.module.normalize_topics(
                ["funding,china", "money-market", "liquidity"]
            ),
            ["money-market", "china-economy", "market-liquidity"],
        )

    def test_all_sources_are_fixed_public_https_routes(self):
        urls = [
            source.url for sources in self.module.ROUTES.values() for source in sources
        ]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(url.startswith("https://") for url in urls))
        self.assertNotIn("localhost", " ".join(urls))
        self.assertEqual(set(urls), set(self.module.SOURCE_ADAPTERS))
        self.assertEqual(set(urls), set(self.module.ALLOWED_URLS))
        for sources in self.module.ROUTES.values():
            for source in sources:
                self.assertTrue(source.human_scope_url.startswith("https://"))
                self.assertEqual(source.financial_authority, "none")
                self.assertEqual(source.carrier_state, "not_published")
                self.assertFalse(hasattr(source, "carrier_url"))

    def test_same_host_non_route_and_human_scope_urls_are_not_fetchable(self):
        canonical = self.module.ROUTES["money-market"][0]
        calls = 0

        def opener(request, *, timeout):
            nonlocal calls
            calls += 1
            return Response(request.full_url, b"{}")

        for url in (
            "https://api.seiche.info/not-a-fixed-route",
            canonical.human_scope_url,
        ):
            candidate = self.module.Source(
                canonical.product,
                url,
                canonical.evidence_class,
                canonical.human_scope_url,
            )
            result = self.module.fetch_source(
                candidate,
                max_bytes=1024,
                timeout=1,
                opener=opener,
            )
            self.assertFalse(result["ok"])
            self.assertIn("outside the HTTPS allowlist", result["error"])
        self.assertEqual(calls, 0)

    def test_packet_keeps_documents_and_retrieval_clocks_separate(self):
        def opener(request, *, timeout):
            self.assertEqual(timeout, 3)
            return Response(
                request.full_url,
                json.dumps({"status": "structural"}).encode(),
            )

        packet = self.module.build_packet(
            ["china-economy", "bank-risk"],
            max_bytes=1024,
            timeout=3,
            opener=opener,
        )
        self.assertEqual(packet["status"], "complete")
        self.assertEqual(packet["transport_status"], packet["status"])
        self.assertEqual(packet["status_semantics"], "transport_only")
        self.assertEqual(packet["evidence_status"], "not_evaluated")
        self.assertEqual(packet["carrier_verification"], "not_performed")
        self.assertEqual(
            [row["product"] for row in packet["sources"]],
            ["Palimpsest", "Seiche", "LiquiLens"],
        )
        self.assertTrue(
            all(row["retrieved_at"].endswith("Z") for row in packet["sources"])
        )
        self.assertTrue(
            all(
                row["document"] == {"status": "structural"} for row in packet["sources"]
            )
        )
        self.assertTrue(
            all(row["financial_authority"] == "none" for row in packet["sources"])
        )
        self.assertTrue(
            all(row["carrier_state"] == "not_published" for row in packet["sources"])
        )
        self.assertTrue(all("carrier_url" not in row for row in packet["sources"]))
        self.assertTrue(
            all(row["resolved_url"] == row["source_url"] for row in packet["sources"])
        )
        self.assertTrue(
            all(
                row["content_sha256"].startswith("sha256:")
                and len(row["content_sha256"]) == 71
                for row in packet["sources"]
            )
        )

    def test_explicit_adapters_report_only_allowlisted_state_and_clocks(self):
        fixtures = {
            "https://api.seiche.info/api/v2/money-markets": (
                {
                    "status": "PARTIAL",
                    "generated_at": "2026-08-25T19:35:45Z",
                },
                {"response_status"},
                {"generated_at"},
            ),
            "https://api.seiche.info/api/v2/world-markets?section=capital_markets": (
                {
                    "status": "derived",
                    "capital_markets": {"status": "derived"},
                    "generated_at": "2026-08-25T19:34:43Z",
                    "as_of": "2026-08-24",
                    "clocks": {
                        "snapshot_generated_at": "2026-08-25T19:34:43Z",
                        "evaluation_at": "2026-08-25T19:35:45Z",
                        "latest_domain_as_of": "2026-08-24",
                        "selected_evidence_as_of": "2026-08-24",
                        "domains": {"capital_markets": "2026-08-24"},
                    },
                },
                {"response_status", "section_status"},
                {
                    "generated_at",
                    "as_of",
                    "snapshot_generated_at",
                    "evaluation_at",
                    "latest_domain_as_of",
                    "selected_evidence_as_of",
                    "capital_markets_domain_as_of",
                },
            ),
            "https://palimpsest.info/readings/china-index-latest.json": (
                {
                    "economic_state": {"status": "warming_up"},
                    "readiness": {"status": "warming_up"},
                    "generated_at": "2026-08-23T17:27:00Z",
                    "head": {
                        "as_of": "2026-08-23T17:27:00Z",
                        "generated_at": "2026-08-23T17:27:00Z",
                    },
                    "observation_ledger": {
                        "collection_clock": {"first": "c1", "last": "c2"},
                        "release_clock": {"first": "r1", "last": "r2"},
                        "period_coverage": {"first": "p1", "last": "p2"},
                    },
                },
                {"economic_state", "readiness"},
                {
                    "generated_at",
                    "head_as_of",
                    "head_generated_at",
                    "collection_first",
                    "collection_last",
                    "release_first",
                    "release_last",
                    "period_first",
                    "period_last",
                },
            ),
            "https://api.seiche.info/api/v2/world-markets?section=china_macro": (
                {
                    "status": "structural",
                    "china_macro": {
                        "status": "structural",
                        "evidence_status": "unavailable",
                    },
                },
                {
                    "response_status",
                    "section_status",
                    "section_evidence_status",
                },
                set(),
            ),
            "https://api.liquilens.in/api/failure-radar/board": (
                {
                    "as_of": "2026-08-24",
                    "market_layer": {"as_of": "2026-08-11"},
                    "historical_evidence": {"status": "PIT_PROXY"},
                },
                {"historical_evidence_status"},
                {"as_of", "market_layer_as_of"},
            ),
            "https://api.seiche.info/undertow/x402/summary": (
                {"asof": "2026-08-25", "funding_regime": "STRAIN"},
                {"funding_regime"},
                {"asof"},
            ),
        }
        sources = {
            source.url: source
            for route_sources in self.module.ROUTES.values()
            for source in route_sources
        }
        for source_url, (document, state_names, clock_names) in fixtures.items():
            document.update(
                {
                    "unconfigured": {
                        "status": "spoofed",
                        "freshness": "fresh",
                        "eligibility": "eligible",
                        "rights": "open",
                    }
                }
            )
            raw = json.dumps(document, sort_keys=True).encode()
            result = self.module.fetch_source(
                sources[source_url],
                max_bytes=16_384,
                timeout=1,
                opener=lambda request, timeout, raw=raw: Response(
                    request.full_url, raw
                ),
            )
            self.assertTrue(result["ok"])
            reported = result["source_reported"]
            state = [] if reported["state"] == "not_reported" else reported["state"]
            clocks = [] if reported["clocks"] == "not_reported" else reported["clocks"]
            self.assertEqual({item["name"] for item in state}, state_names)
            self.assertEqual({item["name"] for item in clocks}, clock_names)
            for item in [*state, *clocks]:
                self.assertTrue(item["path"].startswith("/"))
                self.assertEqual(
                    item["provenance"],
                    {
                        "kind": "source_document",
                        "source_url": source_url,
                        "content_sha256": result["content_sha256"],
                    },
                )
            adapted = json.dumps(reported, sort_keys=True)
            for forbidden in ("freshness", "eligibility", "rights", "spoofed"):
                self.assertNotIn(forbidden, adapted)

    def test_missing_configured_fields_are_not_reported_not_inferred(self):
        source = self.module.ROUTES["money-market"][0]
        document = {
            "nested": {"status": "complete"},
            "freshness": "fresh",
            "rights": "open",
        }
        raw = json.dumps(document).encode()
        result = self.module.fetch_source(
            source,
            max_bytes=1024,
            timeout=1,
            opener=lambda request, timeout: Response(request.full_url, raw),
        )
        self.assertEqual(
            result["source_reported"],
            {
                "adapter": "seiche_money_markets_v1",
                "state": "not_reported",
                "clocks": "not_reported",
            },
        )

    def test_redirect_handler_rejects_before_following(self):
        handler = self.module.RejectRedirects()
        request = self.module.urllib.request.Request(
            "https://api.seiche.info/api/v2/money-markets"
        )
        with self.assertRaisesRegex(
            urllib.error.HTTPError,
            "redirects are not accepted",
        ) as caught:
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://example.invalid/redirected",
            )
        caught.exception.close()

    def test_redirects_oversize_and_invalid_json_are_explicit_errors(self):
        source = self.module.ROUTES["money-market"][0]

        redirect = self.module.fetch_source(
            source,
            max_bytes=1024,
            timeout=1,
            opener=lambda request, timeout: Response(
                request.full_url + "/moved", b"{}"
            ),
        )
        self.assertFalse(redirect["ok"])
        self.assertIn("redirects are not accepted", redirect["error"])

        calls = 0

        def opener(request, *, timeout):
            nonlocal calls
            calls += 1
            body = b"x" * 20 if calls == 1 else b"not-json"
            return Response(request.full_url, body)

        packet = self.module.build_packet(
            ["china-economy"],
            max_bytes=10,
            timeout=1,
            opener=opener,
        )
        self.assertEqual(packet["status"], "unavailable")
        self.assertEqual(packet["transport_status"], "unavailable")
        self.assertEqual(packet["status_semantics"], "transport_only")
        self.assertEqual(packet["evidence_status"], "not_evaluated")
        self.assertEqual(packet["carrier_verification"], "not_performed")
        self.assertTrue(
            all(not row["ok"] and row["error"] for row in packet["sources"])
        )
        self.assertNotIn('"document": 0', json.dumps(packet))
        self.assertIn("never converted to zero or calm", packet["absence_policy"])
        self.assertIn("untrusted evidence data", packet["data_handling"])


if __name__ == "__main__":
    unittest.main()
