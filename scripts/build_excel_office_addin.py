#!/usr/bin/env python3
"""Build a deterministic Office.js source and manifest archive; never deploy it."""
import argparse
import hashlib
import io
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OFFICE = ROOT / "docs/office"
DEST = OFFICE / "excel"
FILES = ("README.md", "insert.js", "taskpane.html", "taskpane.js", "taskpane.css",
         "manifest.xml", "privacy.html", "icon-16.png", "icon-20.png", "icon-32.png", "icon-64.png", "icon-80.png", "icon-128.png")


def build():
    entries = {"excel/" + name: (DEST / name).read_bytes() for name in FILES}
    entries["office-core.js"] = (OFFICE / "office-core.js").read_bytes()
    entries["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    checksums = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(entries.items())).encode()
    entries["SHA256SUMS"] = checksums
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        for name, data in sorted(entries.items()):
            info = ZipInfo("financial-evidence-excel/" + name, (2026, 10, 18, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return {"SHA256SUMS": checksums, "financial-evidence-excel.zip": output.getvalue()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, data in build().items():
        target = DEST / name
        if args.check:
            if not target.exists() or target.read_bytes() != data:
                raise SystemExit(f"Stale Excel add-in asset: {name}; run scripts/build_excel_office_addin.py")
        else:
            target.write_bytes(data)
    print("Excel add-in package matches source" if args.check else "Built Excel add-in package")


if __name__ == "__main__":
    main()
