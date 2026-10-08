"""Failure-oriented tests for durable financial research infrastructure."""

import copy
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from datetime import timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from test_openbb_tables import MONEY, source_result
from financial_evidence.agents import EvidenceAgentClient
from financial_evidence.service import EvidenceService
from financial_evidence.runtime.assessment import assess
from financial_evidence.runtime.catalog import manifest
from financial_evidence.runtime.contracts import Workflow, decode, digest, encode, presets
from financial_evidence.runtime.engine import Runtime, execute, verify_bundle
from financial_evidence.runtime.store import Store

NOW = datetime(2026, 9, 28, 12, tzinfo=timezone.utc).timestamp()


def workflow(**changes):
    value = presets()[0]
    value["parameters"]["entity"] = "US-USD"
    value["requirements"]["max_observation_age_seconds"] = 604800
    value["interval_seconds"] = 60
    value["daily_run_limit"] = 20
    value.update(changes)
    return Workflow.parse(value)


def result(document=None, *, ok=True):
    service = EvidenceService(ttl=0, fetcher=lambda source, **_: source_result(source, document, ok))
    try:
        return EvidenceAgentClient(service).query("money_markets", entity="US-USD", limit=25)
    finally:
        service.close()


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "state"
        self.store = Store(self.root, traffic_class="synthetic")
        self.clock = NOW
        self.calls = []
        self.output = result()

        def executor(job):
            self.calls.append(job.id)
            return copy.deepcopy(self.output)

        self.runtime = Runtime(self.store, executor=executor, clock=lambda: self.clock)
        self.job = workflow()
        self.store.register(self.job, self.clock)

    def run_once(self, key="one"):
        return self.runtime.run(self.job.id, key)

    def test_real_projection_zero_preserved_and_replay_keeps_original_clock(self):
        run = self.run_once()
        self.assertEqual(run["status"], "complete")
        self.clock += 86400
        replay = self.runtime.replay(run["run_id"])
        record = replay["bundle"]["record"]
        self.assertEqual(record["result"]["results"][0]["value"], 0)
        self.assertEqual(record["result"]["results"][0]["as_of"], "2026-09-24")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(replay["network_calls"], 0)
        self.assertFalse(replay["verification"]["execution_authority"])

    def test_same_key_survives_process_restart_without_second_fetch(self):
        original = self.run_once()
        self.clock += 600
        restarted = Runtime(Store(self.root), executor=lambda _: self.fail("duplicate fetch"), clock=lambda: self.clock)
        repeated = restarted.run(self.job.id, "one")
        self.assertEqual(repeated["run_id"], original["run_id"])
        self.assertEqual(repeated["reason"], "existing_run")

    def test_concurrent_process_connections_admit_only_one_fetch(self):
        entered, release = threading.Event(), threading.Event()

        def blocked(_):
            entered.set()
            self.assertTrue(release.wait(3))
            return self.output

        first = Runtime(Store(self.root), executor=blocked, clock=lambda: self.clock)
        second = Runtime(Store(self.root), executor=lambda _: self.fail("overlap"), clock=lambda: self.clock)
        with ThreadPoolExecutor(2) as pool:
            future = pool.submit(first.run, self.job.id, "a")
            self.assertTrue(entered.wait(3))
            try:
                self.assertEqual(second.run(self.job.id, "b")["reason"], "in_flight")
                self.assertEqual(second.run(self.job.id, "a")["reason"], "existing_run")
            finally:
                release.set()
            self.assertEqual(future.result()["status"], "complete")

    def test_changed_policy_requires_new_id_and_invalid_config_never_fetches(self):
        self.assertFalse(self.store.register(self.job, self.clock)["created"])
        altered = workflow(daily_run_limit=10)
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.store.register(altered, self.clock)
        for change in ({"operation": "submit_order"}, {"interval_seconds": True}, {"daily_run_limit": 0},
                       {"id": "../../broker"}, {"parameters": {"dataset": "money_markets", "url": "http://localhost"}},
                       {"parameters": {"dataset": "money_markets", "limit": 101}},
                       {"parameters": {"dataset": "money_markets", "entity": None}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                workflow(**change)
        self.assertFalse(self.calls)

    def test_cooldown_budget_and_stop_are_enforced_before_fetch(self):
        job = workflow(id="limited", daily_run_limit=1)
        self.store.register(job, self.clock)
        self.assertTrue(self.runtime.run("limited", "one")["admitted"])
        self.assertEqual(self.runtime.run("limited", "two")["reason"], "cooldown")
        self.clock += 61
        self.assertEqual(self.runtime.run("limited", "two")["reason"], "workflow_daily_limit")
        self.store.control(self.clock, stopped=True)
        self.assertEqual(self.run_once()["reason"], "stopped")
        self.store.control(self.clock, stopped=False)
        self.store.control(self.clock, job=self.job.id, enabled=False)
        self.assertEqual(self.run_once()["reason"], "paused")
        self.assertEqual(len(self.calls), 1)

    def test_installation_budget_counts_failed_and_successful_attempts(self):
        store = Store(Path(self.temp.name)/"small", limits={"daily_runs": 1})
        store.register(self.job, self.clock)
        other = workflow(id="other")
        store.register(other, self.clock)
        runtime = Runtime(store, executor=lambda _: self.output, clock=lambda: self.clock)
        runtime.run(self.job.id, "one")
        self.assertEqual(runtime.run("other", "two")["reason"], "installation_daily_limit")

    def test_expired_claim_is_interrupted_and_late_writer_cannot_commit(self):
        claim = self.store.claim(self.job.id, "lost", self.clock)
        self.clock += 121
        same = self.runtime.run(self.job.id, "lost")
        self.assertEqual(same["status"], "interrupted")
        with self.assertRaisesRegex(ValueError, "claim"):
            self.store.finish(claim["run_id"], self.clock, None, "late")
        self.assertTrue(self.runtime.run(self.job.id, "new")["admitted"])

    def test_clock_rollback_prevents_new_network_work(self):
        self.clock -= 6
        with self.assertRaisesRegex(ValueError, "backwards"):
            self.run_once()
        self.assertFalse(self.calls)

    def test_transport_failure_opens_circuit_then_one_probe_can_recover(self):
        self.output = result(ok=False)
        for index in range(4):
            self.assertEqual(self.run_once(str(index))["status"], "blocked")
            self.clock += 61
        self.assertEqual(self.run_once("blocked")["reason"], "circuit_open")
        self.clock += 61
        self.output = result()
        self.assertEqual(self.run_once("recover")["status"], "complete")
        self.assertEqual(self.store.jobs()[0]["failures"], 0)

    def test_null_rights_stale_future_and_missing_clocks_remain_blocked(self):
        cases = [({"value": None}, "numeric_value_missing"), ({"rights_status": None}, "rights_not_established"),
                 ({"unit": None}, "unit_missing"), ({"as_of": "2020-01-01"}, "observation_too_old"),
                 ({"as_of": "2030-01-01"}, "observation_in_future"), ({"as_of": None}, "observation_clock_unknown"),
                 ({"as_of": "2026-09-28T10:00:00"}, "observation_clock_unknown"),
                 ({"source_url": "https://attacker.invalid"}, "missing_provenance")]
        for change, reason in cases:
            sample = copy.deepcopy(self.output)
            sample["results"][0].update(change)
            with self.subTest(change=change):
                checked = assess(sample, self.job, self.clock)
                self.assertEqual(checked["status"], "blocked")
                self.assertIn(reason, checked["reasons"])

    def test_empty_paginated_and_partial_sections_are_not_complete(self):
        for change, reason in [({"results": []}, "no_matching_rows"), ({"next_offset": 25}, "page_incomplete"),
                               ({"transport_status": "partial"}, "transport_incomplete")]:
            sample = {**self.output, **change}
            self.assertIn(reason, assess(sample, self.job, self.clock)["reasons"])

    def test_authority_and_nonfinite_output_cannot_enter_journal_as_success(self):
        for change in ({"financial_authority": "trade"}, {"evidence_status": "verified"},
                       {"change_status": "unchanged"}, {"revision": "invalid"}):
            self.output = {**result(), **change}
            self.assertEqual(self.run_once(str(len(self.calls)))["status"], "error")
            self.clock += 4000

    def test_hash_tamper_detected_in_journal_and_portable_bundle(self):
        run = self.run_once()
        bundle = self.runtime.bundle(run["run_id"])
        bundle["record"]["result"]["results"][0]["value"] = 999
        with self.assertRaisesRegex(ValueError, "integrity"):
            verify_bundle(bundle)
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("UPDATE runs SET bundle=? WHERE id=?", (b"{}", run["run_id"]))
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.runtime.replay(run["run_id"])

    def test_rehashed_bundle_cannot_claim_verified_or_execution_authority(self):
        run = self.run_once()
        bundle = self.runtime.bundle(run["run_id"])
        bundle["record"]["authority"]["execution"] = True
        bundle["sha256"] = digest(bundle["record"])
        with self.assertRaisesRegex(ValueError, "authority"):
            verify_bundle(bundle)

    def test_unchanged_full_result_retained_and_ordered_cursor_is_resumable(self):
        first = self.run_once()
        self.clock += 61
        second = self.run_once("two")
        capture = self.runtime.bundle(second["run_id"])["record"]
        self.assertEqual(capture["change"], "unchanged")
        self.assertEqual(len(capture["result"]["results"]), 1)
        first_page = self.store.events(0, 2)
        self.assertTrue(first_page["has_more"])
        second_page = self.store.events(first_page["next_cursor"], 100)
        self.assertTrue(all(event["id"] > first_page["next_cursor"] for event in second_page["events"]))
        self.assertFalse(second_page["has_more"])
        self.assertEqual(second_page, self.store.events(first_page["next_cursor"], 100))

    def test_unchanged_revision_can_become_stale_without_becoming_fresh(self):
        self.assertEqual(self.run_once()["status"], "complete")
        self.clock += 8 * 86400
        later = self.run_once("later")
        self.assertEqual(later["status"], "blocked")
        record = self.runtime.bundle(later["run_id"])["record"]
        self.assertEqual(record["change"], "unchanged")
        self.assertIn("observation_too_old", record["assessment"]["reasons"])
        self.assertEqual(self.store.jobs()[0]["failures"], 0)

    def test_three_product_review_retains_separate_sections_and_missingness(self):
        job = workflow(id="combined-review", operation="review", parameters={"bank": "missing", "limit": 2})
        self.store.register(job, self.clock)
        service = EvidenceService(ttl=0, fetcher=lambda source, **_: source_result(source))
        try:
            runtime = Runtime(self.store, executor=lambda _: EvidenceAgentClient(service).review(bank="missing", limit=2),
                              clock=lambda: self.clock)
            run = runtime.run(job.id, "review")
            self.assertEqual(run["status"], "blocked")
            record = runtime.bundle(run["run_id"])["record"]
            self.assertEqual([s["dataset"] for s in record["result"]["sections"]],
                             ["money_markets", "bank_risk", "market_liquidity"])
            self.assertIn("no_matching_rows", record["assessment"]["reasons"])
            self.assertFalse(record["assessment"]["execution_authority"])
        finally:
            service.close()

    def test_own_usage_and_acknowledgements_never_become_external_customers(self):
        run = self.run_once()
        self.store.acknowledge(run["run_id"], "useful", self.clock)
        self.store.acknowledge(run["run_id"], "useful", self.clock)
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.store.acknowledge(run["run_id"], "not_useful", self.clock)
        report = self.store.report()
        self.assertEqual(report["operator_reported_outcomes"], {"useful": 1})
        for field in ("external_active_users", "returning_external_users", "paid_customers", "revenue"):
            self.assertIsNone(report[field])
        self.assertFalse(report["coverage_complete"])
        with self.assertRaises(ValueError):
            Store(Path(self.temp.name)/"invalid", traffic_class="external_verified")

    def test_online_backup_restores_idempotency_and_receipt_integrity(self):
        run = self.run_once()
        recovered = Path(self.temp.name)/"restore"
        recovered.mkdir(mode=0o700)
        receipt = self.store.backup(recovered/"runtime.sqlite")
        restored = Runtime(Store(recovered), executor=lambda _: self.fail("replayed network"), clock=lambda: self.clock)
        self.assertEqual(restored.run(self.job.id, "one")["run_id"], run["run_id"])
        self.assertTrue(restored.replay(run["run_id"])["verification"]["valid"])
        self.assertEqual(len(receipt["sha256"]), 64)
        with self.assertRaises(FileExistsError):
            self.store.backup(recovered/"runtime.sqlite")

    def test_symlinks_hardlinks_and_public_state_rejected(self):
        linked = Path(self.temp.name)/"linked"
        linked.symlink_to(self.root)
        with self.assertRaises(ValueError):
            Store(linked)
        os.chmod(self.root, 0o755)
        with self.assertRaises(ValueError):
            Store(self.root)
        os.chmod(self.root, 0o700)
        os.link(self.store.path, Path(self.temp.name)/"hardlink")
        with self.assertRaises(ValueError):
            self.store.report()

    def test_storage_and_job_allowances_fail_explicitly(self):
        store = Store(Path(self.temp.name)/"tiny", limits={"receipt_bytes": 1, "jobs": 1, "runs": 1})
        store.register(self.job, self.clock)
        with self.assertRaises(OverflowError):
            store.register(workflow(id="extra"), self.clock)
        runtime = Runtime(store, executor=lambda _: self.output, clock=lambda: self.clock)
        run = runtime.run(self.job.id, "one")
        self.assertEqual(run["error"], "receipt_storage_full")
        self.clock += 61
        self.assertEqual(runtime.run(self.job.id, "two")["reason"], "journal_full")

    def test_deadline_becomes_durable_failure_and_is_not_retried(self):
        self.runtime.executor = lambda _: (_ for _ in ()).throw(subprocess.TimeoutExpired("worker", 45))
        run = self.run_once()
        self.assertEqual(run["error"], "research_deadline_exceeded")
        self.assertEqual(self.run_once()["run_id"], run["run_id"])

    def test_tick_bounds_work_and_skips_disabled_jobs(self):
        self.store.register(workflow(id="other"), self.clock)
        tick = self.runtime.tick(limit=1)
        self.assertEqual(len(tick["runs"]), 1)
        self.assertTrue(tick["more_due"])
        self.assertEqual(len(self.runtime.tick()["runs"]), 1)
        self.assertEqual(self.runtime.tick()["runs"], [])

    def test_exhausted_workflow_does_not_starve_later_due_work(self):
        self.store.register(workflow(id="a-limited", daily_run_limit=1), self.clock)
        self.runtime.run("a-limited", "used")
        self.clock += 61
        self.run_once()
        self.clock += 61
        tick = self.runtime.tick(limit=1)
        self.assertEqual(tick["runs"][0]["reason"], "workflow_daily_limit")
        self.assertEqual(tick["admitted_count"], 1)
        self.assertEqual(tick["runs"][1]["job"], self.job.id)

    def test_small_concurrent_clock_skew_clamps_and_does_not_reopen_budget(self):
        self.run_once()
        self.clock -= 1
        self.assertEqual(self.run_once("two")["reason"], "cooldown")
        self.assertEqual(len(self.calls), 1)
        self.store.register(workflow(id="later"), self.clock)
        other = self.runtime.run("later", "one")
        self.assertEqual(self.runtime.bundle(other["run_id"])["record"]["started_at"],
                         datetime.fromtimestamp(NOW, timezone.utc).isoformat())

    def test_rehashed_malformed_metadata_is_rejected(self):
        run = self.run_once()
        original = self.runtime.bundle(run["run_id"])
        for changes in ({"started_at": None}, {"run_id": "bad"}, {"traffic_class": "external_verified"},
                        {"implementation": {}}, {"change": "trade_approved"}):
            value = copy.deepcopy(original)
            value["record"].update(changes)
            value["sha256"] = digest(value["record"])
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                verify_bundle(value)

    def test_result_cannot_exceed_owner_registered_row_limit(self):
        self.output["results"] *= 26
        with self.assertRaisesRegex(ValueError, "row allowance"):
            assess(self.output, self.job, self.clock)

    def test_json_rejects_duplicates_overflow_and_payload_limits(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'"\xff"'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode(raw)
        with self.assertRaises(ValueError):
            decode(b"{}", limit=1)

    def test_default_executor_has_a_process_deadline_and_fixed_command(self):
        with patch("financial_evidence.runtime.engine.subprocess.run") as process:
            process.return_value = subprocess.CompletedProcess([], 0, encode(self.output), b"")
            execute(self.job, traffic_class="synthetic")
            args, kwargs = process.call_args
            self.assertEqual(kwargs["timeout"], 45)
            self.assertNotIn("shell", kwargs)
            self.assertEqual(args[0][-2:], ["--traffic-class", "synthetic"])

    def test_catalog_and_cli_are_offline_and_worker_rejects_execution(self):
        self.assertFalse(manifest()["execution_authority"])
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]/"src")}
        command = subprocess.run([sys.executable, "-m", "financial_evidence.runtime.cli", "catalog"],
                                 capture_output=True, env=env, timeout=10)
        self.assertEqual(command.returncode, 0, command.stderr)
        self.assertEqual(decode(command.stdout)["authority"], "research_only")
        worker = subprocess.run([sys.executable, "-m", "financial_evidence.runtime.worker"],
                                input=b'{"operation":"submit_order"}', capture_output=True, env=env, timeout=10)
        self.assertEqual(worker.returncode, 1)
        self.assertEqual(worker.stderr, b"research_worker_failed\n")


