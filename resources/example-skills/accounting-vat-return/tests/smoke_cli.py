#!/usr/bin/env python3
"""End-to-end smoke for the synthetic, review-only VAT draft workflow."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from pypdf import PdfReader

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "vat_return_draft.py"


def run_pdf_export(
    source: Path,
    output: Path,
    period: str,
    form_version: str,
    law_watch_report: Path,
    supplemental_form_inputs: Path,
) -> str:
    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(source),
            "--taxpayer-tax-id",
            "0100000001",
            "--taxpayer-name",
            "Eigent Synthetic Co.",
            "--period",
            period,
            "--form-version",
            form_version,
            "--taxpayer-case",
            "credit_method_production_business",
            "--filing-type",
            "first",
            "--invoice-data-complete",
            "--law-watch-report",
            str(law_watch_report),
            "--supplemental-form-inputs",
            str(supplemental_form_inputs),
            "--output",
            str(output),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if run.returncode != 0:
        raise SystemExit(run.stderr or run.stdout)
    reader = PdfReader(output)
    assert len(reader.pages) == 2
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "DỰ THẢO" in text
    assert "CHƯA NỘP" in text
    assert "1000" in text
    return text


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "synthetic-invoices.csv"
        tt80_source = root / "synthetic-invoices-tt80.csv"
        output = root / "draft.json"
        tt80_output = root / "tt80-draft.json"
        tt89_pdf = root / "tt89-draft.pdf"
        tt80_pdf = root / "tt80-draft.pdf"
        review_workbook = root / "review-only.xlsx"
        law_watch_report = root / "law-watch-report.json"
        supplemental_form_inputs = root / "supplemental-form-inputs.json"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-12,0100000001,0300000001,AA/26E,00017,1000,5%,50,1050,Bình thường,30,31\n"
            "2026-08-13,0100000002,0100000001,BB/26E,00018,2000,10%,200,2200,Bình thường,23,24\n",
            encoding="utf-8",
        )
        tt80_source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2025-10-15,0100000001,0300000001,AA/25E,00019,1000,5%,50,1050,Bình thường,30,31\n"
            "2025-10-16,0300000001,0100000001,BB/25E,00020,1000,5%,50,1050,Bình thường,23,24\n",
            encoding="utf-8",
        )
        required_sources = [
            "congbao_tt80_2021",
            "vanban_law_vat_48_2024",
            "vanban_decree_vat_181_2025",
            "vanban_circular_vat_69_2025",
            "vanban_tt89_2026",
            "vanban_tt40_2025_tt80_form_update",
            "vanban_tt94_2025_tt80_update",
            "vanban_tt21_2026_tt80_update",
            "congbao_correction_2551_2026",
            "vanban_tt110_2026",
        ]
        law_watch_report.write_text(
            json.dumps(
                {
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
            ),
            encoding="utf-8",
        )
        supplemental_form_inputs.write_text(
            json.dumps(
                {
                    "22": {"amount": "0", "source": "synthetic fixture confirms zero"},
                    "25": {
                        "amount": "50",
                        "source": "synthetic fixture confirms deductible input VAT",
                    },
                    "37": {"amount": "0", "source": "synthetic fixture confirms zero"},
                    "38": {"amount": "0", "source": "synthetic fixture confirms zero"},
                    "39a": {"amount": "0", "source": "synthetic fixture confirms zero"},
                    "40b": {"amount": "0", "source": "synthetic fixture confirms zero"},
                    "42": {"amount": "0", "source": "synthetic fixture confirms zero"},
                }
            ),
            encoding="utf-8",
        )
        run = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(source),
                "--taxpayer-tax-id",
                "0100000001",
                "--period",
                "2026-Q3",
                "--form-version",
                "89/2026/TT-BTC",
                "--taxpayer-case",
                "credit_method_production_business",
                "--filing-type",
                "first",
                "--invoice-data-complete",
                "--law-watch-report",
                str(law_watch_report),
                "--supplemental-form-inputs",
                str(supplemental_form_inputs),
                "--output",
                str(output),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if run.returncode != 0:
            raise SystemExit(run.stderr or run.stdout)
        draft = json.loads(output.read_text(encoding="utf-8"))
        assert draft["draft_status"] == "draft_ready_for_review"
        assert draft["totals"]["by_direction"]["sales"]["invoice_count"] == 1
        assert draft["totals"]["by_direction"]["purchases"]["invoice_count"] == 1
        assert draft["independent_check"]["status"] == "pass"
        assert draft["form_field_draft"]["amounts"]["30"] == "1000"
        assert draft["form_field_draft"]["amounts"]["31"] == "50"
        assert draft["form_field_draft"]["amounts"]["23"] == "2000"
        assert draft["form_field_draft"]["amounts"]["24"] == "200"
        assert draft["form_field_draft"]["amounts"]["23a"] == "0"
        assert draft["form_field_draft"]["amounts"]["24a"] == "0"
        assert draft["form_field_draft"]["amounts"]["27"] == "1000"
        assert draft["form_field_draft"]["amounts"]["34"] == "1000"
        assert draft["form_field_draft"]["calculation_complete"] is True
        assert draft["form_field_draft"]["amounts"]["40a"] == "0"
        assert draft["form_field_draft"]["amounts"]["41"] == "0"
        assert draft["form_field_draft"]["independent_check"]["status"] == "pass"
        assert draft["legal_form"]["version"] == "89/2026/TT-BTC"
        assert draft["legal_form"]["submission_ready"] is False
        assert draft["legal_form"]["xml_export"] == "NOT_STARTED_SCHEMA_NOT_VERIFIED"
        tt80_run = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(tt80_source),
                "--taxpayer-tax-id",
                "0100000001",
                "--period",
                "2025-Q4",
                "--form-version",
                "80/2021/TT-BTC",
                "--taxpayer-case",
                "credit_method_production_business",
                "--filing-type",
                "first",
                "--invoice-data-complete",
                "--law-watch-report",
                str(law_watch_report),
                "--supplemental-form-inputs",
                str(supplemental_form_inputs),
                "--output",
                str(tt80_output),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if tt80_run.returncode != 0:
            raise SystemExit(tt80_run.stderr or tt80_run.stdout)
        tt80_draft = json.loads(tt80_output.read_text(encoding="utf-8"))
        assert tt80_draft["draft_status"] == "draft_ready_for_review"
        assert tt80_draft["legal_form"]["version"] == "80/2021/TT-BTC"
        assert tt80_draft["legal_form"]["applicability_review"]["status"] == "pass"
        assert tt80_draft["form_field_draft"]["amounts"]["30"] == "1000"
        assert tt80_draft["form_field_draft"]["independent_check"]["status"] == "pass"
        tt80_pdf_text = run_pdf_export(
            tt80_source,
            tt80_pdf,
            "2025-Q4",
            "80/2021/TT-BTC",
            law_watch_report,
            supplemental_form_inputs,
        )
        assert "Xã/phường/đặc khu" in tt80_pdf_text
        run_pdf_export(
            source,
            tt89_pdf,
            "2026-Q3",
            "89/2026/TT-BTC",
            law_watch_report,
            supplemental_form_inputs,
        )
        workbook_run = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(source),
                "--taxpayer-tax-id",
                "0100000001",
                "--period",
                "2026-Q3",
                "--form-version",
                "89/2026/TT-BTC",
                "--taxpayer-case",
                "credit_method_production_business",
                "--filing-type",
                "first",
                "--invoice-data-complete",
                "--law-watch-report",
                str(law_watch_report),
                "--supplemental-form-inputs",
                str(supplemental_form_inputs),
                "--output",
                str(review_workbook),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if workbook_run.returncode != 0:
            raise SystemExit(workbook_run.stderr or workbook_run.stdout)
        with zipfile.ZipFile(review_workbook) as archive:
            assert archive.testzip() is None
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
            invoice_xml = archive.read("xl/worksheets/sheet3.xml").decode("utf-8")
            warning_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
            assert "00_Canh bao" in workbook_xml
            assert "01_Tong hop" in workbook_xml
            assert "02_Hoa don" in workbook_xml
            assert "03_Ngoai le" in workbook_xml
            assert "00017" in invoice_xml
            assert "KHÔNG PHẢI TỜ KHAI CHÍNH THỨC" in warning_xml
            assert "NOT STARTED" in warning_xml
            assert b"<f" not in b"".join(
                archive.read(name)
                for name in archive.namelist()
                if name.endswith(".xml")
            )
        print(
            "PASS: import -> classify -> validate -> aggregate -> TT80/TT89 review drafts -> independent check -> JSON, internal XLSX, and watermarked official-template PDF export"
        )
        print(
            "INFO: law-watch input is synthetic fixture data, not a live-source result"
        )
        print(
            "BLOCKED as designed: official 01/GTGT XLSX export and XML schema remain disabled"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
