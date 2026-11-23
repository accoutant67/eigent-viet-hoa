from __future__ import annotations

import json
import jsonschema
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

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


def write_law_watch_report(path: Path, version: str) -> Path:
    required_sources = {
        "80/2021/TT-BTC": [
            "congbao_tt80_2021",
            "vanban_tt40_2025_tt80_form_update",
            "vanban_tt94_2025_tt80_update",
            "vanban_tt21_2026_tt80_update",
        ],
        "89/2026/TT-BTC": [
            "vanban_law_vat_48_2024",
            "vanban_decree_vat_181_2025",
            "vanban_circular_vat_69_2025",
            "vanban_tt89_2026",
            "vanban_tt40_2025_tt80_form_update",
            "vanban_tt94_2025_tt80_update",
            "vanban_tt21_2026_tt80_update",
            "congbao_correction_2551_2026",
            "vanban_tt110_2026",
        ],
    }[version]
    report = {
        "fixture_only": True,
        "checked_at": "2099-01-01T00:00:00+00:00",
        "source_accessed": True,
        "listing_entries": 50,
        "proposals": [],
        "approved_period_metadata_unchanged": True,
        "auto_applied": False,
        "official_reference_checks": [
            {"name": name, "status": "pass"} for name in required_sources
        ],
    }
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


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
            draft["legal_form"]["xml_export"], "DRAFT_EXPORT_IMPLEMENTED_HTKK_IMPORT_UNVERIFIED"
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

    def test_xlsx_source_exports_internal_review_workbook_without_mutation(self) -> None:
        original = self.workbook.read_bytes()
        draft = vat.build_draft(
            self.workbook, "0100000001", "2026-Q3", sheet_name="HoaDon"
        )
        output = vat.write_draft(draft, self.root / "review-workbook.xlsx")
        self.assertEqual(self.workbook.read_bytes(), original)
        with self.assertRaisesRegex(vat.VatDraftError, "ghi đè"):
            vat.write_draft(draft, self.workbook, force=True)
        self.assertEqual(self.workbook.read_bytes(), original)
        with zipfile.ZipFile(output) as archive:
            self.assertIsNone(archive.testzip())
            xml_parts = [
                name
                for name in archive.namelist()
                if name.endswith(".xml") or name.endswith(".rels")
            ]
            parsed = {name: ET.fromstring(archive.read(name)) for name in xml_parts}
            workbook = parsed["xl/workbook.xml"]
            names = [
                sheet.attrib["name"]
                for sheet in workbook.findall(f"{{{MAIN_NS}}}sheets/{{{MAIN_NS}}}sheet")
            ]
            self.assertEqual(
                names,
                ["00_Canh bao", "01_Tong hop", "02_Hoa don", "03_Ngoai le"],
            )
            all_text = " ".join(
                element.text or ""
                for root in parsed.values()
                for element in root.iter(f"{{{MAIN_NS}}}t")
            )
            self.assertIn("BẢN SOÁT XÉT NỘI BỘ", all_text)
            self.assertIn("không thay thế mẫu 01/GTGT", all_text)
            self.assertIn("00017", all_text)
            self.assertNotIn("<f", " ".join(archive.read(name).decode() for name in xml_parts))
        review = load_workbook(output, read_only=True, data_only=False)
        self.addCleanup(review.close)
        self.assertEqual(
            review.sheetnames,
            ["00_Canh bao", "01_Tong hop", "02_Hoa don", "03_Ngoai le"],
        )
        self.assertEqual(review["02_Hoa don"]["I2"].value, "00017")
        self.assertFalse(
            any(
                cell.data_type == "f"
                for sheet in review.worksheets
                for row in sheet.iter_rows()
                for cell in row
            )
        )
        self.assertFalse(draft["legal_form"]["submission_ready"])

    def test_tt89_form_draft_blocks_when_tt110_source_is_not_verified(self) -> None:
        source = self.root / "tt110-not-verified.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0100000001,0300000001,S1,1,100,5%,5,105,Bình thường,30,31\n",
            encoding="utf-8",
        )
        report_path = write_law_watch_report(
            self.root / "tt110-not-verified.json", "89/2026/TT-BTC"
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["official_reference_checks"] = [
            item
            for item in report["official_reference_checks"]
            if item["name"] != "vanban_tt110_2026"
        ]
        report_path.write_text(json.dumps(report), encoding="utf-8")
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=report_path,
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertEqual(draft["legal_form"]["law_watch_review"]["status"], "blocked")
        self.assertIn(
            "vanban_tt110_2026",
            draft["legal_form"]["law_watch_review"]["unverified_sources"],
        )

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
        self.assertEqual(
            versions["80/2021/TT-BTC"]["verified_purchase_field_relationships"][
                "imported_purchase_value_subset"
            ],
            "23a",
        )
        self.assertEqual(
            versions["89/2026/TT-BTC"]["verified_purchase_field_relationships"][
                "imported_purchase_vat_subset"
            ],
            "24a",
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

    def test_explicit_tt89_lines_keep_categories_distinct_and_recompute_formulas(
        self,
    ) -> None:
        source = self.root / "mapped-tt89.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0100000001,0300000001,S1,1,1000,0%,0,1000,Bình thường,[29],\n"
            "2026-08-02,0100000001,0300000002,S2,2,500,5%,25,525,Bình thường,[30],[31]\n"
            "2026-08-03,0100000001,0300000003,S3,3,200,10%,20,220,Bình thường,[32],[33]\n"
            "2026-08-04,0100000001,0300000004,S4,4,100,không kê khai,0,100,Bình thường,[32a],\n"
            "2026-08-05,0100000001,0300000005,S5,5,10,không tính giá tính thuế,0,10,Bình thường,[32b],\n"
            "2026-08-06,0100000001,0300000006,S6,6,300,không chịu thuế,0,300,Bình thường,[26],\n"
            "2026-08-07,0100000001,0300000007,S7,7,70,ngoài phạm vi,0,70,Bình thường,[34a],\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )
        field_draft = draft["form_field_draft"]
        self.assertEqual(draft["draft_status"], "draft_ready_for_review")
        self.assertTrue(field_draft["mapping_complete"])
        self.assertEqual(field_draft["amounts"]["29"], "1000")
        self.assertEqual(field_draft["amounts"]["26"], "300")
        self.assertEqual(field_draft["amounts"]["32a"], "100")
        self.assertEqual(field_draft["amounts"]["32b"], "10")
        self.assertEqual(field_draft["amounts"]["34a"], "70")
        self.assertEqual(field_draft["amounts"]["32"], "200")
        self.assertEqual(field_draft["amounts"]["33"], "20")
        self.assertEqual(field_draft["amounts"]["27"], "1790")
        self.assertEqual(field_draft["amounts"]["28"], "45")
        self.assertEqual(field_draft["amounts"]["34"], "2160")
        self.assertIsNone(field_draft["amounts"]["22"])
        self.assertIsNone(field_draft["amounts"]["25"])
        self.assertIsNone(field_draft["amounts"]["36"])
        self.assertEqual(field_draft["independent_check"]["status"], "pass")
        self.assertFalse(draft["legal_form"]["submission_ready"])
        self.assertFalse(draft["legal_form"]["auto_form_selection"])

    def test_form_line_is_never_inferred_from_tax_rate(self) -> None:
        source = self.root / "unmapped-zero-rate.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status\n"
            "2026-08-01,0100000001,0300000001,S1,1,1000,0%,0,1000,Bình thường\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-08",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )
        self.assertEqual(draft["draft_status"], "draft_ready_partial_form")
        self.assertEqual(draft["form_field_draft"]["unmapped_sales_rows"], [2])
        self.assertNotIn("29", draft["form_field_draft"]["amounts"])
        self.assertEqual(
            draft["form_field_draft"]["findings"][0]["code"],
            "sales_form_line_mapping_missing",
        )

    def test_form_line_from_new_version_is_rejected_for_tt80(self) -> None:
        source = self.root / "tt80-invalid-line.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code\n"
            "2026-05-01,0100000001,0300000001,S1,1,100,không thuộc phạm vi,0,100,Bình thường,34a\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q2",
            form_version="80/2021/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "80/2021/TT-BTC"
            ),
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertEqual(
            draft["form_field_draft"]["mapping_status"], "blocked_invalid_line"
        )
        self.assertIn(
            "sales_form_line_not_in_selected_version",
            [item["code"] for item in draft["findings"]],
        )

    def test_form_draft_is_blocked_without_law_watch_report(self) -> None:
        source = self.root / "without-law-watch.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code\n"
            "2026-08-01,0100000001,0300000001,S1,1,100,5%,5,105,Bình thường,30\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertEqual(
            draft["form_field_draft"]["mapping_status"], "blocked_legal_review"
        )
        self.assertEqual(
            draft["legal_form"]["law_watch_review"]["reason"],
            "law_watch_report_required_for_form_draft",
        )

    def test_form_draft_is_blocked_when_law_watch_has_new_proposals(self) -> None:
        source = self.root / "proposal-pending.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0100000001,0300000001,S1,1,100,5%,5,105,Bình thường,30,31\n",
            encoding="utf-8",
        )
        report_path = write_law_watch_report(
            self.root / "law-watch-proposal.json", "89/2026/TT-BTC"
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["proposals"] = [{"citation": "999/2099/TT-BTC"}]
        report_path.write_text(json.dumps(report), encoding="utf-8")
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=report_path,
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertIn(
            "new_legal_proposals_require_review",
            draft["legal_form"]["law_watch_review"]["reason_codes"],
        )
        self.assertEqual(
            draft["form_field_draft"]["mapping_status"], "blocked_legal_review"
        )

    def test_form_draft_requires_confirmation_when_sales_are_absent(self) -> None:
        source = self.root / "purchases-only.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0300000001,0100000001,S1,1,100,5%,5,105,Bình thường,23,24\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )
        field_draft = draft["form_field_draft"]
        self.assertFalse(field_draft["mapping_complete"])
        self.assertEqual(field_draft["amounts"]["23"], "100")
        self.assertEqual(field_draft["amounts"]["23a"], "0")
        self.assertEqual(field_draft["amounts"]["24"], "5")
        self.assertEqual(field_draft["amounts"]["24a"], "0")
        self.assertNotIn("23a", field_draft["external_inputs_not_provided"])
        self.assertIn(
            "no_sales_records_for_form_mapping_requires_confirmation",
            [item["code"] for item in field_draft["findings"]],
        )

    def test_purchase_fields_sum_import_subset_into_form_totals(self) -> None:
        source = self.root / "domestic-and-import-purchases.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0300000001,0100000001,D1,1,1000,5%,50,1050,Bình thường,23,24\n"
            "2026-08-02,0300000002,0100000001,I1,2,2000,10%,200,2200,Bình thường,23a,24a\n"
            "2026-08-03,0100000001,0400000001,S1,3,500,5%,25,525,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )

        fields = draft["form_field_draft"]
        self.assertTrue(fields["mapping_complete"])
        self.assertEqual(fields["amounts"]["23"], "3000")
        self.assertEqual(fields["amounts"]["23a"], "2000")
        self.assertEqual(fields["amounts"]["24"], "250")
        self.assertEqual(fields["amounts"]["24a"], "200")
        self.assertEqual(fields["independent_check"]["status"], "pass")

    def test_tt80_purchase_fields_keep_import_subset_in_parent_totals(self) -> None:
        source = self.root / "tt80-purchases.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2025-05-01,0300000001,0100000001,D1,1,400,5%,20,420,Bình thường,23,24\n"
            "2025-05-02,0300000002,0100000001,I1,2,600,10%,60,660,Bình thường,23a,24a\n"
            "2025-05-03,0100000001,0400000001,S1,3,500,5%,25,525,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2025-Q2",
            form_version="80/2021/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-tt80.json", "80/2021/TT-BTC"
            ),
        )

        fields = draft["form_field_draft"]
        self.assertTrue(fields["mapping_complete"])
        self.assertEqual(fields["amounts"]["23"], "1000")
        self.assertEqual(fields["amounts"]["23a"], "600")
        self.assertEqual(fields["amounts"]["24"], "80")
        self.assertEqual(fields["amounts"]["24a"], "60")
        self.assertEqual(fields["amounts"]["26"], "0")
        self.assertEqual(fields["amounts"]["29"], "0")
        self.assertEqual(fields["amounts"]["32"], "0")
        self.assertEqual(fields["amounts"]["32a"], "0")
        self.assertEqual(fields["amounts"]["33"], "0")
        self.assertIsNone(fields["amounts"]["22"])
        self.assertIsNone(fields["amounts"]["25"])
        self.assertIsNone(fields["amounts"]["36"])
        self.assertNotIn("32b", fields["amounts"])
        self.assertNotIn("34a", fields["amounts"])
        self.assertEqual(fields["independent_check"]["status"], "pass")

    def test_purchase_field_without_explicit_mapping_is_not_inferred(self) -> None:
        source = self.root / "unmapped-purchase.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0300000001,0100000001,P1,1,1000,5%,50,1050,Bình thường,,\n"
            "2026-08-02,0100000001,0400000001,S1,2,500,5%,25,525,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )

        fields = draft["form_field_draft"]
        self.assertFalse(fields["mapping_complete"])
        self.assertEqual(fields["unmapped_purchase_rows"], [2])
        self.assertEqual(fields["amounts"]["23"], "0")
        self.assertEqual(fields["amounts"]["24"], "0")
        self.assertIn(
            "purchase_form_line_mapping_missing",
            [item["code"] for item in fields["findings"]],
        )
        self.assertEqual(fields["independent_check"]["status"], "review_required")

    def test_purchase_tax_mapping_must_match_import_subset(self) -> None:
        source = self.root / "mismatched-purchase-tax-line.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0300000001,0100000001,I1,1,1000,5%,50,1050,Bình thường,23a,24\n"
            "2026-08-02,0100000001,0400000001,S1,2,500,5%,25,525,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )

        fields = draft["form_field_draft"]
        self.assertEqual(fields["mapping_status"], "blocked_invalid_line")
        self.assertIn(
            "purchase_form_tax_line_mismatch",
            [item["code"] for item in fields["findings"]],
        )
        self.assertEqual(fields["independent_check"]["status"], "review_required")

    def test_malformed_law_watch_listing_count_blocks_form_draft(self) -> None:
        report_path = write_law_watch_report(
            self.root / "malformed-listing-count.json", "89/2026/TT-BTC"
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["listing_entries"] = "not-a-count"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        source = self.root / "valid-tt89.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0100000001,0300000001,S1,1,100,5%,5,105,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = vat.build_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=report_path,
        )
        self.assertEqual(draft["legal_form"]["law_watch_review"]["status"], "blocked")
        self.assertIn(
            "official_listing_not_accessed",
            draft["legal_form"]["law_watch_review"]["reason_codes"],
        )

    def test_vat_roles_are_unique_and_bound_to_existing_tools(self) -> None:
        roles_path = Path(__file__).resolve().parents[1] / "roles.json"
        roles_data = json.loads(roles_path.read_text(encoding="utf-8"))
        roles = roles_data["roles"]
        identifiers = [role["role_id"] for role in roles]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(
            set(identifiers),
            {
                "HD01",
                "HD02",
                "HD03",
                "HD04",
                "TK01",
                "TK05",
                "BM01",
                "BM02",
                "BM03",
                "PL01",
                "PL02",
                "PL03",
                "PL04",
                "KTT03",
            },
        )
        self.assertEqual(roles_data["agent_registration"], "none")
        self.assertTrue(all(role.get("implementation_status") for role in roles))
        self.assertIn(
            "reuses_existing_skill_report_required",
            next(role for role in roles if role["role_id"] == "PL01")[
                "implementation_status"
            ],
        )


class VatInvoiceXmlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_xml(self, name: str, xml: str) -> Path:
        path = self.root / name
        path.write_text(xml, encoding="utf-8")
        return path

    def invoice(self, extra_tax_subtotal: str = "") -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
 <cbc:ID>INV-001</cbc:ID><cbc:IssueDate>2026-08-12</cbc:IssueDate>
 <cac:AccountingSupplierParty><cac:Party><cac:PartyName><cbc:Name>Seller</cbc:Name></cac:PartyName>
  <cac:PartyTaxScheme><cbc:CompanyID>0300000001</cbc:CompanyID></cac:PartyTaxScheme>
 </cac:Party></cac:AccountingSupplierParty>
 <cac:AccountingCustomerParty><cac:Party><cac:PartyLegalEntity><cbc:RegistrationName>Buyer</cbc:RegistrationName></cac:PartyLegalEntity>
  <cac:PartyTaxScheme><cbc:CompanyID>0100000001</cbc:CompanyID></cac:PartyTaxScheme>
 </cac:Party></cac:AccountingCustomerParty>
 <cac:TaxTotal><cbc:TaxAmount currencyID="VND">50</cbc:TaxAmount>
  <cac:TaxSubtotal><cbc:TaxableAmount currencyID="VND">1000</cbc:TaxableAmount>
   <cbc:TaxAmount currencyID="VND">50</cbc:TaxAmount>
   <cac:TaxCategory><cbc:Percent>5</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
  </cac:TaxSubtotal>{extra_tax_subtotal}
 </cac:TaxTotal><cac:LegalMonetaryTotal><cbc:TaxExclusiveAmount currencyID="VND">1000</cbc:TaxExclusiveAmount><cbc:PayableAmount currencyID="VND">1050</cbc:PayableAmount></cac:LegalMonetaryTotal>
