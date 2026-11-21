from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import vat_return_draft as vat


def valid_draft(version: str, period: str) -> dict:
    return {
        "draft_status": "draft_ready_partial_form",
        "source_file": "synthetic.csv",
        "input_format": "csv",
        "taxpayer_tax_id": "0100000001",
        "taxpayer_name": "Công ty thử nghiệm",
        "period": {"label": period},
        "findings": [],
        "legal_form": {
            "version": version,
            "status": "APPLICABILITY_AND_LAW_REVIEW_PASS_FOR_INTERNAL_DRAFT",
            "submission_ready": False,
            "applicability_review": {"status": "pass", "filing_type": "first"},
            "law_watch_review": {"status": "pass"},
        },
        "form_field_draft": {
            "mapping_status": "partial_inputs",
            "submission_ready": False,
            "amounts": {
                "22": "0",
                "23": "2000",
                "24": "200",
                "25": "150",
                "30": "1000",
                "31": "50",
                "32b": None,
                "34a": None,
                "40a": "0",
                "40b": None,
                "43": None,
            },
        },
    }


class VatReturnPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_tt80_after_tt40_exports_two_page_watermarked_pdf(self) -> None:
        output = self.root / "tt80-2025-q3.pdf"
        draft = valid_draft("80/2021/TT-BTC", "2025-Q3")
        vat.write_draft(draft, output)

        reader = PdfReader(output)
        self.assertEqual(len(reader.pages), 2)
        page_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        page_two_text = reader.pages[1].extract_text() or ""
        self.assertIn("DỰ THẢO", page_text)
        self.assertIn("CHƯA KÝ", page_text)
        self.assertIn("Quý 3 năm 2025", page_text)
        self.assertIn("Xã/phường/đặc khu", page_text)
        self.assertIn("xã/phường/đặc khu", page_two_text)
        self.assertIn("2000", page_text)
        self.assertEqual(reader.metadata.title, "Dự thảo 01/GTGT — Quý 3 năm 2025")

    def test_tt80_pre_tt40_does_not_apply_new_address_label(self) -> None:
        output = self.root / "tt80-2025-q2.pdf"
        vat.write_draft(valid_draft("80/2021/TT-BTC", "2025-Q2"), output)
        page_text = PdfReader(output).pages[0].extract_text() or ""
        self.assertNotIn("Xã/phường/đặc khu", page_text)
        self.assertIn("Quý 2 năm 2025", page_text)

    def test_tt89_exports_values_and_keeps_missing_values_blank(self) -> None:
        output = self.root / "tt89-2026-q3.pdf"
        vat.write_draft(valid_draft("89/2026/TT-BTC", "2026-Q3"), output)
        reader = PdfReader(output)
        self.assertEqual(len(reader.pages), 2)
        first_page = reader.pages[0].extract_text() or ""
        second_page = reader.pages[1].extract_text() or ""
        self.assertIn("Công ty thử nghiệm", first_page)
        self.assertIn("Quý 3 năm 2026", first_page)
        self.assertIn("2000", first_page)
        self.assertIn("CHƯA NỘP", second_page)
        self.assertNotIn("None", first_page + second_page)

    def test_tt89_monthly_export_maps_new_fields(self) -> None:
        output = self.root / "tt89-2026-07.pdf"
        draft = valid_draft("89/2026/TT-BTC", "2026-07")
        draft["form_field_draft"]["amounts"].update({"32b": "75", "34a": "25"})
        vat.write_draft(draft, output)
        reader = PdfReader(output)
        self.assertEqual(len(reader.pages), 2)
        first_page = reader.pages[0].extract_text() or ""
        self.assertIn("Tháng 07 năm 2026", first_page)
        self.assertIn("75", first_page)
        self.assertIn("25", first_page)

    def test_pdf_export_blocks_wrong_period_or_blocking_finding(self) -> None:
        wrong_period = valid_draft("80/2021/TT-BTC", "2026-Q3")
        with self.assertRaisesRegex(vat.VatDraftError, "ngoài thời gian"):
            vat.write_draft(wrong_period, self.root / "wrong-period.pdf")

        blocked = valid_draft("89/2026/TT-BTC", "2026-Q3")
        blocked["findings"] = [{"severity": "block", "code": "test_block"}]
        with self.assertRaisesRegex(vat.VatDraftError, "mức chặn"):
            vat.write_draft(blocked, self.root / "blocked.pdf")

    def test_pdf_export_requires_passed_legal_review(self) -> None:
        blocked = valid_draft("89/2026/TT-BTC", "2026-Q3")
        blocked["legal_form"]["status"] = "BLOCKED_APPLICABILITY_OR_LEGAL_REVIEW"
        with self.assertRaisesRegex(vat.VatDraftError, "Rà soát phạm vi"):
            vat.write_draft(blocked, self.root / "blocked-review.pdf")


if __name__ == "__main__":
    unittest.main()
