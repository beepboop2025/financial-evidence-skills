#!/usr/bin/env python3
"""Render or install the owned runtime operations units after reviewing a plan."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import time

from ops_common import HEX, atomic, bound_identity, config, decode, inspect_journal, private, regular, runtime_identity, utc


def absolute(value):
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(value)) or ".." in Path(value).parts:
        raise ValueError("systemd paths must be absolute without spaces or substitutions")
    return str(value)


def render(cfg, *, python, code, config_path, credentials, user):
    python, code, config_path, credentials = map(absolute, (python, code, config_path, credentials))
    root, state = map(absolute, (cfg["root"], cfg["state"]))
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
        raise ValueError("invalid service account")
    common = "UMask=0077\nEnvironment=PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\nNoNewPrivileges=true\nPrivateTmp=true\nProtectSystem=strict\nProtectHome=true\nPrivateDevices=true\nProtectKernelTunables=true\nProtectKernelModules=true\nProtectControlGroups=true\nRestrictSUIDSGID=true\n"
    prefix = f"{python} {code}/ops.py --config {config_path}"
    result = {}

    def service(name, description, body, *, network=False):
        ordering = "After=network-online.target\nWants=network-online.target\n" if network else ""
        result[name + ".service"] = (f"[Unit]\nDescription={description}\n{ordering}RequiresMountsFor={root} {state}\n\n[Service]\n"
                                     + body + common + "\n[Install]\nWantedBy=multi-user.target\n")

    def timer(name, description, initial, interval):
        result[name + ".timer"] = (f"[Unit]\nDescription={description}\n\n[Timer]\nOnActiveSec={initial}\nOnUnitActiveSec={interval}\nAccuracySec=1s\nUnit={name}.service\n\n[Install]\nWantedBy=timers.target\n")

    service("financial-evidence-runtime", "Bounded Financial Evidence research scheduler",
            f"Type=oneshot\nUser={user}\nGroup={user}\nExecStart={Path(python).parent}/financial-evidence-runtime --root {root} tick --limit 1\n"
            f"TimeoutStartSec=60\nMemoryMax=256M\nCPUQuota=50%\nTasksMax=16\nReadWritePaths={root}\nRestrictAddressFamilies=AF_UNIX AF_INET AF_INET6\n", network=True)
    timer("financial-evidence-runtime", "Schedule bounded research once a minute", "15s", "60s")
    service("financial-evidence-runtime-backup", "Encrypted research journal backup with exact offsite restoration",
            f"Type=oneshot\nUser=root\nEnvironmentFile={credentials}\n"
            f"ExecStart=/usr/bin/env RESTIC_CACHE_DIR={state}/restic-cache {prefix} backup\n"
            f"TimeoutStartSec=20min\nMemoryMax=512M\nCPUQuota=50%\nNice=10\nReadOnlyPaths={root}\nReadWritePaths={state}\n"
            "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6\n", network=True)
    # A startup-relative trigger can rearm on a shared host's daemon reload.
    # Calendar slots survive reloads without producing extra startup backups.
    result["financial-evidence-runtime-backup.timer"] = (
        "[Unit]\nDescription=Restore-verify encrypted research backup every 15 minutes\n\n"
        "[Timer]\nOnCalendar=*-*-* *:00/15:00 UTC\nPersistent=true\nAccuracySec=1s\n"
        "Unit=financial-evidence-runtime-backup.service\n\n[Install]\nWantedBy=timers.target\n")
    service("financial-evidence-runtime-monitor", "Inspect runtime scheduling, capacity, source blocks and offsite recovery",
            f"Type=oneshot\nUser=root\nExecStart={prefix} monitor\nTimeoutStartSec=45s\nMemoryMax=256M\n"
            f"ReadOnlyPaths={root}\nReadWritePaths={state}\nPrivateNetwork=true\n")
    timer("financial-evidence-runtime-monitor", "Refresh private runtime health every minute", "10s", "60s")
    service("financial-evidence-runtime-dashboard", "Private read-only Financial Evidence operations console",
            f"Type=simple\nUser=root\nExecStart={prefix} serve --port 8768\nRestart=on-failure\nRestartSec=10s\n"
            f"MemoryMax=128M\nTasksMax=32\nReadOnlyPaths={state}\nRestrictAddressFamilies=AF_UNIX AF_INET\nIPAddressDeny=any\nIPAddressAllow=localhost\n")
    return result


def activate(files):
    """An existing console must adopt the newly installed immutable release."""
    subprocess.run(["systemctl", "enable", "--now", *[name for name in files if name.endswith(".timer")]], check=True)
    subprocess.run(["systemctl", "enable", "financial-evidence-runtime-dashboard.service"], check=True)
    # enable --now does not restart an already active service. Only this
    # read-only console is restarted; research and backup workers are not.
    subprocess.run(["systemctl", "restart", "financial-evidence-runtime-dashboard.service"], check=True)


def previous_units(path, cfg, files):
    if path is None:
        return {}
    path = Path(path)
    private(path.parent)
    plan = decode(regular(path, 65536), limit=65536)
    if not isinstance(plan, dict):
        raise ValueError("prior applied plan must be an object")
    hashes = plan.get("unit_sha256", {})
    if (plan.get("schema") != "financial-evidence.runtime-ops-installation.v1"
            or plan.get("applied") is not True or plan.get("installation_id") != cfg["installation_id"]
            or not isinstance(hashes, dict) or set(hashes) != set(files)
            or not all(isinstance(value, str) and HEX.fullmatch(value) for value in hashes.values())):
        raise ValueError("prior applied plan does not bind this installation and unit inventory")
    return hashes


def owned_units(directory, files, hashes):
    """Descriptions are not ownership evidence; require the prior applied bytes."""
    result = {}
    for name in files:
        path = Path(directory) / name
        if path.is_symlink():
            raise ValueError("existing unit is symlinked")
        if not path.exists():
            if name in hashes:
                raise ValueError("prior installed unit is missing")
            continue
        raw = regular(path, 65536)
        if hashlib.sha256(raw).hexdigest() != hashes.get(name):
            raise ValueError("existing unit differs from --previous-plan; reconcile ownership")
        result[name] = raw
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--runtime-python", required=True)
    parser.add_argument("--credentials", required=True, help="Existing root-private restic EnvironmentFile; contents are never copied")
    parser.add_argument("--runtime-user", default="financial-research")
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous-plan", help="Prior applied plan.json, required when replacing installed units")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    os.umask(0o077)
    cfg = config(args.config)
    runtime_identity(cfg)
    value = inspect_journal(Path(cfg["root"]) / "runtime.sqlite", full=True)
    bound_identity(value, cfg)
    files = render(cfg, python=args.runtime_python, code=Path(__file__).resolve().parent,
                   config_path=args.config, credentials=args.credentials, user=args.runtime_user)
    prior_hashes = previous_units(args.previous_plan, cfg, files)
    output = Path(args.output)
    output.mkdir(mode=0o700, exist_ok=False)
    for name, body in files.items():
        atomic(output / name, body.encode(), raw=True)
    plan = {"schema": "financial-evidence.runtime-ops-installation.v1", "prepared_at": utc(),
            "installation_id": cfg["installation_id"], "unit_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in files.items()},
            "source_writes": False, "credentials_copied": False, "broker_authority": False,
            "backup_interval_seconds": 900, "backup_schedule": "UTC quarter-hours with persistent catch-up",
            "monitor_interval_seconds": 60, "dashboard_bind": "127.0.0.1:8768", "applied": False,
            "previous_plan": str(Path(args.previous_plan).absolute()) if args.previous_plan else None}
    atomic(output / "plan.json", plan)
    if not args.apply:
        print(json.dumps(plan, indent=2))
        return 0
    if os.getuid() != 0 or pwd.getpwnam(args.runtime_user).pw_uid != Path(cfg["root"]).stat().st_uid:
        raise ValueError("root installation and exact runtime account required")
    private(cfg["state"])
    credentials = Path(args.credentials)
    if credentials.is_symlink() or not credentials.is_file() or credentials.stat().st_uid != 0 or credentials.stat().st_mode & 0o077:
        raise ValueError("existing root-private credential file required")
    current = Path("/etc/systemd/system")
    previous = owned_units(current, files, prior_hashes)
    old = private(output / "previous", create=True)
    for name, raw in previous.items():
        atomic(old / name, raw, raw=True)
    subprocess.run(["systemd-analyze", "verify", *[str(output / name) for name in files]], check=True, capture_output=True)
    # Never interrupt an active backup or research attempt to install helpers.
    for unit in ("financial-evidence-runtime.service", "financial-evidence-runtime-backup.service"):
        state = subprocess.run(["systemctl", "show", unit, "--property=ActiveState", "--value"], capture_output=True, text=True, check=True).stdout.strip()
        if state in {"active", "activating", "deactivating"}:
            raise ValueError("owned service busy; reconcile before installation")
    previously_active = []
    dashboard = "financial-evidence-runtime-dashboard.service"
    dashboard_was_active = subprocess.run(["systemctl", "show", dashboard, "--property=ActiveState", "--value"],
                                          check=True, capture_output=True, text=True).stdout.strip() == "active"
    written = []
    try:
        for name in files:
            if name.endswith(".timer"):
                active = subprocess.run(["systemctl", "show", name, "--property=ActiveState", "--value"], check=True, capture_output=True, text=True).stdout.strip()
                if active == "active":
                    previously_active.append(name)
                    subprocess.run(["systemctl", "stop", name], check=True)
        # A tick may have begun between preflight and stopping the timers.
        # Await its bounded completion instead of killing it or replacing work.
        deadline = time.monotonic() + 65
        for unit in ("financial-evidence-runtime.service", "financial-evidence-runtime-backup.service"):
            while subprocess.run(["systemctl", "show", unit, "--property=ActiveState", "--value"], check=True, capture_output=True, text=True).stdout.strip() in {"active", "activating", "deactivating"}:
                if time.monotonic() > deadline:
                    raise ValueError("owned attempt did not finish; original timers will resume")
                time.sleep(1)
        for name, body in files.items():
            atomic(current / name, body.encode(), raw=True)
            (current / name).chmod(0o644)
            written.append(name)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        activate(files)
    except Exception:
        # Restore only the files this attempt wrote. Do not stop a source worker
        # or a possibly accepted backup; any active intent remains inspectable.
        for name in written:
            if name.endswith(".timer"):
                subprocess.run(["systemctl", "stop", name], check=False)
        if dashboard in written and not (old / dashboard).exists():
            subprocess.run(["systemctl", "stop", dashboard], check=False)
        for name in written:
            if (old / name).exists():
                atomic(current / name, (old / name).read_bytes(), raw=True)
                (current / name).chmod(0o644)
            else:
                (current / name).unlink(missing_ok=True)
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        if previously_active:
            subprocess.run(["systemctl", "start", *previously_active], check=False)
        if dashboard_was_active and dashboard in written:
            subprocess.run(["systemctl", "restart", dashboard], check=False)
        plan.update(applied=False, failed_at=utc(), prior_timers_resumed=previously_active)
        atomic(output / "plan.json", plan)
        raise
    plan.update(applied=True, applied_at=utc(), prior_units_retained=str(old), dashboard_restarted=True)
    atomic(output / "plan.json", plan)
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
