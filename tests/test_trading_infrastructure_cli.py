import contextlib
import io
import json
import unittest
from unittest.mock import patch

from financial_evidence.trading.cli import main


class InfrastructureCliTests(unittest.TestCase):
    def run_cli(self, args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = main(args)
        return code, json.loads(out.getvalue())

    def test_pilot_failure_is_nonzero_and_source_catalog_read_is_not_approval(self):
        with patch("financial_evidence.trading.feed_pilot.run_replay_pilot", return_value={"status":"failed"}):
            self.assertEqual(self.run_cli(["feed-pilot"])[0], 2)
        with patch("financial_evidence.trading.source_contract.qualify_sources", return_value={"status":"blocked"}):
            code, value = self.run_cli(["source-access"])
            self.assertEqual(code, 0)
            self.assertEqual(value["status"], "blocked")

    def test_catalog_exception_contents_are_not_printed(self):
        with patch("financial_evidence.trading.source_contract.qualify_sources", side_effect=ValueError("private")):
            code, value = self.run_cli(["source-access"])
            self.assertEqual(code, 2)
            self.assertNotIn("private", json.dumps(value))

    def test_empty_or_keepalive_only_stream_is_not_success(self):
        for heartbeat in (False, True):
            class Reader:
                def __init__(self, **kwargs):
                    pass
                async def __aenter__(self):
                    return self
                async def __aexit__(self, *_):
                    pass
                async def events(self):
                    if heartbeat:
                        yield {"event":"keepalive","data":{"transport_only":True}}
            with patch("financial_evidence.trading.context.ContextClient", Reader):
                code, value = self.run_cli(["context", "--events"])
                self.assertEqual(code, 2)
                self.assertEqual(value["events"], [])
