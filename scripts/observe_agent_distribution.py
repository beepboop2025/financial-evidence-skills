#!/usr/bin/env python3
"""Observe public agent projects and distribution receipts; never infer private use."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs/distribution/agent-ecosystem.json"
LEDGER = ROOT / "docs/marketplaces.json"
MAX_BYTES = 5_000_000
SEARCHES = {
    "finance": "finance agent in:name,description,topics archived:false",
    "trading": "trading agent in:name,description,topics archived:false",
    "shopping": "shopping agent in:name,description,topics archived:false",
    "arbitrage": "arbitrage in:name,description,topics archived:false",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch(url):
    """Only HTTPS GETs. No cookies, tokens, remote tools or external code execution."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("public observation URL must use HTTPS without credentials")
    command = ["curl", "--silent", "--show-error", "--location", "--max-redirs", "3",
               "--connect-timeout", "5", "--max-time", "15", "--max-filesize", str(MAX_BYTES),
               "--proto", "=https", "--proto-redir", "=https", "--user-agent",
               "FinancialEvidence-Discovery/1.0 (+https://agents.seiche.info/privacy)",
               "--write-out", "\n%{http_code}\n%{url_effective}", url]
    try:
        result = subprocess.run(command, capture_output=True, timeout=18)
        body, code, final = result.stdout.rsplit(b"\n", 2)
        status = int(code)
        meta = {"url": url, "final_url": final.decode(), "http_status": status,
                "observed_at": utc_now(), "status": "retrieved" if result.returncode == 0 and status == 200 else "unavailable"}
        if meta["status"] == "retrieved":
            meta.update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
            return meta, body
        meta["error"] = "response_size_limit" if result.returncode == 63 else ("http_error" if status else "transport_error")
        return meta, b""
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return {"url": url, "observed_at": utc_now(), "status": "unavailable", "error": "transport_error"}, b""


def repository_candidates(payload):
    """Search results are possible projects, never counts of deployed agents."""
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list) or not isinstance(payload.get("total_count"), int):
        raise ValueError("invalid repository search response")
    candidates = []
    for item in payload["items"]:
        name, url = item.get("full_name"), item.get("html_url")
        if not isinstance(name, str) or not isinstance(url, str) or not url.startswith("https://github.com/"):
            raise ValueError("invalid public repository record")
        candidates.append({"id": name, "url": url, "description": item.get("description"),
                           "updated_at": item.get("updated_at"), "language": item.get("language"),
                           "topics": item.get("topics", []), "qualification": "unreviewed_candidate",
                           "agent_instances": None, "private_activity_access": False})
    return candidates


def discover_repositories(fetcher=fetch):
    results = []
    for segment, query in SEARCHES.items():
        url = "https://api.github.com/search/repositories?" + urlencode({"q": query, "sort": "updated", "per_page": 50})
        meta, body = fetcher(url)
        row = {"id": segment, "query": query, **meta, "candidates": [], "query_complete": False}
        if meta["status"] == "retrieved":
            try:
                payload = json.loads(body)
                row["candidates"] = repository_candidates(payload)
                row["total_matches"] = payload["total_count"]
                row["query_complete"] = not payload.get("incomplete_results", True) and payload["total_count"] <= len(row["candidates"])
                row["status"] = "observed"
            except (ValueError, TypeError, KeyError):
                row.update(status="invalid_response", error="invalid_repository_schema")
        results.append(row)
    return results


def discover_registry(fetcher=fetch):
    results = []
    for term in ("finance", "trading", "shopping", "arbitrage"):
        url = "https://registry.modelcontextprotocol.io/v0.1/servers?" + urlencode({"search": term, "limit": 100, "version": "latest"})
        meta, body = fetcher(url)
        row = {"id": term, **meta, "servers": [], "query_complete": False}
        if meta["status"] == "retrieved":
            try:
                payload = json.loads(body)
                if not isinstance(payload, dict) or not isinstance(payload.get("servers"), list):
                    raise ValueError("missing servers")
                for entry in payload["servers"]:
                    server = entry["server"]
                    if not isinstance(server, dict) or not isinstance(server.get("name"), str) or not isinstance(server.get("version"), str):
                        raise ValueError("invalid server identity")
                    row["servers"].append({"name": server["name"], "version": server["version"],
                                           "description": server.get("description"), "qualification": "unreviewed_candidate"})
                metadata = payload.get("metadata", {})
                if not isinstance(metadata, dict):
                    raise ValueError("invalid pagination metadata")
                row["query_complete"] = "metadata" in payload and not metadata.get("nextCursor")
                row["status"] = "observed"
            except (ValueError, TypeError, KeyError):
                row.update(status="invalid_response", servers=[], error="invalid_registry_schema")
        results.append(row)
    return results


