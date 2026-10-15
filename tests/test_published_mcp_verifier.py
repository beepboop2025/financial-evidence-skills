"""Publication acceptance must distinguish validation from failed retrieval."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from financial_evidence.mcp import dispatch

spec = importlib.util.spec_from_file_location(
    "published_mcp_verifier", ROOT / "scripts/verify_published_mcp.py",
)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class PublishedMcpVerifierTests(unittest.TestCase):
    def responses(self, command, **kwargs):
        responses = [dispatch(json.loads(line)) for line in kwargs["input"].splitlines()]
        return subprocess.CompletedProcess(
            command, 0, "".join(json.dumps(item) + "\n" for item in responses if item), "",
        )

    def test_default_published_contract_remains_the_unchanged_historical_release(self):
        self.assertEqual(verifier.CONTRACT.name, "financial-evidence-mcp-v0.1.7.json")
        self.assertEqual(hashlib.sha256(verifier.CONTRACT.read_bytes()).hexdigest(), "37a30178ec7f45737a7ce1ee7f39d3da7c2433a5c2179eee3ea98073abe9670a")
        contract = json.loads(verifier.CONTRACT.read_text())
        fetch = next(tool for tool in contract["tools"] if tool["name"] == "financial_evidence_fetch")
        self.assertEqual(fetch["inputSchema"]["properties"]["max_bytes"]["default"], 1_048_576)

    def test_strict_protocol_accepts_only_expected_validation_errors(self):
        with patch.object(verifier.subprocess, "run", side_effect=self.responses):
            self.assertEqual(verifier.verify(["test-artifact"], contract_path=ROOT / "integrations/financial-evidence-mcp-current.json")["status"], "PASS")

    def test_unavailable_fetch_is_not_argument_validation(self):
        def unavailable(command, **kwargs):
            result = self.responses(command, **kwargs)
            responses = [json.loads(line) for line in result.stdout.splitlines()]
            packet = {"transport_status": "unavailable", "sources": []}
            responses[-1]["result"] = {
                "isError": True, "structuredContent": packet,
                "content": [{"type": "text", "text": json.dumps(packet)}],
            }
            result.stdout = "".join(json.dumps(item) + "\n" for item in responses)
            return result

        with patch.object(verifier.subprocess, "run", side_effect=unavailable):
            with self.assertRaises(AssertionError):
                verifier.verify(["test-artifact"], contract_path=ROOT / "integrations/financial-evidence-mcp-current.json")


if __name__ == "__main__":
    unittest.main()
