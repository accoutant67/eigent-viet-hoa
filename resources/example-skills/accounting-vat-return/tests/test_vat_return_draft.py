from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import vat_return_draft as vat


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def make_workbook(
    path: Path, *, duplicate: bool = False, formula: bool = False
) -> None:
    def q(tag: str) -> str:
        return f"{{{MAIN_NS}}}{tag}"

    shared_text = [
        "Ngày hóa đơn",
        "MST người bán",
        "Tên người bán",
        "MST người mua",
        "Ký hiệu hóa đơn",
        "Số hóa đơn",
        "Tiền trước thuế",
        "Thuế suất",
        "Tiền thuế",
        "Tổng thanh toán",
        "Trạng thái",
        "2026-08-12",
        "0100000001",
        "Cùng tên NCC",
        "0300000001",
        "AA/26E",
        "5%",
        "Bên mua",
        "0100000002",
        "Bên bán",
        "Bình thường",
    ]
    index = {value: offset for offset, value in enumerate(shared_text)}
    shared = ET.Element(
        q("sst"), {"count": str(len(shared_text)), "uniqueCount": str(len(shared_text))}
    )
    for value in shared_text:
        item = ET.SubElement(shared, q("si"))
        ET.SubElement(item, q("t")).text = value
    worksheet = ET.Element(q("worksheet"))
    data = ET.SubElement(worksheet, q("sheetData"))
    headers = shared_text[:11]
    rows = [
        [
            "2026-08-12",
            "0100000001",
            "Bên mua",
            "0300000001",
            "AA/26E",
            17,
            "1000",
            "5%",
            "50",
            "1050",
            "Bình thường",
        ],
        [
            "2026-08-12",
            "0100000002",
            "Cùng tên NCC",
            "0100000001",
            "AA/26E",
            17,
            "2000",
            "10%",
            "200",
            "2200",
            "Bình thường",
        ],
        [
            "2026-08-12",
            "0100000003",
            "Cùng tên NCC",
            "0100000001",
            "BB/26E",
            22,
            "500",
            "0%",
            "0",
            "500",
            "Bình thường",
        ],
    ]
    if duplicate:
        rows[2][1] = "0100000002"
        rows[2][4] = "AA/26E"
        rows[2][5] = 17
    if formula:
        rows[0][6] = "=500+500"

    def add_row(number: int, values: list[str | int]) -> None:
        row = ET.SubElement(data, q("row"), {"r": str(number)})
        for column, value in enumerate(values):
            letters = chr(ord("A") + column)
            cell = ET.SubElement(row, q("c"), {"r": f"{letters}{number}"})
            if column == 5 and value == 17:
                cell.set("s", "1")
                ET.SubElement(cell, q("v")).text = "17"
            elif isinstance(value, str) and value.startswith("="):
                ET.SubElement(cell, q("f")).text = value[1:]
                ET.SubElement(cell, q("v")).text = "1000"
            elif isinstance(value, str) and value in index:
                cell.set("t", "s")
                ET.SubElement(cell, q("v")).text = str(index[value])
            elif value == "":
                cell.set("t", "inlineStr")
                inline = ET.SubElement(cell, q("is"))
                ET.SubElement(inline, q("t")).text = ""
            else:
                ET.SubElement(cell, q("v")).text = str(value)

    add_row(1, headers)
    for number, values in enumerate(rows, start=2):
        add_row(number, values)
    workbook = ET.Element(q("workbook"))
    workbook.set("xmlns:r", REL_NS)
    sheets = ET.SubElement(workbook, q("sheets"))
    ET.SubElement(
        sheets,
        q("sheet"),
        {"name": "HoaDon", "sheetId": "1", f"{{{REL_NS}}}id": "rId1"},
    )
    relationships = ET.Element(f"{{{PKG_NS}}}Relationships")
    ET.SubElement(
        relationships,
        f"{{{PKG_NS}}}Relationship",
        {
            "Id": "rId1",
            "Type": f"{REL_NS}/worksheet",
            "Target": "worksheets/sheet1.xml",
        },
    )
    style_root = ET.Element(q("styleSheet"))
    num_formats = ET.SubElement(style_root, q("numFmts"), {"count": "1"})
    ET.SubElement(num_formats, q("numFmt"), {"numFmtId": "164", "formatCode": "00000"})
    xfs = ET.SubElement(style_root, q("cellXfs"), {"count": "2"})
    ET.SubElement(
        xfs, q("xf"), {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"}
    )
    ET.SubElement(
        xfs, q("xf"), {"numFmtId": "164", "fontId": "0", "fillId": "0", "borderId": "0"}
    )

    def xml(element: ET.Element) -> bytes:
        return ET.tostring(element, encoding="utf-8", xml_declaration=True)

    content_types = b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("xl/workbook.xml", xml(workbook))
        archive.writestr("xl/_rels/workbook.xml.rels", xml(relationships))
        archive.writestr("xl/sharedStrings.xml", xml(shared))
        archive.writestr("xl/styles.xml", xml(style_root))
        archive.writestr("xl/worksheets/sheet1.xml", xml(worksheet))


class VatReturnDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workbook = self.root / "synthetic-invoices.xlsx"
        make_workbook(self.workbook)

    def test_import_preserves_zero_padded_invoice_number_and_never_matches_names(
        self,
    ) -> None:
        original = self.workbook.read_bytes()
        draft = vat.build_draft(
            self.workbook, "0100000001", "2026-Q3", sheet_name="HoaDon"
        )
        self.assertEqual(self.workbook.read_bytes(), original)
        self.assertEqual(draft["draft_status"], "draft_ready_unmapped")
        self.assertEqual(
            [record["invoice_number"] for record in draft["records"]],
            ["00017", "00017", "22"],
        )
        self.assertEqual(
            [record["direction"] for record in draft["records"]],
            ["sales", "purchases", "purchases"],
        )
        self.assertEqual(
            draft["totals"]["by_direction"]["purchases"]["invoice_count"], 2
        )
        self.assertFalse(draft["findings"])
        self.assertEqual(draft["independent_check"]["status"], "pass")
        self.assertIsNone(draft["legal_form"]["form_number"])
        self.assertFalse(draft["legal_form"]["auto_form_selection"])
        self.assertEqual(
            draft["legal_form"]["status"],
            "OFFICIAL_FORM_SOURCE_VERIFIED; PERIOD_AND_FIELD_EXPORT_MAPPING_REQUIRE_REVIEW",
        )
        self.assertEqual(draft["legal_form"]["verified_versions"][1]["pdf_page"], 241)
        self.assertEqual(
            draft["legal_form"]["xml_export"], "NOT_STARTED_SCHEMA_NOT_VERIFIED"
        )

    def test_xml_reader_rejects_dtd_even_after_large_leading_whitespace(self) -> None:
        payload = (
            b"<?xml version='1.0'?>"
            + b" " * 5000
            + b"<!DOCTYPE root [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>"
            + b"<root>&xxe;</root>"
        )
        with self.assertRaisesRegex(vat.VatDraftError, "Unsafe XML declaration"):
            vat._safe_xml(payload, "fixture.xml")

    def test_duplicate_invoice_identity_is_held_from_totals(self) -> None:
        make_workbook(self.workbook, duplicate=True)
        draft = vat.build_draft(
            self.workbook, "0100000001", "2026-Q3", sheet_name="HoaDon"
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertTrue(
            any(
                item["code"] == "duplicate_invoice_identity"
                for item in draft["findings"]
            )
        )
        self.assertEqual(
            draft["totals"]["by_direction"]["purchases"]["invoice_count"], 0
        )

    def test_formula_inputs_are_not_used_for_draft_totals(self) -> None:
        make_workbook(self.workbook, formula=True)
        draft = vat.build_draft(
            self.workbook, "0100000001", "2026-08", sheet_name="HoaDon"
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertTrue(
            any(
                item["code"] == "formula_values_require_source_review"
                for item in draft["findings"]
            )
        )
        self.assertEqual(draft["totals"]["by_direction"]["sales"]["invoice_count"], 0)

    def test_out_of_period_rows_are_not_silently_included(self) -> None:
        draft = vat.build_draft(
            self.workbook, "0100000001", "2026-07", sheet_name="HoaDon"
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertEqual(draft["totals"]["by_direction"]["sales"]["invoice_count"], 0)
        self.assertTrue(
            any(
                item["code"] == "outside_selected_period_by_invoice_date"
                for item in draft["findings"]
            )
        )

    def test_out_of_period_rows_are_excluded_without_blocking_valid_period_rows(
        self,
    ) -> None:
        source = self.root / "mixed-period.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status\n"
            "2026-08-01,0100000001,0300000001,S1,17,100,5%,5,105,Bình thường\n"
            "2026-07-01,0100000001,0300000001,S1,18,200,5%,10,210,Bình thường\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(source, "0100000001", "2026-08")
        self.assertEqual(draft["draft_status"], "draft_ready_unmapped")
        self.assertEqual(draft["totals"]["by_direction"]["sales"]["invoice_count"], 1)
        self.assertTrue(
            any(
                item["severity"] == "info"
                and item["code"] == "outside_selected_period_by_invoice_date"
                for item in draft["findings"]
            )
        )

    def test_money_parser_handles_vietnamese_thousands_and_decimal_separators(
        self,
    ) -> None:
        self.assertEqual(vat.parse_money("1.000"), vat.Decimal("1000"))
        self.assertEqual(vat.parse_money("1,25"), vat.Decimal("1.25"))
        self.assertEqual(vat.parse_money("1.234.567,89"), vat.Decimal("1234567.89"))

    def test_csv_import_exports_review_only_json(self) -> None:
        source = self.root / "invoice.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status\n"
            "2026-10-01,0100000001,0300000001,S1,00017,100,5%,5,105,Bình thường\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(source, "0100000001", "2026-10")
        output = vat.write_draft(draft, self.root / "out.json")
        loaded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(loaded["records"][0]["invoice_number"], "00017")
        self.assertFalse(loaded["legal_form"]["submission_ready"])
        self.assertEqual(loaded["draft_status"], "draft_ready_unmapped")

    def test_amount_mismatch_blocks_submission_draft_and_checks_month_quarter(
        self,
    ) -> None:
        source = self.root / "bad.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status\n"
            "2026-10-01,0100000001,0300000001,S1,17,100,5%,5,106,Bình thường\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(source, "0100000001", "2026-Q4")
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertTrue(
            any(
                item["code"] == "invoice_amounts_do_not_reconcile"
                for item in draft["findings"]
            )
        )
        self.assertEqual(vat.period_window("2026-02")[0].isoformat(), "2026-02-01")
        self.assertEqual(vat.period_window("2026-Q4")[1].isoformat(), "2026-12-31")

    def test_unknown_or_missing_invoice_status_is_never_silent(self) -> None:
        source = self.root / "status.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status\n"
            "2026-10-01,0100000001,0300000001,S1,17,100,5%,5,105,Chưa rõ\n"
            "2026-10-01,0100000001,0300000001,S1,18,100,5%,5,105,\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(source, "0100000001", "2026-10")
        codes = [finding["code"] for finding in draft["findings"]]
        self.assertIn("invoice_status_unrecognized_requires_manual_treatment", codes)
        self.assertIn("missing_required_fields:status", codes)
        self.assertEqual(draft["totals"]["by_direction"]["sales"]["invoice_count"], 0)

    def test_official_form_catalog_has_verified_candidates_without_auto_selection(
        self,
    ) -> None:
        catalog_path = (
            Path(__file__).resolve().parents[1] / "legal" / "form_catalog.json"
        )
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        form = catalog["filing_form"]
        self.assertEqual(form["form_number"], "01/GTGT")
        self.assertFalse(form["auto_form_selection"])
        versions = {item["instrument"]: item for item in form["versions"]}
        self.assertEqual(versions["89/2026/TT-BTC"]["annex"], "Phụ lục I")
        self.assertEqual(versions["89/2026/TT-BTC"]["verified_form_page"], 241)
        self.assertIn("32b", versions["89/2026/TT-BTC"]["verified_form_items"])
        self.assertEqual(
            versions["80/2021/TT-BTC"]["verified_form_formulas"]["27"],
            "29 + 30 + 32 + 32a",
        )
        self.assertIn(
            "40b <= 40a",
            versions["89/2026/TT-BTC"]["verified_form_constraints"],
        )
        self.assertEqual(
            versions["80/2021/TT-BTC"]["effective_from"],
            "2022-01-01",
        )
        self.assertEqual(
            form["related_annexes"]["status"],
            "official_inventory_identified_applicability_review_required",
        )


if __name__ == "__main__":
    unittest.main()
