"""Offline acceptance against a declared, pinned Carrier paper-host checkout.

This imports Carrier's real ASGI service through its synthetic integration rig.
There are no broker credentials, real submissions, network calls or fill claims.
Run with the Carrier trading-copilot locked test environment plus this package.
"""

import argparse
import asyncio
from datetime import timedelta
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

from financial_evidence.agents import EvidenceAgentClient
from financial_evidence.core import source_reported_metadata
from financial_evidence.runtime.cli import write_new
from financial_evidence.runtime.contracts import Workflow, encode, presets
from financial_evidence.runtime.engine import Runtime, implementation, verify_bundle
from financial_evidence.runtime.store import Store
from financial_evidence.service import EvidenceService

CARRIER_COMMIT = "328832ee996734ec2a2d5f27ad458e528d7f33ef"


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_fixture(root):
    root = Path(root).resolve(strict=True)
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    check(head == CARRIER_COMMIT, "Carrier checkout does not match declared pin")
    subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--"], check=True)
    # This is an explicit test dependency, never a production sibling import.
    sys.path.insert(0, str(root / "integrations/trading-copilot/tests"))
    import test_agent_host
    return test_agent_host


async def acceptance(output, fixture):
    output = Path(output)
    output.mkdir(mode=0o700)  # Do not replace prior evidence.
    clock = fixture.NOW
    observed = [clock.date().isoformat()]
    source_calls = []

    def fetcher(source, **_):
        source_calls.append(source.url)
        document = {"schema": "seiche.global-money-markets.v1", "synthetic_fixture": True,
                    "markets": [{"market_id": "DEMO-USD", "display_name": "Synthetic research fixture",
                                 "benchmark": {"mnemonic": "SYNTHETIC", "value": 0, "unit": "%",
                                               "availability": "AVAILABLE", "status": "FRESH",
                                               "asof": observed[0], "redistribution_status": "allowed"}}]}
        raw = encode(document)
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        return {"product": source.product, "source_url": source.url,
                "retrieved_at": clock.isoformat(), "ok": True, "financial_authority": "none",
                "carrier_state": "not_published", "document": document,
                "content_sha256": digest, "bytes": len(raw),
                "source_reported": source_reported_metadata(source, document, content_sha256=digest)}

    service = EvidenceService(ttl=0, fetcher=fetcher)
    try:
        client = EvidenceAgentClient(service)
        store = Store(output / "research", traffic_class="synthetic")
        runtime = Runtime(store, executor=lambda job: client.query(**job.value["parameters"]),
                          clock=lambda: clock.timestamp())
        spec = presets()[0]
        spec["parameters"]["entity"] = "DEMO-USD"
        store.register(Workflow.parse(spec), clock.timestamp())
        run = runtime.run(spec["id"], "paper-host:research")
        check(run["status"] == "complete", "research fixture did not complete")
        bundle = runtime.bundle(run["run_id"])
        check(bundle["record"]["assessment"]["status"] == "requirements_met", "research checks failed")
        check(verify_bundle(bundle)["execution_authority"] is False, "research gained execution authority")
        write_new(output / "research-receipt.json", bundle)
        intent = "research-" + run["run_id"]
        proposal = {"intent_id": intent, "side": "sell", "notional_usd": 1000}
        # Link locally; the host accepts an intent, not caller-issued evidence.
        write_new(output / "intent-link.json", {"schema": "financial-evidence.research-intent-link.v1",
                  "research_sha256": bundle["sha256"], "proposal": proposal,
                  "carrier_commit": CARRIER_COMMIT, "execution_authority": False})
        async with fixture.rig(output / "paper-host", enabled=False) as host:
            response = await host.client.post("/v1/assessments", json=proposal)
            check(response.status_code == 200, "host assessment failed")
            assessment = response.json()
            check(assessment["submission_authorized"] is False, "assessment authorized a submission")
            check(set(assessment["evidence"]) == {"seiche", "undertow", "liquilens"},
                  "host did not acquire its own three-product evidence")
            reads = len(host.source_calls)
            check(reads > 0, "host skipped independent evidence acquisition")
            repeated = await host.client.post("/v1/assessments", json=proposal)
            check(repeated.json()["assessment_id"] == assessment["assessment_id"], "intent not stable")
            check(len(host.source_calls) == reads, "duplicate intent repeated source acquisition")
            forged = await host.client.post("/v1/assessments", json={**proposal, "research_bundle": bundle})
            check(forged.status_code == 422, "host admitted caller research as authority")
            read_only = await host.client.post("/v1/orders/submit",
                headers={"Authorization": "Bearer " + fixture.READ_TOKEN},
                json={"assessment_id": assessment["assessment_id"]})
            check(read_only.status_code == 403, "research token could submit")
            disabled = await host.client.post("/v1/orders/submit",
                json={"assessment_id": assessment["assessment_id"]})
            check(disabled.status_code == 409 and not host.sdk.orders, "operator stop did not prevent submission")
            check(not host.account_calls, "disabled submission reached the account provider")
        async with fixture.rig(output / "paper-host", enabled=False) as restarted:
            same = await restarted.client.post("/v1/assessments", json=proposal)
            check(same.json()["assessment_id"] == assessment["assessment_id"], "restart lost intent binding")
            check(not restarted.source_calls and not restarted.sdk.orders, "restart replayed work")
        observed[0] = (clock - timedelta(days=8)).date().isoformat()
        spec["id"] = "stale-research"
        store.register(Workflow.parse(spec), clock.timestamp())
        blocked = runtime.run(spec["id"], "paper-host:stale")
        check(blocked["assessment"]["status"] == "blocked", "stale research was promoted")
        check("observation_too_old" in blocked["assessment"]["reasons"], "source clock ignored")
        write_new(output / "blocked-receipt.json", runtime.bundle(blocked["run_id"]))
        backup = store.backup(output / "research-backup.sqlite")
        restored_root = output / "restored-research"
        restored_root.mkdir(mode=0o700)
        shutil.copy2(output / "research-backup.sqlite", restored_root / "runtime.sqlite")
        def no_fetch(_):
            raise RuntimeError("restored intent unexpectedly fetched evidence")
        restored = Runtime(Store(restored_root), executor=no_fetch, clock=lambda: clock.timestamp())
        check(restored.run("funding-watch", "paper-host:research")["run_id"] == run["run_id"],
              "restoration lost research idempotency")
        check(restored.replay(run["run_id"])["bundle"] == bundle, "restore changed research receipt")
        check(len(source_calls) == 2, "unexpected research acquisition count")
        report = {"schema": "financial-evidence.runtime-paper-host-acceptance.v1", "status": "PASS",
                  "implementation": implementation(), "carrier_commit": CARRIER_COMMIT,
                  "traffic_class": "synthetic", "network_calls": 0, "broker_orders": 0,
                  "live_paper_fills_verified": False, "execution_authority": False,
                  "external_adoption_verified": False, "backup": backup,
                  "research_sha256": bundle["sha256"], "assessment_id": assessment["assessment_id"],
                  "checks": ["research_integrity", "independent_host_assessment", "stable_intent",
                             "caller_evidence_rejected", "read_scope_cannot_submit", "operator_stop",
                             "restart_no_replay", "stale_research_blocked", "research_backup_restore"]}
        write_new(output / "report.json", report)
        return report
    finally:
        service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    fixture = load_fixture(args.carrier_root)
    with patch("socket.create_connection", side_effect=RuntimeError("network denied")), \
         patch("socket.socket.connect", side_effect=RuntimeError("network denied")), \
         patch("urllib.request.OpenerDirector.open", side_effect=RuntimeError("network denied")):
        print(encode(asyncio.run(acceptance(args.output, fixture))).decode())
