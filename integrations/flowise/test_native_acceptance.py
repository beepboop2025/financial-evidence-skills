"""Fail-closed receipt checks; these do not substitute for native execution."""
import copy
import json
import unittest

from native_acceptance import ENDPOINT, public_page, validate_definition, validate_execution


def definition_fixture():
    return {"nodes": [
        {"id": "startAgentflow_0", "data": {"name": "startAgentflow", "inputs": {
            "startInputType": "chatInput", "startEphemeralMemory": True, "startState": [], "startPersistState": False}}},
        {"id": "toolAgentflow_0", "data": {"name": "toolAgentflow", "inputs": {
            "toolAgentflowSelectedTool": "customMCP", "toolAgentflowSelectedToolConfig": {
                "toolAgentflowSelectedTool": "customMCP", "mcpActions": ["financial_evidence_query"],
                "mcpServerConfig": json.dumps({"url": ENDPOINT})}, "toolUpdateState": [],
            "toolInputArgs": [{"inputArgName": key, "inputArgValue": value} for key, value in
                              {"dataset": "money_markets", "limit": 1, "offset": 0}.items()]}}}],
        "edges": [{"source": "startAgentflow_0", "target": "toolAgentflow_0"}]}


def result_fixture():
    page = {
        "dataset": "market_liquidity", "limit": 1, "offset": 0, "returned_rows": 1,
        "transport_status": "complete", "evidence_status": "not_evaluated",
        "carrier_verification": "not_performed", "diagnostics": [],
        "results": [{"entity_id": "UST", "availability": "unavailable", "value": None}],
        "sources": [{"source_url": "https://example.org/source", "source_reported": {
            "state": [{"name": "response_status", "value": "PARTIAL"}], "clocks": []}}],
    }
    result = {"executionId": "test-execution", "agentFlowExecutedData": [
        {"nodeId": "startAgentflow_0", "status": "FINISHED"},
        {"nodeId": "toolAgentflow_0", "status": "FINISHED", "data": {"output": {
            "content": json.dumps([{"type": "text", "text": json.dumps(page)}])}}},
    ]}
    return result, page


class ReceiptTests(unittest.TestCase):
    def test_production_candidate_has_no_synthetic_header(self):
        validate_definition(definition_fixture(), "money_markets", synthetic_tag_required=False)

    def test_higher_precedence_tool_aliases_and_credentials_rejected(self):
        for key in ("selectedTool", "selectedToolConfig", "credentialId"):
            with self.subTest(key=key), self.assertRaises(AssertionError):
                flow = definition_fixture()
                flow["nodes"][1]["data"]["inputs"][key] = "unsafe-override"
                validate_definition(flow, "money_markets", synthetic_tag_required=False)

    def test_string_numeric_argument_rejected(self):
        flow = definition_fixture()
        flow["nodes"][1]["data"]["inputs"]["toolInputArgs"][1]["inputArgValue"] = "1"
        with self.assertRaises(AssertionError):
            validate_definition(flow, "money_markets", synthetic_tag_required=False)

    def test_finished_native_nodes_preserve_missing_value_and_partial_source(self):
        result, expected = result_fixture()
        page, steps = validate_execution(result, "market_liquidity")
        self.assertEqual(page, expected)
        self.assertEqual(len(steps), 2)
        self.assertIsNone(public_page(page)["rows"][0]["value"])
        self.assertEqual(public_page(page)["sources"][0]["source_reported"]["state"][0]["value"], "PARTIAL")

    def test_http_success_is_insufficient_when_native_tool_failed(self):
        result, _ = result_fixture()
        for state in ("ERROR", "STOPPED", "TERMINATED", "INPROGRESS"):
            with self.subTest(state=state), self.assertRaises(AssertionError):
                broken = copy.deepcopy(result)
                broken["agentFlowExecutedData"][1]["status"] = state
                validate_execution(broken, "market_liquidity")

    def test_missing_persisted_identity_or_native_step_rejected(self):
        result, _ = result_fixture()
        result.pop("executionId")
        with self.assertRaises(AssertionError):
            validate_execution(result, "market_liquidity")
        result, _ = result_fixture()
        result["agentFlowExecutedData"].pop()
        with self.assertRaises(AssertionError):
            validate_execution(result, "market_liquidity")

    def test_unavailable_zero_is_rejected(self):
        result, page = result_fixture()
        page["results"][0]["value"] = 0
        result["agentFlowExecutedData"][1]["data"]["output"]["content"] = json.dumps([
            {"type": "text", "text": json.dumps(page)}])
        with self.assertRaises(AssertionError):
            validate_execution(result, "market_liquidity")

    def test_projection_drops_unrecognized_private_fields(self):
        _, page = result_fixture()
        page["owner"] = {"password": "not-for-export"}
        page["results"][0]["cookie"] = "not-for-export"
        page["sources"][0]["headers"] = {"Authorization": "not-for-export"}
        page["sources"][0]["source_reported"]["state"][0]["private"] = "not-for-export"
        self.assertNotIn("not-for-export", json.dumps(public_page(page)))


if __name__ == "__main__":
    unittest.main()
