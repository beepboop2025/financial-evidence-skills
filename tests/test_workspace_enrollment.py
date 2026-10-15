import hashlib
import importlib.util
import json
import unittest

from financial_evidence.trading.enroll import enroll_workspace

HAS_HTTPX = importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(HAS_HTTPX, "optional HTTP transport dependency required")
class WorkspaceEnrollmentTests(unittest.TestCase):
    def test_explicit_enrollment_solves_challenge_without_implicit_rights(self):
        import httpx
        seen = []
        challenge = {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "difficulty_bits": 16}

        def reply(request):
            seen.append(request)
            if request.method == "GET":
                return httpx.Response(200, json={"challenge": challenge, "signature": "test", "policy_version": "test-v1"})
            body = json.loads(request.content)
            self.assertEqual(hashlib.sha256(f"{challenge['id']}:{body['proof']}".encode()).digest()[:2], b"\0\0")
            self.assertNotIn("training", body)
            self.assertNotIn("resale", body)
            return httpx.Response(201, json={"owner_token": "san_owner", "agent_token": "san_agent"})

        result = enroll_workspace("https://example.test", "Team", "Agent", acknowledge_data_notice=True, transport=httpx.MockTransport(reply))
        self.assertEqual(result["agent_token"], "san_agent")
        self.assertEqual(len(seen), 2)

    def test_no_enrollment_without_explicit_notice_or_secure_destination(self):
        with self.assertRaisesRegex(ValueError, "acknowledge"):
            enroll_workspace("https://example.test", "Team", "Agent")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            enroll_workspace("http://remote.example", "Team", "Agent", acknowledge_data_notice=True)

    def test_failed_submission_is_not_replayed(self):
        import httpx
        seen = []

        def reply(request):
            seen.append(request.method)
            if request.method == "GET":
                return httpx.Response(200, json={"challenge": {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "difficulty_bits": 16},
                                               "signature": "test", "policy_version": "test"})
            return httpx.Response(503)

        with self.assertRaisesRegex(RuntimeError, "no automatic retry"):
            enroll_workspace("https://example.test", "Team", "Agent", acknowledge_data_notice=True, transport=httpx.MockTransport(reply))
        self.assertEqual(seen, ["GET", "POST"])


if __name__ == "__main__":
    unittest.main()
