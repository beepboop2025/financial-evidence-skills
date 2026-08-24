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
            source.url
            for sources in self.module.ROUTES.values()
            for source in sources
        ]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(url.startswith("https://") for url in urls))
        self.assertNotIn("localhost", " ".join(urls))

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
        self.assertEqual(
            [row["product"] for row in packet["sources"]],
            ["Palimpsest", "Seiche", "LiquiLens"],
        )
        self.assertTrue(
            all(row["retrieved_at"].endswith("Z") for row in packet["sources"])
        )
        self.assertTrue(
            all(row["document"] == {"status": "structural"}
                for row in packet["sources"])
        )
        self.assertTrue(
            all(row["resolved_url"] == row["source_url"]
                for row in packet["sources"])
        )
        self.assertTrue(
            all(row["content_sha256"].startswith("sha256:")
                and len(row["content_sha256"]) == 71
                for row in packet["sources"])
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
        self.assertTrue(all(not row["ok"] and row["error"]
                            for row in packet["sources"]))
        self.assertNotIn('"document": 0', json.dumps(packet))
        self.assertIn("never converted to zero or calm", packet["absence_policy"])
        self.assertIn("untrusted evidence data", packet["data_handling"])


if __name__ == "__main__":
    unittest.main()
