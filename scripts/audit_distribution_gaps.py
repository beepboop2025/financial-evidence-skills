#!/usr/bin/env python3
"""Read-only publication identity checks and a complete channel-ledger inventory."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1_000_000
HOSTS = frozenset({"pypi.org", "registry.npmjs.org", "api.github.com",
                  "registry.modelcontextprotocol.io", "agents.seiche.info",
                  "beepboop2025.github.io"})
KINDS = frozenset({"pypi", "npm", "mcp_registry", "github_release", "json_fields", "text_links"})
VERSION = re.compile(r"[0-9][0-9A-Za-z.+_-]{0,79}\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
INTEGRITY = re.compile(r"sha(?:256|384|512)-[A-Za-z0-9+/]{32,128}={0,2}\Z")


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def require(value, reason):
    if not value:
        raise ValueError(reason)


def read_json(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), "local_path_outside_repository")
    raw = path.read_bytes()
    require(len(raw) <= MAX_BYTES, "local_json_too_large")
    value = json.loads(raw)
    require(isinstance(value, dict), "local_json_not_object")
    return value


def source_version(root):
    text = (root / "pyproject.toml").read_text()
    section = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", text)
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', section.group(1)) if section else None
    require(match is not None and VERSION.fullmatch(match.group(1)), "source_package_version_unavailable")
    return match.group(1)


def safe_url(url):
    require(isinstance(url, str) and len(url) <= 2048 and not re.search(r"[\x00-\x20\x7f]", url), "invalid_url")
    parsed = urlparse(url)
    require(parsed.scheme == "https" and parsed.hostname in HOSTS
            and parsed.port in (None, 443) and not parsed.username and not parsed.password
            and not parsed.fragment and not parsed.query, "unapproved_public_url")
    return url


def fetch(url):
    """No credentials, redirects, curl config, cookies or unbounded requests."""
    safe_url(url)
    command = ["curl", "--disable", "--silent", "--show-error", "--proto", "=https",
               "--connect-timeout", "4", "--max-time", "10", "--max-filesize", str(MAX_BYTES),
               "--user-agent", "Financial-Evidence-distribution-audit/1",
               "--header", "X-Financial-Evidence-Traffic-Class: synthetic",
               "--write-out", "\n%{http_code}\n%{content_type}", url]
    # No token is accepted or read; in particular this is safe for every fixed
    # public host. --disable prevents a user's curlrc from adding credentials.
    try:
        result = subprocess.run(command, capture_output=True, timeout=12, check=False)
        body, code, content_type = result.stdout.rsplit(b"\n", 2)
        status = int(code)
        meta = {"url": url, "observed_at": now(), "http_status": status,
                "content_type": content_type.decode("ascii", errors="replace")[:100]}
        if result.returncode != 0 or len(body) > MAX_BYTES:
            return {**meta, "status": "unavailable", "reason": "body_limit_or_transport_failure"}, b""
        if status != 200:
            return {**meta, "status": "missing" if status == 404 else "unavailable",
                    "reason": "http_404" if status == 404 else "http_not_success"}, b""
        return {**meta, "status": "retrieved", "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest()}, body
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"url": url, "observed_at": now(), "status": "unavailable", "reason": "transport_failure"}, b""


def load_inputs(root):
    ledger = read_json(root, "docs/marketplaces.json")
    catalog = read_json(root, "docs/distribution/channel-contracts.json")
    manifest = read_json(root, "docs/integrations.json")
    entries = ledger.get("entries")
    require(isinstance(entries, list) and len(entries) <= 2000, "invalid_ledger_entries")
    states = ledger.get("state_definitions", {})
    require(isinstance(states, dict), "invalid_ledger_states")
    ids = set()
    for row in entries:
        require(isinstance(row, dict) and isinstance(row.get("id"), str)
                and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,119}", row["id"])
                and row["id"] not in ids, "invalid_or_duplicate_ledger_id")
        require(isinstance(row.get("state"), str) and row["state"] in states, "undefined_ledger_state")
        ids.add(row["id"])
    require(catalog.get("schema") == "financial-evidence.channel-contracts.v1", "invalid_catalog_schema")
    channels = catalog.get("channels")
    require(isinstance(channels, list) and 0 < len(channels) <= 64, "invalid_channel_count")
    seen = set()
    for channel in channels:
        require(isinstance(channel, dict), "invalid_channel")
        cid = channel.get("id")
        require(isinstance(cid, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,119}", cid)
                and cid not in seen, "invalid_or_duplicate_channel_id")
        require(isinstance(channel.get("kind"), str) and channel["kind"] in KINDS, "invalid_probe_kind")
        require(type(channel.get("required")) is bool, "required_flag_missing")
        require(isinstance(channel.get("ledger_ids", []), list)
                and all(isinstance(x, str) for x in channel.get("ledger_ids", [])), "invalid_channel_ledger_ids")
        if channel["kind"] in {"json_fields", "text_links"}:
            safe_url(channel.get("url"))
            if channel["kind"] == "json_fields":
                require(isinstance(channel.get("fields"), dict) and channel["fields"], "contract_fields_required")
            else:
                links = channel.get("links")
                require(isinstance(links, list) and 0 < len(links) <= 10
                        and channel.get("content_type") in {"text/plain", "text/html"}, "invalid_text_contract")
                for link in links:
                    safe_url(link)
        else:
            require(isinstance(channel.get("expected"), dict), "expected_version_source_required")
        seen.add(cid)
    return ledger, catalog, manifest


def expected(channel, ledger, manifest, root):
    source = channel.get("expected", {})
    kind = source.get("kind")
    result = {"identity": channel.get("identity"), "version": None, "basis": kind or "contract"}
    if channel["kind"] in {"json_fields", "text_links"}:
        result["fields"] = channel.get("fields", {})
        return result
    if kind == "published_root":
        result["version"] = manifest.get("last_verified_release")
        result["release_state"] = manifest.get("release_state")
    elif kind == "ledger":
        entry = next((e for e in ledger["entries"] if e["id"] == source.get("id")), None)
        require(entry is not None, "expected_component_missing_from_ledger")
        version = entry.get("version")
        if version is None:
            # These fixed, versioned registry/release URLs are the component's
            # own recorded version, never the root Financial Evidence version.
            path = urlparse(entry.get("listing_url", "")).path.rstrip("/")
            version = path.rsplit("/", 1)[-1]
            if "/releases/tag/" in path and version.startswith("v"):
                version = version[1:]
        result["version"] = version
    elif kind == "candidate_package":
        package_path = root / source["path"]
        if not package_path.is_file():
            result.update(publication_state="pending_publication", reason="candidate_artifact_not_present")
            return result
        package = read_json(root, source["path"])
        result.update(identity=package.get("name"), version=package.get("version"))
        receipt_path = root / source["receipt"]
        if not receipt_path.is_file():
            result.update(publication_state="pending_publication", reason="publication_receipt_missing")
        else:
            receipt = read_json(root, source["receipt"])
            if receipt.get("npm_published") is not True:
                result.update(publication_state="pending_publication", reason="publication_not_confirmed")
            else:
                require(receipt.get("package") == result["identity"] and receipt.get("version") == result["version"],
                        "candidate_publication_receipt_identity_mismatch")
                require(receipt.get("schema") == "financial-evidence.ai-sdk-publication.v1"
                        and isinstance(receipt.get("source_commit"), str)
                        and re.fullmatch(r"[a-f0-9]{40}", receipt["source_commit"])
                        and isinstance(receipt.get("tarball_sha256"), str)
                        and SHA256.fullmatch(receipt["tarball_sha256"])
                        and isinstance(receipt.get("tarball_sha512_integrity"), str)
                        and INTEGRITY.fullmatch(receipt["tarball_sha512_integrity"])
                        and receipt["tarball_sha512_integrity"].startswith("sha512-")
                        and isinstance(receipt.get("observed_at"), str),
                        "invalid_candidate_publication_receipt")
                observed = datetime.fromisoformat(receipt["observed_at"].replace("Z", "+00:00"))
                require(observed.tzinfo is not None and observed <= datetime.now(timezone.utc), "invalid_receipt_clock")
                result["publication_state"] = "published"
                result["npm_integrity"] = receipt["tarball_sha512_integrity"]
    else:
        raise ValueError("unknown_expected_version_source")
    require(isinstance(result["version"], str) and VERSION.fullmatch(result["version"]), "invalid_expected_version")
    require(isinstance(result["identity"], str) and len(result["identity"]) <= 200, "invalid_expected_identity")
    return result


def probe_url(channel, expectation):
    kind = channel["kind"]
    name = expectation["identity"]
    if kind in {"json_fields", "text_links"}:
        return safe_url(channel["url"])
    require(isinstance(name, str) and re.fullmatch(r"[@A-Za-z0-9_.\-/]+", name), "invalid_provider_identity")
    if kind == "pypi":
        require("/" not in name and "@" not in name, "invalid_pypi_name")
        url = "https://pypi.org/pypi/" + quote(name, safe="") + "/json"
    elif kind == "npm":
        url = "https://registry.npmjs.org/" + quote(name, safe="") + "/latest"
    elif kind == "mcp_registry":
        url = "https://registry.modelcontextprotocol.io/v0.1/servers/" + quote(name, safe="") + "/versions/latest"
    else:
        require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name), "invalid_github_repository")
        url = "https://api.github.com/repos/" + name + "/releases/tags/v" + quote(expectation["version"], safe="")
    return safe_url(url)


def fields_match(actual, wanted):
    if isinstance(wanted, dict):
        return isinstance(actual, dict) and all(key in actual and fields_match(actual[key], value)
                                                for key, value in wanted.items())
    return type(actual) is type(wanted) and actual == wanted


def verify(channel, expectation, meta, body):
    """Return only allowlisted identity fields; HTTP success is insufficient."""
    if meta["status"] != "retrieved":
        return meta["status"], meta.get("reason", "unavailable"), {}
    kind = channel["kind"]
    content_type = meta.get("content_type", "").split(";", 1)[0].strip().lower()
    if kind == "text_links":
        require(content_type == channel["content_type"], "unexpected_content_type")
        text = body.decode("utf-8")
        matches = {str(index): link in text for index, link in enumerate(channel["links"])}
        return ("current", "required_links_present", {"matched_link_count": len(matches)}) if all(matches.values()) else (
            "drift", "required_discovery_link_missing", {"matched_link_count": sum(matches.values())})
    require(content_type == "application/json" or content_type.endswith("+json"), "unexpected_content_type")
    value = json.loads(body)
    require(isinstance(value, dict), "json_object_required")
    if kind == "json_fields":
        return ("current", "contract_fields_match", {}) if fields_match(value, expectation["fields"]) else (
            "drift", "discovery_contract_changed", {})
    identity, version = expectation["identity"], expectation["version"]
    if kind == "pypi":
        info, files = value.get("info"), value.get("urls")
        require(isinstance(info, dict) and isinstance(files, list), "invalid_pypi_schema")
        observed = {"identity": info.get("name"), "version": info.get("version")}
        require(isinstance(observed["identity"], str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", observed["identity"])
                and isinstance(observed["version"], str) and VERSION.fullmatch(observed["version"]), "invalid_pypi_identity")
        same_name = re.sub(r"[-_.]+", "-", observed["identity"]).lower() == re.sub(r"[-_.]+", "-", identity).lower()
        available = [f for f in files if isinstance(f, dict) and f.get("yanked") is False
                     and isinstance(f.get("digests"), dict) and isinstance(f["digests"].get("sha256"), str)
                     and SHA256.fullmatch(f["digests"]["sha256"])]
        observed["non_yanked_artifact_count"] = len(available)
        if not same_name or observed["version"] != version:
            return "drift", "package_identity_or_version_differs", observed
        return ("current", "published_package_identity_matches", observed) if available else (
            "missing", "no_non_yanked_distribution", observed)
    if kind == "npm":
        dist = value.get("dist")
        require(isinstance(value.get("name"), str) and re.fullmatch(r"[@A-Za-z0-9_./-]{1,200}", value["name"])
                and isinstance(value.get("version"), str) and VERSION.fullmatch(value["version"])
                and isinstance(dist, dict) and isinstance(dist.get("integrity"), str)
                and INTEGRITY.fullmatch(dist["integrity"]), "invalid_npm_schema")
        observed = {"identity": value["name"], "version": value["version"], "registry_integrity": dist["integrity"],
                    "artifact_bytes_verified": False}
        if value["name"] != identity or value["version"] != version:
            return "drift", "package_identity_or_version_differs", observed
        if value.get("deprecated"):
            return "drift", "package_deprecated", observed
        if expectation.get("npm_integrity") and expectation["npm_integrity"] != dist["integrity"]:
            return "drift", "registry_integrity_differs_from_publication_receipt", observed
        return "current", "published_package_identity_matches", observed
    if kind == "mcp_registry":
        server, metadata = value.get("server"), value.get("_meta")
        require(isinstance(server, dict) and isinstance(metadata, dict), "invalid_registry_schema")
        official = metadata.get("io.modelcontextprotocol.registry/official")
        require(isinstance(official, dict) and isinstance(server.get("name"), str)
                and re.fullmatch(r"[A-Za-z0-9_./-]{1,200}", server["name"])
                and isinstance(server.get("version"), str) and VERSION.fullmatch(server["version"])
                and official.get("status") in ("active", "deprecated", "deleted")
                and type(official.get("isLatest")) is bool, "invalid_registry_identity")
        observed = {"identity": server["name"], "version": server["version"],
                    "status": official["status"], "is_latest": official["isLatest"]}
        if server["name"] != identity or server["version"] != version:
            return "drift", "registry_identity_or_version_differs", observed
        if official["status"] != "active" or official["isLatest"] is not True:
            return "drift", "registry_not_active_latest", observed
        return "current", "active_latest_registry_identity_matches", observed
    require(isinstance(value.get("tag_name"), str) and len(value["tag_name"]) <= 100 and type(value.get("draft")) is bool
            and type(value.get("prerelease")) is bool and isinstance(value.get("assets"), list)
            and isinstance(value.get("html_url"), str), "invalid_release_schema")
    observed = {"tag": value["tag_name"], "draft": value["draft"], "prerelease": value["prerelease"],
                "asset_count": len(value["assets"]), "artifact_bytes_verified": False,
                "version_check": "pinned_verified_release_exists_not_latest_discovery"}
    if (value["tag_name"] != "v" + version or value["draft"] or value["prerelease"]
            or value["html_url"] != "https://github.com/" + identity + "/releases/tag/v" + version):
        return "drift", "release_identity_or_publication_differs", observed
    if not value["assets"]:
        return "missing", "release_has_no_assets", observed
    return "current", "published_release_identity_matches", observed


def audit(root=ROOT, *, fetcher=fetch, offline=False):
    ledger, catalog, manifest = load_inputs(root)
    candidate_version = source_version(root)
    entries = ledger["entries"]
    inventory = [{"id": row["id"], "declared_state": row["state"],
                  "listing_url_present": bool(row.get("listing_url")),
                  "submission_url_present": bool(row.get("submission_url")),
                  "observation": "not_monitored", "reason": "no_authoritative_probe_configured",
                  "publication_acceptance_inferred": False} for row in entries]
    by_id = {row["id"]: row for row in inventory}
    results, jobs, findings = [], [], []
    for channel in catalog["channels"]:
        result = {"id": channel["id"], "kind": channel["kind"], "required": channel["required"],
                  "ledger_ids": [i for i in channel.get("ledger_ids", []) if i in by_id],
                  "status": "not_checked", "publication_acceptance_inferred": False}
        prefix = channel.get("ledger_listing_prefix")
        if prefix:
            result["ledger_ids"] = sorted(set(result["ledger_ids"]) | {
                row["id"] for row in entries if isinstance(row.get("listing_url"), str)
                and (row["listing_url"].startswith(prefix)
                     or row["listing_url"].rstrip("/") == prefix.rstrip("/"))})
        if channel.get("ledger_required") and not result["ledger_ids"]:
            findings.append({"channel": channel["id"], "severity": "error", "reason": "channel_missing_from_ledger"})
        try:
            expectation = expected(channel, ledger, manifest, root)
            result["expected"] = expectation
            if expectation.get("publication_state") == "pending_publication":
                result.update(status="pending_publication", reason=expectation["reason"])
            elif offline:
                result["url"] = probe_url(channel, expectation)
                result["reason"] = "offline_inventory_only"
            else:
                result["url"] = probe_url(channel, expectation)
                jobs.append((channel, result))
        except (ValueError, TypeError, KeyError, OSError):
            result.update(status="invalid_configuration", reason="expected_identity_unavailable_or_invalid")
        results.append(result)

    def check(job):
        channel, result = job
        try:
            meta, body = fetcher(result["url"])
            result["transport"] = meta
            status, reason, observed = verify(channel, result["expected"], meta, body)
            result.update(status=status, reason=reason, observed=observed)
        except (ValueError, TypeError, KeyError, UnicodeError):
            result.update(status="invalid_response", reason="provider_response_not_verifiable")
        return result

    # At most 64 reviewed endpoints, four workers, 12 seconds per subprocess.
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(check, jobs))
    for result in results:
        if result["status"] in {"drift", "missing", "invalid_configuration"}:
            findings.append({"channel": result["id"], "severity": "error", "reason": result["reason"]})
        elif result["required"] and result["status"] in {"unavailable", "invalid_response", "pending_publication"}:
            findings.append({"channel": result["id"], "severity": "unknown", "reason": result["reason"]})
        for entry_id in result["ledger_ids"]:
            row = by_id[entry_id]
            row.update(observation=result["status"], reason=result.get("reason"), channel=result["id"])
    status = "not_checked" if offline else ("gaps_detected" if any(f["severity"] == "error" for f in findings)
                                           else "incomplete" if findings else "configured_checks_passed")
    counts = Counter(row["observation"] for row in inventory)
    return {"schema": "financial-evidence.distribution-gaps.v1", "observed_at": now(), "status": status,
            "read_only": True, "traffic_class": "synthetic", "ledger_inventory_complete": len(inventory) == len(entries),
            "coverage_complete": False, "independent_adoption_verified": False, "raw_response_payloads_retained": False,
            "root_release": {"source_version": candidate_version, "manifest_version": manifest.get("version"),
                             "last_verified_release": manifest.get("last_verified_release"),
                             "release_state": manifest.get("release_state"),
                             "candidate_differs_from_verified": candidate_version != manifest.get("last_verified_release")},
            "inputs": {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
                       for path in ("docs/marketplaces.json", "docs/integrations.json", "docs/distribution/channel-contracts.json", "pyproject.toml")},
            "ledger_record_count": len(inventory), "inventory_observation_counts": dict(sorted(counts.items())),
            "ledger_declared_state_counts": dict(sorted(Counter(row["state"] for row in entries).items())),
            "channels": results, "ledger_inventory": inventory, "findings": findings,
            "scope": "Exact configured publication identities and ledger inventory; no inferred listing acceptance, artifact execution, trades or users"}


def markdown(report):
    lines = ["# Distribution gaps", "", f"Observed: {report['observed_at']}", f"Result: {report['status']}", "",
             f"All {report['ledger_record_count']} ledger records are represented. Unmonitored records remain unverified.",
             "Publication identity, registry availability, maintainer acceptance and adoption remain separate.", "",
             "| Channel | Expected version | Observed version/tag | Assessment | Reason |", "|---|---|---|---|---|"]
    def cell(value):
        return str(value if value is not None else "unknown").replace("|", "\\|").replace("\n", " ")[:200]
    for channel in report["channels"]:
        observed = channel.get("observed", {})
        lines.append("| " + " | ".join(map(cell, (channel["id"], channel.get("expected", {}).get("version"),
                    observed.get("version", observed.get("tag")), channel["status"], channel.get("reason")))) + " |")
    lines += ["", "## Findings", ""]
    lines += [f"- {cell(f['channel'])}: {cell(f['reason'])} ({f['severity']})." for f in report["findings"]] or ["No configured-channel gaps observed."]
    lines += ["", "## Complete ledger inventory", "", "| Record | Declared state | Observation |", "|---|---|---|"]
    for row in report["ledger_inventory"]:
        lines.append("| " + " | ".join(map(cell, (row["id"], row["declared_state"], row["observation"]))) + " |")
    return "\n".join(lines) + "\n"


def exit_status(report):
    if report["status"] == "not_checked":
        return 0
    return 1 if report["status"] == "gaps_detected" else 2 if report["status"] == "incomplete" else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true", help="Inventory and configuration only; no publication verification")
    args = parser.parse_args()
    report = audit(offline=args.offline)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "distribution-gaps.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (args.output / "REPORT.md").write_text(markdown(report))
    print(json.dumps({"status": report["status"], "ledger_records": report["ledger_record_count"],
                      "configured_channels": len(report["channels"]), "findings": len(report["findings"])}))
    return exit_status(report)


if __name__ == "__main__":
    raise SystemExit(main())
