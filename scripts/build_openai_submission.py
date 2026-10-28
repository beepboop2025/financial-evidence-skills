#!/usr/bin/env python3
"""Build the independently versioned OpenAI submission ZIP without a runtime release."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "integrations/openai/financial-evidence/plugin.json"
FILES = (
    ".mcp.json", "LICENSE", "assets/logo-400.png", "assets/logo.svg",
    "skills/financial-evidence/SKILL.md",
    "skills/financial-evidence/references/routing.md",
    "skills/financial-evidence/scripts/fetch_evidence.py",
)


def build():
    manifest = json.loads((ROOT / MANIFEST).read_text())
    version = manifest["version"]
    files = {name: (ROOT / name).read_bytes() for name in FILES}
    files[".codex-plugin/plugin.json"] = (ROOT / MANIFEST).read_bytes()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            target.writestr(info, data)
    body = buffer.getvalue()
    stem = f"docs/distribution/downloads/financial-evidence-openai-plugin-v{version}"
    receipt = {
        "schema": "financial-evidence.openai-candidate.v1",
        "plugin_version": version,
        "runtime_version": json.loads((ROOT / ".codex-plugin/plugin.json").read_text())["version"],
        "state": "prepared_candidate",
        "official_directory_approved": False,
        "review_cases_status": "configured_not_model_tested",
        "demo_recording_status": "not_recorded",
        "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    return {stem + ".zip": body,
            stem + ".json": (json.dumps(receipt, indent=2) + "\n").encode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for relative, expected in build().items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit("Stale OpenAI candidate: " + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    print("OpenAI candidate files match.")


if __name__ == "__main__":
    main()
