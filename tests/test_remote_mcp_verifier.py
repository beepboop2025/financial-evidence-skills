import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.verify_remote_mcp import (
    CONTRACT,
    decode_response,
    normalize_tools,
    require_fetch_semantics,
)


class RemoteMcpVerifierTests(unittest.TestCase):
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
                                "kind": "source_reported_allowlisted_field",
                                "source_url": source_url,
                                "content_sha256": digest,
                            },
                        }],
                        "clocks": "not_reported",
                    },
                }],
            },
        }
        require_fetch_semantics(result)
        result["structuredContent"]["output_status"] = "unavailable"
        with self.assertRaisesRegex(RuntimeError, "semantic boundary differs"):
            require_fetch_semantics(result)


if __name__ == "__main__":
    unittest.main()
