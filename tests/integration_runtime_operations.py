"""Actual encrypted Restic backup/restore with installed runtime and no source calls."""

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from unittest.mock import patch

from test_runtime_operations import ROOT, NOW, result, workflow
from financial_evidence.runtime.engine import Runtime, implementation
from financial_evidence.runtime.store import Store
from ops_backup import Restic, backup, recover
from ops_common import atomic, inspect_journal
from install import render


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).absolute()
    output.mkdir(mode=0o700, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="private-restic-", dir=output) as folder:
        root = Path(folder).resolve()
        state = root / "operations"
        state.mkdir(mode=0o700)
        source = root / "source"
        store = Store(source, traffic_class="synthetic")
        spec = workflow()
        store.register(spec, NOW)
        runtime = Runtime(store, executor=lambda _: result(), clock=lambda: NOW)
        first = runtime.run(spec.id, "acceptance-1")
        environment = {k: v for k, v in os.environ.items() if not k.startswith(("RESTIC_", "AWS_"))}
        environment.update(RESTIC_REPOSITORY=str(root / "repository"), RESTIC_PASSWORD=secrets.token_urlsafe(48), RESTIC_CACHE_DIR=str(root / "cache"))
        with patch.dict(os.environ, environment, clear=True):
            restic = Restic()
            restic("init")  # Only this isolated synthetic test may initialize a repository.
            repository_id = json.loads(restic("cat", "config"))["id"]
            cfg = {"schema": "financial-evidence.runtime-ops.v1", "root": str(source), "state": str(state),
                   "installation_id": store.report()["installation_id"], "package_version": "0.1.7",
                   "implementation_sha256": implementation()["sha256"], "repository_id": repository_id,
                   "jobs": {spec.id: spec.sha256}, "due_grace_seconds": 180, "backup_max_age_seconds": 3600,
                   "monitor_max_age_seconds": 180, "min_free_bytes": 1048576}
            receipt = backup(cfg)
            receipt_path = state / "receipts" / (receipt["operation_id"] + ".json")
            recovery = recover(cfg, receipt_path, root / "recovered")
            assert recovery["admission_stopped"] and recovery["restored_receipts"] == 1
            restored = Runtime(Store(root / "recovered"), executor=lambda _: (_ for _ in ()).throw(AssertionError("source call during restore")), clock=lambda: NOW + 300)
            assert restored.run(spec.id, "acceptance-1")["run_id"] == first["run_id"]
            assert restored.run(spec.id, "new-key")["reason"] == "stopped"
            runtime.clock = lambda: NOW + 300
            runtime.run(spec.id, "acceptance-2")
            second = backup(cfg)
            assert second["snapshot_id"] != receipt["snapshot_id"] and second["verified_receipts"] == 2
            restic("check", "--read-data")
            snapshots = json.loads(restic("snapshots", "--tag", "runtime-ops-v1"))
            assert len(snapshots) == 2
            atomic(output / "first-backup.json", receipt)
            atomic(output / "second-backup.json", second)
            atomic(output / "recovery.json", recovery)
            unit_dir = output / "units"
            unit_dir.mkdir()
            import pwd
            rendered = render(cfg, python=sys.executable, code=ROOT / "integrations/agent-runtime/operations", config_path=root / "config.json", credentials=root / "credentials.env", user=pwd.getpwuid(os.getuid()).pw_name)
            for name, body in rendered.items():
                (unit_dir / name).write_text(body)
            if sys.platform.startswith("linux"):
                subprocess.run(["systemd-analyze", "verify", *map(str, unit_dir.iterdir())], check=True, capture_output=True)
            report = {"status": "PASS", "package_version": "0.1.7", "real_restic": True,
                      "restic_version": subprocess.check_output(["restic", "version"], text=True).strip(),
                      "exact_snapshots_verified": 2, "restored_admission_stopped": True, "retry_keys_preserved": True,
                      "source_network_calls": 0, "broker_orders": 0, "full_repository_check": True,
                      "native_systemd_unit_verification": sys.platform.startswith("linux"), "traffic_class": "synthetic"}
            atomic(output / "report.json", report)
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
