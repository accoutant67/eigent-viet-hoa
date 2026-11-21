#!/usr/bin/env python3
"""Prepare a review-only VAT return draft from a CSV or .xlsx invoice sheet.

The tool does not determine tax eligibility, apply tax law, write to an input
workbook, populate a legal form, generate XML, sign, or submit a return.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import posixpath
import re
import sys
import tempfile
import unicodedata
import zipfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from defusedxml import DefusedXmlException
from defusedxml import ElementTree as ET

MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DOC_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_CELL_REF = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")
_ZERO_FORMAT = re.compile(r"^0+$")
_DATE_FORMAT = re.compile(r"(?i)(?:y|d)|m{1,4}.*(?:y|d)|(?:y|d).*m{1,4}")

FIELD_ALIASES: dict[str, set[str]] = {
    "invoice_date": {
        "invoice_date",
        "date",
        "ngay_hoa_don",
        "ngay_lap_hoa_don",
        "ngay_chung_tu",
    },
    "seller_tax_id": {
        "seller_tax_id",
        "seller_mst",
        "mst_nguoi_ban",
        "ma_so_thue_nguoi_ban",
        "mst_ben_ban",
    },
    "seller_name": {"seller_name", "ten_nguoi_ban", "ten_don_vi_ban"},
    "buyer_tax_id": {
        "buyer_tax_id",
        "buyer_mst",
        "mst_nguoi_mua",
        "ma_so_thue_nguoi_mua",
        "mst_ben_mua",
    },
    "buyer_name": {"buyer_name", "ten_nguoi_mua", "ten_don_vi_mua"},
    "invoice_series": {
        "invoice_series",
        "series",
        "ky_hieu_hoa_don",
        "ky_hieu_mau_so_hoa_don",
    },
    "invoice_number": {
        "invoice_number",
        "invoice_no",
        "so_hoa_don",
        "so_hoa_don_dien_tu",
    },
    "net_amount": {
        "net_amount",
        "taxable_amount",
        "amount_before_tax",
        "tien_truoc_thue",
        "thanh_tien_chua_thue",
        "cong_tien_hang",
    },
    "tax_rate": {"tax_rate", "vat_rate", "thue_suat", "thue_suat_gtgt"},
    "tax_amount": {"tax_amount", "vat_amount", "tien_thue", "tien_thue_gtgt"},
    "gross_amount": {
        "gross_amount",
        "total_amount",
        "grand_total",
        "tong_thanh_toan",
        "tong_tien_thanh_toan",
        "tong_cong_thanh_toan",
    },
    "status": {"status", "invoice_status", "trang_thai", "tinh_trang_hoa_don"},
    "declared_direction": {"direction", "loai_hoa_don", "mua_vao_ban_ra"},
}
ALIAS_TO_FIELD = {
    alias: field for field, aliases in FIELD_ALIASES.items() for alias in aliases
}
REQUIRED_FIELDS = (
    "invoice_date",
    "seller_tax_id",
    "invoice_series",
    "invoice_number",
    "net_amount",
    "tax_rate",
    "tax_amount",
    "gross_amount",
    "status",
)
HOLD_STATUS = {
    "adjusted",
    "adjustment",
    "replacement",
    "replaced",
    "cancelled",
    "canceled",
    "void",
    "huy",
    "da_huy",
    "thay_the",
    "da_thay_the",
    "dieu_chinh",
    "hoa_don_dieu_chinh",
}
NORMAL_STATUS = {
    "normal",
    "valid",
    "original",
    "goc",
    "binh_thuong",
    "hop_le",
}


class VatDraftError(ValueError):
    """Raised when a source or requested draft cannot be safely processed."""


def normalize_label(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold()).replace("đ", "d")
    plain = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", "_", plain).strip("_")


def _safe_xml(payload: bytes, member: str) -> ET.Element:
    try:
        return ET.fromstring(
            payload,
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )
    except DefusedXmlException as exc:
        raise VatDraftError(
            f"Unsafe XML declaration in workbook member: {member}"
        ) from exc
    except ET.ParseError as exc:
        raise VatDraftError(f"Invalid workbook XML in {member}: {exc}") from exc


def _column_index(reference: str) -> tuple[int, int]:
    match = _CELL_REF.fullmatch(reference.upper())
    if not match:
        raise VatDraftError(f"Unsupported Excel cell reference: {reference}")
    column = 0
    for letter in match.group(1):
        column = column * 26 + ord(letter) - ord("A") + 1
    return column - 1, int(match.group(2))


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = _safe_xml(archive.read("xl/sharedStrings.xml"), "xl/sharedStrings.xml")
    return [
        "".join(node.text or "" for node in item.iter(MAIN_NS + "t"))
        for item in root.findall(MAIN_NS + "si")
    ]


def _style_formats(archive: zipfile.ZipFile) -> list[tuple[int, str]]:
    if "xl/styles.xml" not in archive.namelist():
        return []
    root = _safe_xml(archive.read("xl/styles.xml"), "xl/styles.xml")
    custom: dict[int, str] = {}
    formats = root.find(MAIN_NS + "numFmts")
    if formats is not None:
        for item in formats.findall(MAIN_NS + "numFmt"):
            try:
                custom[int(item.attrib.get("numFmtId", ""))] = item.attrib.get(
                    "formatCode", ""
                )
            except ValueError:
                continue
    xfs = root.find(MAIN_NS + "cellXfs")
    if xfs is None:
        return []
    result: list[tuple[int, str]] = []
    for item in xfs.findall(MAIN_NS + "xf"):
        try:
            format_id = int(item.attrib.get("numFmtId", "0"))
        except ValueError:
            format_id = 0
        result.append((format_id, custom.get(format_id, "")))
    return result


def _workbook_sheet_paths(archive: zipfile.ZipFile) -> list[tuple[str, str, bool]]:
    names = set(archive.namelist())
    if "xl/workbook.xml" not in names or "xl/_rels/workbook.xml.rels" not in names:
        raise VatDraftError("File không có cấu trúc workbook .xlsx được hỗ trợ.")
    workbook = _safe_xml(archive.read("xl/workbook.xml"), "xl/workbook.xml")
    relationships = _safe_xml(
        archive.read("xl/_rels/workbook.xml.rels"), "xl/_rels/workbook.xml.rels"
    )
    targets = {
        item.attrib.get("Id", ""): item.attrib.get("Target", "")
        for item in relationships.findall(PKG_REL_NS + "Relationship")
    }
    sheets: list[tuple[str, str, bool]] = []
    container = workbook.find(MAIN_NS + "sheets")
    if container is None:
        raise VatDraftError("Workbook không có danh sách sheet.")
    for sheet in container.findall(MAIN_NS + "sheet"):
        name = sheet.attrib.get("name", "")
        relationship_id = sheet.attrib.get(DOC_REL_NS + "id", "")
        target = targets.get(relationship_id)
        if not name or not target:
            raise VatDraftError("Không ánh xạ được tên sheet tới tệp dữ liệu.")
        path = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join("xl", target))
        )
        if not path.startswith("xl/") or path.startswith("xl/../"):
            raise VatDraftError("Đường dẫn sheet nằm ngoài gói workbook.")
        if path not in names:
            raise VatDraftError(f"Thiếu dữ liệu sheet: {name}.")
        sheets.append((name, path, sheet.attrib.get("state") == "hidden"))
    return sheets


def _formatted_value(
    cell: ET.Element,
    shared: list[str],
    formats: list[tuple[int, str]],
) -> tuple[str, bool]:
    cell_type = cell.attrib.get("t", "")
    formula = cell.find(MAIN_NS + "f") is not None
    if cell_type == "inlineStr":
        inline = cell.find(MAIN_NS + "is")
        return (
            "".join(node.text or "" for node in inline.iter(MAIN_NS + "t"))
            if inline is not None
            else "",
            formula,
        )
    value_node = cell.find(MAIN_NS + "v")
    raw = value_node.text if value_node is not None and value_node.text else ""
    if cell_type == "s" and raw:
        try:
            return shared[int(raw)], formula
        except (ValueError, IndexError) as exc:
            raise VatDraftError(
                "Chỉ số shared string trong workbook không hợp lệ."
            ) from exc
    if cell_type == "b":
        return ("TRUE" if raw == "1" else "FALSE"), formula
    if not raw:
        return "", formula

    style_id = int(cell.attrib.get("s", "0"))
    format_id, format_code = formats[style_id] if style_id < len(formats) else (0, "")
    if format_id in range(14, 23) or _DATE_FORMAT.search(format_code):
        try:
            serial = Decimal(raw)
            date_value = dt.datetime(1899, 12, 30) + dt.timedelta(days=float(serial))
            return date_value.date().isoformat(), formula
        except (InvalidOperation, OverflowError, ValueError):
            pass
    if _ZERO_FORMAT.fullmatch(format_code):
        try:
            numeric = Decimal(raw)
            if numeric == numeric.to_integral_value():
                return str(int(numeric)).zfill(len(format_code)), formula
        except InvalidOperation:
            pass
    return raw, formula


def read_xlsx_rows(
    path: Path, sheet_name: str | None = None, header_row: int | None = None
) -> list[dict[str, Any]]:
    if header_row is not None and header_row < 1:
        raise VatDraftError("Hàng tiêu đề Excel phải từ 1 trở lên.")
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            member_names = [item.filename for item in members]
            if len(member_names) != len(set(member_names)):
                raise VatDraftError("Workbook có entry ZIP trùng tên.")
            if sum(item.file_size for item in members) > MAX_UNCOMPRESSED_BYTES:
                raise VatDraftError("Workbook vượt giới hạn dung lượng giải nén.")
            sheets = _workbook_sheet_paths(archive)
            if sheet_name:
                selected = [
                    item
                    for item in sheets
                    if item[0].casefold() == sheet_name.casefold()
                ]
                if not selected:
                    raise VatDraftError(f"Không tìm thấy sheet: {sheet_name}.")
                target = selected[0]
            elif len(sheets) == 1:
                target = sheets[0]
            else:
                visible = [item for item in sheets if not item[2]]
                if len(visible) != 1:
                    raise VatDraftError("Workbook có nhiều sheet; hãy chọn --sheet.")
                target = visible[0]
            shared = _shared_strings(archive)
            formats = _style_formats(archive)
            root = _safe_xml(archive.read(target[1]), target[1])
    except zipfile.BadZipFile as exc:
        raise VatDraftError("Tệp đầu vào không phải gói .xlsx hợp lệ.") from exc
    except OSError as exc:
        raise VatDraftError(f"Không đọc được workbook: {exc}") from exc

    sheet_data = root.find(MAIN_NS + "sheetData")
    if sheet_data is None:
        raise VatDraftError("Sheet không có vùng dữ liệu.")
    table: dict[int, dict[int, tuple[str, bool]]] = {}
    for row in sheet_data.findall(MAIN_NS + "row"):
        for cell in row.findall(MAIN_NS + "c"):
            reference = cell.attrib.get("r", "")
            column, row_number = _column_index(reference)
            table.setdefault(row_number, {})[column] = _formatted_value(
                cell, shared, formats
            )
    if not table:
        return []
    selected_header_row = header_row if header_row is not None else min(table)
    if selected_header_row not in table:
        raise VatDraftError(
            f"Không tìm thấy hàng tiêu đề Excel: {selected_header_row}."
        )
    max_column = max(table[selected_header_row], default=-1)
    headers = [
        table[selected_header_row].get(index, ("", False))[0]
        for index in range(max_column + 1)
    ]
    result: list[dict[str, Any]] = []
    for row_number in sorted(
        number for number in table if number > selected_header_row
    ):
        cells = table[row_number]
        raw: dict[str, Any] = {}
        formula_fields: list[str] = []
        for index, header in enumerate(headers):
            if not header.strip():
                continue
            value, is_formula = cells.get(index, ("", False))
            raw[header] = value
            if is_formula:
                formula_fields.append(
                    ALIAS_TO_FIELD.get(normalize_label(header), header)
                )
        if any(str(value).strip() for value in raw.values()):
            result.append(
                {"source_row": row_number, "raw": raw, "formula_fields": formula_fields}
            )
    return result


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames:
                raise VatDraftError("CSV không có hàng tiêu đề.")
            return [
                {"source_row": index, "raw": row, "formula_fields": []}
                for index, row in enumerate(reader, start=2)
            ]
    except (OSError, UnicodeError, csv.Error) as exc:
        raise VatDraftError(f"Không đọc được CSV: {exc}") from exc


def read_invoice_rows(
    path: str | Path,
    sheet_name: str | None = None,
    header_row: int | None = None,
) -> list[dict[str, Any]]:
    source = Path(path)
    suffix = source.suffix.casefold()
    if suffix == ".xlsx":
        return read_xlsx_rows(source, sheet_name, header_row)
    if suffix == ".csv":
        if sheet_name:
            raise VatDraftError("--sheet chỉ áp dụng cho tệp .xlsx.")
        if header_row not in (None, 1):
            raise VatDraftError("CSV chỉ hỗ trợ tiêu đề ở hàng 1.")
        return read_csv_rows(source)
    raise VatDraftError(
        "Chỉ nhận .xlsx hoặc .csv; XML/PDF/ảnh chưa triển khai trong slice này."
    )


def parse_date(value: str) -> dt.date | None:
    cleaned = value.strip()
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    return None


def period_window(period: str) -> tuple[dt.date, dt.date, str]:
    month_match = re.fullmatch(r"(\d{4})-(\d{2})", period)
    quarter_match = re.fullmatch(r"(\d{4})-Q([1-4])", period, re.IGNORECASE)
    if month_match:
        year, month = int(month_match.group(1)), int(month_match.group(2))
        if month not in range(1, 13):
            raise VatDraftError("Tháng phải nằm trong khoảng 01–12.")
        start = dt.date(year, month, 1)
        next_month = dt.date(year + (month == 12), month % 12 + 1, 1)
        return start, next_month - dt.timedelta(days=1), "month"
    if quarter_match:
        year, quarter = int(quarter_match.group(1)), int(quarter_match.group(2))
        month = (quarter - 1) * 3 + 1
        start = dt.date(year, month, 1)
        next_month = month + 3
        end = dt.date(year + (next_month > 12), (next_month - 1) % 12 + 1, 1)
        return start, end - dt.timedelta(days=1), "quarter"
    raise VatDraftError("Kỳ phải theo dạng YYYY-MM hoặc YYYY-Q1 đến YYYY-Q4.")


def parse_money(value: str) -> Decimal | None:
    cleaned = value.strip().replace("₫", "").replace("VND", "").replace("đ", "")
    cleaned = re.sub(r"\s+", "", cleaned)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if cleaned.count(",") == 1 and len(cleaned.rsplit(",", 1)[1]) in (1, 2):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "." in cleaned:
        if cleaned.count(".") > 1 or len(cleaned.rsplit(".", 1)[1]) == 3:
            cleaned = cleaned.replace(".", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def money_text(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f") if normalized else "0"


def normalize_tax_id(value: str) -> str:
    return value.strip().upper()


def _canonical_raw(raw: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for label, value in raw.items():
        field = ALIAS_TO_FIELD.get(normalize_label(str(label)))
        if field and field not in values:
            values[field] = str(value or "").strip()
    return values


def _canonical_status(value: str) -> str:
    return normalize_label(value)


def _period_contains(
    invoice_date: dt.date | None, start: dt.date, end: dt.date
) -> bool:
    return invoice_date is not None and start <= invoice_date <= end


def _invoice_records(
    imported: list[dict[str, Any]], taxpayer_tax_id: str, start: dt.date, end: dt.date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    taxpayer = normalize_tax_id(taxpayer_tax_id)
    for item in imported:
        source_row = int(item["source_row"])
        data = _canonical_raw(item["raw"])
        missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
        invoice_date = parse_date(data.get("invoice_date", ""))
        seller_id = normalize_tax_id(data.get("seller_tax_id", ""))
        buyer_id = normalize_tax_id(data.get("buyer_tax_id", ""))
        if seller_id == taxpayer and buyer_id == taxpayer:
            direction = "self_party_conflict"
        elif seller_id == taxpayer:
            direction = "sales"
        elif buyer_id == taxpayer:
            direction = "purchases"
        else:
            direction = "unclassified"

        declared = normalize_label(data.get("declared_direction", ""))
        declared_direction_mismatch = False
        if declared:
            expected = {
                "sales": {"sales", "sale", "ban_ra", "ban"},
                "purchases": {"purchase", "purchases", "mua_vao", "mua"},
            }.get(direction, set())
            if declared not in expected:
                declared_direction_mismatch = True

        amounts: dict[str, Decimal | None] = {
            key: parse_money(data.get(key, ""))
            for key in ("net_amount", "tax_amount", "gross_amount")
        }
        formula_fields = sorted(set(item.get("formula_fields", [])))
        status_key = _canonical_status(data.get("status", ""))
        record = {
            "source_row": source_row,
            "invoice_date": invoice_date.isoformat()
            if invoice_date
            else data.get("invoice_date", ""),
            "direction": direction,
            "seller_tax_id": seller_id,
            "seller_name": data.get("seller_name", ""),
            "buyer_tax_id": buyer_id,
            "buyer_name": data.get("buyer_name", ""),
            "invoice_series": data.get("invoice_series", ""),
            "invoice_number": data.get("invoice_number", ""),
            "net_amount": money_text(amounts["net_amount"])
            if amounts["net_amount"] is not None
            else None,
            "tax_rate_label": data.get("tax_rate", ""),
            "tax_amount": money_text(amounts["tax_amount"])
            if amounts["tax_amount"] is not None
            else None,
            "gross_amount": money_text(amounts["gross_amount"])
            if amounts["gross_amount"] is not None
            else None,
            "invoice_status": data.get("status", "") or "unspecified",
            "formula_fields": formula_fields,
            "eligible_for_draft_totals": False,
            "review_reasons": [],
        }
        record_errors: list[str] = []
        if declared_direction_mismatch:
            record_errors.append("declared_direction_mismatch")
        if missing:
            record_errors.append("missing_required_fields:" + ",".join(missing))
        if invoice_date is None:
            record_errors.append("invalid_invoice_date")
        if direction in {"self_party_conflict", "unclassified"}:
            record_errors.append(direction)
        for name, value in amounts.items():
            if value is None:
                record_errors.append("invalid_" + name)
            elif value < 0:
                record_errors.append("negative_" + name)
        if formula_fields:
            record_errors.append("formula_values_require_source_review")
        if status_key in HOLD_STATUS:
            record_errors.append("invoice_status_requires_manual_treatment")
        elif status_key and status_key not in NORMAL_STATUS:
            record_errors.append(
                "invoice_status_unrecognized_requires_manual_treatment"
            )
        outside_period = not _period_contains(invoice_date, start, end)
        if outside_period:
            record["review_reasons"].append("outside_selected_period_by_invoice_date")
        if all(value is not None for value in amounts.values()):
            if amounts["net_amount"] + amounts["tax_amount"] != amounts["gross_amount"]:
                record_errors.append("invoice_amounts_do_not_reconcile")
        if record_errors:
            record["review_reasons"] = record_errors + (
                ["outside_selected_period_by_invoice_date"] if outside_period else []
            )
            findings.extend(
                {"severity": "block", "code": code, "source_row": source_row}
                for code in record_errors
            )
        else:
            record["eligible_for_draft_totals"] = not outside_period
            if not status_key:
                record["review_reasons"].append("invoice_status_not_provided")
                findings.append(
                    {
                        "severity": "review",
                        "code": "invoice_status_not_provided",
                        "source_row": source_row,
                    }
                )
            if outside_period:
                findings.append(
                    {
                        "severity": "info",
                        "code": "outside_selected_period_by_invoice_date",
                        "source_row": source_row,
                    }
                )
        records.append(record)

    duplicate_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for record in records:
        key = (
            record["direction"],
            record["seller_tax_id"],
            record["invoice_series"].casefold(),
            record["invoice_number"].casefold(),
        )
        if all(key[1:]):
            duplicate_groups[key].append(record)
    for group in duplicate_groups.values():
        if len(group) > 1:
            rows = sorted(record["source_row"] for record in group)
            findings.append(
                {
                    "severity": "block",
                    "code": "duplicate_invoice_identity",
                    "source_rows": rows,
                }
            )
            for record in group:
                record["eligible_for_draft_totals"] = False
                record["review_reasons"].append("duplicate_invoice_identity")
    return records, findings


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, dict[str, Decimal]] = {
        "sales": {
            "invoice_count": Decimal(0),
            "net_amount": Decimal(0),
            "tax_amount": Decimal(0),
            "gross_amount": Decimal(0),
        },
        "purchases": {
            "invoice_count": Decimal(0),
            "net_amount": Decimal(0),
            "tax_amount": Decimal(0),
            "gross_amount": Decimal(0),
        },
    }
    rates: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {
            "invoice_count": Decimal(0),
            "net_amount": Decimal(0),
            "tax_amount": Decimal(0),
            "gross_amount": Decimal(0),
        }
    )
    for record in records:
        if not record["eligible_for_draft_totals"]:
            continue
        direction = record["direction"]
        rate = record["tax_rate_label"] or "UNSPECIFIED"
        totals[direction]["invoice_count"] += 1
        rates[f"{direction}:{rate}"]["invoice_count"] += 1
        for field in ("net_amount", "tax_amount", "gross_amount"):
            amount = Decimal(record[field])
            totals[direction][field] += amount
            rates[f"{direction}:{rate}"][field] += amount

    def render(groups: dict[str, dict[str, Decimal]]) -> dict[str, dict[str, Any]]:
        rendered: dict[str, dict[str, Any]] = {}
        for group, values in sorted(groups.items()):
            rendered[group] = {
                key: int(value) if key == "invoice_count" else money_text(value)
                for key, value in values.items()
            }
        return rendered

    return {
        "by_direction": render(totals),
        "by_direction_and_invoice_rate_label": render(rates),
    }


def _independent_check(
    records: list[dict[str, Any]], totals: dict[str, Any]
) -> dict[str, Any]:
    # Keep a separate reduction path so a defect in _aggregate is less likely
    # to be repeated by the independent reconciliation pass.
    direction_values: dict[str, dict[str, Decimal]] = {
        "sales": {
            "invoice_count": Decimal(0),
            "net_amount": Decimal(0),
            "tax_amount": Decimal(0),
            "gross_amount": Decimal(0),
        },
        "purchases": {
            "invoice_count": Decimal(0),
            "net_amount": Decimal(0),
            "tax_amount": Decimal(0),
            "gross_amount": Decimal(0),
        },
    }
    rate_values: dict[str, dict[str, Decimal]] = {}
    for record in records:
        if record["eligible_for_draft_totals"] is not True:
            continue
        direction = record["direction"]
        key = f"{direction}:{record['tax_rate_label'] or 'UNSPECIFIED'}"
        direction_values[direction]["invoice_count"] += Decimal(1)
        rate_values.setdefault(
            key,
            {
                "invoice_count": Decimal(0),
                "net_amount": Decimal(0),
                "tax_amount": Decimal(0),
                "gross_amount": Decimal(0),
            },
        )["invoice_count"] += Decimal(1)
        for amount_field in ("net_amount", "tax_amount", "gross_amount"):
            amount = Decimal(str(record[amount_field]))
            direction_values[direction][amount_field] += amount
            rate_values[key][amount_field] += amount

    def render_independent(
        values: dict[str, dict[str, Decimal]],
    ) -> dict[str, dict[str, Any]]:
        return {
            group: {
                field: int(value) if field == "invoice_count" else money_text(value)
                for field, value in sorted(fields.items())
            }
            for group, fields in sorted(values.items())
        }

    independent = {
        "by_direction": render_independent(direction_values),
        "by_direction_and_invoice_rate_label": render_independent(rate_values),
    }
    return {
        "status": "pass" if independent == totals else "fail",
        "recomputed_totals": independent,
        "totals_match": independent == totals,
        "method": "recomputed from eligible invoice rows in a separate aggregation pass",
    }


def build_draft(
    input_path: str | Path,
    taxpayer_tax_id: str,
    period: str,
    *,
    sheet_name: str | None = None,
    header_row: int | None = None,
) -> dict[str, Any]:
    source = Path(input_path)
    if not source.is_file():
        raise VatDraftError("Tệp đầu vào không tồn tại hoặc không phải tệp thường.")
    start, end, period_type = period_window(period)
    if not taxpayer_tax_id.strip():
        raise VatDraftError("Cần MST người nộp thuế để phân loại mua vào/bán ra.")
    imported = read_invoice_rows(source, sheet_name, header_row)
    records, findings = _invoice_records(imported, taxpayer_tax_id, start, end)
    if imported and not any(record["eligible_for_draft_totals"] for record in records):
        findings.append(
            {"severity": "block", "code": "no_eligible_invoices_in_selected_period"}
        )
    totals = _aggregate(records)
    independent = _independent_check(records, totals)
    if not independent["totals_match"]:
        findings.append({"severity": "block", "code": "independent_check_failed"})
    blocking = [item for item in findings if item["severity"] == "block"]
    return {
        "tool": "accounting-vat-return-draft",
        "draft_status": "blocked_review_required"
        if blocking
        else "draft_ready_unmapped",
        "source_file": source.name,
        "input_format": source.suffix.casefold().lstrip("."),
        "taxpayer_tax_id": taxpayer_tax_id.strip(),
        "period": {
            "label": period.upper(),
            "type": period_type,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "filter_basis": "invoice_date_only; manual period and legal treatment review required",
        },
        "workflow": [
            {"step": "import", "status": "completed", "records_read": len(imported)},
            {
                "step": "classify",
                "status": "completed_with_review" if blocking else "completed",
                "rules": "party tax ID; never match by name",
            },
            {
                "step": "validate",
                "status": "review_required" if findings else "passed",
                "finding_count": len(findings),
            },
            {
                "step": "aggregate",
                "status": "completed",
                "eligible_invoice_count": sum(
                    record["eligible_for_draft_totals"] for record in records
                ),
            },
            {"step": "prepare_draft", "status": "prepared_not_official_form"},
            {"step": "independent_check", "status": independent["status"]},
            {"step": "export", "status": "JSON_draft_only"},
        ],
        "legal_form": {
            "form_number": None,
            "candidate_form_number": "01/GTGT",
            "version": None,
            "status": "OFFICIAL_FORM_SOURCE_VERIFIED; PERIOD_AND_FIELD_EXPORT_MAPPING_REQUIRE_REVIEW",
            "verified_versions": [
                {
                    "instrument": "80/2021/TT-BTC",
                    "annex": "II",
                    "period_candidate": "before 2026-07-01",
                    "status": "official form and relevant address amendments identified; tax-period applicability requires review",
                },
                {
                    "instrument": "89/2026/TT-BTC",
                    "annex": "I",
                    "pdf_page": 241,
                    "period_candidate": "from 2026-07-01",
                    "status": "official form page confirmed; transition and taxpayer case require review",
                },
            ],
            "auto_form_selection": False,
            "xml_export": "NOT_STARTED_SCHEMA_NOT_VERIFIED",
            "submission_ready": False,
            "note": "Nguồn biểu mẫu chính thức đã được xác định; chưa bật ánh xạ xuất Excel, lựa chọn phiên bản hoặc lập XML trước khi hoàn thành rà soát kỳ áp dụng, trường dữ liệu, phụ lục và schema.",
        },
        "totals": totals,
        "independent_check": independent,
        "findings": findings,
        "records": records,
        "limitations": [
            "Chỉ nhận dữ liệu .xlsx hoặc .csv có hàng tiêu đề; XML/PDF/ảnh chưa triển khai.",
            "Đây là bản tổng hợp nội bộ, không phải tờ khai pháp định và không kết luận điều kiện khấu trừ.",
            "Mức thuế suất được giữ nguyên đúng nhãn nguồn; không suy thuế suất hoặc tự tính lại tiền thuế.",
            "Hóa đơn điều chỉnh, thay thế, hủy, trùng, ngoài kỳ hoặc có ô công thức cần xử lý thủ công trước khi tổng hợp.",
            "Tệp nguồn chỉ được đọc; báo cáo xuất là JSON riêng. Xuất Excel/XLSX và XML chưa bắt đầu.",
        ],
    }


def write_draft(
    draft: dict[str, Any], output_path: str | Path, *, force: bool = False
) -> Path:
    destination = Path(output_path)
    if destination.suffix.casefold() != ".json":
        raise VatDraftError("Chỉ xuất JSON dự thảo; không gắn JSON vào đuôi tệp khác.")
    source_name = str(draft.get("source_file", ""))
    if destination.name == source_name and destination.suffix.casefold() in {
        ".xlsx",
        ".csv",
    }:
        raise VatDraftError("Không được ghi đè workbook hoặc CSV nguồn.")
    if destination.exists() and not force:
        raise VatDraftError("Tệp dự thảo đã tồn tại; dùng --force khi muốn ghi đè.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(draft, ensure_ascii=False, indent=2) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
        return destination
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Tệp hóa đơn .xlsx hoặc .csv.")
    parser.add_argument(
        "--taxpayer-tax-id", required=True, help="MST dùng để phân loại bên mua/bán."
    )
    parser.add_argument(
        "--period", required=True, help="Kỳ YYYY-MM hoặc YYYY-Q1..YYYY-Q4."
    )
    parser.add_argument("--sheet", help="Tên sheet đầu vào .xlsx.")
    parser.add_argument(
        "--header-row",
        type=int,
        help="Số hàng tiêu đề trong Excel; mặc định hàng có dữ liệu đầu tiên.",
    )
    parser.add_argument("--output", help="Đường dẫn JSON dự thảo riêng.")
    parser.add_argument(
        "--force", action="store_true", help="Cho phép ghi đè tệp dự thảo đã có."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    input_path = Path(args.input)
    output_path = (
        Path(args.output)
        if args.output
        else input_path.with_name(f"{input_path.stem}.vat-draft.json")
    )
    try:
        if input_path.exists() and output_path.resolve() == input_path.resolve():
            raise VatDraftError("Đường dẫn xuất không được ghi đè tệp nguồn.")
        draft = build_draft(
            input_path,
            args.taxpayer_tax_id,
            args.period,
            sheet_name=args.sheet,
            header_row=args.header_row,
        )
        write_draft(draft, output_path, force=args.force)
        print(
            json.dumps(
                {
                    "status": draft["draft_status"],
                    "output": str(output_path),
                    "findings": len(draft["findings"]),
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(f"vat-draft: ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