def discover_directory(fetcher=fetch):
    """Read the free curated index; never execute its commands or MCP endpoints."""
    meta, body = fetcher("https://agentndx.ai/api/servers.json")
    result = {**meta, "candidates": [], "catalog_entries": None, "global_coverage_complete": False}
    if meta["status"] != "retrieved":
        return result
    try:
        payload = json.loads(body)
        servers = payload["servers"]
        if not isinstance(servers, list):
            raise ValueError("invalid index")
        selected = []
        for server in servers:
            if not isinstance(server, dict) or not isinstance(server.get("id"), str) or not isinstance(server.get("name"), str):
                raise ValueError("invalid server metadata")
            description = json.dumps({k: server.get(k) for k in ("name", "description", "category", "tags", "use_cases")})
            if re.search(r"financ|trading|arbitrage|commerce|shopping|payment|cryptocurrency", description, re.I):
                selected.append({"id": server["id"], "name": server["name"],
                                 "description": server.get("description"), "homepage_url": server.get("homepage_url"),
                                 "github_url": server.get("github_url"), "protocols": server.get("protocols", []),
                                 "qualification": "unreviewed_candidate", "private_activity_access": False})
        result.update(status="observed", catalog_entries=len(servers), candidates=selected,
                      provider_updated_at=payload.get("updated"))
    except (ValueError, TypeError, KeyError):
        result.update(status="invalid_response", error="invalid_directory_schema")
    return result


def compare(previous, current):
    """A failed or truncated observation cannot prove a project disappeared."""
    old_rows = {r["id"]: r for r in previous.get("repository_searches", [])}
    changes = []
    for row in current["repository_searches"]:
        old = old_rows.get(row["id"])
        value = {"segment": row["id"], "added": [], "removed": [], "status": "no_comparable_snapshot"}
        if old and old.get("status") == row.get("status") == "observed" and old.get("query") == row.get("query"):
            before, after = ({r["id"] for r in x["candidates"]} for x in (old, row))
            value.update(status="compared", added=sorted(after - before))
            value["removals_evaluable"] = bool(old.get("query_complete") and row.get("query_complete"))
            if value["removals_evaluable"]:
                value["removed"] = sorted(before - after)
        changes.append(value)
    return changes


def markdown(report):
    lines = ["# Agent ecosystem and distribution observation", "", f"Observed: {report['observed_at']}", "",
             "Public project metadata and marketplace reachability only. Coverage is partial; deployed agents, trades, purchases and adoption are unknown.", "",
             f"- Curated opportunities: {len(report['targets'])}",
             f"- Product/channel ledger records: {report['ledger_record_count']}",
             f"- Distinct public repository candidates: {report['repository_candidate_count']}", "",
             f"- Relevant public directory candidates: {len(report['directory']['candidates']) if report['directory']['status'] == 'observed' else 'unknown'} (overlap with repository candidates is not deduplicated)", "",
             "## Public discovery", "", "| Search | Observation | Returned | Query complete |", "|---|---|---:|---|"]
    for row in report["repository_searches"]:
        lines.append(f"| {row['id']} | {row['status']} | {len(row['candidates']) if row['status'] == 'observed' else 'unknown'} | {row['query_complete']} |")
    lines += ["", "An absent result in a bounded search is not evidence of inactivity. Marketplace HTTP responses never change the verified ledger state.", "",
              "## Endpoint observations", "", "| Group | Record | HTTP | Observation |", "|---|---|---:|---|"]
    for group in ("targets", "marketplaces"):
        for row in report[group]:
            lines.append(f"| {group} | {row['id']} | {row.get('http_status', 'unknown')} | {row['status']} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--skip-registry", action="store_true", help="Record registry as not checked; never infer zero coverage")
    args = parser.parse_args()
    catalog = json.loads(CATALOG.read_text())
    ledger = json.loads(LEDGER.read_text())
    targets = catalog["targets"]
    marketplaces = [e for e in ledger["entries"] if e.get("listing_url")]
    urls = sorted({t["source_url"] for t in targets} | {e["listing_url"] for e in marketplaces})
    with ThreadPoolExecutor(max_workers=4) as pool:
        observations = dict(zip(urls, pool.map(lambda url: fetch(url)[0], urls)))
    repository_searches = discover_repositories()
    registry_searches = [] if args.skip_registry else discover_registry()
    directory = discover_directory()
    report = {"schema": "liquilens.agent-distribution-observation.v1", "observed_at": utc_now(),
              "catalog_sha256": hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
              "coverage_complete": False, "private_activity_access": False,
              "agent_instances": None, "purchases_observed": None,
              "ledger_record_count": len(ledger["entries"]),
              "ledger_state_changes": [],
              "targets": [{"id": t["id"], "segment": t["segment"], **observations[t["source_url"]]} for t in targets],
              "marketplaces": [{"id": e["id"], "ledger_state": e["state"], **observations[e["listing_url"]]} for e in marketplaces],
              "repository_searches": repository_searches,
              "repository_candidate_count": len({c["id"] for r in repository_searches for c in r["candidates"]}) if any(r["status"] == "observed" for r in repository_searches) else None,
              "directory": directory,
              "registry_observation": "not_checked" if args.skip_registry else "attempted",
              "registry_searches": registry_searches}
    previous = json.loads(args.previous.read_text()) if args.previous and args.previous.is_file() else {}
    report["changes"] = compare(previous, report)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "observation.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "REPORT.md").write_text(markdown(report))
    print(json.dumps({"report": str(args.output / "REPORT.md"), "repository_candidates": report["repository_candidate_count"],
                      "coverage_complete": False, "targets": len(targets), "marketplace_pages": len(marketplaces)}))


if __name__ == "__main__":
    main()
