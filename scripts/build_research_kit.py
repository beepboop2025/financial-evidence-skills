#!/usr/bin/env python3
"""Build a reproducible, source-only research kit; --check detects stale assets."""
import argparse
import hashlib
import io
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "docs/tools"
FILES = (
    "research_client.py", "research_desk.ipynb", "FinancialEvidenceRows.pq",
    "mcp.json", "agent-instructions.md", "setup.md", "vendor-readiness.md",
)


def build():
    entries = {name: (KIT / name).read_bytes() for name in FILES}
    entries["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    entries["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(content).hexdigest()}  {name}\n"
        for name, content in sorted(entries.items())
    ).encode()
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in sorted(entries.items()):
            info = ZipInfo("financial-evidence-research-kit/" + name, (2026, 10, 6, 0, 0, 0))
            info.compress_type = ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return {"research-kit.zip": buffer.getvalue(), "SHA256SUMS": entries["SHA256SUMS"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build()
    for name, content in outputs.items():
        target = KIT / name
        if args.check:
            if not target.exists() or target.read_bytes() != content:
                raise SystemExit(f"Stale {name}; run scripts/build_research_kit.py")
        else:
            target.write_bytes(content)
    print("Research kit matches its source files" if args.check else "Built research kit and file checksums")


if __name__ == "__main__":
    main()
