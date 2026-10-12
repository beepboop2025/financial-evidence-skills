import unittest
from scripts.observe_agent_distribution import compare, discover_repositories, repository_candidates


class AgentDiscoveryEvidenceTests(unittest.TestCase):
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
        def malformed(url):
            return {"status": "retrieved", "url": url, "http_status": 200}, b'{"message":"rate limited"}'
        self.assertTrue(all(r["status"] == "invalid_response" for r in discover_repositories(malformed)))

    def test_repository_metadata_does_not_imply_users_or_data_access(self):
        item = repository_candidates({"total_count": 1, "items": [{"full_name": "owner/project", "html_url": "https://github.com/owner/project"}]})[0]
        self.assertIsNone(item["agent_instances"])
        self.assertFalse(item["private_activity_access"])
        self.assertEqual(item["qualification"], "unreviewed_candidate")


if __name__ == "__main__":
    unittest.main()
