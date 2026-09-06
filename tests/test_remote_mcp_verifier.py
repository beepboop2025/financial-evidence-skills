import io
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from financial_evidence import core

from scripts.verify_remote_mcp import (
    CONTRACT,
    decode_response,
    normalize_tools,
    require_fetch_semantics,
    verify,
)


class RemoteMcpVerifierTests(unittest.TestCase):
    def test_requests_preserve_the_negotiated_protocol(self):
        seen = []

        def respond(request, timeout):
            payload = json.loads(request.data)
            headers = {key.lower(): value for key, value in request.header_items()}
            method = payload["method"]
            seen.append(method)
            if method == "initialize":
                self.assertEqual(payload["params"]["protocolVersion"], "2025-11-25")
                result = {
                    "serverInfo": CONTRACT["serverInfo"],
                    "protocolVersion": "2025-11-25",
                }
            else:
                # The legacy initialize handshake cannot authorize a modern
                # per-request envelope merely by changing this HTTP header.
                self.assertEqual(headers.get("mcp-protocol-version"), "2025-11-25")
                result = {"tools": CONTRACT["tools"]} if method == "tools/list" else {}
            response = io.BytesIO(json.dumps({
                "jsonrpc": "2.0", "id": payload["id"], "result": result,
            }).encode())
            response.headers = {
                "Content-Type": "application/json", "X-LiquiLens-Worker-Tag": "a" * 40,
            }
            return response

        with patch("urllib.request.urlopen", side_effect=respond), patch(
            "scripts.verify_remote_mcp.require_fetch_semantics"
        ) as require_semantics:
            verify("https://example.invalid/mcp", "a" * 40)
        self.assertEqual(seen, ["initialize", "tools/list", "tools/call"])
        require_semantics.assert_called_once_with({})

    def test_unexpected_negotiated_protocol_fails_before_tool_requests(self):
        initialized = {
            "jsonrpc": "2.0", "id": "initialize", "result": {
                "serverInfo": CONTRACT["serverInfo"], "protocolVersion": "unsupported",
            },
        }
        with patch("scripts.verify_remote_mcp._post", return_value=(
            initialized, {"x-liquilens-worker-tag": "a" * 40},
        )) as post:
            with self.assertRaisesRegex(RuntimeError, "negotiated protocol differs"):
                verify("https://example.invalid/mcp", "a" * 40)
        self.assertEqual(post.call_count, 1)

    def test_contract_decoder_and_normalizer_are_exact(self):
        payload = {"jsonrpc": "2.0", "id": "x", "result": {"tools": []}}
        encoded = json.dumps(payload).encode()
        self.assertEqual(decode_response(encoded, "application/json"), payload)
        self.assertEqual(
            decode_response(b"data: " + encoded + b"\n\n", "text/event-stream"),
            payload,
        )
        decorated = json.loads(json.dumps(CONTRACT["tools"]))
        decorated[0]["inputSchema"]["$schema"] = (
            "https://json-schema.org/draft/2020-12/schema"
        )
        decorated[0]["inputSchema"]["properties"] = {}
        self.assertEqual(normalize_tools(decorated), CONTRACT["tools"])

    def test_fetch_semantics_fail_closed(self):
        digest = "sha256:" + "a" * 64
        source_url = "https://api.seiche.info/api/v2/money-markets"
        result = {
            "isError": False,
            "structuredContent": {
                "status": "complete",
                "transport_status": "complete",
                "status_semantics": "transport_only",
                "evidence_status": "not_evaluated",
                "carrier_verification": "not_performed",
                "output_status": "complete",
                "output_error": None,
                "sources": [{
                    "product": "Seiche",
                    "ok": True,
                    "bytes": 99,
                    "source_url": source_url,
                    "content_sha256": digest,
                    "source_reported": {
                        "adapter": "seiche_money_markets_v1",
                        "state": [{
                            "name": "response_status",
                            "value": "PARTIAL",
                            "path": "/status",
                            "provenance": {
                                "kind": "source_document",
                                "source_url": source_url,
                                "content_sha256": digest,
                            },
                        }],
                        "clocks": "not_reported",
                    },
                }],
            },
        }
        canonical = core.source_reported_metadata(
            core.ROUTES["money-market"][0], {"status": "PARTIAL"},
            content_sha256=digest,
        )
        source = result["structuredContent"]["sources"][0]
        self.assertEqual(source["source_reported"], canonical)
        require_fetch_semantics(result)
        source["source_reported"]["state"][0]["provenance"]["kind"] = (
            "source_reported_allowlisted_field"
        )
        with self.assertRaisesRegex(RuntimeError, "source-reported provenance differs"):
            require_fetch_semantics(result)
        source["source_reported"] = canonical
        result["structuredContent"]["output_status"] = "unavailable"
        with self.assertRaisesRegex(RuntimeError, "semantic boundary differs"):
            require_fetch_semantics(result)


if __name__ == "__main__":
    unittest.main()
