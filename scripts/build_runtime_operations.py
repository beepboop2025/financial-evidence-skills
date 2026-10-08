#!/usr/bin/env python3
"""Build a source-bound operations archive, separate from the runtime wheel."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "integrations/agent-runtime/operations"
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root).strip():
        raise ValueError("commit the reviewed source before building a release")
    output = Path(args.output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    version = "1.0.2"
    names = ("ops.py", "ops_common.py", "ops_backup.py", "ops_monitor.py", "install.py", "configure.py",
             "ops_recovery.py", "ops_diagnostics.py", "README.md", "RELEASE_NOTES.md", "runtime-release.json")
    entries = {name: (source / name).read_bytes() for name in names}
    manifest = {"schema": "financial-evidence.runtime-ops-release.v1", "version": version,
                "source_commit": commit, "runtime": json.loads(entries["runtime-release.json"]),
                "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(entries.items())}}
    entries["source.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    archive = output / ("financial-evidence-runtime-ops-" + version + ".tar")
    with tarfile.open(archive, "w", format=tarfile.USTAR_FORMAT) as stream:
        for name, raw in sorted(entries.items()):
            info = tarfile.TarInfo("financial-evidence-runtime-ops-" + version + "/" + name)
            info.size, info.mode, info.mtime = len(raw), 0o644, 0
            stream.addfile(info, io.BytesIO(raw))
    (output / "source.json").write_bytes(entries["source.json"])
    (output / "SHA256SUMS").write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in [archive, output / "source.json"]))
    print(json.dumps({"source_commit": commit, "archive": str(archive), "files": len(entries)}, indent=2))


if __name__ == "__main__":
    main()
