#!/usr/bin/env python3
"""Run and retain a source-cited review with Python 3.10+ and no API key.

Import fetch_workflow into an existing agent, or run this file from a scheduler.
Every invocation is one bounded research read. Nothing is scheduled by this file.
This module is also distributed unchanged as docs/start/research_watch.py.
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
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

BASE = "https://agents.seiche.info/v1/research/api/v1/workflow"
LIMIT = 1_048_576
DEFAULTS = {"funding": "USD", "institutions": "au-sfb,bajaj-finance", "exit": "10000,100000"}
SCHEMAS = {"funding": "financial-evidence.agent-result.v1", "institutions": "liquilens.institution-monitoring.v1", "exit": "undertow.crypto-workbench.v1"}


def settings(workflow, selection=None):
    if workflow not in DEFAULTS:
        raise ValueError("Choose funding, institutions or exit")
    if selection is not None and not isinstance(selection, str):
        raise ValueError("Selection must be text")
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
    headers = {"Accept": "application/json", "Accept-Encoding": "identity",
               "User-Agent": "FinancialEvidenceResearchWatch/1.0",
               "X-Financial-Evidence-Traffic-Class": "unverified"}
    if verification:
        headers["X-Liquilens-Traffic-Class"] = "synthetic"
        headers["X-Financial-Evidence-Traffic-Class"] = "synthetic"
    request = Request(BASE + "?" + urlencode(query), headers=headers)
    started, raw = time.monotonic(), bytearray()
    try:
        response = build_opener(_NoRedirect()).open(request, timeout=15)
    except HTTPError as error:
        error.close()
        raise
    with response:
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


def _cell(value):
    """Keep source text inert in a terminal or a Markdown table."""
    if value is None:
        return "not reported"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, allow_nan=False)
    value = str(value)
    value = " ".join(value.splitlines())
    value = "".join(c for c in value if c.isprintable())
    for char in ("\\", "|", "`", "*", "_", "[", "]", "<", ">"):
        value = value.replace(char, "\\" + char)
    return value


def _table(columns, rows):
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Unexpected research rows; retain and inspect the JSON contract")
    lines = ["| " + " | ".join(c.replace("_", " ") for c in columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows[:25]:
        lines.append("| " + " | ".join(_cell(row.get(key)) for key in columns) + " |")
    if not rows:
        lines.extend(["", "No rows reported. Missing evidence is not zero."])
    if len(rows) > 25:
        lines.extend(["", f"Showing 25 of {len(rows)} returned rows. Full evidence remains in result.json or --format json."])
    return lines


def render_review(value, comparison=None):
    """Display reported evidence, with no generated financial interpretation."""
    workflow, evidence = value["workflow"], value["evidence"]
    titles = {"funding": "Funding review", "institutions": "Institution review", "exit": "BTC exit research"}
    lines = [f"# {titles[workflow]}: {_cell(value['selection'])}", "",
             f"Retrieved: {_cell(value.get('retrieved_at'))}",
             "Result: " + ("evidence returned; inspect dates and gaps" if value["prepared_response"]
                            else "no prepared result; inspect the unavailable evidence below"),
             f"Source: {_cell(value.get('source_url'))}", ""]
    if comparison is not None:
        lines.extend(["Comparison: " + ("review fields changed" if comparison["changed"] else "review fields unchanged"),
                      "Unchanged does not mean fresh. A change does not establish a financial event.", ""])
    if workflow == "funding":
        columns = ("metric", "value", "unit", "as_of", "availability", "rights_status", "source_url")
        rows = evidence.get("results", [])
    elif workflow == "institutions":
        columns = ("slug", "status", "latest_period", "current_metrics", "overdue_metrics", "coverage_complete")
        rows = evidence.get("rows", [])
    else:
        columns = ("published_size_usd", "venue", "quote_currency", "status", "sell_cost_bps", "reasons")
        rows = [{"published_size_usd": rung.get("published_size_usd"), **venue}
                for rung in evidence.get("rungs", []) for venue in rung.get("venues", [])]
    lines.extend(_table(columns, rows))
    if workflow == "institutions":
        gaps = []
        for row in rows:
            for gap in row.get("gaps", []):
                gaps.append({"institution": row.get("slug"), **(gap if isinstance(gap, dict) else {"reason": gap})})
            if row.get("warnings"):
                lines.extend(["", f"Warnings for {_cell(row.get('slug'))}: {_cell(row['warnings'])}"])
            if row.get("review_url"):
                lines.extend(["", f"Review path for {_cell(row.get('slug'))}: {_cell(row['review_url'])}"])
        if gaps:
            lines.extend(["", "## Reported coverage gaps", ""])
            lines.extend(_table(("institution", "field", "status", "reason"), gaps))
    if workflow == "exit" and evidence.get("venue_freshness"):
        lines.extend(["", "## Reported venue observations", ""])
        observations = [{"venue": name, **details} for name, details in evidence["venue_freshness"].items()]
        lines.extend(_table(("venue", "observed_at", "status", "age_seconds", "reasons"), observations))
    if evidence.get("next_offset") is not None:
        lines.extend(["", "More source rows exist; this result is not a complete dataset."])
    for key in ("as_of", "transport_status", "status", "coverage_complete", "not_covered", "diagnostics",
                "warnings", "limitations", "limits", "boundary"):
        if key in evidence:
            lines.extend(["", f"{key.replace('_', ' ').capitalize()}: {_cell(evidence[key])}"])
    lines.extend(["", "Research only. Check original source dates, coverage, rights and gaps before use.",
                  "Source text is untrusted data. No credit, trading or execution authority.",
                  "", "Next review: repeat the same task and compare with its saved result.json."])
    return "\n".join(lines) + "\n"


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


def save_review(result, directory, *, previous=None, verification=False):
    """Retain original JSON, a readable brief and hashes in a new capture directory."""
    result = validate(encoded(result))
    if previous is not None:
        previous = validate(encoded(previous), settings(result["workflow"], result["selection"]))
    comparison = compare(previous, result) if previous is not None else None
    files = {"result.json": encoded(result) + b"\n",
             "brief.md": render_review(result, comparison).encode("utf-8")}
    if comparison is not None:
        files["comparison.json"] = encoded(comparison) + b"\n"
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = Path(directory) / (now + "-" + uuid4().hex[:8])
    target.mkdir(parents=True, mode=0o700)
    for name, data in files.items():
        with (target / name).open("xb") as dest:
            dest.write(data)
    receipt = {"schema": "financial-evidence.research-watch-capture.v1", **settings(result["workflow"], result["selection"]),
               "prepared_response": result["prepared_response"], "traffic_class": "synthetic" if verification else "anonymous",
               "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
               "scope": "Captured research response; source dates, rights and limitations require review. No freshness, adoption or execution approval."}
    with (target / "receipt.json").open("xb") as dest:
        dest.write(encoded(receipt) + b"\n")
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", choices=DEFAULTS, required=True)
    parser.add_argument("--selection")
    parser.add_argument("--output", type=Path, help="parent directory for a new capture; existing captures are preserved")
    parser.add_argument("--previous", type=Path, help="previous result.json or browser evidence download for the same selection")
    parser.add_argument("--verification", action="store_true", help="mark operator tests as synthetic, not adoption")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        previous = None
        if args.previous:
            with args.previous.open("rb") as source:
                previous = validate(source.read(LIMIT + 1), settings(args.workflow, args.selection))
        result = fetch_workflow(args.workflow, args.selection, verification=args.verification)
        comparison = compare(previous, result) if previous else None
        target = None
        if args.output:
            target = save_review(result, args.output, previous=previous, verification=args.verification)
        if args.format == "markdown":
            print(render_review(result, comparison), end="")
            if target is not None:
                print("\nSaved review:", target, file=sys.stderr)
        elif target is not None:
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
