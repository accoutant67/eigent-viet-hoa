#!/usr/bin/env python3
"""Generate synthetic HTKK 01/GTGT demos through the existing VAT CLI/exporter."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "vat_return_draft.py"
TEMPLATE = SKILL_ROOT / "reference" / "htkk-5.8.5" / "InterfaceTemplates" / "xml" / "01_GTGT_TT89_xml_309.xml"
SCHEMA = SKILL_ROOT / "reference" / "htkk-5.8.5" / "InterfaceTemplates" / "Validate" / "01_GTGT_TT89_309.xsd"
VERSION = "89/2026/TT-BTC"
TAX_ID = "0000000000"  # syntactically shaped test-only placeholder; not a real taxpayer ID


def _law_watch_report(path: Path) -> None:
    sources = [
        "vanban_law_vat_48_2024", "vanban_decree_vat_181_2025",
        "vanban_circular_vat_69_2025", "vanban_tt89_2026",
        "vanban_tt40_2025_tt80_form_update", "vanban_tt94_2025_tt80_update",
        "vanban_tt21_2026_tt80_update", "congbao_correction_2551_2026",
        "vanban_tt110_2026",
    ]
    path.write_text(json.dumps({
        "fixture_only": True,
        "checked_at": "2099-01-01T00:00:00+00:00",
        "source_accessed": True,
        "listing_entries": 50,
        "proposals": [],
        "approved_period_metadata_unchanged": True,
        "auto_applied": False,
        "official_reference_checks": [{"name": name, "status": "pass"} for name in sources],
    }), encoding="utf-8")


def _invoice_csv(path: Path) -> None:
    header = (
        "invoice_date,seller_tax_id,buyer_tax_id,invoice_series,invoice_number,"
        "net_amount,tax_rate,tax_amount,gross_amount,status,form_line_code,"
        "form_tax_line_code\n"
    )
    rows: list[str] = []
    for month in (7, 8, 9):
        date = f"2026-{month:02d}-12"
        rows.append(
            f"{date},0000000001,{TAX_ID},P{month:02d}/26,{month:02d}017,"
            "2000,10%,200,2200,Bình thường,23,24\n"
        )
        rows.append(
            f"{date},{TAX_ID},0000000002,S{month:02d}/26,{month:02d}018,"
            "1000,5%,50,1050,Bình thường,30,31\n"
        )
    path.write_text(header + "".join(rows), encoding="utf-8")


def _run_cli(source: Path, law_report: Path, period: str, output: Path) -> None:
    run = subprocess.run(
        [
            sys.executable, str(SCRIPT), str(source),
            "--taxpayer-tax-id", TAX_ID,
            "--period", period,
            "--form-version", VERSION,
            "--law-watch-report", str(law_report),
            "--output", str(output),
        ],
        capture_output=True, check=False, text=True,
    )
    if run.returncode != 0:
        raise RuntimeError(run.stderr or run.stdout or f"VAT CLI failed for {period}")


def _integer(value: object, label: str) -> int:
    text = str(value)
    if not text or not text.lstrip("-").isdigit():
        raise AssertionError(f"{label} is not an integer VND amount: {text!r}")
    return int(text)


def _verify_case(
    output: Path, reference_root: ET.Element, draft: dict[str, object],
    *, period_type: str, period_value: str,
) -> dict[str, object]:
    root = ET.parse(output).getroot()
    if root.tag != "HSoThueDTu":
        raise AssertionError(f"Unexpected XML root: {root.tag}")
    if [node.tag for node in root.iter()] != [node.tag for node in reference_root.iter()]:
        raise AssertionError("Output element tree differs from the selected HTKK TT89 template")
    if root.tag.startswith("{"):
        raise AssertionError("Output namespace differs from the unqualified HTKK sample")
    form = root.find("./HSoKhaiThue/TTinChung/TTinTKhaiThue/TKhaiThue")
    if form is None or form.findtext("maTKhai") != "01/GTGT":
        raise AssertionError("Form number is missing or incorrect")
    if form.findtext("tenTKhai") != "Tờ khai thuế giá trị gia tăng":
        raise AssertionError("Vietnamese form label was not preserved")
    cycle = form.find("KyKKhaiThue")
    if cycle is None or cycle.findtext("kieuKy") != period_type or cycle.findtext("kyKKhai") != period_value:
        raise AssertionError("Filing period is incorrect")
    if root.findtext("./HSoKhaiThue/TTinChung/TTinTKhaiThue/NNT/mst") != TAX_ID:
        raise AssertionError("Synthetic taxpayer ID or leading zeroes were lost")

    form_draft = draft["form_field_draft"]
    amounts = form_draft["amounts"]
    for code, value in amounts.items():
        if value is None:
            continue
        node = root.find(f"./HSoKhaiThue/CTieuTKhaiChinh//ct{code}")
        if node is None or node.text != str(value):
            raise AssertionError(f"Indicator [{code}] does not round-trip to XML")
        _integer(value, f"Indicator [{code}]")

    formulae = {
        "27": ({"29", "30", "32", "32a", "32b"}, lambda a: a["29"] + a["30"] + a["32"] + a["32a"] - a["32b"]),
        "28": ({"31", "33"}, lambda a: a["31"] + a["33"]),
        "34": ({"26", "27", "34a"}, lambda a: a["26"] + a["27"] + a["34a"]),
        "35": ({"28"}, lambda a: a["28"]),
    }
    formula_checks: dict[str, str] = {}
    for code, (dependencies, formula) in formulae.items():
        if code not in amounts or not dependencies.issubset(amounts):
            formula_checks[code] = "NEEDS_REVIEW: required source indicators are incomplete"
            continue
        values = {key: _integer(amounts[key], f"Indicator [{key}]") for key in dependencies}
        if _integer(amounts[code], f"Indicator [{code}]") != formula(values):
            raise AssertionError(f"Formula check failed for [{code}]")
        formula_checks[code] = "PASS"

    if not form_draft["mapping_complete"] or form_draft["independent_check"]["status"] != "pass":
        raise AssertionError("Selected synthetic case has incomplete mapping or failed independent check")
    return {
        "file": output.name, "bytes": output.stat().st_size,
        "period_type": period_type, "period": period_value,
        "taxpayer_tax_id": TAX_ID, "taxpayer_tax_id_is_synthetic": True,
        "draft_record_count": len(draft["records"]), "root": root.tag, "namespace": "(none)",
        "template_element_tree": "PASS", "parse_round_trip": "PASS",
        "form_number": "01/GTGT", "form_label_unicode": "PASS",
        "integer_amounts_round_trip": "PASS", "formula_checks": formula_checks,
        "independent_vat_check": "PASS", "submission_ready": False,
    }


def generate(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE.is_file() or not SCHEMA.is_file():
        raise FileNotFoundError("HTKK TT89 template or related validation XSD is missing")
    template_hash_before = hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
    reference_root = ET.parse(TEMPLATE).getroot()
    schema_root = ET.parse(SCHEMA).getroot()
    schema_namespace = schema_root.attrib.get("targetNamespace", "")
    root_namespace = reference_root.tag.partition("}")[0].lstrip("{") if "}" in reference_root.tag else ""
    if not schema_namespace or schema_namespace == root_namespace:
        raise AssertionError("The recorded XSD mismatch must be re-evaluated against this sample")

    with tempfile.TemporaryDirectory(prefix="htkk-vat-demo-") as temporary:
        work = Path(temporary)
        source = work / "synthetic-invoices.csv"
        law_report = work / "synthetic-law-watch-report.json"
        _invoice_csv(source)
        _law_watch_report(law_report)
        cases = [
            ("month", "2026-07", "M", "07/2026", "01_GTGT_TT89_demo_month_2026-07.xml"),
            ("quarter", "2026-Q3", "Q", "Q3/2026", "01_GTGT_TT89_demo_quarter_2026-Q3.xml"),
        ]
        results = []
        for name, cli_period, cycle, display_period, filename in cases:
            draft_path = work / f"{name}-draft.json"
            xml_path = output_dir / filename
            _run_cli(source, law_report, cli_period, draft_path)
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            if draft["legal_form"]["version"] != VERSION or draft["legal_form"]["submission_ready"] is not False:
                raise AssertionError("Unexpected form version or non-draft status")
            _run_cli(source, law_report, cli_period, xml_path)
            results.append(_verify_case(
                xml_path, reference_root, draft, period_type=cycle,
                period_value=display_period,
            ))

    template_hash_after = hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
    if template_hash_after != template_hash_before:
        raise AssertionError("Bundled HTKK source template changed during export")
    report = {
        "repository_component": "existing accounting-vat-return CLI and HTKK XML exporter",
        "fixture_data": "fully synthetic; no real company or personal information",
        "form_version": VERSION, "reference_template": TEMPLATE.name,
        "reference_template_sha256": template_hash_before, "template_unchanged": True,
        "cases": results,
        "xsd_validation": {
            "status": "BLOCKED", "schema": SCHEMA.name,
            "schema_target_namespace": schema_namespace,
            "instance_root_namespace": root_namespace or "(none)",
            "reason": (
                "The HTKK instance template/exporter use an unqualified HSoThueDTu root, "
                f"while this XSD targets {schema_namespace!r} with qualified elements. "
                "The XSD cannot validate this instance as-is; schema rules were not changed."
            ),
        },
        "htkk_windows_import": "NOT_TESTED",
        "tax_authority_receipt": "OUT_OF_SCOPE", "submission_ready": False,
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "# Synthetic HTKK 01/GTGT demos\n\n"
        "Generated by the existing accounting-vat-return CLI and htkk_vat_xml_export.py "
        "using the selected TT89 template. Values and identifiers are synthetic; the "
        "all-zero MST is a syntax-test placeholder, not a registered taxpayer. These "
        "files are not ready to sign or submit.\n\n"
        "- Monthly: July 2026.\n- Quarterly: Q3/2026.\n"
        "- See report.json for checks and the XSD mismatch.\n"
        "- HTKK Windows re-import has not been tested.\n",
        encoding="utf-8",
    )
    print("PASS: synthetic invoice CSV -> existing VAT CLI -> TT89 monthly and quarterly XML")
    print("PASS: parse, root, period, form, integer values, formulas, template tree")
    print("PASS: source template unchanged")
    print("BLOCKED: applicable XSD validation; namespace mismatch")
    print("NOT TESTED: import into HTKK on Windows")
    return report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    generate(parser.parse_args().output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
