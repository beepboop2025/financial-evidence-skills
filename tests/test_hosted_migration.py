"""Current downloads preserve archives and make server routing explicit."""
from email.message import Message
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


migration = module("migration_plan", "scripts/plan_hosted_migration.py")
builder = module("hosted_noise_builder", "scripts/build_hosted_noisefloor_kit.py")
client = module("hosted_noise_client", "scripts/templates/noisefloor_hosted_client.py")


class HostedMigrationTests(unittest.TestCase):
    def test_plan_does_not_disclose_credentials_or_change_input(self):
        config = {"mcpServers": {"private-name": {"url": "https://api.seiche.info/mcp", "headers": {"Authorization": "Bearer SECRET"}},
                                 "custom": {"url": "https://secret.example/private?key=SECRET"}}}
        before = json.dumps(config)
        report = migration.plan(config)
        self.assertEqual(json.dumps(config), before)
        self.assertEqual(report["credential_blocks_require_review"], 1)
        self.assertEqual(report["unmapped_urls"], 1)
        self.assertEqual(report["replacements"][0]["to"], "https://agents.seiche.info/products/seiche/mcp")
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertNotIn("secret.example", json.dumps(report))
        self.assertNotIn("private-name", json.dumps(report))
        self.assertFalse(report["writes_performed"])

    def test_exact_url_mapping_does_not_rewrite_prefix_attacks_or_query_credentials(self):
        report = migration.plan({"servers": [{"url": "https://api.seiche.info/mcp?token=secret"},
            {"url": "https://api.seiche.info.evil/mcp"}, {"url": "https://agents.seiche.info/products/seiche/mcp"}]})
        self.assertEqual(report["replacements"], [])
        self.assertEqual(report["unmapped_urls"], 2)

    def test_generated_kit_matches_and_archive_hashes_remain_true(self):
        for name, body in builder.assets().items():
            self.assertEqual((builder.OUT / name).read_bytes(), body, name)
        manifest = json.loads((builder.OUT / "manifest.json").read_text())
        for name, digest in manifest["files"].items():
            self.assertEqual(hashlib.sha256((builder.OUT / name).read_bytes()).hexdigest(), digest)
        spec = json.loads((builder.OUT / "openapi.json").read_text())
        self.assertEqual(spec["servers"], [{"url": client.BASE}])
        self.assertNotIn("spectral_review.py", manifest["files"])
        self.assertIn("hosted_review.py", manifest["files"])
        collection = json.loads((builder.OUT / "noisefloor.postman_collection.json").read_text())
        for item in collection["item"]:
            self.assertIn({"key": "X-Financial-Evidence-Traffic-Class", "value": "synthetic"}, item["request"]["header"])
        for name in ("noisefloor.http", "spectral.bru", "dyson.bru"):
            self.assertIn("X-Financial-Evidence-Traffic-Class: synthetic", (builder.OUT / name).read_text())

    def test_distribution_config_contains_fourteen_products_and_public_community(self):
        config = json.loads((ROOT / "docs/distribution/agent-mcp-config.json").read_text())["mcpServers"]
        self.assertEqual(len(config), 15)
        self.assertEqual(sum('/products/' in row['url'] for row in config.values()), 14)
        self.assertEqual(config['seiche-community']['url'], 'https://agents.seiche.info/social/mcp')
        self.assertTrue(all(set(row) <= {'url', 'type'} for row in config.values()))

    def test_hosted_request_preserves_reply_without_native_fallback(self):
        calls = []
        class Response(io.BytesIO):
            headers = Message()
            headers['Content-Type'] = 'application/json'
            def geturl(self):
                return calls[-1].full_url
        def opener(request, **kwargs):
            calls.append(request)
            return Response(b'{"status":"insufficient_data","value":null}')
        result = client.assess('spectral', {'series': []}, synthetic=True, opener=opener)
        self.assertEqual(result, {'status': 'insufficient_data', 'value': None})
        self.assertEqual(calls[0].full_url, client.BASE + '/v1/spectral/assess')
        self.assertEqual(calls[0].get_header('X-financial-evidence-traffic-class'), 'synthetic')
        self.assertIsNone(calls[0].get_header('Authorization'))
        def unavailable(request, **kwargs):
            calls.append(request)
            raise HTTPError(request.full_url, 503, 'unavailable', {}, None)
        with self.assertRaises(HTTPError) as caught:
            client.assess('spectral', {'series': []}, opener=unavailable)
        caught.exception.close()
        self.assertEqual(len(calls), 2)

    def test_hosted_client_rejects_nonfinite_oversized_or_unknown_requests_before_io(self):
        def unexpected(*args, **kwargs):
            self.fail('invalid input must not reach network')
        for operation, payload in [('private', {}), ('spectral', {'value': float('nan')}), ('spectral', {'text': 'x' * client.MAX_BYTES})]:
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                client.assess(operation, payload, opener=unexpected)


if __name__ == '__main__':
    unittest.main()
