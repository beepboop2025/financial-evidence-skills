#!/usr/bin/env python3
"""Capture public funding evidence, replay it, and export a bounded review.

Exit 0: checks passed; 1: data/identity needs attention; 2: capture or input failed.
Each attempt has an exclusive directory. Replay never contacts a service or
replaces the live current summary. No alert, trade, or source repair is performed.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_funding_review import (
    MAX_BYTES,
    POLICY_ID,
    REQUIRED,
    evaluate,
    finite_number,
    load_document,
    publication_denied,
    timestamp,
)
from financial_evidence import tables as table_policy
from financial_evidence.core import _parse_finite_float, _reject_nonfinite

ORIGIN = "https://api.seiche.info"
PROTOCOL = "2025-11-25"
SCHEMA = "liquidity-lab.funding-capture.v1"
SOURCE_NAMES = ("mcp-initialize", "mcp-initialized", "funding-desk", "atlas", "health")
BACKEND_NAMES = ("backend-health", "backend-release")


class ReplayPolicyMismatch(ValueError):
    """The original release is required to reproduce the original policy."""


def implementation_fingerprints():
    return {
        "checker_source_sha256": sha256(
            Path(__file__).with_name("check_funding_review.py").read_bytes()
        ),
        "capture_tool_sha256": sha256(Path(__file__).read_bytes()),
        "publication_policy_sha256": sha256(Path(table_policy.__file__).read_bytes()),
    }


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def strict_json(raw):
    return json.loads(
        raw, parse_constant=_reject_nonfinite, parse_float=_parse_finite_float
    )


def encoded(document):
    return (json.dumps(document, indent=2, allow_nan=False) + "\n").encode()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def backend_origin(value):
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or re.fullmatch(r"(?:/[A-Za-z0-9_-]+)*/?", parsed.path) is None
        or not parsed.hostname
        or parsed.scheme not in ("https", "http")
        or (
            parsed.scheme == "http"
            and parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        )
    ):
        raise ValueError(
            "backend URL must use HTTPS, or HTTP localhost, with a safe path prefix and no credentials"
        )
    return value.rstrip("/")


def fetch(name, url, *, payload=None, session=None, timeout=15, opener=None):
    """Bound bytes, socket inactivity, and elapsed body-read time; never redirect.

    read1 limits each blocking read to one socket operation. The elapsed check
    plus socket timeout bounds a slow response to approximately 2 * timeout.
    A truncated prefix is retained and explicitly never considered replayable.
    """
    headers = {
        "User-Agent": "LiquidityLab-Funding-Operator/1",
        "X-Liquilens-Traffic-Class": "synthetic",
        "Accept": "application/json, text/event-stream",
        "Accept-Encoding": "identity",
    }
    body = None if payload is None else encoded(payload)
    if body is not None:
        headers.update(
            {"Content-Type": "application/json", "MCP-Protocol-Version": PROTOCOL}
        )
    if session:
        headers["Mcp-Session-Id"] = session
    receipt = {
        "name": name,
        "url": url,
        "method": "GET" if body is None else "POST",
        "started_at": utcnow(),
        "http_status": None,
        "complete": False,
        "traffic_class": "operator_verification",
        "error": None,
    }
    if body is not None:
        receipt["request_sha256"] = sha256(body)
    started = time.monotonic()
    raw = bytearray()
    response_session = None
    try:
        request = urllib.request.Request(url, data=body, headers=headers)
        try:
            response = (opener or urllib.request.build_opener(NoRedirect())).open(
                request, timeout=timeout
            )
        except urllib.error.HTTPError as error:
            response = error
        with response:
            receipt["http_status"] = response.status
            receipt["content_type"] = response.headers.get("Content-Type", "")
            response_session = response.headers.get("Mcp-Session-Id")
            while True:
                if time.monotonic() - started > timeout:
                    raise TimeoutError("response exceeded elapsed read limit")
                chunk = response.read1(min(65536, MAX_BYTES + 1 - len(raw)))
                if not chunk:
                    receipt["complete"] = True
                    break
                raw.extend(chunk)
                if len(raw) > MAX_BYTES:
                    raise ValueError("response exceeds 2 MiB")
        if not 200 <= receipt["http_status"] < 300:
            receipt["error"] = "http_error"
    except (OSError, ValueError, urllib.error.URLError) as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)[:240]
    receipt.update(
        {
            "finished_at": utcnow(),
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "bytes": len(raw),
            "sha256": sha256(raw),
        }
    )
    return receipt, bytes(raw), response_session


def rpc_result(raw, request_id):
    """Accept one matching JSON-RPC reply, including finite SSE data frames."""
    try:
        replies = [strict_json(raw)]
    except (ValueError, UnicodeError):
        text = raw.decode("utf-8").replace("\r\n", "\n")
        replies = []
        for event in text.split("\n\n"):
            data = "\n".join(
                line[5:].lstrip(" ")
                for line in event.splitlines()
                if line.startswith("data:")
            )
            if data:
                replies.append(strict_json(data))
    matching = [r for r in replies if isinstance(r, dict) and r.get("id") == request_id]
    if len(matching) != 1:
        raise ValueError("missing or ambiguous JSON-RPC reply")
    reply = matching[0]
    result = reply.get("result")
    if (
        reply.get("jsonrpc") != "2.0"
        or "error" in reply
        or not isinstance(result, dict)
        or result.get("isError")
    ):
        raise ValueError("JSON-RPC request did not succeed")
    return result


def decode_desk(raw):
    result = rpc_result(raw, "funding-desk")
    if isinstance(result.get("structuredContent"), dict):
        return result["structuredContent"]
    content = result.get("content", [])
    texts = [
        item.get("text")
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    if len(texts) != 1:
        raise ValueError("desk requires one structured object or one text payload")
    desk = strict_json(texts[0])
    if not isinstance(desk, dict):
        raise ValueError("desk payload is not an object")
    return desk


def spreadsheet_text(value):
    text = "" if value is None else str(value)
    return (
        "'" + text
        if text.lstrip().startswith(("=", "+", "-", "@"))
        or text.startswith(("\t", "\r", "\n"))
        else text
    )


def export_csv(desk, report):
    """Export only allowed usable values; retain one row for every required id."""
    rows = {}
    duplicates = set()
    sections = desk.get("sections")
    for section in sections if isinstance(sections, list) else []:
        if not isinstance(section, dict):
            continue
        metrics = section.get("metrics")
        for row in metrics if isinstance(metrics, list) else []:
            if not isinstance(row, dict) or row.get("id") not in REQUIRED:
                continue
            name = row["id"]
            if name in rows:
                duplicates.add(name)
            rows[name] = (
                row,
                publication_denied(desk)
                or publication_denied(section)
                or publication_denied(row),
            )
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "metric_id",
            "value",
            "unit",
            "observation_date",
            "source",
            "cadence",
            "publisher_freshness",
            "value_state",
            "evaluated_at",
            "review_status",
        ]
    )
    for name, (unit, cadence) in REQUIRED.items():
        row, denied = rows.get(name, ({}, False))
        state = (
            "restricted"
            if denied
            else "duplicate"
            if name in duplicates
            else "available"
            if row.get("status") == "available" and finite_number(row.get("value"))
            else "unavailable"
        )
        writer.writerow(
            [
                name,
                row["value"] if state == "available" else "",
                spreadsheet_text(row.get("unit", unit)),
                spreadsheet_text(row.get("asof")),
                spreadsheet_text(row.get("source")),
                spreadsheet_text(row.get("cadence", cadence)),
                spreadsheet_text(row.get("freshness")),
                state,
                report["evaluated_at"],
                report["status"],
            ]
        )
    return output.getvalue().encode("utf-8")


def analyze(
    records,
    bodies,
    *,
    evaluated_at,
    max_snapshot_age_seconds,
    expected_release=None,
    backend=None,
):
    def responded(names):
        return all(
            (r := records.get(name, {})).get("complete")
            and not r.get("error")
            and isinstance(r.get("http_status"), int)
            and 200 <= r["http_status"] < 300
            for name in names
        )

    source_available = responded(SOURCE_NAMES)
    backend_available = responded(BACKEND_NAMES) if backend else True
    report = {
        "schema": "liquidity-lab.funding-review-check.v1",
        "policy_id": POLICY_ID,
        "evaluated_at": timestamp(evaluated_at).isoformat(),
        "status": "not_evaluated",
        "issues": [],
    }
    desk = None
    errors = []
    release = None
    if source_available:
        try:
            initialized = rpc_result(bodies["mcp-initialize"], "funding-init")
            if initialized.get("protocolVersion") != PROTOCOL:
                raise ValueError("unsupported negotiated MCP protocol")
            desk = decode_desk(bodies["funding-desk"])
            atlas, health = (strict_json(bodies[name]) for name in ("atlas", "health"))
            report = evaluate(
                desk,
                atlas,
                health,
                evaluated_at=evaluated_at,
                max_snapshot_age_seconds=max_snapshot_age_seconds,
            )
            report["input_sha256"] = {
                "desk": sha256(encoded(desk)),
                "atlas": sha256(bodies["atlas"]),
                "health": sha256(bodies["health"]),
            }
        except (
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
            RecursionError,
        ) as error:
            source_available = False
            desk = None
            errors.append("source_payload_invalid: " + str(error)[:240])
    identity = "not_requested"
    if backend and backend_available:
        try:
            health = strict_json(bodies["backend-health"])
            release = strict_json(bodies["backend-release"])
            if (
                not isinstance(health, dict)
                or health.get("status") != "ok"
                or not isinstance(release, dict)
            ):
                raise ValueError("backend health or release payload invalid")
            release_id = release.get("release_id")
            if (
                not isinstance(release_id, str)
                or not release_id
                or health.get("release_id") != release_id
            ):
                identity = "mismatch"
            else:
                identity = (
                    "observed"
                    if not expected_release
                    else "matched"
                    if release_id == expected_release
                    else "mismatch"
                )
        except (ValueError, TypeError, OverflowError, RecursionError) as error:
            backend_available = False
            errors.append("backend_payload_invalid: " + str(error)[:240])
            identity = "unavailable"
    elif backend:
        identity = "unavailable"
    available = source_available and backend_available
    ready = available and report["status"] == "checks_passed" and identity != "mismatch"
    summary = {
        "availability": "available" if available else "unavailable",
        "source_availability": "available" if source_available else "unavailable",
        "backend_availability": ("available" if backend_available else "unavailable")
        if backend
        else "not_requested",
        "data_readiness": report["status"],
        "release_identity": identity,
        "ready": ready,
        "errors": errors,
        "observed_release": release,
        "exit_code": 0 if ready else 1 if available else 2,
    }
    return summary, report, desk


def new_directory(output, category, at):
    root = output / category
    root.mkdir(parents=True, exist_ok=True)
    path = root / (timestamp(at).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex)
    path.mkdir(mode=0o700)
    return path


def finish(directory, manifest, bodies):
    summary, report, desk = analyze(
        manifest["requests"],
        bodies,
        evaluated_at=manifest["evaluated_at"],
        max_snapshot_age_seconds=manifest["max_snapshot_age_seconds"],
        expected_release=manifest.get("expected_release"),
        backend=manifest.get("backend_url"),
    )
    manifest.update(summary)
    write_new(directory / "review.json", encoded(report))
    if desk is not None:
        write_new(directory / "desk.json", encoded(desk))
        write_new(directory / "funding-observations.csv", export_csv(desk, report))
    manifest["artifact_sha256"] = {
        p.name: sha256(p.read_bytes())
        for p in sorted(directory.iterdir())
        if p.is_file()
    }
    write_new(directory / "manifest.json", encoded(manifest))
    return manifest


def update_current(output, directory, manifest):
    """Serialize concurrent writers and preserve references to earlier successes."""
    with (output / ".current.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = output / "current.json"
        previous = load_document(path)[0] if path.exists() else {}
        reference = {
            "capture": str(directory.relative_to(output)),
            "capture_id": directory.name,
            "evaluated_at": manifest["evaluated_at"],
            "manifest_sha256": sha256((directory / "manifest.json").read_bytes()),
            "availability": manifest["availability"],
            "data_readiness": manifest["data_readiness"],
            "release_identity": manifest["release_identity"],
            "ready": manifest["ready"],
        }
        if previous and timestamp(previous["latest"]["evaluated_at"]) > timestamp(
            reference["evaluated_at"]
        ):
            return
        current = {
            "schema": "liquidity-lab.funding-current.v1",
            "latest": reference,
            "last_available": reference
            if manifest["availability"] == "available"
            else previous.get("last_available"),
            "last_ready": reference
            if manifest["ready"]
            else previous.get("last_ready"),
        }
        prior = previous.get("measurement", {})
        probes = prior.get("probes", 0) + 1
        available_probes = prior.get("available_probes", 0) + int(
            manifest["availability"] == "available"
        )
        consecutive_failures = (
            0
            if manifest["availability"] == "available"
            else prior.get("consecutive_unavailable_probes", 0) + 1
        )
        current["measurement"] = {
            "scope": "scheduled_operator_samples_not_continuous_uptime_or_sla",
            "first_probe_at": prior.get("first_probe_at", manifest["evaluated_at"]),
            "latest_probe_at": manifest["evaluated_at"],
            "probes": probes,
            "available_probes": available_probes,
            "ready_probes": prior.get("ready_probes", 0) + int(manifest["ready"]),
            "sampled_availability_pct": round(available_probes / probes * 100, 4),
            "consecutive_unavailable_probes": consecutive_failures,
            "longest_unavailable_probe_run": max(
                prior.get("longest_unavailable_probe_run", 0), consecutive_failures
            ),
            "latest_request_latencies_seconds": {
                name: receipt.get("elapsed_seconds")
                for name, receipt in manifest["requests"].items()
            },
        }
        temporary = output / (".current-" + uuid.uuid4().hex + ".tmp")
        try:
            write_new(temporary, encoded(current))
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def capture(
    output,
    *,
    backend=None,
    expected_release=None,
    timeout=15,
    max_snapshot_age_seconds=900,
    fetcher=fetch,
):
    directory = new_directory(output, "captures", utcnow())
    records, bodies = {}, {}

    def request(name, url, payload=None, session=None):
        receipt, raw, next_session = fetcher(
            name, url, payload=payload, session=session, timeout=timeout
        )
        write_new(directory / (name + ".response"), raw)
        records[name], bodies[name] = receipt, raw
        return next_session

    session = request(
        "mcp-initialize",
        ORIGIN + "/mcp",
        {
            "jsonrpc": "2.0",
            "id": "funding-init",
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL,
                "capabilities": {},
                "clientInfo": {"name": "LiquidityLab-Funding-Operator", "version": "1"},
            },
        },
    )
    request(
        "mcp-initialized",
        ORIGIN + "/mcp",
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        session,
    )
    request(
        "funding-desk",
        ORIGIN + "/mcp",
        {
            "jsonrpc": "2.0",
            "id": "funding-desk",
            "method": "tools/call",
            "params": {"name": "money_market_context", "arguments": {"section": "all"}},
        },
        session,
    )
    request("atlas", ORIGIN + "/api/v2/money-markets")
    request("health", ORIGIN + "/api/health")
    if backend:
        request("backend-health", backend + "/healthz")
        request("backend-release", backend + "/api/v1/release")
    manifest = {
        "schema": SCHEMA,
        "mode": "capture",
        "evaluated_at": utcnow(),
        "max_snapshot_age_seconds": max_snapshot_age_seconds,
        "backend_url": backend,
        "expected_release": expected_release,
        "requests": records,
        "policy_id": POLICY_ID,
        **implementation_fingerprints(),
    }
    finish(directory, manifest, bodies)
    update_current(output, directory, manifest)
    return directory, manifest


def replay(source, output):
    manifest, manifest_hash = load_document(source / "manifest.json")
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unrecognized capture manifest")
    fingerprints = implementation_fingerprints()
    if manifest.get("policy_id") != POLICY_ID or any(
        manifest.get(key) != digest for key, digest in fingerprints.items()
    ):
        raise ReplayPolicyMismatch(
            "policy_version_mismatch: capture/checker/publication implementation differs; use the original release to replay this capture"
        )
    original_review, review_hash = load_document(source / "review.json")
    if manifest.get("artifact_sha256", {}).get("review.json") != review_hash:
        raise ValueError("original review hash mismatch")
    if (
        not isinstance(original_review, dict)
        or original_review.get("policy_id") != POLICY_ID
    ):
        raise ReplayPolicyMismatch(
            "policy_version_mismatch: original review policy differs; use the original release to replay this capture"
        )
    expected = set(SOURCE_NAMES) | (
        set(BACKEND_NAMES) if manifest.get("backend_url") else set()
    )
    if set(manifest.get("requests", {})) != expected:
        raise ValueError("capture request set is incomplete or unexpected")
    bodies = {}
    for name, receipt in manifest["requests"].items():
        with (source / (name + ".response")).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 2)
        if (
            len(raw) > MAX_BYTES + 1
            or sha256(raw) != receipt.get("sha256")
            or len(raw) != receipt.get("bytes")
        ):
            raise ValueError("response hash or size mismatch: " + name)
        bodies[name] = raw
    directory = new_directory(output, "replays", utcnow())
    replay_manifest = {
        key: manifest.get(key)
        for key in (
            "schema",
            "evaluated_at",
            "max_snapshot_age_seconds",
            "backend_url",
            "expected_release",
            "requests",
            "policy_id",
            *fingerprints,
        )
    }
    replay_manifest.update(
        {
            "mode": "replay",
            "original_manifest_sha256": manifest_hash,
            "original_policy_id": original_review["policy_id"],
            "replayed_at": utcnow(),
        }
    )
    for name, raw in bodies.items():
        write_new(directory / (name + ".response"), raw)
    return directory, finish(directory, replay_manifest, bodies)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--backend-url", type=backend_origin)
    parser.add_argument("--expected-release")
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--max-snapshot-age-seconds", type=int, default=900)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args(argv)
    try:
        if not finite_number(args.timeout) or not 1 <= args.timeout <= 30:
            raise ValueError("timeout must be between 1 and 30 seconds")
        if not 1 <= args.max_snapshot_age_seconds <= 86400:
            raise ValueError("snapshot age must be between 1 and 86400 seconds")
        if args.expected_release and not args.backend_url:
            raise ValueError("expected release requires a backend URL")
        if args.replay and (args.backend_url or args.expected_release):
            raise ValueError("replay uses the backend identity recorded in the capture")
        directory, manifest = (
            replay(args.replay, args.output_dir)
            if args.replay
            else capture(
                args.output_dir,
                backend=args.backend_url,
                expected_release=args.expected_release,
                timeout=args.timeout,
                max_snapshot_age_seconds=args.max_snapshot_age_seconds,
            )
        )
        print(
            json.dumps(
                {
                    "capture_directory": str(directory),
                    **{
                        key: manifest[key]
                        for key in (
                            "availability",
                            "data_readiness",
                            "release_identity",
                            "ready",
                            "exit_code",
                        )
                    },
                },
                indent=2,
            )
        )
        return manifest["exit_code"]
    except ReplayPolicyMismatch as error:
        print(json.dumps({"status": "policy_version_mismatch", "error": str(error)}))
        return 2
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        RecursionError,
    ) as error:
        print(json.dumps({"status": "operator_error", "error": str(error)[:240]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
