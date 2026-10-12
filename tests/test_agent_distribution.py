import unittest
from scripts.observe_agent_distribution import compare, discover_directory, discover_registry, discover_repositories, markdown, repository_candidates


class AgentDiscoveryEvidenceTests(unittest.TestCase):
    def test_registry_schema_drift_is_reported_without_aborting_other_sources(self):
        for body in (b'[]', b'{"servers":[{"server":null}]}', b'{"servers":[],"metadata":null}'):
            with self.subTest(body=body):
                def response(url):
                    return {"status": "retrieved", "url": url}, body
                self.assertTrue(all(row["status"] == "invalid_response" for row in discover_registry(response)))

    def test_registry_without_pagination_metadata_does_not_claim_complete_search(self):
        def response(url):
            return {"status": "retrieved", "url": url}, b'{"servers":[]}'
        self.assertTrue(all(not row["query_complete"] for row in discover_registry(response)))

    def test_directory_records_are_metadata_and_commands_are_never_executed(self):
        def response(url):
            return {"status": "retrieved", "url": url}, b'{"servers":[{"id":"finance","name":"Finance tool","endpoint":"malicious command","install_cmd":"do not run"},{"id":"unrelated","name":"Image tool"}]}'
        result = discover_directory(response)
        self.assertEqual(result["catalog_entries"], 2)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertNotIn("install_cmd", result["candidates"][0])
        self.assertNotIn("endpoint", result["candidates"][0])
        self.assertFalse(result["global_coverage_complete"])

    def test_partial_malformed_directory_is_not_a_successful_empty_observation(self):
        def response(url):
            return {"status": "retrieved", "url": url}, b'{"servers":[{"id":"finance","name":"Finance tool"},null]}'
        result = discover_directory(response)
        self.assertEqual(result["status"], "invalid_response")
        self.assertIsNone(result["catalog_entries"])

    def test_provider_error_cannot_be_reported_as_empty_success(self):
        def failed(url):
            return {"status": "unavailable", "url": url, "http_status": 403}, b""
        rows = discover_repositories(failed)
        self.assertTrue(all(r["status"] == "unavailable" and not r["query_complete"] for r in rows))
        old = {"repository_searches": [{"id": "finance", "status": "observed", "query": rows[0]["query"],
                                        "query_complete": True, "candidates": [{"id": "owner/existing"}]}]}
        self.assertEqual(compare(old, {"repository_searches": rows})[0]["removed"], [])

    def test_bounded_search_does_not_report_disappearances(self):
        old = {"repository_searches": [{"id": "trading", "query": "same", "status": "observed",
                 "query_complete": False, "candidates": [{"id": "a/old"}]}]}
        current = {"repository_searches": [{"id": "trading", "query": "same", "status": "observed",
                     "query_complete": False, "candidates": [{"id": "b/new"}]}]}
        result = compare(old, current)[0]
        self.assertEqual(result["added"], ["b/new"])
        self.assertEqual(result["removed"], [])
        self.assertFalse(result["removals_evaluable"])

    def test_schema_failure_preserves_unknown(self):
        for body in (b'{"message":"rate limited"}', b'{"total_count":1,"items":[null]}'):
            with self.subTest(body=body):
                def malformed(url):
                    return {"status": "retrieved", "url": url, "http_status": 200}, body
                self.assertTrue(all(r["status"] == "invalid_response" for r in discover_repositories(malformed)))

    def test_readable_report_exposes_registry_and_directory_failures(self):
        report = {"observed_at": "2026-10-12T00:00:00Z", "targets": [], "marketplaces": [],
                  "ledger_record_count": 0, "repository_candidate_count": None, "repository_searches": [],
                  "registry_observation": "attempted", "registry_searches": [
                      {"id": "finance", "status": "unavailable", "servers": [], "query_complete": False}],
                  "directory": {"status": "invalid_response", "candidates": []}}
        rendered = markdown(report)
        self.assertIn("| MCP registry: finance | unavailable | unknown | False |", rendered)
        self.assertIn("AgentNDX catalog: invalid_response", rendered)

    def test_repository_metadata_does_not_imply_users_or_data_access(self):
        item = repository_candidates({"total_count": 1, "items": [{"full_name": "owner/project", "html_url": "https://github.com/owner/project"}]})[0]
        self.assertIsNone(item["agent_instances"])
        self.assertFalse(item["private_activity_access"])
        self.assertEqual(item["qualification"], "unreviewed_candidate")


if __name__ == "__main__":
    unittest.main()
