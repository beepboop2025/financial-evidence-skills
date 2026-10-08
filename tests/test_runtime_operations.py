"""Failure-oriented acceptance of the separately deployed operations component."""

import copy
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import http.client
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/agent-runtime/operations"))
sys.path.insert(0, str(ROOT / "src"))

from test_runtime import NOW, result, workflow
from financial_evidence.runtime.engine import Runtime, implementation
from financial_evidence.runtime.store import Store
from ops_common import atomic, config, inspect_journal, regular, sha
from ops_backup import backup, recover
from ops_recovery import candidates, recover_snapshot
from ops_diagnostics import diagnose
from ops_monitor import UNITS, assess, monitor, transitions
from ops import handler
from install import activate, render


class FakeRestic:
    def __init__(self):
        self.repository_id = "a" * 64
        self.snapshots = {}
        self.calls = []
        self.fail_upload_before = False
        self.fail_upload_after = False
        self.corrupt_restore = False

    def __call__(self, *args):
        self.calls.append(args)
        if args[:2] == ("cat", "config"):
            return json.dumps({"id": self.repository_id}).encode()
        if args[0] == "backup":
            if self.fail_upload_before:
                raise RuntimeError("provider may have a credential in its error")
            path = Path(args[-1])
            identifier = hashlib.sha256(str(len(self.snapshots)).encode()).hexdigest()
            self.snapshots[identifier] = {"id": identifier, "paths": [str(path)],
                                          "hostname": "financial-evidence-runtime", "time": "2026-10-08T09:00:00Z",
                                          "tags": [args[n + 1] for n, a in enumerate(args) if a == "--tag"],
                                          "files": {p.name: p.read_bytes() for p in path.iterdir()}}
            if self.fail_upload_after:
                raise RuntimeError("accepted before connection dropped")
            return json.dumps({"message_type": "summary", "snapshot_id": identifier}).encode()
        if args[0] == "snapshots":
            return json.dumps([{k: v for k, v in row.items() if k != "files"} for row in self.snapshots.values()
                               if row["id"] == args[-1] or args[-1] in row["tags"]]).encode()
        if args[0] == "dump":
            return self.snapshots[args[1]]["files"][Path(args[2]).name]
        if args[0] == "restore":
            row = self.snapshots[args[1]]
            destination = Path(args[-1]) / Path(row["paths"][0]).relative_to("/")
            destination.mkdir(parents=True)
            for name, data in row["files"].items():
                target = destination / name
                target.write_bytes(data + (b"tampered" if name == "runtime.sqlite" and self.corrupt_restore else b""))
                target.chmod(0o600)
            return b'{}'
        raise AssertionError(args)


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.state = self.base / "operations"
        self.state.mkdir(mode=0o700)
        self.root = self.base / "research"
        self.store = Store(self.root, traffic_class="synthetic")
        self.workflow = workflow()
        self.store.register(self.workflow, NOW)
        self.runtime = Runtime(self.store, executor=lambda _: result(), clock=lambda: NOW)
        self.run = self.runtime.run(self.workflow.id, "permanent-key")
        self.cfg = {"schema": "financial-evidence.runtime-ops.v1", "root": str(self.root), "state": str(self.state),
                    "installation_id": self.store.report()["installation_id"], "package_version": "0.1.7",
                    "implementation_sha256": implementation()["sha256"], "repository_id": "a" * 64,
                    "jobs": {self.workflow.id: self.workflow.sha256}, "due_grace_seconds": 180,
                    "backup_max_age_seconds": 3600, "monitor_max_age_seconds": 180, "min_free_bytes": 1048576}
        self.restic = FakeRestic()
        # Unit tests may run before installation in the stdlib source matrix.
        # The separate real-Restic consumer installs and verifies the package.
        metadata = patch("ops_common.importlib.metadata.version", return_value="0.1.7")
        metadata.start()
        self.addCleanup(metadata.stop)
        self.units = {name: {"Id": name, "ActiveState": "active" if name.endswith(".timer") or "dashboard" in name else "inactive",
                             "Result": "success", "ExecMainStatus": "0"} for name in UNITS}
        self.units["financial-evidence-runtime.timer"]["LastTriggerUSec"] = datetime.fromtimestamp(NOW, timezone.utc).strftime("%a %Y-%m-%d %H:%M:%S UTC")

    def report(self, *, now=NOW, **changes):
        values = {"journal": inspect_journal(self.root / "runtime.sqlite"), "service_units": self.units,
                  "backup": {"status": "verified", "last_verified": {"verified_at": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                  "installation_id": self.cfg["installation_id"], "repository_id": self.cfg["repository_id"]}},
                  "free_bytes": 10737418240, "now": now}
        values.update(changes)
        return assess(self.cfg, **values)

    def test_config_rejects_unknown_fields_relative_paths_and_missing_identity(self):
        path = self.base / "config.json"
        for changes in ({"root": "relative"}, {"repository_id": "latest"}, {"jobs": {}}, {"unsupported": True}, {"due_grace_seconds": True}):
            atomic(path, {**self.cfg, **changes})
            with self.assertRaises((ValueError, TypeError)):
                config(path)
        atomic(path, self.cfg)
        self.assertEqual(config(path), self.cfg)

    def test_observer_is_readonly_and_does_not_initialize_missing_state(self):
        path = self.root / "runtime.sqlite"
        before = sha(path.read_bytes())
        value = inspect_journal(path, full=True)
        self.assertEqual(value["verified_receipts"], 1)
        self.assertEqual(sha(path.read_bytes()), before)
        missing = self.base / "missing/runtime.sqlite"
        with self.assertRaises(OSError):
            inspect_journal(missing)
        self.assertFalse(missing.parent.exists())

    def test_journal_binding_tamper_is_rejected(self):
        with closing(sqlite3.connect(self.root / "runtime.sqlite")) as db:
            db.execute("UPDATE runs SET status='blocked'")
            db.commit()
        with self.assertRaisesRegex(ValueError, "binding"):
            inspect_journal(self.root / "runtime.sqlite", full=True)

    def test_private_journal_and_symlink_checks(self):
        path = self.root / "runtime.sqlite"
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            inspect_journal(path)
        path.chmod(0o600)
        link = self.base / "link"
        link.symlink_to(path)
        with self.assertRaises((OSError, ValueError)):
            inspect_journal(link)

    def test_exact_offsite_restore_retains_keys_and_does_not_touch_source(self):
        before = sha((self.root / "runtime.sqlite").read_bytes())
        receipt = backup(self.cfg, restic=self.restic)
        self.assertEqual(receipt["status"], "verified")
        self.assertEqual(receipt["verified_receipts"], 1)
        self.assertEqual(sha((self.root / "runtime.sqlite").read_bytes()), before)
        self.assertFalse((self.state / "active-backup.json").exists())
        self.assertEqual(list((self.state / "pending").iterdir()), [])
        self.assertFalse(receipt["source_writes"])
        self.assertFalse(any(call[0] in {"init", "forget", "prune", "unlock"} for call in self.restic.calls))

    def test_accepted_upload_with_lost_ack_is_reconciled_without_repeating_upload(self):
        self.restic.fail_upload_after = True
        with self.assertRaises(RuntimeError):
            backup(self.cfg, restic=self.restic)
        self.restic.fail_upload_after = False
        receipt = backup(self.cfg, restic=self.restic)
        self.assertEqual(receipt["status"], "verified")
        self.assertEqual(sum(c[0] == "backup" for c in self.restic.calls), 1)
        self.assertTrue(any(c[0] == "snapshots" for c in self.restic.calls))

    def test_unaccepted_uncertain_upload_is_not_automatically_repeated(self):
        self.restic.fail_upload_before = True
        with self.assertRaises(RuntimeError):
            backup(self.cfg, restic=self.restic)
        self.restic.fail_upload_before = False
        with self.assertRaisesRegex(ValueError, "uncertain"):
            backup(self.cfg, restic=self.restic)
        self.assertEqual(sum(c[0] == "backup" for c in self.restic.calls), 1)
        self.assertTrue((self.state / "active-backup.json").exists())

    def test_corrupt_restoration_never_becomes_success_and_retry_only_restores(self):
        self.restic.corrupt_restore = True
        with self.assertRaisesRegex(ValueError, "checksum"):
            backup(self.cfg, restic=self.restic)
        self.assertEqual(json.loads((self.state / "backup.json").read_text())["status"], "failed")
        self.restic.corrupt_restore = False
        self.assertEqual(backup(self.cfg, restic=self.restic)["status"], "verified")
        self.assertEqual(sum(c[0] == "backup" for c in self.restic.calls), 1)

    def test_wrong_repository_refuses_before_upload(self):
        self.restic.repository_id = "b" * 64
        with self.assertRaises(ValueError):
            backup(self.cfg, restic=self.restic)
        self.assertFalse(any(c[0] == "backup" for c in self.restic.calls))

    def test_cleanup_crash_reuses_verified_receipt_without_new_upload(self):
        real_remove = shutil.rmtree
        called = []
        def fail_cleanup(path, *args, **kwargs):
            if Path(path).parent.name == "pending" and not called:
                called.append(True)
                raise OSError("cleanup interrupted")
            return real_remove(path, *args, **kwargs)
        with patch("ops_backup.shutil.rmtree", side_effect=fail_cleanup):
            with self.assertRaises(OSError):
                backup(self.cfg, restic=self.restic)
        receipt = backup(self.cfg, restic=self.restic)
        self.assertEqual(receipt["status"], "verified")
        self.assertEqual(sum(c[0] == "backup" for c in self.restic.calls), 1)
        self.assertFalse((self.state / "active-backup.json").exists())

    def test_concurrent_backup_lock_prevents_duplicate_work(self):
        import fcntl
        with (self.state / "backup.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                backup(self.cfg, restic=self.restic)
        self.assertEqual(self.restic.calls, [])

    def test_restore_is_new_stopped_and_same_key_never_fetches(self):
        receipt = backup(self.cfg, restic=self.restic)
        path = self.state / "receipts" / (receipt["operation_id"] + ".json")
        target = self.base / "recovered"
        report = recover(self.cfg, path, target, restic=self.restic)
        self.assertTrue(report["admission_stopped"])
        self.assertEqual(report["source_network_calls"], 0)
        restored = Runtime(Store(target), executor=lambda _: self.fail("recovery fetched source data"), clock=lambda: NOW + 300)
        repeated = restored.run(self.workflow.id, "permanent-key")
        self.assertEqual(repeated["run_id"], self.run["run_id"])
        self.assertEqual(restored.run(self.workflow.id, "new-key")["reason"], "stopped")
        with self.assertRaises(ValueError):
            recover(self.cfg, path, target, restic=self.restic)

    def test_changed_workflow_inventory_requires_operator_review(self):
        cfg = {**self.cfg, "jobs": {self.workflow.id: "c" * 64}}
        with self.assertRaises(ValueError):
            backup(cfg, restic=self.restic)
        self.assertFalse(any(c[0] == "backup" for c in self.restic.calls))

    def test_disaster_recovery_with_source_and_operations_directories_lost(self):
        receipt = backup(self.cfg, restic=self.restic)
        self.root.rename(self.base / "lost-research")
        self.state.rename(self.base / "lost-operations")
        self.restic.calls.clear()
        catalog = candidates(self.cfg, restic=self.restic)
        self.assertEqual(catalog["snapshots"][0]["status"], "candidate_not_restore_verified")
        target = self.base / "replacement"
        recovery = recover_snapshot(self.cfg, receipt["snapshot_id"], target, restic=self.restic)
        self.assertTrue(recovery["admission_stopped"])
        self.assertEqual(recovery["previous_host_verification"], "unknown")
        reconstructed = json.loads((target / "reconstructed-receipt.json").read_text())
        self.assertEqual(reconstructed["keys_sha256"], receipt["keys_sha256"])
        restored = Runtime(Store(target), executor=lambda _: self.fail("unexpected source fetch"), clock=lambda: NOW + 300)
        self.assertEqual(restored.run(self.workflow.id, "permanent-key")["run_id"], self.run["run_id"])
        self.assertEqual(restored.run(self.workflow.id, "new-key")["reason"], "stopped")
        self.assertFalse(self.root.exists())
        self.assertFalse(self.state.exists())
        self.assertTrue(all(call[0] in {"cat", "snapshots", "dump", "restore"} for call in self.restic.calls))
        # The reconstructed receipt supports the ordinary recovery path too.
        again = recover(self.cfg, target / "reconstructed-receipt.json", self.base / "second-recovery", restic=self.restic)
        self.assertEqual(again["snapshot_id"], receipt["snapshot_id"])

    def test_disaster_recovery_refuses_latest_prefixes_and_wrong_repository(self):
        for identifier in ("latest", "abcd1234", "--latest", None):
            with self.assertRaises(ValueError):
                recover_snapshot(self.cfg, identifier, self.base / "rejected", restic=self.restic)
        self.assertEqual(self.restic.calls, [])
        self.restic.repository_id = "b" * 64
        with self.assertRaises(ValueError):
            candidates(self.cfg, restic=self.restic)
        self.assertEqual(len(self.restic.calls), 1)

    def test_disaster_recovery_rejects_foreign_and_unsafe_snapshot_metadata(self):
        receipt = backup(self.cfg, restic=self.restic)
        original = copy.deepcopy(self.restic.snapshots[receipt["snapshot_id"]])
        for changes in ({"hostname": "another-host"}, {"tags": ["runtime-ops-v1", "installation-" + "0" * 32]},
                        {"paths": ["/data/../pending/" + receipt["operation_id"] + "/payload"]},
                        {"paths": ["/data/other/payload"]}, {"time": "2026-10-08T09:00:00"}):
            with self.subTest(changes=changes):
                self.restic.snapshots[receipt["snapshot_id"]] = {**original, **changes}
                with self.assertRaises(ValueError):
                    recover_snapshot(self.cfg, receipt["snapshot_id"], self.base / "rejected", restic=self.restic)
                self.assertFalse((self.base / "rejected").exists())

    def test_disaster_recovery_rejects_runtime_workflow_and_manifest_drift(self):
        receipt = backup(self.cfg, restic=self.restic)
        snapshot = self.restic.snapshots[receipt["snapshot_id"]]
        original = json.loads(snapshot["files"]["manifest.json"])
        for changes in ({"implementation_sha256": "e" * 64}, {"operation_id": "0" * 32},
                        {"package_version": "9.0.0"}, {"extra": "field"}):
            with self.subTest(changes=changes):
                snapshot["files"]["manifest.json"] = json.dumps({**original, **changes}).encode()
                with self.assertRaises(ValueError):
                    recover_snapshot(self.cfg, receipt["snapshot_id"], self.base / "rejected", restic=self.restic)
                self.assertFalse((self.base / "rejected").exists())
        snapshot["files"]["manifest.json"] = json.dumps(original).encode()
        with self.assertRaises(ValueError):
            recover_snapshot({**self.cfg, "jobs": {self.workflow.id: "e" * 64}}, receipt["snapshot_id"], self.base / "rejected", restic=self.restic)

    def test_disaster_recovery_never_accepts_corrupt_or_extra_files(self):
        receipt = backup(self.cfg, restic=self.restic)
        self.restic.corrupt_restore = True
        with self.assertRaisesRegex(ValueError, "checksum"):
            recover_snapshot(self.cfg, receipt["snapshot_id"], self.base / "corrupt", restic=self.restic)
        self.assertFalse((self.base / "corrupt/runtime.sqlite").exists())
        self.restic.corrupt_restore = False
        self.restic.snapshots[receipt["snapshot_id"]]["files"]["unexpected"] = b"not part of the journal"
        with self.assertRaisesRegex(ValueError, "inventory"):
            recover_snapshot(self.cfg, receipt["snapshot_id"], self.base / "extra", restic=self.restic)
        self.assertFalse((self.base / "extra/reconstructed-receipt.json").exists())

    def test_failed_stop_transaction_cannot_publish_a_live_recovery_copy(self):
        receipt = backup(self.cfg, restic=self.restic)
        connect = sqlite3.connect
        class RefuseStop(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                if sql.startswith("UPDATE meta SET value='true'"):
                    raise sqlite3.OperationalError("injected stop failure")
                return super().execute(sql, *args, **kwargs)
        def failing_connect(*args, **kwargs):
            return connect(*args, **kwargs, factory=RefuseStop)
        with patch("ops_backup.sqlite3.connect", side_effect=failing_connect):
            with self.assertRaises(sqlite3.OperationalError):
                recover_snapshot(self.cfg, receipt["snapshot_id"], self.base / "stop-failed", restic=self.restic)
        self.assertFalse((self.base / "stop-failed/runtime.sqlite").exists())
        self.assertFalse((self.base / "stop-failed/recovery.json").exists())
        self.assertFalse(self.store.report()["stopped"])

    def test_diagnostics_explain_original_rows_without_changing_policy_or_source(self):
        value = result()
        value["results"][0].update(value=None, rights_status=None, availability="withheld")
        self.runtime.executor = lambda _: value
        self.runtime.clock = lambda: NOW + 300
        self.runtime.run(self.workflow.id, "source-block")
        before = sha((self.root / "runtime.sqlite").read_bytes())
        report = diagnose(self.cfg, now=NOW + 90000)
        job = report["jobs"][0]
        self.assertEqual(job["affected_row_counts"]["rights_not_established"], 1)
        self.assertEqual(job["affected_row_counts"]["numeric_value_missing"], 1)
        self.assertEqual(job["affected_row_counts"]["source_not_available"], 1)
        self.assertEqual(job["assessment_time"], "original_capture_only")
        self.assertEqual(job["requirements"], self.workflow.value["requirements"])
        self.assertIsNone(job["representative_rows"][0]["rights_status"])
        self.assertEqual(report["source_network_calls"], 0)
        self.assertFalse(report["policy_changes"])
        self.assertEqual(sha((self.root / "runtime.sqlite").read_bytes()), before)
        with self.assertRaises(ValueError):
            diagnose(self.cfg, job="unregistered")

    def test_corrupt_previous_monitor_state_is_reported_and_replaced(self):
        (self.state / "health.json").write_bytes(b'{"invalid":')
        value = monitor(self.cfg, service_units=self.units, now=NOW)
        self.assertIn("previous_monitor_state_invalid", {i["code"] for i in value["issues"]})
        self.assertEqual(json.loads((self.state / "health.json").read_text()), value)
        self.assertEqual(json.loads((self.state / "diagnostics.json").read_text())["status"], "observed")
        next_value = monitor(self.cfg, service_units=self.units, now=NOW + 1)
        self.assertNotIn("previous_monitor_state_invalid", {i["code"] for i in next_value["issues"]})

    def test_source_blocks_are_distinct_from_operations_failure(self):
        journal = inspect_journal(self.root / "runtime.sqlite")
        journal["jobs"][0]["latest"].update(status="blocked", reasons=["rights_not_established"])
        report = self.report(journal=journal)
        self.assertEqual(report["operations_status"], "healthy")
        self.assertEqual(report["source_status"], "blocked")
        self.assertIsNone(report["external_active_users"])
        self.assertFalse(report["coverage_complete"])

    def test_missed_scheduler_and_overdue_workflow_are_critical(self):
        report = self.report(now=NOW + 1000)
        self.assertEqual(report["operations_status"], "critical")
        codes = {i["code"] for i in report["issues"]}
        self.assertIn("scheduler_heartbeat_stale", codes)
        self.assertIn("workflow_overdue", codes)

    def test_failed_or_stale_backup_is_never_hidden_by_healthy_jobs(self):
        for status in (None, {"status": "failed", "last_verified": None}):
            self.assertEqual(self.report(backup=status)["operations_status"], "critical")
        value = self.report()["backup"]
        value["last_verified"]["verified_at"] = datetime.fromtimestamp(NOW - 7200, timezone.utc).isoformat()
        self.assertIn("offsite_restore_stale", {i["code"] for i in self.report(backup=value)["issues"]})

    def test_disk_capacity_and_interrupted_claim_diagnostics(self):
        journal = inspect_journal(self.root / "runtime.sqlite")
        journal["runs"] = 9000
        journal["jobs"][0]["latest"].update(status="running", started=NOW - 130)
        report = self.report(journal=journal, free_bytes=0)
        codes = {i["code"] for i in report["issues"]}
        self.assertTrue({"runs_capacity_warning", "claim_interrupted", "disk_reserve_low"} <= codes)

    def test_transitions_deduplicate_and_record_resolution(self):
        issue = {"id": "example", "code": "example", "severity": "critical", "job": None}
        current = {"issues": [issue]}
        self.assertEqual(len(transitions(None, current, "now")), 1)
        self.assertEqual(transitions(current, current, "later"), [])
        self.assertEqual(transitions(current, {"issues": []}, "fixed")[0]["transition"], "resolved")

    def test_monitor_failure_replaces_old_success_without_mutating_source(self):
        before = sha((self.root / "runtime.sqlite").read_bytes())
        with patch("ops_monitor.runtime_identity", side_effect=ValueError("private path or token")):
            value = monitor(self.cfg, service_units=self.units)
        self.assertEqual(value["operations_status"], "critical")
        self.assertNotIn("private path or token", (self.state / "health.json").read_text())
        self.assertEqual(sha((self.root / "runtime.sqlite").read_bytes()), before)

    def test_renderer_is_bounded_and_binds_only_loopback(self):
        args = {"python": "/opt/runtime/.venv/bin/python", "code": "/opt/runtime-ops/release", "config_path": "/etc/runtime-ops/config.json",
                "credentials": "/etc/runtime-ops/backup.env", "user": "financial-research"}
        rendered = render(self.cfg, **args)
        self.assertEqual(len(rendered), 7)
        self.assertIn("OnUnitActiveSec=15min", rendered["financial-evidence-runtime-backup.timer"])
        self.assertIn("IPAddressAllow=localhost", rendered["financial-evidence-runtime-dashboard.service"])
        self.assertNotIn("rm ", "".join(rendered.values()))
        for changed in ({"code": "/tmp/evil%N"}, {"user": "root\nExecStart=evil"}):
            with self.assertRaises(ValueError):
                render(self.cfg, **{**args, **changed})

    def test_upgrade_replaces_active_console_without_restarting_research_workers(self):
        running_console = ["old-release"]
        def systemctl(command, **kwargs):
            if command[1] == "restart":
                self.assertEqual(command[2:], ["financial-evidence-runtime-dashboard.service"])
                running_console[0] = "new-release"
            elif command[1] == "enable":
                pass  # enable --now intentionally cannot replace an active process.
            else:
                self.fail("unexpected service mutation")
        with patch("install.subprocess.run", side_effect=systemctl):
            activate({name: "" for name in UNITS})
        self.assertEqual(running_console[0], "new-release")

    def test_http_readonly_host_filter_and_stale_fail_closed(self):
        value = self.report()
        atomic(self.state / "health.json", value)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.cfg))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(path, method="GET", headers=None):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            try:
                connection.request(method, path, headers=headers or {})
                response = connection.getresponse()
                return response.status, response.read()
            finally:
                connection.close()
        self.assertEqual(request("/", headers={"Host": "attacker.example"})[0], 421)
        self.assertEqual(request("/../runtime.sqlite")[0], 404)
        self.assertEqual(request("/", method="POST")[0], 405)
        self.assertEqual(request("/")[0], 200)
        status, body = request("/status.json")
        self.assertEqual(status, 503)  # The September fixture cannot claim current health.
        self.assertEqual(json.loads(body)["operations_status"], "stale")
        self.assertEqual(request("/diagnostics.json")[0], 503)
        atomic(self.state / "diagnostics.json", diagnose(self.cfg, now=NOW))
        status, body = request("/diagnostics.json")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["status"], "stale")
        atomic(self.state / "diagnostics.json", diagnose(self.cfg))
        self.assertEqual(request("/diagnostics.json")[0], 200)


if __name__ == "__main__":
    unittest.main()
