import hashlib
import json

import httpx
import pytest

from financial_evidence.trading.enroll import enroll_workspace


def test_explicit_enrollment_solves_challenge_without_implicit_rights():
    seen = []
    challenge = {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "difficulty_bits": 16}
    def reply(request):
        seen.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"challenge": challenge, "signature": "test", "policy_version": "test-v1"})
        body = json.loads(request.content)
        assert hashlib.sha256(f"{challenge['id']}:{body['proof']}".encode()).digest()[:2] == b"\0\0"
        assert "training" not in body and "resale" not in body
        return httpx.Response(201, json={"owner_token": "san_owner", "agent_token": "san_agent"})
    result = enroll_workspace("https://example.test", "Team", "Agent", acknowledge_data_notice=True, transport=httpx.MockTransport(reply))
    assert result["agent_token"] == "san_agent"
    assert len(seen) == 2


def test_no_enrollment_without_explicit_notice_or_secure_destination():
    with pytest.raises(ValueError, match="acknowledge"):
        enroll_workspace("https://example.test", "Team", "Agent")
    with pytest.raises(ValueError, match="HTTPS"):
        enroll_workspace("http://remote.example", "Team", "Agent", acknowledge_data_notice=True)


def test_failed_submission_is_not_replayed():
    seen = []
    def reply(request):
        seen.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json={"challenge": {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "difficulty_bits": 16},
                                           "signature": "test", "policy_version": "test"})
        return httpx.Response(503)
    with pytest.raises(RuntimeError, match="no automatic retry"):
        enroll_workspace("https://example.test", "Team", "Agent", acknowledge_data_notice=True, transport=httpx.MockTransport(reply))
    assert seen == ["GET", "POST"]
