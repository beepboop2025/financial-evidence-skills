#!/usr/bin/env python3
"""Run a Financial Evidence workflow with Python 3.10+; no packages or key needed.

Import fetch_workflow into an existing agent, or run this file from a scheduler.
Every invocation is one bounded research read. Nothing is scheduled by this file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

BASE = "https://api.seiche.info/openbb/api/v1/workflow"
LIMIT = 1_048_576
DEFAULTS = {"funding": "USD", "institutions": "au-sfb,bajaj-finance", "exit": "10000,100000"}
SCHEMAS = {"funding": "financial-evidence.agent-result.v1", "institutions": "liquilens.institution-monitoring.v1", "exit": "undertow.crypto-workbench.v1"}


def settings(workflow, selection=None):
    if workflow not in DEFAULTS:
        raise ValueError("Choose funding, institutions or exit")
    selection = (selection or DEFAULTS[workflow]).strip()
    if len(selection) > 160:
        raise ValueError("Selection is too long")
    if workflow == "funding":
        selection = selection.upper()
        if not re.fullmatch(r"[A-Z]{3}", selection):
            raise ValueError("Use a three-letter currency")
    else:
        values = [s.strip() for s in selection.split(",")]
        if workflow == "institutions":
            if len(values) > 5 or any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s) for s in values):
                raise ValueError("Use one to five institution slugs")
        else:
            if len(values) > 4 or any(not re.fullmatch(r"\d+(?:\.\d{1,2})?", s) or not 0 < float(s) <= 1_000_000 for s in values):
                raise ValueError("Use one to four USD sizes from 0.01 to 1000000")
            values = [format(float(s), ".2f").rstrip("0").rstrip(".") for s in values]
        selection = ",".join(dict.fromkeys(values))
    return {"workflow": workflow, "selection": selection}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def validate(raw, request=None):
    if len(raw) > LIMIT:
        raise ValueError("Response exceeds 1 MiB")
    value = json.loads(raw, object_pairs_hook=_object)
    encoded(value)  # Reject non-finite values, including overflow.
    if not isinstance(value, dict) or value.get("schema") != "financial-evidence.workflow-result.v1":
        raise ValueError("Unexpected workflow response")
    actual = settings(value.get("workflow"), value.get("selection"))
    if value.get("selection") != actual["selection"] or (request is not None and actual != request):
        raise ValueError("Response selection does not match the request")
    evidence = value.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("schema") != SCHEMAS[actual["workflow"]]:
        raise ValueError("Original product schema changed")
    if hashlib.sha256(encoded(evidence)).hexdigest() != value.get("content_sha256"):
        raise ValueError("Original product evidence digest does not match")
    if not isinstance(value.get("prepared_response"), bool):
        raise ValueError("Missing prepared-response status")
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_workflow(workflow, selection=None, *, verification=False):
    """Return the original source-cited response; no model, key or background job."""
    query = settings(workflow, selection)
    headers = {"Accept": "application/json", "User-Agent": "FinancialEvidenceResearchWatch/1.0"}
    if verification:
        headers["X-Liquilens-Traffic-Class"] = "synthetic"
    request = Request(BASE + "?" + urlencode(query), headers=headers)
    started, raw = time.monotonic(), bytearray()
    with build_opener(_NoRedirect()).open(request, timeout=15) as response:
        if response.headers.get_content_type() != "application/json":
            raise ValueError("Unexpected response content type")
        while True:
            chunk = response.read(65536)
            raw.extend(chunk)
            if len(raw) > LIMIT or time.monotonic() - started > 30:
                raise ValueError("Response exceeded the byte or elapsed-time limit")
            if not chunk:
                break
    return validate(raw, query)


def review_state(value):
    """Compare evidence fields, not successful retrieval times or cache ages."""
    evidence, workflow = value["evidence"], value["workflow"]
    if workflow == "funding":
        fields = ("entity_id", "metric", "source_field", "value", "unit", "as_of", "availability", "source_status", "rights_status", "source_url", "content_sha256")
        return {"rows": [{k: row.get(k) for k in fields} for row in evidence["results"]],
                "transport_status": evidence.get("transport_status"), "next_offset": evidence.get("next_offset"),
                "diagnostics": evidence.get("diagnostics")}
    if workflow == "institutions":
        return {"records": {row["slug"]: {k: row.get(k) for k in ("status", "content_sha256", "coverage_complete", "gaps", "warnings")} for row in evidence["rows"]},
                "not_covered": evidence.get("not_covered"), "policy_version": evidence.get("policy_version")}
    return {"rungs": evidence["rungs"], "requests": evidence["requests"], "status": evidence.get("status"),
            "venues": {name: {k: row.get(k) for k in ("observed_at", "status", "reasons")}
                       for name, row in evidence.get("venue_freshness", {}).items()}}


def compare(previous, current):
    if settings(previous["workflow"], previous["selection"]) != settings(current["workflow"], current["selection"]):
        raise ValueError("Compare only the same workflow and selection")
    before, after = review_state(previous), review_state(current)
    return {"schema": "financial-evidence.research-watch-comparison.v1",
            "changed": encoded(before) != encoded(after), "previous_retrieved_at": previous.get("retrieved_at"),
            "current_retrieved_at": current.get("retrieved_at"), "before": before, "after": after,
            "scope": "Evidence review fields only. Institution fingerprints include review aging and policy. Unchanged does not mean fresh; changed does not establish a financial event or authorize action."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", choices=DEFAULTS, required=True)
    parser.add_argument("--selection")
    parser.add_argument("--output", type=Path, help="parent directory for a new capture; existing captures are preserved")
    parser.add_argument("--previous", type=Path, help="previous result.json or browser evidence download for the same selection")
    parser.add_argument("--verification", action="store_true", help="mark operator tests as synthetic, not adoption")
    args = parser.parse_args(argv)
    try:
        previous = None
        if args.previous:
            with args.previous.open("rb") as source:
                previous = validate(source.read(LIMIT + 1), settings(args.workflow, args.selection))
        result = fetch_workflow(args.workflow, args.selection, verification=args.verification)
        comparison = compare(previous, result) if previous else None
        if args.output:
            now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            target = args.output / (now + "-" + uuid4().hex[:8])
            target.mkdir(parents=True, mode=0o700)
            files = {"result.json": encoded(result) + b"\n"}
            if comparison is not None:
                files["comparison.json"] = encoded(comparison) + b"\n"
            for name, data in files.items():
                with (target / name).open("xb") as dest:
                    dest.write(data)
            receipt = {"schema": "financial-evidence.research-watch-capture.v1", **settings(args.workflow, args.selection),
                       "prepared_response": result["prepared_response"], "traffic_class": "synthetic" if args.verification else "anonymous",
                       "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
                       "scope": "Captured research response; source dates, rights and limitations require review. No freshness, adoption or execution approval."}
            with (target / "receipt.json").open("xb") as dest:
                dest.write(encoded(receipt) + b"\n")
            print(json.dumps({"capture_directory": str(target), "prepared_response": result["prepared_response"],
                              "changed": comparison["changed"] if comparison else None}))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result["prepared_response"] else 2
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
