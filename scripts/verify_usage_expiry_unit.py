#!/usr/bin/env python3
"""Exercise a usage-expiry unit's exact Docker commands against a built image.

Only the unit's ${...} placeholders and the host side of the /data/usage mount
are substituted. The check shows that:

1. with no leftover container, ExecStartPre is a quiet no-op;
2. a never-started container holding the fixed name (the 2026-11-01 and
   2026-11-02 midnight failure) blocks ExecStart, and ExecStartPre removes it;
3. ExecStart then completes with --network none against a scratch store;
4. ExecStartPre never removes a running container of that name.

It creates and removes containers under the unit's fixed name, so it refuses
to run outside CI.

    python3 scripts/verify_usage_expiry_unit.py UNIT NAME=VALUE [NAME=VALUE ...]
"""

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

USAGE_MOUNT = ":/data/usage:rw"


def fail(message, result=None):
    detail = ""
    if result is not None:
        detail = f"\nexit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    raise SystemExit(f"FAIL: {message}{detail}")


def run(argv):
    return subprocess.run(argv, capture_output=True, text=True, timeout=240, check=False)


def state(name):
    result = run(["docker", "container", "inspect", "--format", "{{.State.Status}}", name])
    return result.stdout.strip() if result.returncode == 0 else None


def commands(unit):
    found = {}
    for line in Path(unit).read_text().splitlines():
        key, separator, value = line.partition("=")
        if separator and key in ("ExecStartPre", "ExecStart"):
            if key in found:
                fail(f"{unit} has more than one {key}")
            found[key] = value
    if set(found) != {"ExecStartPre", "ExecStart"}:
        fail(f"{unit} needs exactly one ExecStartPre and one ExecStart")
    return found


def expand(command, values, store):
    argv = shlex.split(re.sub(r"\$\{(\w+)\}", lambda match: values[match.group(1)], command))
    return [store + USAGE_MOUNT if arg.endswith(USAGE_MOUNT) else arg for arg in argv]


def main():
    if os.environ.get("CI") != "true":
        raise SystemExit("CI only: this replaces containers under the unit's fixed name")
    unit, *assignments = sys.argv[1:]
    values = dict(assignment.split("=", 1) for assignment in assignments)
    store = tempfile.mkdtemp(prefix="usage-expiry-")
    os.chmod(store, 0o777)  # the job runs as the unit's non-root --user
    found = commands(unit)
    pre = expand(found["ExecStartPre"], values, store)
    start = expand(found["ExecStart"], values, store)
    name = start[start.index("--name") + 1]
    image = start[start.index("--entrypoint") + 2]
    if start[start.index("--network") + 1] != "none":
        fail("ExecStart must run with --network none")
    try:
        quiet = run(pre)
        if quiet.returncode or quiet.stdout or quiet.stderr:
            fail("ExecStartPre is not a quiet no-op without a leftover", quiet)

        created = run(["docker", "create", "--name", name, image])
        if created.returncode or state(name) != "created":
            fail("could not create the never-started leftover", created)
        blocked = run(start)
        if blocked.returncode == 0 or "already in use" not in blocked.stderr:
            fail("the leftover did not reproduce the name conflict", blocked)
        removed = run(pre)
        if removed.returncode or state(name) is not None:
            fail("ExecStartPre did not remove the never-started leftover", removed)

        job = run(start)
        if job.returncode:
            fail("ExecStart failed with --network none", job)
        report = json.loads(job.stdout)
        if "evaluated_at" not in report or not (Path(store) / "applications.sqlite").is_file():
            fail("ExecStart did not produce its report and store", job)
        if state(name) is not None:
            fail("the finished job left its container behind", job)

        running = run(["docker", "run", "--detach", "--name", name, "--entrypoint", "python",
                       image, "-c", "import time; time.sleep(300)"])
        if running.returncode or state(name) != "running":
            fail("could not start a running container under the fixed name", running)
        refused = run(pre)
        if refused.returncode == 0 or state(name) != "running":
            fail("ExecStartPre removed or ignored a running container", refused)
    finally:
        run(["docker", "rm", "--force", name])
    print(json.dumps({
        "unit": unit,
        "container": name,
        "network": "none",
        "never_started_leftover_removed": True,
        "running_container_preserved": True,
        "report_keys": sorted(report),
    }, indent=2))


if __name__ == "__main__":
    main()
