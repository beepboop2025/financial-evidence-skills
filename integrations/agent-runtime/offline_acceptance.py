"""Exercise an installed runtime with synthetic data and denied network access.

Run using the Python interpreter of the candidate installation. This script
does not modify sys.path, so it can also test a wheel outside the checkout.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
from unittest.mock import patch

from financial_evidence.agents import EvidenceAgentClient
from financial_evidence.core import source_reported_metadata
from financial_evidence.service import EvidenceService
from financial_evidence.runtime.cli import write_new
from financial_evidence.runtime.contracts import Workflow, encode, presets
from financial_evidence.runtime.engine import Runtime, implementation, verify_bundle
from financial_evidence.runtime.store import Store


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def acceptance(output):
    output = Path(output)
    output.mkdir(mode=0o700)  # Fresh destination required; never replace evidence.
    now = [datetime(2026, 9, 28, 12, tzinfo=timezone.utc).timestamp()]
    calls = []
    document = {"schema": "seiche.global-money-markets.v1", "synthetic_fixture": True, "markets": [{
        "market_id": "DEMO-USD", "display_name": "Synthetic example; not a market observation",
        "benchmark": {"mnemonic": "SYNTHETIC", "value": 0, "unit": "%",
                      "availability": "AVAILABLE", "status": "FRESH", "asof": "2026-09-28",
                      "redistribution_status": "allowed"}}]}

    def fetcher(source, **_):
        calls.append(source.url)
        raw = encode(document)
        sha = "sha256:" + hashlib.sha256(raw).hexdigest()
        return {"product": source.product, "source_url": source.url,
                "retrieved_at": "2026-09-28T12:00:00Z", "ok": True,
                "financial_authority": "none", "carrier_state": "not_published",
                "document": document, "content_sha256": sha, "bytes": len(raw),
                "source_reported": source_reported_metadata(source, document, content_sha256=sha)}

    service = EvidenceService(ttl=0, fetcher=fetcher)
    try:
        client = EvidenceAgentClient(service)
        def executor(job):
            return client.query(**job.value["parameters"])

        store = Store(output/"state", traffic_class="synthetic")
        runtime = Runtime(store, executor=executor, clock=lambda: now[0])
        policy = presets()[0]
        policy["parameters"]["entity"] = "DEMO-USD"
        store.register(Workflow.parse(policy), now[0])
        first = runtime.run(policy["id"], "example:first")
        check(first["status"] == "complete", "synthetic result did not meet configured requirements")
        check(runtime.run(policy["id"], "example:first")["run_id"] == first["run_id"], "key was not stable")
        check(len(calls) == 1, "same key repeated a fetch")
        now[0] += 901
        second = runtime.run(policy["id"], "example:second")
        check(runtime.bundle(second["run_id"])["record"]["change"] == "unchanged", "change detection failed")
        store.acknowledge(first["run_id"], "useful", now[0])
        store.control(now[0], stopped=True)
        check(runtime.run(policy["id"], "example:stopped")["reason"] == "stopped", "stop did not gate admission")
        bundle = runtime.bundle(first["run_id"])
        check(bundle["record"]["workflow_sha256"] == Workflow.parse(policy).sha256, "policy binding changed")
        check(bundle["record"]["result"]["results"][0]["value"] == 0, "zero was lost")
        write_new(output/"receipt.json", bundle)
        verify_bundle(bundle)
        replay = runtime.replay(first["run_id"])
        check(replay["network_calls"] == 0 and len(calls) == 2, "replay fetched data")
        backup = store.backup(output/"backup.sqlite")
        restored = output/"restored"
        restored.mkdir(mode=0o700)
        shutil.copy2(output/"backup.sqlite", restored/"runtime.sqlite")
        def no_fetch(_):
            raise RuntimeError("restored idempotency failed")
        recovered = Runtime(Store(restored), executor=no_fetch, clock=lambda: now[0])
        check(recovered.run(policy["id"], "example:first")["run_id"] == first["run_id"], "restore lost the run")
        check(recovered.bundle(first["run_id"]) == bundle, "restored receipt changed")
        events = store.events(limit=2)
        next_page = store.events(after=events["next_cursor"])
        check(all(e["id"] > events["next_cursor"] for e in next_page["events"]), "cursor replay failed")
        metrics = store.report()
        check(metrics["external_active_users"] is None and metrics["paid_customers"] is None,
              "synthetic activity was promoted to traction")
        report = {"schema": "financial-evidence.runtime-acceptance.v1", "status": "PASS",
                  "implementation": implementation(), "traffic_class": "synthetic",
                  "network_calls": 0, "synthetic_source_reads": len(calls), "run_id": first["run_id"],
                  "receipt_sha256": bundle["sha256"], "backup": backup,
                  "checks": ["existing_projection", "zero_preserved", "immutable_policy", "same_key_once",
                             "change_detection", "stop", "offline_replay", "portable_integrity",
                             "cursor_resume", "backup_restore", "unknown_customer_counts"],
                  "metrics": metrics, "live_source_verification": False,
                  "execution_authority": False, "external_adoption_verified": False}
        write_new(output/"report.json", report)
        return report
    finally:
        service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="New private evidence directory")
    args = parser.parse_args()
    with patch("socket.create_connection", side_effect=RuntimeError("network denied")), \
         patch("urllib.request.OpenerDirector.open", side_effect=RuntimeError("network denied")):
        print(encode(acceptance(args.output)).decode())
