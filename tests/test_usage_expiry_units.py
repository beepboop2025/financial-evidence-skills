"""Usage-expiry units: off the midnight burst, recover a stale name, no network.

On 2026-11-01 and 2026-11-02 the funding usage expiry timed out at 00:01:00.
About 30 units start at midnight on its host; Docker created the container but
did not start it within 60 s, and the never-started container kept the fixed
name, so the next run failed on a name conflict. Off-peak, the job takes 2 s.
"""

import contextlib
import importlib.util
import io
import json
import shlex
import socket
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from financial_evidence import application_usage
from financial_evidence import institutional

FUNDING_SERVICE = ROOT / "integrations/institutional/financial-evidence-usage-expiry.service"
FUNDING_TIMER = ROOT / "integrations/institutional/financial-evidence-usage-expiry.timer"
WORKSPACE_SERVICE = ROOT / "integrations/openbb/financial-evidence-workspace-usage-expiry.service"

# The existing hardening flags, unchanged, plus --network none.
FUNDING_EXEC_START = (
    "/usr/bin/docker run --rm --name financial-evidence-usage-expiry --network none"
    " --read-only --cap-drop ALL --security-opt no-new-privileges --memory 96m"
    " --cpus 0.25 --pids-limit 16 --user 65532:65532"
    " -v /var/lib/financial-evidence-institutional/usage:/data/usage:rw"
    " --entrypoint python ${INSTITUTIONAL_IMAGE}"
    " -m financial_evidence.institutional usage --directory /data/usage"
)
WORKSPACE_EXEC_START = (
    "/usr/bin/docker run --rm --name financial-evidence-workspace-usage-expiry --network none"
    " --read-only --cap-drop ALL --security-opt no-new-privileges --memory 128m"
    " --cpus 0.25 --pids-limit 32 --user ${WORKSPACE_UID}:${WORKSPACE_GID}"
    " -v /var/lib/financial-evidence-workspace/usage:/data/usage:rw"
    " --entrypoint python ${WORKSPACE_IMAGE}"
    " -m financial_evidence.workspace_usage report --directory /data/usage"
)


def directives(path):
    """Every Key=Value line of a unit file, in order (keys may repeat)."""
    lines = Path(path).read_text().splitlines()
    return [tuple(line.split("=", 1)) for line in lines if "=" in line and not line.startswith("#")]


def values(path, key):
    return [value for name, value in directives(path) if name == key]


def offline(*args, **kwargs):
    raise AssertionError("the usage expiry attempted network access")


@contextlib.contextmanager
def network_disabled():
    with patch.object(socket, "socket", side_effect=offline), \
            patch.object(socket, "create_connection", side_effect=offline), \
            patch.object(socket, "getaddrinfo", side_effect=offline):
        yield


def utc_day(days_ago=0):
    return (datetime.now(timezone.utc).date() - timedelta(days=days_ago)).isoformat()


def seed_applications(root):
    """One current and one long-inactive installation, with fresh and stale completions."""
    with application_usage.connect(root) as db:
        for identifier, last_seen in (("current", utc_day()), ("inactive", utc_day(200))):
            db.execute(
                "INSERT INTO applications VALUES (?, ?, ?, ?, 'unverified', NULL)",
                (identifier, identifier + "-hash", last_seen, last_seen),
            )
        for day, packet in ((utc_day(), "fresh"), (utc_day(120), "stale")):
            db.execute(
                "INSERT INTO completions VALUES ('current', ?, ?, 'unverified')", (day, packet)
            )


def remaining(root, query):
    with contextlib.closing(sqlite3.connect(Path(root) / "applications.sqlite")) as db:
        return sorted(row[0] for row in db.execute(query))


class UsageExpiryUnitTests(unittest.TestCase):
    def test_hardening_flags_are_unchanged_and_network_is_disabled(self):
        self.assertEqual(values(FUNDING_SERVICE, "ExecStart"), [FUNDING_EXEC_START])
        self.assertEqual(values(WORKSPACE_SERVICE, "ExecStart"), [WORKSPACE_EXEC_START])

    def test_pre_start_removes_only_a_stopped_container_of_the_exact_name(self):
        for service in (FUNDING_SERVICE, WORKSPACE_SERVICE):
            with self.subTest(service=service.name):
                start = shlex.split(values(service, "ExecStart")[0])
                name = start[start.index("--name") + 1]
                self.assertEqual(
                    [shlex.split(command) for command in values(service, "ExecStartPre")],
                    [[
                        "/bin/sh",
                        "-c",
                        f"/usr/bin/docker container inspect {name} >/dev/null 2>&1 || exit 0; "
                        f"exec /usr/bin/docker rm {name}",
                    ]],
                )

    def test_start_timeout_leaves_a_margin_over_the_two_second_job(self):
        for service in (FUNDING_SERVICE, WORKSPACE_SERVICE):
            with self.subTest(service=service.name):
                self.assertEqual(values(service, "TimeoutStartSec"), ["300"])

    def test_funding_expiry_runs_once_daily_off_the_midnight_burst(self):
        self.assertEqual(values(FUNDING_TIMER, "OnCalendar"), ["*-*-* 00:17:00 UTC"])
        self.assertEqual(values(FUNDING_TIMER, "RandomizedDelaySec"), ["60"])
        self.assertEqual(values(FUNDING_TIMER, "Persistent"), ["true"])
        timer_keys = {name for name, _ in directives(FUNDING_TIMER)}
        self.assertFalse(timer_keys & {"OnActiveSec", "OnBootSec", "OnStartupSec", "OnUnitActiveSec", "OnUnitInactiveSec"})

    def test_funding_expiry_needs_no_network_and_purges_both_datasets(self):
        with tempfile.TemporaryDirectory() as root:
            db, _ = institutional.connect_events(root)
            with contextlib.closing(db):
                for day in (utc_day(), utc_day(45)):
                    db.execute("INSERT INTO events VALUES (?, ?, ?, 'packet_download')", ("v" * 64, day, "p"))
                db.commit()
            seed_applications(root)
            output = io.StringIO()
            argv = ["financial_evidence.institutional", "usage", "--directory", root]
            with network_disabled(), patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
                self.assertEqual(institutional.main(), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["consented_download_events"], 1)
            self.assertEqual(report["applications"]["schema"], "financial-evidence.application-usage.v1")
            self.assertEqual(remaining(root, "SELECT id FROM applications"), ["current"])
            self.assertEqual(remaining(root, "SELECT packet FROM completions"), ["fresh"])

    @unittest.skipUnless(importlib.util.find_spec("fastapi"), "workspace dependencies required")
    def test_workspace_expiry_needs_no_network_and_purges_its_dataset(self):
        from financial_evidence import workspace_usage

        with tempfile.TemporaryDirectory() as root:
            seed_applications(root)
            output = io.StringIO()
            argv = ["financial_evidence.workspace_usage", "report", "--directory", root]
            with network_disabled(), patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
                workspace_usage.main()
            report = json.loads(output.getvalue())
            self.assertEqual(report["schema"], "financial-evidence.research-growth.v2")
            self.assertEqual(remaining(root, "SELECT id FROM applications"), ["current"])
            self.assertEqual(remaining(root, "SELECT packet FROM completions"), ["fresh"])


if __name__ == "__main__":
    unittest.main()
