"""Safety regression tests for the HTKK XML exporter."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPT_DIR))
from htkk_vat_xml_export import HtkkXmlExportError, export_01_gtgt_xml  # noqa: E402


class HtkkXmlSourceProtectionTests(unittest.TestCase):
    def test_export_refuses_to_overwrite_selected_reference_template(self) -> None:
        template = (
            Path(__file__).resolve().parents[1]
            / "reference"
            / "htkk-5.8.5"
            / "InterfaceTemplates"
            / "xml"
            / "01_GTGT_TT89_xml_309.xml"
        )
        before = template.read_bytes()
        draft = {
            "form_field_draft": {
                "form_number": "01/GTGT",
                "mapping_complete": True,
                "mapping_status": "review_required",
                "amounts": {"23": "0"},
            },
            "legal_form": {"version": "89/2026/TT-BTC"},
            "taxpayer_tax_id": "0123456789",
            "period": {
                "type": "month",
                "start": "2026-07-01",
                "end": "2026-07-31",
            },
        }

        with self.assertRaisesRegex(HtkkXmlExportError, "Refusing to overwrite"):
            export_01_gtgt_xml(draft, template)

        self.assertEqual(template.read_bytes(), before)


    def test_rejects_incomplete_month_or_quarter_bounds(self) -> None:
        """A draft must never label a partial period as a complete filing month/quarter."""
        import tempfile

        draft = {
            "form_field_draft": {
                "form_number": "01/GTGT",
                "mapping_complete": True,
                "mapping_status": "review_required",
                "amounts": {"23": "0"},
            },
            "legal_form": {"version": "89/2026/TT-BTC"},
            "taxpayer_tax_id": "0123456789",
        }
        cases = [
            ("month-start", "month", "2026-07-02", "2026-07-31", "calendar month"),
            ("month-end", "month", "2026-07-01", "2026-07-30", "calendar month"),
            ("month-reversed", "month", "2026-07-31", "2026-07-01", "calendar month"),
            ("quarter-start", "quarter", "2026-07-02", "2026-09-30", "calendar quarter"),
            ("quarter-end", "quarter", "2026-07-01", "2026-09-29", "calendar quarter"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            for name, period_type, start, end, error in cases:
                with self.subTest(case=name):
                    output = Path(folder) / f"{name}.xml"
                    draft["period"] = {
                        "type": period_type, "start": start, "end": end,
                    }
                    with self.assertRaisesRegex(HtkkXmlExportError, error):
                        export_01_gtgt_xml(draft, output)
                    self.assertFalse(output.exists())

    def test_accepts_complete_leap_year_month(self) -> None:
        """February 29 is the correct inclusive month end in a leap year."""
        import tempfile

        draft = {
            "form_field_draft": {
                "form_number": "01/GTGT",
                "mapping_complete": True,
                "mapping_status": "review_required",
                "amounts": {"23": "0"},
            },
            "legal_form": {"version": "89/2026/TT-BTC"},
            "taxpayer_tax_id": "0123456789",
            "period": {
                "type": "month", "start": "2028-02-01", "end": "2028-02-29",
            },
        }
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "leap-year.xml"
            export_01_gtgt_xml(draft, output)
            self.assertTrue(output.exists())
            self.assertIn(b"02/2028", output.read_bytes())


if __name__ == "__main__":
    unittest.main()
