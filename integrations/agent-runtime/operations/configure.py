#!/usr/bin/env python3
"""Bind operations to the verified runtime and the owner's existing workflows."""

import argparse
import json
import os
from pathlib import Path

from ops_common import atomic, config, inspect_journal, private, regular, runtime_identity


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    output = Path(args.output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("configuration destination must be new")
    release = json.loads(regular(Path(__file__).with_name("runtime-release.json"), 8192))
    journal = inspect_journal(Path(args.root) / "runtime.sqlite", full=True)
    value = {"schema": "financial-evidence.runtime-ops.v1", "root": str(Path(args.root).absolute()),
             "state": str(Path(args.state).absolute()), "installation_id": journal["installation_id"],
             "package_version": release["package_version"], "implementation_sha256": release["implementation_sha256"],
             "repository_id": args.repository_id, "jobs": {j["id"]: j["sha256"] for j in journal["jobs"]},
             "due_grace_seconds": 180, "backup_max_age_seconds": 3600, "monitor_max_age_seconds": 180,
             "min_free_bytes": 1_073_741_824}
    runtime_identity(value)
    private(args.state, create=True)
    private(output.parent)
    atomic(output, value)
    config(output)
    print(json.dumps({"configured": True, "path": str(output), "installation_id": journal["installation_id"],
                      "workflows": sorted(value["jobs"]), "source_writes": False}, indent=2))


if __name__ == "__main__":
    main()
