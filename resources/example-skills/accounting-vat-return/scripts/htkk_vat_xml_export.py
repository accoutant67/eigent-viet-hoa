"""Draft-only exporter for the supplied HTKK 01/GTGT XML templates."""
from __future__ import annotations

import calendar
import os
import re
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET

_REFERENCE = Path(__file__).resolve().parents[1] / "reference" / "htkk-5.8.5" / "InterfaceTemplates"
_TEMPLATES = {
    "80/2021/TT-BTC": _REFERENCE / "xml" / "01_GTGT_TT80_xml_283.xml",
    "89/2026/TT-BTC": _REFERENCE / "xml" / "01_GTGT_TT89_xml_309.xml",
}
_TIN = re.compile(r"^(?:[0-9]{10}(?:-[0-9]{3})?|[0-9]{12})$")


class HtkkXmlExportError(ValueError):
    """The selected draft cannot be represented by the chosen HTKK template."""


def _node(root: ET.Element, path: str) -> ET.Element:
    node = root.find(path)
    if node is None:
        raise HtkkXmlExportError(f"HTKK template is missing node: {path}")
    return node


def _set(root: ET.Element, path: str, value: str) -> None:
    _node(root, path).text = value


def _valid_quarter_bounds(start: date, end: date) -> bool:
    if start.day != 1 or start.month not in {1, 4, 7, 10}:
        return False
    end_month = start.month + 2
    end_year = start.year
    if end_month > 12:
        end_month -= 12
        end_year += 1
    return end == date(end_year, end_month, calendar.monthrange(end_year, end_month)[1])


def export_01_gtgt_xml(draft: dict[str, Any], destination: str | Path) -> Path:
    """Write a review-only XML draft, preserving the bundled template's element tree."""
    form = draft.get("form_field_draft")
    version = (draft.get("legal_form") or {}).get("version")
    if not isinstance(form, dict) or form.get("form_number") != "01/GTGT":
        raise HtkkXmlExportError("XML 01/GTGT requires an explicitly selected form.")
    if not form.get("mapping_complete") or form.get("mapping_status") != "review_required":
        raise HtkkXmlExportError("XML export requires complete, non-blocked 01/GTGT line mapping.")
    template_path = _TEMPLATES.get(version)
    if template_path is None or not template_path.is_file():
        raise HtkkXmlExportError(f"No bundled HTKK XML template for form version: {version!r}")
    try:
        root = ET.fromstring(
            template_path.read_bytes(),
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )
    except Exception as exc:
        raise HtkkXmlExportError(f"Cannot parse bundled HTKK XML template: {exc}") from exc

    tax_id = str(draft.get("taxpayer_tax_id") or "")
    if not _TIN.fullmatch(tax_id):
        raise HtkkXmlExportError("Missing or invalid taxpayer tax ID; leading zeroes must be preserved.")
    period = draft.get("period") or {}
    try:
        start = date.fromisoformat(str(period["start"]))
        end = date.fromisoformat(str(period["end"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HtkkXmlExportError("Missing or invalid filing-period start/end dates.") from exc
    period_type = period.get("type")
    if period_type == "month":
        if (
            start.day != 1
            or (start.year, start.month) != (end.year, end.month)
            or end.day != calendar.monthrange(start.year, start.month)[1]
        ):
            raise HtkkXmlExportError("Monthly period start/end do not describe one calendar month.")
        cycle_type = "M"
        month_value = f"{start.month:02d}/{start.year:04d}"
        period_value = month_value
        start_date = end_date = ""
        start_month = end_month = month_value
    elif period_type == "quarter":
        if not _valid_quarter_bounds(start, end):
            raise HtkkXmlExportError("Quarter period start/end do not describe one calendar quarter.")
        cycle_type = "Q"
        period_value = f"Q{(start.month - 1) // 3 + 1}/{start.year:04d}"
        start_date = start.strftime("%d/%m/%Y")
        end_date = end.strftime("%d/%m/%Y")
        start_month = end_month = ""
    else:
        raise HtkkXmlExportError("Unsupported filing period; expected one month or one quarter.")

    base = root.find("./HSoKhaiThue/TTinChung/TTinTKhaiThue/TKhaiThue")
    if base is None:
        raise HtkkXmlExportError("HTKK template is missing filing metadata.")
    cycle = _node(base, "KyKKhaiThue")
    for name, value in (
        ("kieuKy", cycle_type),
        ("kyKKhai", period_value),
        ("kyKKhaiTuNgay", start_date),
        ("kyKKhaiDenNgay", end_date),
        ("kyKKhaiTuThang", start_month),
        ("kyKKhaiDenThang", end_month),
    ):
        _set(cycle, name, value)
    _set(base, "maTKhai", "01/GTGT")
    _set(base, "tenTKhai", "Tờ khai thuế giá trị gia tăng")
    _set(root, "./HSoKhaiThue/TTinChung/TTinTKhaiThue/NNT/mst", tax_id)

    main_form = root.find("./HSoKhaiThue/CTieuTKhaiChinh")
    if main_form is None:
        raise HtkkXmlExportError("HTKK template is missing main form indicators.")
    for code, raw_value in (form.get("amounts") or {}).items():
        if raw_value is None:
            continue
        target = main_form.find(f".//ct{code}")
        if target is None:
            raise HtkkXmlExportError(f"Indicator [{code}] is absent from HTKK template version {version}.")
        text = str(raw_value)
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise HtkkXmlExportError(f"Indicator [{code}] is not a decimal amount.") from exc
        if not amount.is_finite():
            raise HtkkXmlExportError(f"Indicator [{code}] must be a finite decimal.")
        if amount != amount.to_integral_value():
            raise HtkkXmlExportError(
                f"Indicator [{code}] must be a whole-VND amount for the HTKK form; "
                "fractional values are rejected without rounding."
            )
        integer_amount = int(amount)
        if not -(2**63) <= integer_amount <= (2**63 - 1):
            raise HtkkXmlExportError(f"Indicator [{code}] is outside the HTKK signed 64-bit range.")
        if code in {"40a", "40", "41"} and integer_amount < 0:
            raise HtkkXmlExportError(f"Indicator [{code}] must be non-negative in the HTKK form.")
        target.text = str(integer_amount)

    output = Path(destination)
    # Never let an output path (including a symlinked path) replace the bundled
    # reference template used to produce this draft.
    if output.resolve() == template_path.resolve():
        raise HtkkXmlExportError("Refusing to overwrite the bundled HTKK source template.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{output.name}.", suffix=".tmp",
            dir=output.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(ET.tostring(root, encoding="utf-8", xml_declaration=True))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
        return output
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
