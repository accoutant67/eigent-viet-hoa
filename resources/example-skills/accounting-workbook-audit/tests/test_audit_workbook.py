from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))

from scripts.audit_workbook import WorkbookAuditError, audit_workbook, main

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def q(name: str) -> str:
    return f"{{{MAIN_NS}}}{name}"


def xml_bytes(element: ET.Element) -> bytes:
    return ET.tostring(element, encoding="utf-8", xml_declaration=True)


def write_demo_workbook(path: Path) -> None:
    strings = [
        "Mã NV",
        "Tên",
        "Số tiền",
        "Công thức",
        "Nguyễn An",
        "00018",
        "Trùng tên",
        "00019",
        "00020",
        "Lỗi",
        "00021",
        "17",
    ]
    string_index = {value: index for index, value in enumerate(strings)}

    shared = ET.Element(q("sst"), {"count": str(len(strings)), "uniqueCount": str(len(strings))})
    for value in strings:
        item = ET.SubElement(shared, q("si"))
        text = ET.SubElement(item, q("t"))
        text.set(f"{{{XML_NS}}}space", "preserve")
        text.text = value

    style_root = ET.Element(q("styleSheet"))
    num_formats = ET.SubElement(style_root, q("numFmts"), {"count": "1"})
    ET.SubElement(num_formats, q("numFmt"), {"numFmtId": "164", "formatCode": "00000"})
    cell_xfs = ET.SubElement(style_root, q("cellXfs"), {"count": "2"})
    ET.SubElement(cell_xfs, q("xf"), {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"})
    ET.SubElement(cell_xfs, q("xf"), {"numFmtId": "164", "fontId": "0", "fillId": "0", "borderId": "0"})

    worksheet = ET.Element(q("worksheet"))
    sheet_data = ET.SubElement(worksheet, q("sheetData"))

    def add_row(number: int, cells: list[tuple]) -> None:
        row = ET.SubElement(sheet_data, q("row"), {"r": str(number)})
        for reference, kind, value, style, formula in cells:
            attributes = {"r": reference}
            if style is not None:
                attributes["s"] = str(style)
            if kind in {"shared", "error"}:
                attributes["t"] = "s" if kind == "shared" else "e"
            elif kind == "inline":
                attributes["t"] = "inlineStr"
            cell = ET.SubElement(row, q("c"), attributes)
            if formula is not None:
                ET.SubElement(cell, q("f")).text = formula
            if kind == "inline":
                inline = ET.SubElement(cell, q("is"))
                ET.SubElement(inline, q("t")).text = value
            elif kind == "shared":
                ET.SubElement(cell, q("v")).text = str(string_index[value])
            elif value is not None:
                ET.SubElement(cell, q("v")).text = str(value)

    add_row(1, [
        ("A1", "shared", "Mã NV", None, None),
        ("B1", "shared", "Tên", None, None),
        ("C1", "shared", "Số tiền", None, None),
        ("D1", "shared", "Công thức", None, None),
    ])
    add_row(2, [
        ("A2", "number", "17", 1, None),
        ("B2", "shared", "Nguyễn An", None, None),
        ("C2", "number", "-1500.5", None, None),
        ("D2", "number", "-1500.5", None, "SUM(C2:C2)"),
    ])
    add_row(3, [
        ("A3", "inline", "17", None, None),
        ("B3", "shared", "Nguyễn An", None, None),
        ("C3", "number", "-1500.5", None, None),
        ("D3", "number", "-1500.5", None, "SUM(C3:C3)"),
    ])
    add_row(4, [
        ("A4", "number", "17", 1, None),
        ("B4", "shared", "Nguyễn An", None, None),
        ("C4", "number", "-1500.5", None, None),
        ("D4", "number", "-1500.5", None, "SUM(C4:C4)"),
    ])
    add_row(5, [
        ("A5", "shared", "00018", None, None),
        ("C5", "number", "0", None, None),
        ("D5", "number", None, None, "SUM(C5:C5)"),
    ])
    add_row(6, [
        ("A6", "shared", "00019", None, None),
        ("B6", "shared", "Trùng tên", None, None),
        ("C6", "number", "0", None, None),
    ])
    add_row(7, [
        ("A7", "shared", "00020", None, None),
        ("B7", "shared", "Trùng tên", None, None),
        ("C7", "number", "0", None, None),
    ])
    add_row(8, [
        ("A8", "shared", "00021", None, None),
        ("B8", "shared", "Lỗi", None, None),
        ("C8", "error", "#VALUE!", None, None),
    ])

    workbook = ET.Element(q("workbook"))
    workbook.set("xmlns:r", DOC_REL_NS)
    sheets = ET.SubElement(workbook, q("sheets"))
    ET.SubElement(sheets, q("sheet"), {
        "name": "Bảng lương",
        "sheetId": "1",
        f"{{{DOC_REL_NS}}}id": "rId1",
        "state": "hidden",
    })
    relationships = ET.Element(f"{{{PKG_REL_NS}}}Relationships")
    ET.SubElement(relationships, f"{{{PKG_REL_NS}}}Relationship", {
        "Id": "rId1",
        "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
        "Target": "worksheets/sheet1.xml",
    })
    content_types = ET.Element("{http://schemas.openxmlformats.org/package/2006/content-types}Types")

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", xml_bytes(content_types))
        archive.writestr("xl/workbook.xml", xml_bytes(workbook))
        archive.writestr("xl/_rels/workbook.xml.rels", xml_bytes(relationships))
        archive.writestr("xl/sharedStrings.xml", xml_bytes(shared))
        archive.writestr("xl/styles.xml", xml_bytes(style_root))
        archive.writestr("xl/worksheets/sheet1.xml", xml_bytes(worksheet))


class WorkbookAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.workbook = self.root / "demo.xlsx"
        write_demo_workbook(self.workbook)

    def test_detects_duplicates_missing_values_formulas_and_excel_errors(self) -> None:
        original = self.workbook.read_bytes()
        report = audit_workbook(
            self.workbook,
            required_columns=["Tên"],
            key_columns=["Mã NV"],
        )
        sheet = report["sheets"][0]

        self.assertEqual(report["status"], "review_required")
        self.assertEqual(report["summary"]["data_row_count"], 7)
        self.assertEqual(sheet["formula_cell_count"], 4)
        self.assertTrue(sheet["hidden"])
        self.assertEqual(
            sheet["findings"]["duplicate_rows"],
            [{"first_row": 2, "duplicate_row": 4}],
        )
        self.assertEqual(
            sheet["findings"]["duplicate_keys"],
            [{"first_row": 2, "duplicate_row": 4, "columns": ["Mã NV"]}],
        )
        self.assertEqual(
            sheet["findings"]["missing_required_values"],
            [{"row": 5, "column": "Tên"}],
        )
        self.assertEqual(
            sheet["findings"]["excel_errors"],
            [{"cell": "C8", "code": "#VALUE!"}],
        )
        self.assertEqual(self.workbook.read_bytes(), original)

    def test_duplicate_names_are_not_treated_as_duplicate_identity(self) -> None:
        report = audit_workbook(self.workbook, key_columns=["Mã NV"])
        duplicate_rows = report["sheets"][0]["findings"]["duplicate_keys"]
        self.assertEqual(len(duplicate_rows), 1)
        self.assertEqual(duplicate_rows[0]["duplicate_row"], 4)
        self.assertNotIn("Trùng tên", json.dumps(report, ensure_ascii=False))
        self.assertNotIn("Nguyễn An", json.dumps(report, ensure_ascii=False))

    def test_missing_part_of_composite_key_does_not_use_partial_key(self) -> None:
        report = audit_workbook(
            self.workbook,
            key_columns=["Mã NV", "CCCD"],
        )
        sheet = report["sheets"][0]
        self.assertEqual(sheet["finding_counts"]["duplicate_keys"], 0)
        self.assertEqual(
            sheet["findings"]["missing_columns"],
            [{"column": "CCCD", "purpose": "key", "reason": "not_found"}],
        )

    def test_missing_headers_are_reported_without_guessing(self) -> None:
        report = audit_workbook(
            self.workbook,
            required_columns=["Mã nhân viên"],
            key_columns=["Mã nhân viên"],
        )
        missing = report["sheets"][0]["findings"]["missing_columns"]
        self.assertEqual(len(missing), 2)
        self.assertEqual({item["reason"] for item in missing}, {"not_found"})

    def test_cli_writes_a_separate_json_report_and_protects_existing_output(self) -> None:
        output = self.root / "demo.audit.json"
        args = [
            str(self.workbook),
            "--output",
            str(output),
            "--required-column",
            "Tên",
        ]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args), 0)
        parsed = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(parsed["tool"], "accounting-workbook-audit")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args), 2)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args + ["--force"]), 0)

    def test_rejects_non_xlsx_input(self) -> None:
        csv_file = self.root / "source.csv"
        csv_file.write_text("A,B\\n1,2\\n", encoding="utf-8")
        with self.assertRaises(WorkbookAuditError):
            audit_workbook(csv_file)

    def test_rejects_unsafe_xml_declarations(self) -> None:
        unsafe = self.root / "unsafe.xlsx"
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr(
                "xl/workbook.xml",
                '<!DOCTYPE workbook [<!ENTITY x "bad">]><workbook/>',
            )
            archive.writestr("xl/_rels/workbook.xml.rels", "<Relationships/>")
        with self.assertRaisesRegex(WorkbookAuditError, "Unsafe XML"):
            audit_workbook(unsafe)

    def test_rejects_utf16_doctype_before_expanding_entities(self) -> None:
        unsafe = self.root / "utf16-unsafe.xlsx"
        workbook_xml = (
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<!DOCTYPE workbook [<!ENTITY x "expanded">]>'
            "<workbook>&x;</workbook>"
        ).encode("utf-16")
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("xl/workbook.xml", workbook_xml)
            archive.writestr("xl/_rels/workbook.xml.rels", b"<Relationships/>")

        with self.assertRaisesRegex(WorkbookAuditError, "Unsafe XML"):
            audit_workbook(unsafe)


if __name__ == "__main__":
    unittest.main()
