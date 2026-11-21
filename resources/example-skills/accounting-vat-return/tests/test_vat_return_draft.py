from __future__ import annotations

import json
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


TEST_SUPPLEMENTAL_FORM_INPUTS = {
    code: {"amount": "0", "source": "synthetic test fixture explicitly confirms zero"}
    for code in vat.FORM_EXTERNAL_INPUTS
}


def build_ready_form_draft(*args, **kwargs):
    if kwargs.get("form_version"):
        kwargs.setdefault("taxpayer_case", "credit_method_production_business")
        kwargs.setdefault("filing_type", "first")
        kwargs.setdefault("invoice_data_complete", True)
    return vat.build_draft(*args, **kwargs)


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
        draft = build_ready_form_draft(
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
        draft = build_ready_form_draft(
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
        draft = build_ready_form_draft(
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
        draft = build_ready_form_draft(
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
        draft = build_ready_form_draft(source, "0100000001", "2026-08")
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
        draft = build_ready_form_draft(source, "0100000001", "2026-10")
        output = vat.write_draft(draft, self.root / "out.json")
        loaded = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(loaded["records"][0]["invoice_number"], "00017")
        self.assertFalse(loaded["legal_form"]["submission_ready"])
        self.assertEqual(loaded["draft_status"], "draft_ready_unmapped")

    def test_xlsx_source_exports_internal_review_workbook_without_mutation(self) -> None:
        original = self.workbook.read_bytes()
        draft = build_ready_form_draft(
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
        draft = build_ready_form_draft(
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
        draft = build_ready_form_draft(source, "0100000001", "2026-Q4")
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
        draft = build_ready_form_draft(source, "0100000001", "2026-10")
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
        draft = build_ready_form_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )
        field_draft = draft["form_field_draft"]
        self.assertEqual(draft["draft_status"], "draft_ready_partial_form")
        self.assertTrue(field_draft["mapping_complete"])
        self.assertEqual(field_draft["amounts"]["29"], "1000")
        self.assertEqual(field_draft["amounts"]["26"], "300")
        self.assertEqual(field_draft["amounts"]["32a"], "100")
        self.assertEqual(field_draft["amounts"]["32b"], "10")
        self.assertEqual(field_draft["amounts"]["34a"], "70")
        self.assertEqual(field_draft["amounts"]["27"], "1790")
        self.assertEqual(field_draft["amounts"]["28"], "45")
        self.assertEqual(field_draft["amounts"]["34"], "2160")
        self.assertIsNone(field_draft["amounts"]["25"])
        self.assertEqual(field_draft["independent_check"]["status"], "review_required")
        self.assertFalse(draft["legal_form"]["submission_ready"])
        self.assertFalse(draft["legal_form"]["auto_form_selection"])

    def test_form_line_is_never_inferred_from_tax_rate(self) -> None:
        source = self.root / "unmapped-zero-rate.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status\n"
            "2026-08-01,0100000001,0300000001,S1,1,1000,0%,0,1000,Bình thường\n",
            encoding="utf-8",
        )
        draft = build_ready_form_draft(
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
            "2025-05-01,0100000001,0300000001,S1,1,100,không thuộc phạm vi,0,100,Bình thường,34a\n",
            encoding="utf-8",
        )
        draft = build_ready_form_draft(
            source,
            "0100000001",
            "2025-Q2",
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
        draft = build_ready_form_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertEqual(
            draft["form_field_draft"]["mapping_status"], "blocked_applicability_or_legal_review"
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
        draft = build_ready_form_draft(
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
            draft["form_field_draft"]["mapping_status"], "blocked_applicability_or_legal_review"
        )

    def test_form_draft_requires_confirmation_when_sales_are_absent(self) -> None:
        source = self.root / "purchases-only.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0300000001,0100000001,S1,1,100,5%,5,105,Bình thường,23,24\n",
            encoding="utf-8",
        )
        draft = build_ready_form_draft(
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
        draft = build_ready_form_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
            supplemental_form_inputs=TEST_SUPPLEMENTAL_FORM_INPUTS,
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
        draft = build_ready_form_draft(
            source,
            "0100000001",
            "2025-Q2",
            form_version="80/2021/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-tt80.json", "80/2021/TT-BTC"
            ),
            supplemental_form_inputs=TEST_SUPPLEMENTAL_FORM_INPUTS,
        )

        fields = draft["form_field_draft"]
        self.assertTrue(fields["mapping_complete"])
        self.assertEqual(fields["amounts"]["23"], "1000")
        self.assertEqual(fields["amounts"]["23a"], "600")
        self.assertEqual(fields["amounts"]["24"], "80")
        self.assertEqual(fields["amounts"]["24a"], "60")
        self.assertEqual(fields["independent_check"]["status"], "pass")

    def test_purchase_field_without_explicit_mapping_is_not_inferred(self) -> None:
        source = self.root / "unmapped-purchase.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0300000001,0100000001,P1,1,1000,5%,50,1050,Bình thường,,\n"
            "2026-08-02,0100000001,0400000001,S1,2,500,5%,25,525,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = build_ready_form_draft(
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
        self.assertIsNone(fields["amounts"].get("23"))
        self.assertIsNone(fields["amounts"].get("24"))
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
        draft = build_ready_form_draft(
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
        draft = build_ready_form_draft(
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

    def test_default_taxpayer_and_filing_scope_block_form_draft(self) -> None:
        source = self.root / "unconfirmed-scope.csv"
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
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )
        reasons = draft["legal_form"]["applicability_review"]["reasons"]
        self.assertIn("taxpayer_case_not_confirmed_for_01_gtgt", reasons)
        self.assertIn("filing_type_not_confirmed", reasons)
        self.assertEqual(draft["draft_status"], "blocked_review_required")
        self.assertFalse(draft["form_field_draft"]["mapping_complete"])

    def test_form_version_must_match_tax_period(self) -> None:
        source = self.root / "tt89-wrong-period.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-05-01,0100000001,0300000001,S1,1,100,5%,5,105,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = build_ready_form_draft(
            source,
            "0100000001",
            "2026-Q2",
            form_version="89/2026/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )
        self.assertIn(
            "form_version_does_not_match_tax_period",
            draft["legal_form"]["applicability_review"]["reasons"],
        )
        self.assertEqual(draft["draft_status"], "blocked_review_required")

    def test_catalog_and_code_effective_windows_match(self) -> None:
        spec80 = vat._form_version_spec("80/2021/TT-BTC")
        spec89 = vat._form_version_spec("89/2026/TT-BTC")
        self.assertEqual(
            spec80["effective_from"],
            vat.FORM_VERSION_WINDOWS["80/2021/TT-BTC"][0].isoformat(),
        )
        self.assertEqual(
            spec80["effective_through"],
            vat.FORM_VERSION_WINDOWS["80/2021/TT-BTC"][1].isoformat(),
        )
        self.assertEqual(
            spec89["effective_from"],
            vat.FORM_VERSION_WINDOWS["89/2026/TT-BTC"][0].isoformat(),
        )
        overlay_by_instrument = {
            item["instrument"]: item for item in spec80["period_specific_overlays"]
        }
        self.assertEqual(
            overlay_by_instrument["40/2025/TT-BTC"]["effective_from"],
            "2025-07-01",
        )
        self.assertEqual(
            overlay_by_instrument["94/2025/TT-BTC"]["effective_from"],
            "2025-10-14",
        )

    def test_tt94_full_text_review_does_not_block_tt80_form_mapping(self) -> None:
        source = self.root / "tt80-tt94-reviewed.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2025-10-15,0100000001,0300000001,S1,1,100,5%,5,105,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = build_ready_form_draft(
            source,
            "0100000001",
            "2025-Q4",
            form_version="80/2021/TT-BTC",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-tt80-q4.json", "80/2021/TT-BTC"
            ),
        )
        self.assertEqual(draft["legal_form"]["applicability_review"]["status"], "pass")
        self.assertNotIn(
            "tt94_effect_on_01_gtgt_not_verified_for_selected_period",
            draft["legal_form"]["applicability_review"]["reasons"],
        )
        self.assertTrue(draft["form_field_draft"]["mapping_complete"])
        self.assertEqual(draft["legal_form"]["version"], "80/2021/TT-BTC")

    def test_supplementary_filing_is_blocked_until_khbs_flow_exists(self) -> None:
        source = self.root / "supplementary-filing.csv"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-01,0100000001,0300000001,S1,1,100,5%,5,105,Bình thường,30,31\n",
            encoding="utf-8",
        )
        draft = build_ready_form_draft(
            source,
            "0100000001",
            "2026-Q3",
            form_version="89/2026/TT-BTC",
            filing_type="supplementary",
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )
        self.assertIn(
            "supplementary_filing_requires_01_khbs_not_supported",
            draft["legal_form"]["applicability_review"]["reasons"],
        )
        self.assertFalse(draft["legal_form"]["submission_ready"])

    def test_incomplete_invoice_coverage_preserves_unknown_lines(self) -> None:
        source = self.root / "incomplete-coverage.csv"
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
            taxpayer_case="credit_method_production_business",
            filing_type="first",
            invoice_data_complete=False,
            supplemental_form_inputs=TEST_SUPPLEMENTAL_FORM_INPUTS,
            law_watch_report=write_law_watch_report(
                self.root / "law-watch-report.json", "89/2026/TT-BTC"
            ),
        )
        form = draft["form_field_draft"]
        self.assertFalse(form["mapping_complete"])
        self.assertFalse(form["calculation_complete"])
        self.assertEqual(form["amounts"]["30"], "100")
        self.assertIsNone(form["amounts"].get("29"))
        self.assertIn(
            "invoice_data_coverage_not_confirmed_zero_not_assumed",
            [item["code"] for item in form["findings"]],
        )

    def test_conditional_formulas_follow_official_40a_and_41_sign_rules(self) -> None:
        spec = vat._form_version_spec("89/2026/TT-BTC")
        values = {
            "36": vat.Decimal("10"),
            "22": vat.Decimal("0"),
            "37": vat.Decimal("0"),
            "38": vat.Decimal("0"),
            "39a": vat.Decimal("0"),
        }
        self.assertEqual(vat._evaluate_catalog_formula("40a", spec, values), vat.Decimal("10"))
        self.assertIsNone(vat._evaluate_catalog_formula("41", spec, values))
        values["36"] = vat.Decimal("-10")
        self.assertIsNone(vat._evaluate_catalog_formula("40a", spec, values))
        self.assertEqual(vat._evaluate_catalog_formula("41", spec, values), vat.Decimal("-10"))

    def test_supplemental_form_input_requires_amount_and_traceable_source(self) -> None:
        with self.assertRaises(vat.VatDraftError):
            vat._normalize_supplemental_form_inputs({"22": {"amount": "0"}})
        with self.assertRaises(vat.VatDraftError):
            vat._normalize_supplemental_form_inputs(
                {"999": {"amount": "0", "source": "fixture"}}
            )
        amounts, sources = vat._normalize_supplemental_form_inputs(
            {"22": {"amount": "-12", "source": "approved prior-period carry-forward"}}
        )
        self.assertEqual(amounts["22"], vat.Decimal("-12"))
        self.assertEqual(sources["22"], "approved prior-period carry-forward")

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


if __name__ == "__main__":
    unittest.main()
