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


if __name__ == "__main__":
    unittest.main()
