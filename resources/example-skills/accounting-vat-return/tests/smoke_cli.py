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
        source.write_text(
            "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,net_amount,tax_rate,tax_amount,gross_amount,status\n"
            "2026-08-12,0100000001,0300000001,AA/26E,00017,1000,5%,50,1050,Bình thường\n"
            "2026-08-13,0100000002,0100000001,BB/26E,00018,2000,10%,200,2200,Bình thường\n",
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
        assert draft["draft_status"] == "draft_ready_unmapped"
        assert draft["totals"]["by_direction"]["sales"]["invoice_count"] == 1
        assert draft["totals"]["by_direction"]["purchases"]["invoice_count"] == 1
        assert draft["independent_check"]["status"] == "pass"
        assert draft["legal_form"]["submission_ready"] is False
        assert draft["legal_form"]["xml_export"] == "NOT_STARTED_SCHEMA_NOT_VERIFIED"
        print(
            "PASS: import -> classify -> validate -> aggregate -> independent check -> JSON draft"
        )
        print(
            "BLOCKED as designed: official form mapping and XML schema are not enabled"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
