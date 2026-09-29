#!/usr/bin/env python3
"""Update a local funding dataset once. Python 3.10+ on macOS/Linux; no telemetry client."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.seiche.info/funding-evidence"
PACKET = re.compile(r"\d{8}T\d{6}\.\d{6}Z-[a-f0-9]{32}")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def reject(_):
        raise ValueError("nonfinite JSON value")

    return json.loads(raw, parse_constant=reject)


def encoded(value):
    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def get(path, headers):
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                BASE + path,
                headers={"User-Agent": "Financial-Evidence-Daily-Job/1", **headers},
            )
            with urllib.request.build_opener(NoRedirect()).open(
                request, timeout=20
            ) as response:
                raw = response.read(262145)
                if len(raw) > 262144:
                    raise ValueError("response too large")
                return response.status, dict(response.headers.items()), raw
        except urllib.error.HTTPError as error:
            if error.code == 304:
                return 304, dict(error.headers.items()), b""
            if error.code not in (429, 502, 503, 504) or attempt == 2:
                raise
            retry = error.headers.get("Retry-After", "")
            time.sleep(min(20, int(retry)) if retry.isdigit() else 2 ** (attempt + 1))
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("bounded request attempts exhausted")


def header(headers, name):
    return next(
        (value for key, value in headers.items() if key.lower() == name.lower()), None
    )


def read(path):
    if path.is_symlink() or path.stat().st_size > 262144:
        raise ValueError("invalid local artifact")
    return path.read_bytes()


def verify(folder, expected, manifest_hash):
    manifest_raw = read(folder / "manifest.json")
    manifest = decode(manifest_raw)
    if (
        digest(manifest_raw) != manifest_hash
        or manifest.get("packet_id") != expected
        or set(manifest["artifacts"]) != {"review.json", "observations.csv"}
    ):
        raise ValueError("local manifest identity or hash mismatch")
    for name, sha in manifest["artifacts"].items():
        if digest(read(folder / name)) != sha:
            raise ValueError("local packet artifact hash mismatch")
    review = decode(read(folder / "review.json"))
    if review.get("capture_id") != expected or review.get("ready") is not True:
        raise ValueError("local review identity or readiness mismatch")
    return manifest


def atomic(path, raw):
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".pending-", delete=False
    ) as stream:
        pending = Path(stream.name)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def update(root, *, request=get, token=None, operator=False):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".update.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _update(root, request, token, operator)


def _update(root, request, token, operator):
    headers = {"Authorization": "Bearer " + token} if token else {}
    if operator:
        headers.update(
            {"X-Traffic-Class": "synthetic", "X-Operator-Probe": "funding-daily-job"}
        )
    cursor_path = root / "cursor.json"
    cursor = decode(read(cursor_path)) if cursor_path.exists() else None
    if cursor:
        if (
            cursor.get("schema") != "financial-evidence.funding-cursor.v1"
            or not PACKET.fullmatch(cursor["packet_id"])
            or not re.fullmatch(r'"[a-f0-9]{64}"', cursor["etag"])
        ):
            raise ValueError("invalid saved cursor")
        verify(
            root / "packets" / cursor["packet_id"],
            cursor["packet_id"],
            cursor["manifest_sha256"],
        )
    latest_headers = dict(headers)
    if cursor:
        latest_headers["If-None-Match"] = cursor["etag"]
    for attempt in range(3):
        status, response_headers, raw = request("/v1/funding/latest", latest_headers)
        if status == 304:
            if cursor is None or header(response_headers, "ETag") != cursor["etag"]:
                raise ValueError(
                    "conditional response has no matching verified local packet"
                )
            return {
                "status": "unchanged",
                "packet_id": cursor["packet_id"],
                "ready": True,
            }
        if status != 200:
            raise ValueError("latest funding evidence is unavailable")
        latest = decode(raw)
        identifier = latest["packet_id"]
        etag = header(response_headers, "ETag")
        if (
            latest.get("schema") != "financial-evidence.funding.v1"
            or latest.get("ready") is not True
            or not isinstance(identifier, str)
            or not PACKET.fullmatch(identifier)
            or etag != '"' + digest(raw) + '"'
        ):
            raise ValueError("latest contract or response validator mismatch")
        changes = None
        if cursor and cursor["packet_id"] != identifier:
            query = urllib.parse.urlencode(
                {"since": cursor["packet_id"], "until": identifier}
            )
            try:
                code, _, change_raw = request("/v1/funding/changes?" + query, headers)
            except urllib.error.HTTPError as error:
                if error.code == 409 and attempt < 2:
                    continue
                raise
            if code == 409 and attempt < 2:
                continue
            changes = decode(change_raw)
            if (
                code != 200
                or changes.get("before") != cursor["packet_id"]
                or changes.get("after") != identifier
                or changes.get("ready") is not True
            ):
                raise ValueError(
                    "change response does not match cursor and selected packet"
                )
        break
    else:
        raise ValueError("latest packet changed during all bounded attempts")
    packets = root / "packets"
    packets.mkdir(exist_ok=True)
    target = packets / identifier
    if target.exists():
        verify(target, identifier, latest["manifest_sha256"])
    else:
        staging = Path(tempfile.mkdtemp(prefix=".capture-", dir=packets))
        try:
            for name in ("manifest.json", "review.json", "observations.csv"):
                code, _, body = request("/packets/" + identifier + "/" + name, headers)
                if code != 200:
                    raise ValueError("packet artifact unavailable")
                with (staging / name).open("xb") as stream:
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
            verify(staging, identifier, latest["manifest_sha256"])
            os.replace(staging, target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    if decode(read(target / "review.json"))["results"] != latest["observations"]:
        raise ValueError("current view and immutable review disagree")
    change_path = None
    if changes is not None:
        directory = root / "changes"
        directory.mkdir(exist_ok=True)
        change_path = directory / (cursor["packet_id"] + "--" + identifier + ".json")
        atomic(change_path, encoded(changes))
    # The cursor moves only after all three immutable artifacts verify.
    atomic(
        cursor_path,
        encoded(
            {
                "schema": "financial-evidence.funding-cursor.v1",
                "packet_id": identifier,
                "etag": etag,
                "manifest_sha256": latest["manifest_sha256"],
            }
        ),
    )
    return {
        "status": "updated",
        "packet_id": identifier,
        "ready": True,
        "review_asof": latest["review_asof"],
        "saved": str(target),
        "changes": str(change_path) if change_path else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument(
        "--token-file",
        type=Path,
        help="optional private file from explicit application enrollment",
    )
    parser.add_argument(
        "--operator", action="store_true", help="exclude this test from external usage"
    )
    args = parser.parse_args()
    try:
        token = None
        if args.token_file:
            if args.token_file.stat().st_mode & 0o077:
                raise ValueError("token file must be private (chmod 600)")
            token = read(args.token_file).decode().strip()
            if not re.fullmatch(r"fe_[A-Za-z0-9_-]{43}", token):
                raise ValueError("invalid application token")
        print(json.dumps(update(args.state, token=token, operator=args.operator)))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print(
            json.dumps(
                {
                    "status": "failed",
                    "cursor_preserved": True,
                    "reason": "Evidence unavailable or verification failed; retain prior files and retry later.",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
