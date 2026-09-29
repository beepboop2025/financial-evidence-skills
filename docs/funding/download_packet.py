#!/usr/bin/env python3
"""Save one verified public funding packet. No account, package install or telemetry."""

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

BASE = "https://api.seiche.info/funding-evidence"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def get(path):
    request = urllib.request.Request(
        BASE + path, headers={"User-Agent": "Financial-Evidence-Packet-Client/1"}
    )
    with urllib.request.build_opener(NoRedirect()).open(
        request, timeout=20
    ) as response:
        raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError("response too large")
        return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new directory; existing folders are never overwritten",
    )
    args = parser.parse_args()
    try:
        latest = json.loads(get("/latest"))
        identifier = latest["packet"]["packet_id"]
        if not re.fullmatch(r"\d{8}T\d{6}\.\d{6}Z-[a-f0-9]{32}", identifier):
            raise ValueError("invalid packet identity")
        manifest_raw = get("/packets/" + identifier + "/manifest.json")
        manifest = json.loads(manifest_raw)
        if manifest["packet_id"] != identifier or set(manifest["artifacts"]) != {
            "review.json",
            "observations.csv",
        }:
            raise ValueError("invalid packet manifest")
        files = {
            name: get("/packets/" + identifier + "/" + name)
            for name in manifest["artifacts"]
        }
        for name, raw in files.items():
            if hashlib.sha256(raw).hexdigest() != manifest["artifacts"][name]:
                raise ValueError("packet integrity failed")
        review = json.loads(files["review.json"])
        if review["capture_id"] != identifier:
            raise ValueError("review identity mismatch")
        args.output.mkdir(parents=True, exist_ok=False)
        for name, raw in dict(files, **{"manifest.json": manifest_raw}).items():
            with (args.output / name).open("xb") as stream:
                stream.write(raw)
        print(
            json.dumps(
                {
                    "saved": str(args.output),
                    "packet_id": identifier,
                    "review_asof": review.get("review_asof"),
                    "ready": latest["ready"],
                    "scope": review.get("review_scope"),
                }
            )
        )
        return 0 if latest["ready"] else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            json.dumps(
                {
                    "saved": False,
                    "error": type(error).__name__ + ": " + str(error)[:180],
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
