#!/usr/bin/env python3
"""Verify ODS/XLSX using independent readers, optionally real LibreOffice."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--libreoffice", action="store_true")
    args = parser.parse_args()
    expected = json.loads((args.directory / "expected.json").read_text())
    from openpyxl import load_workbook
    from odf.opendocument import load
    from odf.table import Table
    book = load_workbook(args.directory / "review.xlsx", data_only=False)
    assert book.sheetnames == [s["name"] for s in expected]
    for sheet in expected:
        actual = book[sheet["name"]]
        for r, values in enumerate(sheet["rows"], 1):
            for c, value in enumerate(values, 1):
                observed = actual.cell(r, c)
                assert observed.data_type != "f", (sheet["name"], r, c, "unexpected formula")
                assert observed.value == (None if value == "" else value), (sheet["name"], r, c, observed.value, value)
    document = load(str(args.directory / "review.ods"))
    assert [t.getAttribute("name") for t in document.spreadsheet.getElementsByType(Table)] == [s["name"] for s in expected]
    for suffix in ("ods", "xlsx"):
        with ZipFile(args.directory / ("review." + suffix)) as archive:
            assert archive.testzip() is None
            assert not any("vba" in p.lower() or "externallink" in p.lower() for p in archive.namelist())
            if suffix == "ods":
                assert archive.namelist()[0] == "mimetype"
                assert archive.getinfo("mimetype").compress_type == 0
    checks = ["openpyxl_all_cells_and_types", "odfpy_document", "zip_integrity", "no_formulas_or_external_workbook_links"]
    if args.libreoffice:
        executable = shutil.which("libreoffice") or shutil.which("soffice")
        if not executable:
            raise SystemExit("LibreOffice required for native acceptance")
        ns = {"table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0", "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0", "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
        def a(prefix, name):
            return "{" + ns[prefix] + "}" + name
        for suffix in ("ods", "xlsx"):
            out = args.directory / ("native-" + suffix)
            out.mkdir(exist_ok=True)
            profile = (out / "profile").resolve().as_uri()
            subprocess.run([executable, "-env:UserInstallation=" + profile, "--headless", "--convert-to", "fods", "--outdir", str(out), str(args.directory / ("review." + suffix))], check=True, timeout=90, capture_output=True, text=True)
            root = ET.parse(out / "review.fods").getroot()
            tabs = root.findall(".//table:table", ns)
            assert [t.get(a("table", "name")) for t in tabs] == [s["name"] for s in expected]
            for tab, wanted in zip(tabs, expected):
                rows = tab.findall("table:table-row", ns)
                for index, values in enumerate(wanted["rows"]):
                    observed = []
                    for c in rows[index].findall("table:table-cell", ns):
                        formula = c.get(a("table", "formula"))
                        if formula is not None:
                            # Calc represents imported XLSX boolean constants as
                            # TRUE()/FALSE(). Permit only that exact conversion,
                            # in a cell whose original value is the same boolean.
                            original = values[len(observed)] if len(observed) < len(values) else None
                            assert type(original) is bool
                            assert formula == ("of:=TRUE()" if original else "of:=FALSE()")
                        kind = c.get(a("office", "value-type"))
                        if kind == "float":
                            value = float(c.get(a("office", "value")))
                        elif kind == "boolean":
                            value = c.get(a("office", "boolean-value")) == "true"
                        else:
                            value = "\n".join("".join(p.itertext()) for p in c.findall("text:p", ns))
                        repeats = int(c.get(a("table", "number-columns-repeated"), "1"))
                        observed.extend([value] * min(repeats, len(values)))
                    observed = (observed + [""] * len(values))[:len(values)]
                    assert observed == values, (suffix, wanted["name"], index, observed, values)
        checks.extend(["native_libreoffice_ods_all_cells", "native_libreoffice_xlsx_all_cells"])
    receipt = {"schema": "financial-evidence.office-acceptance.v1", "checks": checks, "status": "PASS", "data": "synthetic fixtures; no adoption claim"}
    (args.directory / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
