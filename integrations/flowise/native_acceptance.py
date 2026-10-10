#!/usr/bin/env python3
"""Run bounded research through saved native Flowise Agentflows, using normal OSS auth.

Only public/ is suitable for CI artifacts. Everything else may contain local
owner credentials, cookies, database state or upstream error text.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request

DATASETS = ("money_markets", "bank_risk", "market_liquidity")
ENDPOINT = "https://api.seiche.info/openbb/mcp"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")
    path.chmod(0o600)


def validate_definition(flow: dict, dataset: str, *, synthetic_tag_required=True) -> None:
    """Reject arbitrary tools/credentials before executing a supplied template."""
    assert len(flow["nodes"]) == 2 and len(flow["edges"]) == 1
    start, tool = flow["nodes"]
    assert start["id"] == "startAgentflow_0" and start["data"]["name"] == "startAgentflow"
    assert start["data"]["inputs"] == {"startInputType": "chatInput", "startEphemeralMemory": True,
                                       "startState": [], "startPersistState": False}
    assert tool["id"] == "toolAgentflow_0" and tool["data"]["name"] == "toolAgentflow"
    edge = flow["edges"][0]
    assert edge["source"] == start["id"] and edge["target"] == tool["id"]
    inputs = tool["data"]["inputs"]
    assert set(inputs) == {"toolAgentflowSelectedTool", "toolAgentflowSelectedToolConfig", "toolInputArgs", "toolUpdateState"}
    assert inputs["toolUpdateState"] == []
    assert inputs["toolAgentflowSelectedTool"] == "customMCP"
    config = inputs["toolAgentflowSelectedToolConfig"]
    assert set(config) == {"mcpActions", "mcpServerConfig", "toolAgentflowSelectedTool"}
    assert config["toolAgentflowSelectedTool"] == "customMCP"
    assert config["mcpActions"] == ["financial_evidence_query"]
    mcp = json.loads(config["mcpServerConfig"])
    assert mcp["url"] == ENDPOINT and set(mcp) <= {"url", "headers"}
    assert set(mcp.get("headers", {})) <= {"X-Liquilens-Traffic-Class", "User-Agent"}
    if synthetic_tag_required:
        assert mcp["headers"]["X-Liquilens-Traffic-Class"] == "synthetic"
    else:
        assert "X-Liquilens-Traffic-Class" not in mcp.get("headers", {})
    arguments = {item["inputArgName"]: item["inputArgValue"] for item in inputs["toolInputArgs"]}
    assert arguments == {"dataset": dataset, "limit": 1, "offset": 0}
    assert type(arguments["limit"]) is int and type(arguments["offset"]) is int


def validate_execution(result: dict, dataset: str) -> tuple[dict, list[dict]]:
    steps = result.get("agentFlowExecutedData", [])
    assert len(steps) == 2, "Expected exactly Start and Tool execution"
    assert {step["nodeId"] for step in steps} == {"startAgentflow_0", "toolAgentflow_0"}
    assert all(step["status"] == "FINISHED" for step in steps), "Native execution failed"
    assert result.get("executionId"), "Missing persisted execution identity"
    tool = next(step for step in steps if step["nodeId"] == "toolAgentflow_0")
    content = json.loads(tool["data"]["output"]["content"])
    block = next(item for item in content if item.get("type") == "text" and item.get("text", "").lstrip().startswith("{"))
    page = json.loads(block["text"])
    assert page["dataset"] == dataset
    assert page["limit"] == 1 and page["offset"] == 0
    assert page["returned_rows"] == len(page["results"]) <= 1
    assert page["evidence_status"] == "not_evaluated"
    assert page["carrier_verification"] == "not_performed"
    assert isinstance(page["sources"], list) and isinstance(page["diagnostics"], list)
    for row in page["results"]:
        if str(row.get("availability", "")).lower() in {"unavailable", "restricted_or_unavailable"} and "value" in row:
            assert row["value"] is None, "Unavailable value must remain null"
    return page, [{"node": step["nodeId"], "status": step["status"]} for step in steps]


def public_page(page: dict) -> dict:
    """Explicit field allowlist: never publish a native API result wholesale."""
    fields = ("dataset", "schema", "limit", "offset", "returned_rows", "transport_status",
              "status_semantics", "evidence_status", "carrier_verification")
    row_fields = ("entity_id", "entity_name", "metric", "value", "unit", "as_of", "availability",
                  "source_status", "rights_status", "published_at", "knowledge_time", "retrieved_at",
                  "source_url", "observation_url", "content_sha256", "transport_status")
    source_fields = ("product", "topic", "source_url", "resolved_url", "ok", "retrieved_at", "content_sha256")
    sources = []
    for source in page["sources"]:
        item = {key: source[key] for key in source_fields if key in source}
        reported = source.get("source_reported", {})
        item["source_reported"] = {
            kind: [{key: entry[key] for key in ("name", "path", "value") if key in entry} for entry in reported.get(kind, [])]
            for kind in ("clocks", "state")
        }
        sources.append(item)
    return {**{key: page[key] for key in fields if key in page},
            "rows": [{key: row[key] for key in row_fields if key in row} for row in page["results"]],
            "source_count": len(sources), "sources": sources, "diagnostic_count": len(page["diagnostics"])}


class LocalAPI:
    def __init__(self, port: int, private: Path):
        self.base = f"http://127.0.0.1:{port}"
        self.private = private
        self.owner = {"email": "native-validation@localhost.invalid", "password": "LocalOnly1!" + secrets.token_urlsafe(32)}
        write_json(private / "owner.json", self.owner)
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method: str, path: str, body=None):
        request = urllib.request.Request(self.base + path, method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Origin": self.base,
                     "X-Request-From": "internal", "User-Agent": "Financial-Evidence-Flowise-Native-Acceptance/1.0"})
        try:
            with self.opener.open(request, timeout=120) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            # Error bodies may echo session material. Retain privately, never print.
            (self.private / "last-api-error.txt").write_bytes(exc.read())
            raise RuntimeError(f"Local Flowise API returned HTTP {exc.code} for {method} {path}") from None

    def login(self):
        status, _ = self.call("POST", "/api/v1/account/register", {"user": {
            "name": "Local Native Validation", "email": self.owner["email"], "credential": self.owner["password"]}})
        assert status == 201
        status, _ = self.call("POST", "/api/v1/auth/login", self.owner)
        assert status == 200

    def execute(self, raw: bytes, dataset: str, label: str, public: Path) -> dict:
        flow = json.loads(raw)
        validate_definition(flow, dataset, synthetic_tag_required=label != "marketplace-candidate")
        # Pin the entire graph/metadata to this runtime's trusted builder. This
        # rejects hidden credential fields and Tool's higher-precedence aliases.
        expected = self.private / f"definitions/{label}.json"
        assert flow == json.loads(expected.read_text()), "Candidate differs from the reviewed native definition"
        text = raw.decode("utf-8")
        status, saved = self.call("POST", "/api/v1/chatflows", {
            "name": f"Financial Evidence native {label}", "type": "AGENTFLOW", "flowData": text,
            "deployed": False, "isPublic": False,
            "description": "Synthetic bounded public research MCP verification; no model or trading action."})
        assert status == 200
        flow_id = saved["id"]
        status, readback = self.call("GET", "/api/v1/chatflows/" + flow_id)
        assert status == 200 and readback["id"] == flow_id and readback["type"] == "AGENTFLOW"
        assert readback["flowData"].encode("utf-8") == raw, "Saved workflow bytes changed"
        started = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        status, result = self.call("POST", "/api/v1/internal-prediction/" + flow_id, {
            "question": f"Run bounded public research {dataset}", "streaming": False,
            "overrideConfig": {"sessionId": "synthetic-" + secrets.token_hex(12)}})
        write_json(self.private / f"{label}-execution.json", result)
        assert status == 200
        page, steps = validate_execution(result, dataset)
        export_name = f"financial-evidence-flowise-{label}.json"
        (public / export_name).write_bytes(raw)
        return {"label": label, "dataset": dataset, "flow_id": flow_id,
                "execution_id": result["executionId"], "http_status": status,
                "operator_controlled": True, "exclude_from_adoption_evidence": True,
                "request_started_at": started_at, "request_finished_at": datetime.now(timezone.utc).isoformat(),
                "synthetic_header": label != "marketplace-candidate",
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "export": export_name, "definition_sha256": sha256(raw),
                "saved_definition_readback_identical": True, "saved_type": "AGENTFLOW",
                "native_steps": steps, "query": {"dataset": dataset, "limit": 1, "offset": 0},
                "page": public_page(page)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--node", default=shutil.which("node"))
    parser.add_argument("--port", type=int, default=3311)
    parser.add_argument("--candidate", type=Path, help="Also execute these exact money_markets template bytes")
    parser.add_argument("--generated-candidate", action="store_true", help="Execute the untagged candidate built from committed marketplace metadata")
    args = parser.parse_args()
    assert not (args.candidate and args.generated_candidate), "Choose one candidate source"
    os.umask(0o077)
    runtime = args.runtime_dir.resolve()
    root = args.evidence_dir.resolve()
    # Refuse reuse: an existing owner DB or another service must never be modified.
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    private, public = root / "private", root / "public"
    for folder in (private, public, private / "database", private / "secrets", private / "storage", private / "logs", private / "tmp", private / "definitions"):
        folder.mkdir(mode=0o700)
    with socket.socket() as check:
        check.bind(("127.0.0.1", args.port))
    assert not (runtime / "node_modules/flowise/.env").exists(), "Unexpected runtime dotenv override"
    script = Path(__file__).with_name("build_workflows.cjs")
    subprocess.run([args.node, str(script), str(runtime), str(private / "definitions")], check=True,
                   stdout=(private / "builder.stdout").open("w"), stderr=(private / "builder.stderr").open("w"), timeout=120)
    identity = json.loads((private / "definitions/runtime-identity.json").read_text())
    proof = {"schema": "financial-evidence.flowise-native.v1", "observed_at": datetime.now(timezone.utc).isoformat(),
             "runtime": identity, "source_revision": os.environ.get("GITHUB_SHA"),
             "pr_head_revision": os.environ.get("PR_HEAD_SHA"), "ci_run_id": os.environ.get("GITHUB_RUN_ID"),
             "scope": {"operator_controlled": True, "full_saved_workflow_execution": False,
                       "browser_ui_observed": False, "model_used": False, "adoption_proven": False,
                       "marketplace_acceptance_proven": False, "source_freshness_validated": False,
                       "evidence_validity_validated": False},
             "mcp_endpoint": ENDPOINT, "native_components": ["startAgentflow", "toolAgentflow", "customMCP"],
             "transport": "Native CustomMCP negotiates Streamable HTTP with SSE fallback",
             "status": "failed", "expected_workflow_count": 3 + bool(args.candidate or args.generated_candidate),
             "successful_workflow_count": 0, "runs": []}
    env = {key: os.environ[key] for key in ("HOME", "USER", "LOGNAME", "LANG", "PATH") if key in os.environ}
    env.update({"HOST": "127.0.0.1", "PORT": str(args.port), "APP_URL": f"http://127.0.0.1:{args.port}",
                "TRUST_PROXY": "false", "MODE": "main", "NODE_OPTIONS": "--max-old-space-size=2048",
                "DATABASE_TYPE": "sqlite", "DATABASE_PATH": str(private / "database"),
                "SECRETKEY_STORAGE_TYPE": "local", "SECRETKEY_PATH": str(private / "secrets"),
                "STORAGE_TYPE": "local", "BLOB_STORAGE_PATH": str(private / "storage"),
                "LOG_PATH": str(private / "logs"), "LOG_LEVEL": "info", "TMPDIR": str(private / "tmp"),
                "DISABLE_FLOWISE_TELEMETRY": "true", "ENABLE_METRICS": "false",
                "CUSTOM_MCP_PROTOCOL": "sse", "CUSTOM_MCP_SECURITY_CHECK": "true",
                "CORS_ORIGINS": f"http://127.0.0.1:{args.port}"})
    process = None
    try:
        with (private / "server.log").open("w") as log:
            process = subprocess.Popen([args.node, str(runtime / "node_modules/flowise/bin/run"), "start"],
                                       cwd=runtime, env=env, stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            assert process.poll() is None, "Flowise exited before readiness; inspect private/server.log"
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/v1/ping", timeout=2) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(1)
        else:
            raise TimeoutError("Flowise did not become ready in 180 seconds")
        api = LocalAPI(args.port, private)
        api.login()
        for dataset in DATASETS:
            raw = (private / f"definitions/{dataset}.json").read_bytes()
            proof["runs"].append(api.execute(raw, dataset, dataset, public))
            proof["successful_workflow_count"] = len(proof["runs"])
            print(json.dumps({"dataset": dataset, "native_steps_finished": 2,
                              "rows": proof["runs"][-1]["page"]["returned_rows"]}), flush=True)
        candidate = private / "definitions/marketplace-candidate.json" if args.generated_candidate else args.candidate
        if candidate:
            proof["runs"].append(api.execute(candidate.read_bytes(), "money_markets", "marketplace-candidate", public))
            proof["successful_workflow_count"] = len(proof["runs"])
        proof["scope"]["full_saved_workflow_execution"] = True
        proof["status"] = "passed"
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        proof["task_created_service_stopped"] = process is not None and process.poll() is not None
        write_json(public / "native-proof.json", proof)


if __name__ == "__main__":
    main()
