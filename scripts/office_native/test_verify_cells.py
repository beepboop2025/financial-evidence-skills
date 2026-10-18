"""Checks that the acceptance comparator detects corruption, not just readability."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

from openpyxl import load_workbook
from verify_cells import verify


class CellAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        subprocess.run(["node", str(Path(__file__).resolve().parents[1] / "create_office_fixtures.cjs"), str(cls.root)], check=True)
        cls.expected = json.loads((cls.root / "expected.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_source_workbooks_match_every_cell(self):
        for suffix in ("xlsx", "ods"):
            with self.subTest(suffix=suffix):
                self.assertEqual(verify(self.root / ("review." + suffix), self.expected), 260)

    def test_missing_and_zero_are_distinct(self):
        expected = copy.deepcopy(self.expected)
        expected[0]["rows"][0][0] = 0
        for suffix in ("xlsx", "ods"):
            with self.subTest(suffix=suffix), self.assertRaises(AssertionError):
                verify(self.root / ("review." + suffix), expected)

    def test_native_formula_is_rejected(self):
        book = load_workbook(self.root / "review.xlsx")
        book.worksheets[0]["A1"] = "=2+3"
        path = self.root / "formula.xlsx"
        book.save(path)
        with self.assertRaisesRegex(AssertionError, "unexpected formula"):
            verify(path, self.expected)

    def test_boolean_cannot_silently_become_number(self):
        expected = copy.deepcopy(self.expected)
        found = False
        for sheet in expected:
            for row in sheet["rows"]:
                for index, value in enumerate(row):
                    if type(value) is bool:
                        row[index] = int(value)
                        found = True
        self.assertTrue(found)
        for suffix in ("xlsx", "ods"):
            with self.subTest(suffix=suffix), self.assertRaises(AssertionError):
                verify(self.root / ("review." + suffix), expected)

    def test_odf_accepts_all_xml_boolean_lexical_forms(self):
        # XML Schema boolean permits true/false and 1/0; ONLYOFFICE uses 1/0.
        path = self.root / "boolean-lexical.ods"
        with ZipFile(self.root / "review.ods") as source, ZipFile(path, "w") as target:
            for name in source.namelist():
                data = source.read(name)
                if name == "content.xml":
                    data = data.replace(b'office:boolean-value="true"', b'office:boolean-value="1"').replace(b'office:boolean-value="false"', b'office:boolean-value="0"')
                target.writestr(name, data)
        self.assertEqual(verify(path, self.expected), 260)


if __name__ == "__main__":
    unittest.main()
