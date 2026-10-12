"""Explicit free workspace enrollment; never run automatically during installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit


def enroll_workspace(endpoint, organization, agent, *, acknowledge_data_notice=False, transport=None):
    import httpx
    url = urlsplit(endpoint)
    if (not url.hostname or url.username or url.password or url.query or url.fragment
            or url.scheme not in {"http", "https"} or ".." in url.path or "%" in url.path
            or (url.scheme == "http" and url.hostname not in {"127.0.0.1", "localhost", "::1"})):
        raise ValueError("HTTPS or loopback endpoint required")
    if acknowledge_data_notice is not True:
        raise ValueError("read the platform data notice and explicitly acknowledge it")
    if any(not isinstance(value, str) or not 1 <= len(value.strip()) <= 120 for value in (organization, agent)):
        raise ValueError("bounded team and agent labels required")
    endpoint = endpoint.rstrip("/")
    with httpx.Client(timeout=15, follow_redirects=False, transport=transport) as client:
        def request(method, path, body=None):
            with client.stream(method, endpoint + path, json=body,
                               headers={"Accept-Encoding": "identity"}) as response:
                if response.status_code not in {200, 201}:
                    raise RuntimeError(f"workspace request was not confirmed (HTTP {response.status_code}); no automatic retry")
                data = bytearray()
                for part in response.iter_bytes():
                    data.extend(part)
                    if len(data) > 65536:
                        raise ValueError("workspace response exceeds limit")
                return json.loads(data)
        value = request("GET", "/v1/enrollment/challenge")
        challenge = value["challenge"]
        if challenge.get("difficulty_bits") != 16 or not isinstance(challenge.get("id"), str) or len(challenge["id"]) != 36:
            raise ValueError("unsupported enrollment challenge")
        started, proof = time.monotonic(), None
        for nonce in range(4_000_000):
            if nonce % 1024 == 0 and time.monotonic() - started > 30:
                break
            if hashlib.sha256(f"{challenge['id']}:{nonce}".encode()).digest()[:2] == b"\0\0":
                proof = nonce
                break
        if proof is None:
            raise RuntimeError("workspace preparation deadline exceeded; no enrollment submitted")
        result = request("POST", "/v1/enrollment", {
            "challenge": challenge, "signature": value["signature"], "proof": proof,
            "organization": organization.strip(), "agent": agent.strip(),
            "policy_version": value["policy_version"], "data_notice_acknowledged": True,
        })
        if (not isinstance(result, dict) or not all(isinstance(result.get(k), str) and result[k].startswith("san_")
                                                  for k in ("owner_token", "agent_token"))):
            raise RuntimeError("workspace acceptance or credentials were not confirmed; do not replay automatically")
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="https://agents.seiche.info")
    parser.add_argument("--organization", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--acknowledge-data-notice", action="store_true",
                        help="Acknowledge /privacy; grants no training or resale permission")
    parser.add_argument("--output", type=Path, required=True, help="New private credential file; never overwritten")
    args = parser.parse_args(argv)
    if not args.acknowledge_data_notice:
        parser.error("read /privacy and use --acknowledge-data-notice")
    descriptor = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        result = enroll_workspace(args.endpoint, args.organization, args.agent, acknowledge_data_notice=True)
        with os.fdopen(descriptor, "w") as output:
            descriptor = None
            json.dump(result, output, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
    finally:
        if descriptor is not None:
            os.close(descriptor)
    print(json.dumps({"status": "enrolled", "credentials_file": str(args.output),
                      "shared_training": False, "resale_permission": False}))


if __name__ == "__main__":
    main()