</Invoice>"""

    def test_reads_ubl_invoice_into_existing_normalized_rows(self) -> None:
        source = self.write_xml("synthetic-invoice.xml", self.invoice())
        rows = vat.read_invoice_rows(source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_row"], 1)
        self.assertEqual(rows[0]["raw"]["invoice_number"], "INV-001")
        self.assertEqual(rows[0]["raw"]["invoice_date"], "2026-08-12")
        self.assertEqual(rows[0]["raw"]["seller_tax_id"], "0300000001")
        self.assertEqual(rows[0]["raw"]["buyer_tax_id"], "0100000001")
        self.assertEqual(rows[0]["raw"]["net_amount"], "1000")
        self.assertEqual(rows[0]["raw"]["tax_rate"], "5%")
        self.assertEqual(rows[0]["raw"]["tax_amount"], "50")
        self.assertEqual(rows[0]["raw"]["gross_amount"], "1050")
        self.assertEqual(rows[0]["raw"]["invoice_series"], "")
        self.assertEqual(len(rows[0]["raw"]["source_sha256"]), 64)

    def test_xml_import_flows_into_vat_draft_with_source_trace(self) -> None:
        import hashlib

        source = self.write_xml("synthetic-for-draft.xml", self.invoice())
        draft = vat.build_draft(source, "0100000001", "2026-08")
        record = draft["records"][0]
        self.assertEqual(record["direction"], "purchases")
        self.assertEqual(record["source_trace"]["source_name"], source.name)
        self.assertEqual(
            record["source_trace"]["source_sha256"],
            hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        self.assertIn(
            "missing_required_fields:invoice_series",
            record["review_reasons"],
        )

    def test_reads_multiple_vat_subtotals_without_flattening_tax_breakdown(self) -> None:
        second = """<cac:TaxSubtotal><cbc:TaxableAmount>200</cbc:TaxableAmount>
        <cbc:TaxAmount>20</cbc:TaxAmount><cac:TaxCategory><cbc:Percent>10</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal>"""
        xml = self.invoice(second).replace(
            '<cbc:TaxAmount currencyID="VND">50</cbc:TaxAmount>',
            '<cbc:TaxAmount currencyID="VND">70</cbc:TaxAmount>', 1
        ).replace(
            '<cbc:TaxExclusiveAmount currencyID="VND">1000</cbc:TaxExclusiveAmount>',
            '<cbc:TaxExclusiveAmount currencyID="VND">1200</cbc:TaxExclusiveAmount>'
        ).replace(
            '<cbc:PayableAmount currencyID="VND">1050</cbc:PayableAmount>',
            '<cbc:PayableAmount currencyID="VND">1270</cbc:PayableAmount>'
        )
        source = self.write_xml("synthetic-multirate.xml", xml)
        row = vat.read_invoice_rows(source)[0]["raw"]
        self.assertEqual(row["net_amount"], "1200")
        self.assertEqual(row["tax_amount"], "70")
        self.assertEqual(row["gross_amount"], "1270")
        self.assertEqual(row["tax_rate"], "MULTIPLE")
        self.assertEqual(
            row["tax_breakdown"],
            [
                {"rate_label": "5%", "taxable_amount": "1000", "tax_amount": "50"},
                {"rate_label": "10%", "taxable_amount": "200", "tax_amount": "20"},
            ],
        )
        draft = vat.build_draft(source, "0100000001", "2026-08")
        normalized = draft["records"][0]["normalized_document"]
        schema_path = Path(__file__).resolve().parents[3] / "accounting-data-model" / "v1" / "invoice-record.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(normalized)
        self.assertEqual(len(normalized["tax_breakdown"]), 2)

    def test_extracts_ubl_lines_and_billing_reference(self) -> None:
        line = """<cac:InvoiceLine><cbc:ID>00017</cbc:ID>
        <cbc:InvoicedQuantity unitCode="HOUR">2.500</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="VND">250.125</cbc:LineExtensionAmount>
        <cac:Item><cbc:Description>Dịch vụ kế toán</cbc:Description>
        <cac:ClassifiedTaxCategory><cbc:Percent>5</cbc:Percent></cac:ClassifiedTaxCategory></cac:Item>
        <cac:Price><cbc:PriceAmount currencyID="VND">100.05</cbc:PriceAmount></cac:Price>
        <cac:TaxTotal><cbc:TaxAmount currencyID="VND">12.50625</cbc:TaxAmount>
        <cac:TaxSubtotal><cac:TaxCategory><cbc:Percent>5</cbc:Percent></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>
        </cac:InvoiceLine>"""
        xml = self.invoice().replace("</Invoice>", line + """
        <cac:BillingReference><cac:InvoiceDocumentReference>
        <cbc:ID>00009</cbc:ID><cbc:IssueDate>2026-07-01</cbc:IssueDate>
        </cac:InvoiceDocumentReference></cac:BillingReference></Invoice>""")
        source = self.write_xml("synthetic-line-reference.xml", xml)
        draft = vat.build_draft(source, "0100000001", "2026-08")
        normalized = draft["records"][0]["normalized_document"]
        self.assertEqual(normalized["line_items"]["extraction_status"], "complete")
        line_record = normalized["line_items"]["items"][0]
        self.assertEqual(line_record["source_line_id"], "00017")
        self.assertEqual(line_record["quantity"], "2.5")
        self.assertEqual(line_record["unit_price"], "100.05")
        self.assertEqual(line_record["net_amount"], "250.125")
        self.assertEqual(line_record["tax_rate_label"], "5%")
        self.assertEqual(line_record["tax_amount"], "12.50625")
        self.assertEqual(line_record["description"], "Dịch vụ kế toán")
        self.assertEqual(normalized["relationships"]["references"][0]["identifier"], "00009")

    def test_missing_document_totals_remain_missing_and_are_held(self) -> None:
        xml = self.invoice().replace(
            '<cbc:TaxExclusiveAmount currencyID="VND">1000</cbc:TaxExclusiveAmount>', ''
        ).replace('<cbc:TaxAmount currencyID="VND">50</cbc:TaxAmount>', '', 1)
        source = self.write_xml("synthetic-missing-document-totals.xml", xml)
        raw = vat.read_invoice_rows(source)[0]["raw"]
        self.assertEqual(raw["net_amount"], "")
        self.assertEqual(raw["tax_amount"], "")
        draft = vat.build_draft(source, "0100000001", "2026-08")
        record = draft["records"][0]
        self.assertFalse(record["eligible_for_draft_totals"])
        self.assertIn("invalid_net_amount", record["review_reasons"])
        self.assertIn("invalid_tax_amount", record["review_reasons"])

    def test_rejects_xml_with_unverified_root_namespace(self) -> None:
        source = self.write_xml(
            "not-ubl.xml", '<Invoice><ID>1</ID></Invoice>'
        )
        with self.assertRaisesRegex(vat.VatDraftError, "UNSUPPORTED_PROFILE"):
            vat.read_invoice_rows(source)

    def test_mixed_invoice_import_does_not_change_source_bytes(self) -> None:
        source = self.write_xml("immutable-source.xml", self.invoice())
        before = source.read_bytes()
        vat.read_invoice_rows(source)
        self.assertEqual(source.read_bytes(), before)

    def test_rejects_dtd_and_entity_xml(self) -> None:
        source = self.write_xml(
            "synthetic-unsafe.xml",
            '<!DOCTYPE Invoice [<!ENTITY x "boom">]><Invoice>&x;</Invoice>',
        )
        with self.assertRaisesRegex(vat.VatDraftError, "DTD/entity"):
            vat.read_invoice_rows(source)

    def test_rejects_malformed_and_unsupported_documents(self) -> None:
        malformed = self.write_xml("synthetic-malformed.xml", "<Invoice>")
        unsupported = self.write_xml("synthetic-unsupported.xml", "<CreditNote/>")
        with self.assertRaisesRegex(vat.VatDraftError, "sai cú pháp"):
            vat.read_invoice_rows(malformed)
        with self.assertRaisesRegex(vat.VatDraftError, "UNSUPPORTED_PROFILE"):
            vat.read_invoice_rows(unsupported)

    def test_normalized_invoice_uses_shared_schema_and_preserves_source_values(self) -> None:
        schema_path = (
            Path(__file__).resolve().parents[3]
            / "accounting-data-model"
            / "v1"
            / "invoice-record.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        source = self.write_xml(
            "synthetic-leading-zero.xml",
            self.invoice().replace("<cbc:ID>INV-001</cbc:ID>", "<cbc:ID>00017</cbc:ID>"),
        )
        draft = vat.build_draft(source, "0100000001", "2026-08")
        normalized = draft["records"][0]["normalized_document"]
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(normalized))
        self.assertEqual(errors, [])
        self.assertEqual(normalized["identifier"]["number"], "00017")
        self.assertEqual(normalized["parties"]["buyer"]["tax_id"], "0100000001")
        self.assertEqual(normalized["amounts"]["net"], "1000")
        self.assertEqual(
            normalized["source"]["sha256"],
            vat.hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            normalized["source"]["parser_profile"],
            "oasis-ubl-2-invoice-vat-v2",
        )
        self.assertEqual(normalized["line_items"]["extraction_status"], "not_extracted")
        self.assertEqual(normalized["relationships"]["extraction_status"], "not_extracted")
        self.assertNotIn("references", normalized["relationships"])

    def test_credit_note_is_marked_for_review_and_not_assumed_original(self) -> None:
        xml = self.invoice().replace(
            "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
            "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
        ).replace("<Invoice ", "<CreditNote ", 1).replace(
            "</Invoice>", "</CreditNote>"
        )
        source = self.write_xml("synthetic-credit-note.xml", xml)
        row = vat.read_invoice_rows(source)[0]
        self.assertEqual(row["raw"]["status"], "adjusted")


if __name__ == "__main__":
    unittest.main()


class HtkkVatXmlExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def _draft(self, period: str, version: str) -> dict:
        source = self.root / "mapped.csv"
        invoice_date = "2025-05-12" if period.endswith("Q2") else "2026-10-12"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            f"{invoice_date},0100000001,0300000001,S1,00017,1000,5%,50,1050,Bình thường,30,31\n"
            f"{invoice_date},0300000002,0100000001,P1,00018,2000,10%,200,2200,Bình thường,23,24\n",
            encoding="utf-8",
        )
        law = write_law_watch_report(self.root / "law.json", version)
        return vat.build_draft(
            source, "0100000001", period, form_version=version, law_watch_report=law
        )

    @staticmethod
    def _shape(node: ET.Element) -> tuple:
        return (node.tag, tuple(node.attrib), tuple(HtkkVatXmlExportTests._shape(c) for c in list(node)))

    def test_tt89_month_roundtrip_matches_sample_and_preserves_zeroes_and_whole_vnd(self) -> None:
        draft = self._draft("2026-10", "89/2026/TT-BTC")
        output = vat.write_draft(draft, self.root / "return.xml")
        reference = Path(__file__).resolve().parents[1] / "reference/htkk-5.8.5/InterfaceTemplates/xml/01_GTGT_TT89_xml_309.xml"
        template = ET.parse(reference).getroot()
        generated = ET.parse(output).getroot()
        self.assertEqual(self._shape(generated), self._shape(template))
        cycle = generated.find("./HSoKhaiThue/TTinChung/TTinTKhaiThue/TKhaiThue/KyKKhaiThue")
        self.assertEqual(cycle.findtext("kieuKy"), "M")
        self.assertEqual(cycle.findtext("kyKKhai"), "10/2026")
        self.assertEqual(cycle.findtext("kyKKhaiTuThang"), "10/2026")
        self.assertEqual(generated.findtext("./HSoKhaiThue/TTinChung/TTinTKhaiThue/NNT/mst"), "0100000001")
        self.assertEqual(generated.findtext("./HSoKhaiThue/CTieuTKhaiChinh/HHDVBRaChiuTSuat5/ct30"), "1000")
        self.assertEqual(generated.findtext("./HSoKhaiThue/CTieuTKhaiChinh/HHDVBRaChiuTSuat5/ct31"), "50")
        self.assertFalse(draft["legal_form"]["submission_ready"])

    def test_tt80_quarter_uses_its_template_and_quarter_period_fields(self) -> None:
        draft = self._draft("2025-Q2", "80/2021/TT-BTC")
        generated = ET.parse(vat.write_draft(draft, self.root / "return-tt80.xml")).getroot()
        cycle = generated.find("./HSoKhaiThue/TTinChung/TTinTKhaiThue/TKhaiThue/KyKKhaiThue")
        self.assertEqual(cycle.findtext("kieuKy"), "Q")
        self.assertEqual(cycle.findtext("kyKKhai"), "Q2/2025")
        self.assertEqual(cycle.findtext("kyKKhaiTuNgay"), "01/04/2025")
        self.assertEqual(cycle.findtext("kyKKhaiDenNgay"), "30/06/2025")
        self.assertIsNotNone(generated.find("./HSoKhaiThue/CTieuTKhaiChinh/Header/DiaChiHDSXKDKhacTinhNDTSC/ct11b_quanHuyen_ma"))

    def test_xml_export_rejects_incomplete_mapping_and_wrong_version_lines(self) -> None:
        draft = self._draft("2026-10", "89/2026/TT-BTC")
        draft["form_field_draft"]["mapping_complete"] = False
        with self.assertRaisesRegex(ValueError, "complete, non-blocked"):
            vat.write_draft(draft, self.root / "incomplete.xml")
        draft = self._draft("2025-Q2", "80/2021/TT-BTC")
        draft["form_field_draft"]["amounts"]["34a"] = "1"
        with self.assertRaisesRegex(ValueError, "absent from HTKK template"):
            vat.write_draft(draft, self.root / "wrong-version.xml")

    def test_xml_export_rejects_fractional_vnd_without_rounding(self) -> None:
        draft = self._draft("2026-10", "89/2026/TT-BTC")
        draft["form_field_draft"]["amounts"]["30"] = "1000.25"
        output = self.root / "fractional.xml"
        with self.assertRaisesRegex(ValueError, "whole-VND.*without rounding"):
            vat.write_draft(draft, output)
        self.assertFalse(output.exists())

    def test_xml_export_rejects_negative_nonnegative_indicator(self) -> None:
        draft = self._draft("2026-10", "89/2026/TT-BTC")
        draft["form_field_draft"]["amounts"]["40"] = "-1"
        output = self.root / "negative.xml"
        with self.assertRaisesRegex(ValueError, "must be non-negative"):
            vat.write_draft(draft, output)
        self.assertFalse(output.exists())

    def test_xml_export_refuses_to_overwrite_source(self) -> None:
        draft = self._draft("2026-10", "89/2026/TT-BTC")
        source = self.root / "mapped.csv"
        original = source.read_bytes()
        with self.assertRaisesRegex(vat.VatDraftError, "ghi đè"):
            vat.write_draft(draft, source, force=True)
        self.assertEqual(source.read_bytes(), original)
