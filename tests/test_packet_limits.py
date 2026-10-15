"""The default first funding task accepts a >1 MiB atlas without unbounding reads."""
from contextlib import redirect_stdout
from email.message import Message
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from financial_evidence import cli, core, mcp
from test_openbb_tables import MONEY

DEFAULT_CAP = 4_194_304
SMALL_CAP = 1_048_576
# Reproduce the observed response size without depending on live data or clocks.
DOCUMENT = json.dumps(MONEY).encode()
ATLAS = DOCUMENT + b" " * (2_187_430 - len(DOCUMENT))


class Response(io.BytesIO):
    def __init__(self, url, body, reads):
        super().__init__(body)
        self.url, self.reads = url, reads
        self.headers = Message()
        self.headers["Content-Type"] = "application/json"

    def geturl(self):
        return self.url

    def read(self, size=-1):
        self.reads.append(size)
        return super().read(size)


class PacketLimitTests(unittest.TestCase):
    def entrypoints(self, opener, cap=None):
        budget = {} if cap is None else {"max_bytes": cap}
        with patch.dict(core.build_packet.__kwdefaults__, {"opener": opener}):
            yield "packet", core.build_packet(["money-market"], **budget), None
            output = io.StringIO()
            with redirect_stdout(output):
                args = ["fetch", "--topic", "money-market"]
                if cap is not None:
                    args.extend(["--max-bytes", str(cap)])
                status = cli.main(args)
            yield "cli", json.loads(output.getvalue()), status
            result = mcp.call_tool("financial_evidence_fetch", {"topics": ["money-market"], **budget})
            yield "mcp", json.loads(result["content"][0]["text"]), result["isError"]
        for index, name in enumerate(("financial-evidence", "skills/financial-evidence")):
            module_name = "packet_limit_helper_" + str(index)
            spec = importlib.util.spec_from_file_location(module_name, ROOT / name / "scripts/fetch_evidence.py")
            helper = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = helper
            try:
                spec.loader.exec_module(helper)
                with patch.dict(helper.build_packet.__kwdefaults__, {"opener": opener}):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        args = ["--topic", "money-market"]
                        if cap is not None:
                            args.extend(["--max-bytes", str(cap)])
                        status = helper.main(args)
                    yield name, json.loads(output.getvalue()), status
            finally:
                sys.modules.pop(module_name, None)

    def run_case(self, body, cap, expected_status):
        calls, reads = [], []
        def opener(request, **kwargs):
            calls.append(request.full_url)
            return Response(request.full_url, body, reads)
        count = 0
        for entrypoint, packet, status in self.entrypoints(opener, cap):
            count += 1
            with self.subTest(entrypoint=entrypoint, cap=cap, bytes=len(body)):
                self.assertEqual(packet["transport_status"], expected_status)
                self.assertEqual(packet["evidence_status"], "not_evaluated")
                source = packet["sources"][0]
                self.assertEqual(source["source_url"], core.ROUTES["money-market"][0].url)
                if expected_status == "complete":
                    self.assertEqual(source["document"], MONEY)
                    self.assertEqual(source["bytes"], len(body))
                    self.assertEqual(source["content_sha256"], "sha256:" + hashlib.sha256(body).hexdigest())
                    if entrypoint == "mcp":
                        self.assertIs(status, False)
                    elif entrypoint == "packet":
                        self.assertIsNone(status)
                    else:
                        self.assertEqual(status, 0)
                else:
                    self.assertNotIn("document", source)
                    self.assertIn("response exceeds " + str(cap or DEFAULT_CAP), source["error"])
                    if entrypoint == "mcp":
                        self.assertIs(status, True)
                    elif entrypoint == "packet":
                        self.assertIsNone(status)
                    else:
                        self.assertEqual(status, 2)
        self.assertEqual(count, 5)
        self.assertEqual(calls, [core.source_endpoint(core.ROUTES["money-market"][0].url)] * count)
        # The parser reads one sentinel byte past its budget, never the full body
        # after a caller selects a smaller allowance.
        self.assertEqual(reads, [(cap or DEFAULT_CAP) + 1] * count)

    def test_default_packet_cli_mcp_and_both_helpers_accept_current_atlas_size(self):
        self.run_case(ATLAS, None, "complete")

    def test_explicit_smaller_budget_remains_a_hard_limit_at_every_entrypoint(self):
        self.run_case(ATLAS, SMALL_CAP, "unavailable")

    def test_default_budget_rejects_more_than_four_mib_at_every_entrypoint(self):
        oversized = DOCUMENT + b" " * (DEFAULT_CAP + 1 - len(DOCUMENT))
        self.run_case(oversized, None, "unavailable")

    def test_mcp_advertises_the_same_bounded_default_it_uses(self):
        tool = next(tool for tool in mcp.TOOLS if tool["name"] == "financial_evidence_fetch")
        schema = tool["inputSchema"]["properties"]["max_bytes"]
        self.assertEqual(schema["default"], DEFAULT_CAP)
        self.assertEqual(schema["maximum"], DEFAULT_CAP)


if __name__ == "__main__":
    unittest.main()
