#!/usr/bin/env python3
"""Send an explicitly selected JSON research request to hosted NoiseFloor."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://agents.seiche.info/v1/noisefloor"
ROUTES = {"spectral": "/v1/spectral/assess", "dyson": "/v1/research/dyson",
          "market": "/v1/market/assess", "narrative": "/v1/narrative/triage"}
MAX_BYTES = 2 * 1024 * 1024


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


def _invalid_number(value):
    raise ValueError("JSON numbers must be finite")


def assess(operation, payload, *, synthetic=False, opener=None):
    if operation not in ROUTES or not isinstance(payload, dict):
        raise ValueError("Choose a reviewed operation and one JSON object")
    body = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
    if len(body) > MAX_BYTES:
        raise ValueError("Request exceeds 2 MiB")
    request = Request(BASE + ROUTES[operation], body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "X-Financial-Evidence-Traffic-Class": "synthetic" if synthetic else "unverified",
        "User-Agent": "Financial-Evidence-Hosted-NoiseFloor/1",
    })
    client = opener or build_opener(NoRedirects()).open
    with client(request, timeout=120) as response:
        if response.geturl() != request.full_url:
            raise ValueError("Unexpected response origin or path")
        if response.headers.get_content_type() != "application/json":
            raise ValueError("Expected JSON")
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Response exceeds 4 MiB")
    result = json.loads(raw, parse_constant=_invalid_number)
    json.dumps(result, allow_nan=False)
    if not isinstance(result, dict):
        raise ValueError("Expected one result object")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=ROUTES)
    parser.add_argument("input", type=Path)
    parser.add_argument("--synthetic", action="store_true", help="Label example/test traffic")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.stat().st_size > MAX_BYTES:
        parser.error("Input exceeds 2 MiB")
    payload = json.loads(args.input.read_bytes(), parse_constant=_invalid_number)
    try:
        result = assess(args.operation, payload, synthetic=args.synthetic)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        parser.exit(2, f"Hosted NoiseFloor returned HTTP {status}; no fallback was used.\n")
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result.get("status"), "output": str(args.output)}))


if __name__ == "__main__":
    main()
