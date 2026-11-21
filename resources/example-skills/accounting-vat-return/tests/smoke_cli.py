#!/usr/bin/env python3
"""End-to-end smoke for the synthetic, review-only VAT draft workflow."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "vat_return_draft.py"


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "synthetic-invoices.csv"
        output = root / "draft.json"
        law_watch_report = root / "law-watch-report.json"
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,form_tax_line_code\n"
            "2026-08-12,0100000001,0300000001,AA/26E,00017,1000,5%,50,1050,Bình thường,30,31\n"
            "2026-08-13,0100000002,0100000001,BB/26E,00018,2000,10%,200,2200,Bình thường,23,24\n",
            encoding="utf-8",
        )
        required_sources = [
            "vanban_law_vat_48_2024",
            "vanban_decree_vat_181_2025",
            "vanban_circular_vat_69_2025",
            "vanban_tt89_2026",
            "vanban_tt40_2025_tt80_form_update",
            "vanban_tt94_2025_tt80_update",
            "vanban_tt21_2026_tt80_update",
            "congbao_correction_2551_2026",
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
                "--law-watch-report",
                str(law_watch_report),
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
        assert draft["form_field_draft"]["independent_check"]["status"] == "pass"
        assert draft["legal_form"]["version"] == "89/2026/TT-BTC"
        assert draft["legal_form"]["submission_ready"] is False
        assert draft["legal_form"]["xml_export"] == "NOT_STARTED_SCHEMA_NOT_VERIFIED"
        print(
            "PASS: import -> classify -> validate -> aggregate -> TT89 field draft -> independent check -> JSON export"
        )
        print(
            "INFO: law-watch input is synthetic fixture data, not a live-source result"
        )
        print(
            "BLOCKED as designed: official XLSX output and XML schema are not enabled"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
