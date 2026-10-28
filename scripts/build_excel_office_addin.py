#!/usr/bin/env python3
"""Build a deterministic Office.js source and manifest archive; never deploy it."""
import argparse
import hashlib
import io
from pathlib import Path
from uuid import UUID, uuid5
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OFFICE = ROOT / "docs/office"
DEST = OFFICE / "excel"
FILES = ("README.md", "insert.js", "taskpane.html", "taskpane.js", "taskpane.css",
         "manifest.xml", "privacy.html", "icon-16.png", "icon-20.png", "icon-32.png", "icon-64.png", "icon-80.png", "icon-128.png")


def operator_manifest(source: bytes) -> bytes:
    """Give synthetic verification its own identity without changing permissions."""
    ns = {"app": "http://schemas.microsoft.com/office/appforoffice/1.1",
          "bt": "http://schemas.microsoft.com/office/officeappbasictypes/1.0"}
    root = ET.fromstring(source)
    production_id = root.findtext("app:Id", namespaces=ns)
    test_id = str(uuid5(UUID(production_id), "financial-evidence-operator-test"))
    base = root.find("app:DefaultSettings/app:SourceLocation", ns)
    ribbon = root.find(".//bt:Url[@id='Review.TaskpaneUrl']", ns)
    if base is None or ribbon is None:
        raise ValueError("Both fallback and ribbon task-pane locations are required")
    url = base.attrib["DefaultValue"]
    if ribbon.attrib["DefaultValue"] != url or "?" in url or "#" in url:
        raise ValueError("Production task-pane locations must match without query or fragment")
    text = source.decode("utf-8")
    if text.count(f"<Id>{production_id}</Id>") != 1:
        raise ValueError("Expected exactly one replaceable production app ID")
    if text.count('DisplayName DefaultValue="Financial Evidence"') != 1:
        raise ValueError("Expected exactly one replaceable production display name")
    if text.count(f'DefaultValue="{url}"') != 2:
        raise ValueError("Expected exactly two production task-pane locations")
    return (text.replace(f"<Id>{production_id}</Id>", f"<Id>{test_id}</Id>", 1)
            .replace('DisplayName DefaultValue="Financial Evidence"',
                     'DisplayName DefaultValue="Financial Evidence (verification)"', 1)
            .replace(f'DefaultValue="{url}"', f'DefaultValue="{url}?operator=1"')
            .encode("utf-8"))


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--operator-manifest", type=Path,
                      help="Write a separate synthetic verification manifest to this path")
    args = parser.parse_args()
    if args.operator_manifest:
        if args.operator_manifest.resolve() == (DEST / "manifest.xml").resolve():
            parser.error("The verification manifest must not overwrite production")
        args.operator_manifest.write_bytes(operator_manifest((DEST / "manifest.xml").read_bytes()))
        print(f"Wrote separate verification manifest: {args.operator_manifest}")
        return
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