@unittest.skipUnless(importlib.util.find_spec("mcp"), "optional MCP SDK not installed")
class RuntimeMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_child_discovers_and_replays_without_fetching(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"state"
            runtime = Runtime(Store(root, traffic_class="synthetic"), executor=lambda _: result(), clock=lambda: NOW)
            runtime.store.register(workflow(), NOW)
            captured = runtime.run("funding-watch", "agent:captured")
            params = StdioServerParameters(command=sys.executable,
                args=["-m", "financial_evidence.runtime.mcp", "--root", str(root)],
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]/"src")})
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=15)) as session:
                    await session.initialize()
                    self.assertEqual(len((await session.list_tools()).tools), 6)
                    replay = await session.call_tool("financial_runtime_replay", {"run_id": captured["run_id"]})
                    self.assertFalse(replay.isError)
                    self.assertEqual(replay.structuredContent["network_calls"], 0)
                    self.assertEqual(replay.structuredContent["bundle"]["record"]["traffic_class"], "synthetic")
                    repeated = await session.call_tool("financial_runtime_run", {"job": "funding-watch", "key": "captured"})
                    self.assertEqual(repeated.structuredContent["reason"], "existing_run")
                    self.assertEqual(repeated.structuredContent["run_id"], captured["run_id"])
                    for name in ("financial_runtime_catalog", "financial_runtime_jobs", "financial_runtime_events", "financial_runtime_metrics"):
                        self.assertFalse((await session.call_tool(name, {})).isError)

    async def test_real_sdk_tools_and_offline_calls(self):
        from financial_evidence.runtime.mcp import create_mcp
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Store(Path(tmp)/"state"), executor=lambda _: result(), clock=lambda: NOW)
            runtime.store.register(workflow(), NOW)
            server = create_mcp(runtime)
            tools = await server.list_tools()
            self.assertEqual(len(tools), 6)
            self.assertTrue(all(tool.outputSchema and tool.outputSchema.get("type") == "object" for tool in tools))
            run = next(tool for tool in tools if tool.name == "financial_runtime_run")
            self.assertFalse(run.annotations.readOnlyHint)
            self.assertTrue(run.annotations.idempotentHint)
            self.assertEqual(set(run.inputSchema["required"]), {"job", "key"})
            reply = await server.call_tool("financial_runtime_run", {"job": "funding-watch", "key": "one"})
            self.assertIn("complete", str(reply))
            again = await server.call_tool("financial_runtime_run", {"job": "funding-watch", "key": "one"})
            self.assertIn("existing_run", str(again))
            for name in ("financial_runtime_catalog", "financial_runtime_jobs", "financial_runtime_events", "financial_runtime_metrics"):
                self.assertTrue(await server.call_tool(name, {}))


if __name__ == "__main__":
    unittest.main()
