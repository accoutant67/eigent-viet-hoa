#!/usr/bin/env python3
"""Prepare a review-only VAT return draft from a CSV or .xlsx invoice sheet.

The tool does not determine tax eligibility, apply tax law, write to an input
workbook, populate a legal form, generate XML, sign, or submit a return.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
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
    "form_line_code": {
        "form_line_code",
        "tax_return_line_code",
        "chi_tieu_doanh_thu",
        "ma_chi_tieu_doanh_thu",
    },
    "form_tax_line_code": {
        "form_tax_line_code",
        "tax_return_tax_line_code",
        "chi_tieu_thue",
        "ma_chi_tieu_thue",
    },
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
FORM_CATALOG_PATH = Path(__file__).resolve().parents[1] / "legal" / "form_catalog.json"
FORM_REVENUE_FIELDS = {
    "80/2021/TT-BTC": {"26", "29", "30", "32", "32a"},
    "89/2026/TT-BTC": {"26", "29", "30", "32", "32a", "32b", "34a"},
}
FORM_TAX_FIELDS = {"31", "33"}
FORM_PURCHASE_VALUE_FIELDS = {"23", "23a"}
FORM_PURCHASE_TAX_FIELDS = {"24", "24a"}
PURCHASE_TAX_LINE_BY_VALUE = {"23": "24", "23a": "24a"}
LAW_WATCH_REQUIRED_SOURCES = {
    "80/2021/TT-BTC": {
        "congbao_tt80_2021",
        "vanban_tt40_2025_tt80_form_update",
        "vanban_tt94_2025_tt80_update",
        "vanban_tt21_2026_tt80_update",
    },
    "89/2026/TT-BTC": {
        "vanban_law_vat_48_2024",
        "vanban_decree_vat_181_2025",
        "vanban_circular_vat_69_2025",
        "vanban_tt89_2026",
        "vanban_tt40_2025_tt80_form_update",
        "vanban_tt94_2025_tt80_update",
        "vanban_tt21_2026_tt80_update",
        "congbao_correction_2551_2026",
        "vanban_tt110_2026",
    },
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


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _xml_text(node: ET.Element, names: set[str]) -> str:
    for child in node.iter():
        if _xml_local_name(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return ""


def _xml_direct_children(node: ET.Element, local_name: str) -> list[ET.Element]:
    return [child for child in list(node) if _xml_local_name(child.tag) == local_name]


def _xml_direct_text(node: ET.Element, local_name: str) -> str:
    children = _xml_direct_children(node, local_name)
    if not children:
        return ""
    return (children[0].text or "").strip()


def _decimal_xml(value: str, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise VatDraftError(f"Giá trị {field_name} trong UBL không phải số thập phân.") from exc


def read_ubl_invoice_xml(path: Path) -> list[dict[str, Any]]:
    """Read the bounded UBL 2.x invoice/credit-note subset into VAT row input.

    UBL 2.1 document models and schemas are normative for UBL conformance. This
    importer extracts values, but does not claim XSD/signature validation or
    GDT/HTKK compatibility. Unknown extension content is not executed.
    """
    max_xml_bytes = 20 * 1024 * 1024
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise VatDraftError(f"Không đọc được tệp XML hóa đơn: {exc}") from exc
    if len(payload) > max_xml_bytes:
        raise VatDraftError("Tệp XML hóa đơn vượt giới hạn 20 MiB.")
    try:
        root = ET.fromstring(
            payload,
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )
    except DefusedXmlException as exc:
        raise VatDraftError("XML chứa khai báo DTD/entity không an toàn.") from exc
    except ET.ParseError as exc:
        raise VatDraftError(f"XML hóa đơn sai cú pháp: {exc}") from exc

    document_kind = _xml_local_name(root.tag)
    namespace = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else ""
    expected_namespace = {
        "Invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
        "CreditNote": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
    }
    if document_kind not in expected_namespace or namespace != expected_namespace[document_kind]:
        raise VatDraftError(
            "UNSUPPORTED_PROFILE: XML không thuộc profile UBL Invoice-2/CreditNote-2 được hỗ trợ."
        )

    nodes = list(root.iter())
    if len(nodes) > 100_000:
        raise VatDraftError("XML vượt giới hạn 100.000 phần tử.")
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > 128:
            raise VatDraftError("XML vượt giới hạn độ sâu 128.")
        stack.extend((child, depth + 1) for child in list(node))

    subtotals: list[tuple[str, str, str]] = []
    tax_totals = _xml_direct_children(root, "TaxTotal")
    for tax_total in tax_totals:
        for subtotal in _xml_direct_children(tax_total, "TaxSubtotal"):
            category = next(
                iter(_xml_direct_children(subtotal, "TaxCategory")), None
            )
            if category is None:
                continue
            scheme = next(iter(_xml_direct_children(category, "TaxScheme")), None)
            scheme_id = _xml_direct_text(scheme, "ID") if scheme is not None else ""
            if scheme_id and scheme_id.casefold() not in {"vat", "valueaddedtax"}:
                continue
            taxable = _xml_direct_text(subtotal, "TaxableAmount")
            tax = _xml_direct_text(subtotal, "TaxAmount")
            percent = _xml_direct_text(category, "Percent")
            if not taxable or not tax or not percent:
                raise VatDraftError(
                    "TaxSubtotal thuế GTGT thiếu TaxableAmount, TaxAmount hoặc Percent."
                )
            rate_value = _decimal_xml(percent, "Percent")
            _decimal_xml(taxable, "TaxableAmount")
            _decimal_xml(tax, "TaxAmount")
            subtotals.append((taxable, tax, f"{money_text(rate_value)}%"))
    if not subtotals:
        raise VatDraftError("UBL không có TaxSubtotal VAT được nhận diện.")

    tax_breakdown = [
        {
            "rate_label": rate,
            "taxable_amount": money_text(_decimal_xml(net, "TaxableAmount")),
            "tax_amount": money_text(_decimal_xml(tax, "TaxAmount")),
        }
        for net, tax, rate in subtotals
    ]
    net_total_node = next(iter(_xml_direct_children(
        next(iter(_xml_direct_children(root, "LegalMonetaryTotal")), root),
        "TaxExclusiveAmount",
    )), None)
    net_total = (net_total_node.text or "").strip() if net_total_node is not None else ""
    if not net_total:
        net_total = money_text(sum((_decimal_xml(row[0], "TaxableAmount") for row in subtotals), Decimal(0)))
    tax_total_values = [
        _xml_direct_text(total, "TaxAmount")
        for total in tax_totals
        if _xml_direct_text(total, "TaxAmount")
    ]
    tax_total_value = (
        money_text(sum((_decimal_xml(value, "TaxAmount") for value in tax_total_values), Decimal(0)))
        if tax_total_values
        else money_text(sum((_decimal_xml(row[1], "TaxAmount") for row in subtotals), Decimal(0)))
    )
    rates = sorted({row[2] for row in subtotals})
    tax_rate = rates[0] if len(rates) == 1 else "MULTIPLE"

    def party_values(party_name: str) -> tuple[str, str]:
        party_container = next(iter(_xml_direct_children(root, party_name)), None)
        if party_container is None:
            return "", ""
        party = next(iter(_xml_direct_children(party_container, "Party")), party_container)
        tax_schemes = _xml_direct_children(party, "PartyTaxScheme")
        tax_id = ""
        if tax_schemes:
            tax_id = _xml_direct_text(tax_schemes[0], "CompanyID")
        if not tax_id:
            legal_entities = _xml_direct_children(party, "PartyLegalEntity")
            tax_id = _xml_direct_text(legal_entities[0], "CompanyID") if legal_entities else ""
        name = ""
        for container_name in ("PartyLegalEntity", "PartyName"):
            containers = _xml_direct_children(party, container_name)
            if containers:
                name = _xml_direct_text(containers[0], "RegistrationName") or _xml_direct_text(containers[0], "Name")
                if name:
                    break
        return tax_id, name

    seller_tax_id, seller_name = party_values("AccountingSupplierParty")
    buyer_tax_id, buyer_name = party_values("AccountingCustomerParty")
    date_value = _xml_direct_text(root, "IssueDate")
    invoice_number = _xml_direct_text(root, "ID")
    explicit_series = ""
    for extension in _xml_direct_children(root, "UBLExtensions"):
        explicit_series = _xml_direct_text(extension, "InvoiceSeries")
        if explicit_series:
            break

    legal_totals = next(iter(_xml_direct_children(root, "LegalMonetaryTotal")), None)
    payable = _xml_direct_text(legal_totals, "PayableAmount") if legal_totals is not None else ""
    if not payable:
        raise VatDraftError("XML thiếu PayableAmount; không tự tính tổng thanh toán.")

    line_name = "InvoiceLine" if document_kind == "Invoice" else "CreditNoteLine"
    line_items: list[dict[str, Any]] = []
    line_extraction_complete = True
    for line in _xml_direct_children(root, line_name):
        item_node = next(iter(_xml_direct_children(line, "Item")), None)
        price_node = next(iter(_xml_direct_children(line, "Price")), None)
        quantity_name = "InvoicedQuantity" if document_kind == "Invoice" else "CreditedQuantity"
        quantity = _xml_direct_text(line, quantity_name)
        line_amount = _xml_direct_text(line, "LineExtensionAmount")
        unit_price = _xml_direct_text(price_node, "PriceAmount") if price_node is not None else ""
        description = ""
        if item_node is not None:
            description = _xml_direct_text(item_node, "Description")
            if not description:
                description = _xml_direct_text(item_node, "Name")
        line_tax_rate = ""
        line_tax_amount = ""
        line_tax_totals = _xml_direct_children(line, "TaxTotal")
        if line_tax_totals:
            line_tax_amount = _xml_direct_text(line_tax_totals[0], "TaxAmount")
            subtotals_for_line = _xml_direct_children(line_tax_totals[0], "TaxSubtotal")
            if subtotals_for_line:
                category = next(iter(_xml_direct_children(subtotals_for_line[0], "TaxCategory")), None)
                line_tax_rate = _xml_direct_text(category, "Percent") if category is not None else ""
        line_id = _xml_direct_text(line, "ID")
        line_items.append({
            "description": description or None,
            "quantity": money_text(_decimal_xml(quantity, "Quantity")) if quantity else None,
            "unit": _xml_direct_text(line, quantity_name) and (
                next(iter(_xml_direct_children(line, quantity_name))).attrib.get("unitCode")
            ) or None,
            "unit_price": money_text(_decimal_xml(unit_price, "PriceAmount")) if unit_price else None,
            "net_amount": money_text(_decimal_xml(line_amount, "LineExtensionAmount")) if line_amount else None,
            "tax_rate_label": f"{money_text(_decimal_xml(line_tax_rate, 'Percent'))}%" if line_tax_rate else None,
            "tax_amount": money_text(_decimal_xml(line_tax_amount, "TaxAmount")) if line_tax_amount else None,
            "source_line_id": line_id or None,
        })
        if not all((quantity, unit_price, line_amount, line_tax_rate, line_tax_amount)):
            line_extraction_complete = False

    references: list[dict[str, Any]] = []
    for billing_reference in _xml_direct_children(root, "BillingReference"):
        invoice_ref = next(iter(_xml_direct_children(billing_reference, "InvoiceDocumentReference")), None)
        if invoice_ref is not None:
            ref_id = _xml_direct_text(invoice_ref, "ID")
            ref_date = _xml_direct_text(invoice_ref, "IssueDate")
            if ref_id:
                references.append({
                    "reference_kind": "billing_reference",
                    "identifier": ref_id,
                    "issued_at": ref_date or None,
                })

    raw = {
        "invoice_date": date_value,
        "seller_tax_id": seller_tax_id,
        "seller_name": seller_name,
        "buyer_tax_id": buyer_tax_id,
        "buyer_name": buyer_name,
        "invoice_series": explicit_series,
        "invoice_number": invoice_number,
        "net_amount": net_total,
        "tax_rate": tax_rate,
        "tax_amount": tax_total_value,
        "gross_amount": payable,
        "status": "adjusted" if document_kind == "CreditNote" else "normal",
        "document_kind": "credit_note" if document_kind == "CreditNote" else "invoice",
        "source_profile": f"oasis-ubl-2-{document_kind.casefold()}-vat-v2",
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "source_name": path.name,
        "tax_breakdown": tax_breakdown,
        "line_items": line_items,
        "line_items_extraction_status": "complete" if line_extraction_complete and line_items else ("not_extracted" if not line_items else "partial"),
        "references": references,
        "relationships_extraction_status": "complete" if references else "not_extracted",
    }
    return [{"source_row": 1, "raw": raw, "formula_fields": []}]

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
    if suffix == ".xml":
        if sheet_name or header_row not in (None, 1):
            raise VatDraftError("--sheet/--header-row không áp dụng cho XML.")
        return read_ubl_invoice_xml(source)
    raise VatDraftError(
        "Chỉ nhận .xlsx, .csv hoặc XML UBL Invoice/CreditNote đơn lẻ theo profile được hỗ trợ."
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


def normalize_form_line_code(value: str) -> str:
    cleaned = value.strip().casefold().strip("[]")
    return cleaned if re.fullmatch(r"\d{1,2}[a-z]?", cleaned) else ""


def _form_version_spec(version: str) -> dict[str, Any]:
    try:
        catalog = json.loads(FORM_CATALOG_PATH.read_text(encoding="utf-8"))
        versions = catalog["filing_form"]["versions"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise VatDraftError(
            "Không đọc được danh mục phiên bản mẫu GTGT đã xác minh."
        ) from exc
    for candidate in versions:
        if candidate.get("instrument") == version:
            return candidate
    raise VatDraftError(f"Phiên bản mẫu GTGT chưa có trong danh mục: {version}.")


def _review_law_watch_report(
    report_path: str | Path | None, version: str
) -> dict[str, Any]:
    if report_path is None:
        return {
            "status": "blocked",
            "reason": "law_watch_report_required_for_form_draft",
            "missing_sources": sorted(LAW_WATCH_REQUIRED_SOURCES[version]),
        }
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "blocked",
            "reason": f"law_watch_report_unreadable:{type(exc).__name__}",
            "missing_sources": sorted(LAW_WATCH_REQUIRED_SOURCES[version]),
        }
    if not isinstance(report, dict):
        report = {}
    checks = report.get("official_reference_checks", [])
    status_by_source = (
        {
            str(item.get("name")): str(item.get("status"))
            for item in checks
            if isinstance(item, dict)
        }
        if isinstance(checks, list)
        else {}
    )
    required = LAW_WATCH_REQUIRED_SOURCES[version]
    not_verified = sorted(
        source for source in required if status_by_source.get(source) != "pass"
    )
    proposals = report.get("proposals")
    if not isinstance(proposals, list):
        proposals = ["invalid_proposal_list"]
    reasons: list[str] = []
    try:
        listing_entries = int(report.get("listing_entries", 0) or 0)
    except (TypeError, ValueError):
        listing_entries = 0
    if report.get("source_accessed") is not True or listing_entries < 1:
        reasons.append("official_listing_not_accessed")
    if report.get("approved_period_metadata_unchanged") is not True:
        reasons.append("approved_period_metadata_not_confirmed_unchanged")
    if report.get("auto_applied") is not False:
        reasons.append("law_watch_auto_apply_state_not_safe")
    if proposals:
        reasons.append("new_legal_proposals_require_review")
    if not_verified:
        reasons.append("required_official_references_not_verified")
    return {
        "status": "pass" if not reasons else "blocked",
        "checked_at": report.get("checked_at"),
        "reason_codes": reasons,
        "unverified_sources": not_verified,
        "proposal_count": len(proposals),
        "source_accessed": report.get("source_accessed") is True,
        "auto_applied": report.get("auto_applied"),
    }


def _evaluate_form_formula(
    expression: str, values: dict[str, Decimal | None]
) -> Decimal | None:
    if not re.fullmatch(r"\s*\d{1,2}[a-z]?(?:\s*[+-]\s*\d{1,2}[a-z]?)*\s*", expression):
        raise VatDraftError(f"Công thức biểu mẫu không được hỗ trợ: {expression}")
    pieces = list(re.finditer(r"([+-]?)\s*(\d{1,2}[a-z]?)", expression))
    if not pieces:
        raise VatDraftError(f"Công thức biểu mẫu rỗng hoặc không hợp lệ: {expression}")
    total = Decimal(0)
    for index, piece in enumerate(pieces):
        line_code = piece.group(2)
        amount = values.get(line_code)
        if amount is None:
            return None
        sign = piece.group(1)
        total += amount if index == 0 or sign != "-" else -amount
    return total


def _form_field_draft(
    records: list[dict[str, Any]], version: str | None
) -> dict[str, Any] | None:
    if version is None:
        return None
    spec = _form_version_spec(version)
    allowed_revenue = FORM_REVENUE_FIELDS.get(version)
    if allowed_revenue is None:
        raise VatDraftError(f"Chưa hỗ trợ ánh xạ nháp cho mẫu {version}.")

    values: dict[str, Decimal | None] = {
        "23": Decimal(0),
        "23a": Decimal(0),
        "24": Decimal(0),
        "24a": Decimal(0),
        "25": None,
        "22": None,
        "37": None,
        "38": None,
        "39a": None,
        "40b": None,
        "42": None,
    }
    findings: list[dict[str, Any]] = []
    unmapped_rows: list[int] = []
    unmapped_purchase_rows: list[int] = []
    complete = True
    if not any(
        row["eligible_for_draft_totals"] and row["direction"] == "sales"
        for row in records
    ):
        complete = False
        findings.append(
            {
                "severity": "review",
                "code": "no_sales_records_for_form_mapping_requires_confirmation",
            }
        )

    for record in records:
        if not record["eligible_for_draft_totals"]:
            continue
        if record["direction"] == "purchases":
            value_code = record.get("form_line_code", "")
            tax_code = record.get("form_tax_line_code", "")
            if not value_code:
                complete = False
                unmapped_purchase_rows.append(record["source_row"])
                findings.append(
                    {
                        "severity": "review",
                        "code": "purchase_form_line_mapping_missing",
                        "source_row": record["source_row"],
                    }
                )
                continue
            if value_code not in FORM_PURCHASE_VALUE_FIELDS:
                complete = False
                findings.append(
                    {
                        "severity": "block",
                        "code": "purchase_form_line_not_supported",
                        "source_row": record["source_row"],
                        "line_code": value_code,
                    }
                )
                continue

            net_amount = Decimal(record["net_amount"])
            tax_amount = Decimal(record["tax_amount"])
            values["23"] += net_amount
            if value_code == "23a":
                values["23a"] = (values["23a"] or Decimal(0)) + net_amount

            expected_tax_code = PURCHASE_TAX_LINE_BY_VALUE[value_code]
            if tax_amount and not tax_code:
                complete = False
                findings.append(
                    {
                        "severity": "review",
                        "code": "purchase_form_tax_line_mapping_missing",
                        "source_row": record["source_row"],
                    }
                )
                continue
            if tax_code and tax_code not in FORM_PURCHASE_TAX_FIELDS:
                complete = False
                findings.append(
                    {
                        "severity": "block",
                        "code": "purchase_form_tax_line_not_supported",
                        "source_row": record["source_row"],
                        "line_code": tax_code,
                    }
                )
                continue
            if tax_code and tax_code != expected_tax_code:
                complete = False
                findings.append(
                    {
                        "severity": "block",
                        "code": "purchase_form_tax_line_mismatch",
                        "source_row": record["source_row"],
                        "value_line_code": value_code,
                        "tax_line_code": tax_code,
                        "expected_tax_line_code": expected_tax_code,
                    }
                )
                continue

            values["24"] += tax_amount
            if value_code == "23a":
                values["24a"] = (values["24a"] or Decimal(0)) + tax_amount
            continue
        if record["direction"] != "sales":
            continue

        revenue_code = record.get("form_line_code", "")
        tax_code = record.get("form_tax_line_code", "")
        if not revenue_code:
            complete = False
            unmapped_rows.append(record["source_row"])
            findings.append(
                {
                    "severity": "review",
                    "code": "sales_form_line_mapping_missing",
                    "source_row": record["source_row"],
                }
            )
        elif revenue_code not in allowed_revenue:
            complete = False
            findings.append(
                {
                    "severity": "block",
                    "code": "sales_form_line_not_in_selected_version",
                    "source_row": record["source_row"],
                    "line_code": revenue_code,
                }
            )
        else:
            values[revenue_code] = (values.get(revenue_code) or Decimal(0)) + Decimal(
                record["net_amount"]
            )

        tax_amount = Decimal(record["tax_amount"])
        if tax_amount and not tax_code:
            complete = False
            findings.append(
                {
                    "severity": "review",
                    "code": "sales_form_tax_line_mapping_missing",
                    "source_row": record["source_row"],
                }
            )
        elif tax_code and tax_code not in FORM_TAX_FIELDS:
            complete = False
            findings.append(
                {
                    "severity": "block",
                    "code": "sales_form_tax_line_not_supported",
                    "source_row": record["source_row"],
                    "line_code": tax_code,
                }
            )
        elif tax_code:
            values[tax_code] = (values.get(tax_code) or Decimal(0)) + tax_amount

    if complete:
        for line_code in (
            allowed_revenue
            | FORM_TAX_FIELDS
            | FORM_PURCHASE_VALUE_FIELDS
            | FORM_PURCHASE_TAX_FIELDS
        ):
            values.setdefault(line_code, Decimal(0))

    for line_code, expression in spec["verified_form_formulas"].items():
        values[line_code] = _evaluate_form_formula(expression, values)

    rendered_values = {
        code: money_text(amount) if amount is not None else None
        for code, amount in sorted(values.items())
    }
    blocked = any(item["severity"] == "block" for item in findings)
    return {
        "form_number": "01/GTGT",
        "version": version,
        "mapping_status": "blocked_invalid_line" if blocked else "review_required",
        "mapping_complete": complete and not blocked,
        "selected_by": "explicit_cli_selection",
        "line_mapping_source": "explicit source columns; no tax-rate inference",
        "amounts": rendered_values,
        "unmapped_sales_rows": sorted(unmapped_rows),
        "unmapped_purchase_rows": sorted(unmapped_purchase_rows),
        "findings": findings,
        "external_inputs_not_provided": [
            "22",
            "25",
            "37",
            "38",
            "39a",
            "40b",
            "42",
        ],
        "submission_ready": False,
        "output_type": "internal_json_draft_only",
    }


def _independent_form_check(
    records: list[dict[str, Any]], version: str, primary: dict[str, Any]
) -> dict[str, Any]:
    """Recompute mapped form fields in a separate pass over eligible invoice rows."""
    fields = FORM_REVENUE_FIELDS[version]
    if not any(
        row["eligible_for_draft_totals"] is True and row["direction"] == "sales"
        for row in records
    ):
        return {
            "status": "review_required",
            "reason": "sales records are absent; form mapping needs confirmation",
        }
    recomputed: dict[str, Decimal | None] = {
        "23": Decimal(0),
        "23a": Decimal(0),
        "24": Decimal(0),
        "24a": Decimal(0),
        "25": None,
        "22": None,
        "37": None,
        "38": None,
        "39a": None,
        "40b": None,
        "42": None,
    }
    for row in records:
        if row["eligible_for_draft_totals"] is not True:
            continue
        if row["direction"] == "purchases":
            value_code = row.get("form_line_code", "")
            tax_code = row.get("form_tax_line_code", "")
            if value_code not in FORM_PURCHASE_VALUE_FIELDS:
                return {
                    "status": "review_required",
                    "reason": "purchase value line is unmapped or unsupported",
                }
            expected_tax_code = PURCHASE_TAX_LINE_BY_VALUE[value_code]
            tax_amount = Decimal(str(row["tax_amount"]))
            if tax_amount and tax_code != expected_tax_code:
                return {
                    "status": "review_required",
                    "reason": "purchase tax line is unmapped or mismatched",
                }
            if tax_code and tax_code != expected_tax_code:
                return {
                    "status": "review_required",
                    "reason": "purchase tax line is mismatched",
                }

            net_amount = Decimal(str(row["net_amount"]))
            recomputed["23"] = Decimal(str(recomputed["23"])) + net_amount
            if value_code == "23a":
                recomputed["23a"] = Decimal(str(recomputed["23a"])) + net_amount
            recomputed["24"] = Decimal(str(recomputed["24"])) + tax_amount
            if value_code == "23a":
                recomputed["24a"] = Decimal(str(recomputed["24a"])) + tax_amount
        elif row["direction"] == "sales":
            revenue_code = row.get("form_line_code", "")
            tax_code = row.get("form_tax_line_code", "")
            if revenue_code not in fields:
                return {"status": "review_required", "reason": "sales line is unmapped"}
            recomputed[revenue_code] = Decimal(
                str(recomputed.get(revenue_code) or Decimal(0))
            ) + Decimal(str(row["net_amount"]))
            if Decimal(str(row["tax_amount"])):
                if tax_code not in FORM_TAX_FIELDS:
                    return {
                        "status": "review_required",
                        "reason": "sales tax line is unmapped",
                    }
                recomputed[tax_code] = Decimal(
                    str(recomputed.get(tax_code) or Decimal(0))
                ) + Decimal(str(row["tax_amount"]))
            elif tax_code:
                if tax_code not in FORM_TAX_FIELDS:
                    return {
                        "status": "review_required",
                        "reason": "sales tax line is invalid",
                    }
                recomputed[tax_code] = Decimal(
                    str(recomputed.get(tax_code) or Decimal(0))
                )

    for code in (
        fields | FORM_TAX_FIELDS | FORM_PURCHASE_VALUE_FIELDS | FORM_PURCHASE_TAX_FIELDS
    ):
        recomputed.setdefault(code, Decimal(0))

    formulas = _form_version_spec(version)["verified_form_formulas"]
    for code, expression in formulas.items():
        pieces = re.split(r"\s*([+-])\s*", expression.strip())
        if not pieces or len(pieces) % 2 == 0:
            return {"status": "fail", "reason": "unsupported official formula"}
        current = recomputed.get(pieces[0])
        if current is None:
            recomputed[code] = None
            continue
        result = current
        for offset in range(1, len(pieces), 2):
            operand = recomputed.get(pieces[offset + 1])
            if operand is None:
                result = None
                break
            result = result + operand if pieces[offset] == "+" else result - operand
        recomputed[code] = result

    rendered = {
        code: money_text(amount) if amount is not None else None
        for code, amount in sorted(recomputed.items())
    }
    matches = rendered == primary["amounts"]
    return {
        "status": "pass" if matches else "fail",
        "totals_match": matches,
        "recomputed_amounts": rendered,
        "method": "separate pass over source invoice rows and catalog formulas",
    }


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


def _normalized_document_record(
    record: dict[str, Any], item: dict[str, Any]
) -> dict[str, Any]:
    """Project a VAT row into the versioned shared accounting invoice contract."""
    raw = item.get("raw", {})
    document_kind = raw.get("document_kind")
    if document_kind not in {"invoice", "credit_note"}:
        document_kind = "unspecified"
    source_trace = record["source_trace"]
    tax_breakdown = raw.get("tax_breakdown")
    if not isinstance(tax_breakdown, list):
        tax_breakdown = [{
            "rate_label": record.get("tax_rate_label") or None,
            "taxable_amount": record.get("net_amount"),
            "tax_amount": record.get("tax_amount"),
        }]
    line_items = raw.get("line_items")
    if not isinstance(line_items, list):
        line_items = []
    references = raw.get("references")
    if not isinstance(references, list):
        references = []
    return {
        "schema_version": "1.0.0",
        "document_kind": document_kind,
        "identifier": {
            "number": record.get("invoice_number") or None,
            "series": record.get("invoice_series") or None,
        },
        "issued_at": record.get("invoice_date") or None,
        "parties": {
            "seller": {
                "tax_id": record.get("seller_tax_id") or None,
                "name": record.get("seller_name") or None,
            },
            "buyer": {
                "tax_id": record.get("buyer_tax_id") or None,
                "name": record.get("buyer_name") or None,
            },
        },
        "amounts": {
            "net": record.get("net_amount"),
            "tax": record.get("tax_amount"),
            "gross": record.get("gross_amount"),
        },
        "tax_breakdown": tax_breakdown,
        "line_items": {
            "extraction_status": raw.get("line_items_extraction_status", "not_extracted"),
            **({"items": line_items} if line_items else {}),
        },
        "relationships": {
            "extraction_status": raw.get("relationships_extraction_status", "not_extracted"),
            **({"references": references} if references else {}),
        },
        "source": {
            "file_name": source_trace.get("source_name"),
            "source_row": source_trace.get("source_row"),
            "sha256": source_trace.get("source_sha256"),
            "parser_profile": raw.get("source_profile", "tabular-invoice-v1"),
        },
    }


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
            "form_line_code": normalize_form_line_code(data.get("form_line_code", "")),
            "form_tax_line_code": normalize_form_line_code(
                data.get("form_tax_line_code", "")
            ),
            "tax_amount": money_text(amounts["tax_amount"])
            if amounts["tax_amount"] is not None
            else None,
            "gross_amount": money_text(amounts["gross_amount"])
            if amounts["gross_amount"] is not None
            else None,
            "invoice_status": data.get("status", "") or "unspecified",
            "formula_fields": formula_fields,
            "source_trace": {
                "source_name": item.get("source_name")
                or item["raw"].get("source_name"),
                "source_row": source_row,
                "source_sha256": item.get("source_sha256")
                or item["raw"].get("source_sha256"),
            },
            "eligible_for_draft_totals": False,
            "review_reasons": [],
        }
        record["normalized_document"] = _normalized_document_record(record, item)
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_draft(
    input_path: str | Path,
    taxpayer_tax_id: str,
    period: str,
    *,
    sheet_name: str | None = None,
    header_row: int | None = None,
    form_version: str | None = None,
    law_watch_report: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(input_path)
    if not source.is_file():
        raise VatDraftError("Tệp đầu vào không tồn tại hoặc không phải tệp thường.")
    start, end, period_type = period_window(period)
    if not taxpayer_tax_id.strip():
        raise VatDraftError("Cần MST người nộp thuế để phân loại mua vào/bán ra.")
    imported = read_invoice_rows(source, sheet_name, header_row)
    source_sha256 = _sha256_file(source)
    for item in imported:
        item.setdefault("source_name", source.name)
        item.setdefault("source_sha256", source_sha256)
    records, findings = _invoice_records(imported, taxpayer_tax_id, start, end)
    law_watch_review = (
        _review_law_watch_report(law_watch_report, form_version)
        if form_version
        else None
    )
    if form_version and law_watch_review and law_watch_review["status"] != "pass":
        form_field_draft = {
            "form_number": "01/GTGT",
            "version": form_version,
            "mapping_status": "blocked_legal_review",
            "mapping_complete": False,
            "amounts": {},
            "unmapped_sales_rows": [],
            "findings": [
                {
                    "severity": "block",
                    "code": "law_watch_review_not_passed",
                    "details": law_watch_review,
                }
            ],
            "submission_ready": False,
            "output_type": "internal_json_draft_only",
        }
    else:
        form_field_draft = _form_field_draft(records, form_version)
    if form_field_draft:
        findings.extend(form_field_draft["findings"])
    if imported and not any(record["eligible_for_draft_totals"] for record in records):
        findings.append(
            {"severity": "block", "code": "no_eligible_invoices_in_selected_period"}
        )
    totals = _aggregate(records)
    independent = _independent_check(records, totals)
    if not independent["totals_match"]:
        findings.append({"severity": "block", "code": "independent_check_failed"})
    if form_field_draft and form_field_draft["mapping_complete"]:
        independent_form = _independent_form_check(
            records, form_version, form_field_draft
        )
        form_field_draft["independent_check"] = independent_form
        if independent_form["status"] == "fail":
            findings.append(
                {"severity": "block", "code": "independent_form_check_failed"}
            )
    elif form_field_draft:
        form_field_draft["independent_check"] = {
            "status": "review_required",
            "reason": "form mapping is incomplete or contains invalid lines",
        }
    blocking = [item for item in findings if item["severity"] == "block"]
    if blocking:
        draft_status = "blocked_review_required"
    elif not form_field_draft:
        draft_status = "draft_ready_unmapped"
    elif form_field_draft["mapping_complete"]:
        draft_status = "draft_ready_for_review"
    else:
        draft_status = "draft_ready_partial_form"
    return {
        "tool": "accounting-vat-return-draft",
        "draft_status": draft_status,
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
            {
                "step": "import",
                "owner_roles": ["HD01"],
                "status": "completed",
                "records_read": len(imported),
            },
            {
                "step": "classify",
                "owner_roles": ["HD02", "HD03"],
                "status": "completed_with_review" if blocking else "completed",
                "rules": "party tax ID; never match by name",
            },
            {
                "step": "validate",
                "owner_roles": ["HD04"],
                "status": "review_required" if findings else "passed",
                "finding_count": len(findings),
            },
            {
                "step": "legal_review",
                "owner_roles": ["PL01", "PL02", "PL03", "PL04"],
                "reuses_skill": "accounting-law-watch",
                "status": law_watch_review["status"]
                if law_watch_review
                else "not_run; required before selecting a form version",
            },
            {
                "step": "aggregate",
                "owner_roles": ["TK01"],
                "status": "completed",
                "eligible_invoice_count": sum(
                    record["eligible_for_draft_totals"] for record in records
                ),
            },
            {
                "step": "prepare_draft",
                "owner_roles": ["BM01", "BM03"],
                "status": "prepared_for_review"
                if form_field_draft and form_field_draft["mapping_complete"]
                else "partial_or_unmapped",
            },
            {
                "step": "official_template_copy",
                "owner_roles": ["BM02"],
                "status": "NOT_STARTED",
            },
            {
                "step": "independent_check",
                "owner_roles": ["TK05"],
                "status": form_field_draft["independent_check"]["status"]
                if form_field_draft
                else independent["status"],
            },
            {
                "step": "export",
                "owner_roles": ["BM03"],
                "status": "review_only_json_or_internal_xlsx_with_field_draft"
                if form_field_draft
                else "review_only_json_or_internal_xlsx",
            },
            {
                "step": "approval",
                "owner_roles": ["KTT03"],
                "status": "human_approval_required",
            },
        ],
        "legal_form": {
            "form_number": "01/GTGT" if form_field_draft else None,
            "candidate_form_number": "01/GTGT",
            "version": form_version,
            "status": "EXPLICIT_VERSION_SELECTED; HUMAN_PERIOD_AND_TAXPAYER_REVIEW_REQUIRED"
            if form_version
            else "OFFICIAL_FORM_SOURCE_VERIFIED; PERIOD_AND_FIELD_EXPORT_MAPPING_REQUIRE_REVIEW",
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
            "selected_version_by": "user_cli_option" if form_version else None,
            "law_watch_review": law_watch_review,
            "field_mapping_status": form_field_draft["mapping_status"]
            if form_field_draft
            else "NOT_STARTED",
            "xml_export": "NOT_STARTED_SCHEMA_NOT_VERIFIED",
            "submission_ready": False,
            "note": "Bản JSON/XLSX chỉ là tài liệu soát xét nội bộ, không phải tờ khai pháp định. Mẫu được chọn tường minh qua CLI; người dùng vẫn phải xác nhận kỳ áp dụng, phân loại từng dòng, dữ liệu ngoài hóa đơn, phụ lục và điều kiện kê khai. Chưa điền mẫu XLSX chính thức hoặc lập XML.",
        },
        "totals": totals,
        "independent_check": independent,
        "form_field_draft": form_field_draft,
        "findings": findings,
        "records": records,
        "limitations": [
            "Chỉ nhận dữ liệu .xlsx hoặc .csv có hàng tiêu đề; XML/PDF/ảnh chưa triển khai.",
            "Đây là bản tổng hợp nội bộ, không phải tờ khai pháp định và không kết luận điều kiện khấu trừ.",
            "Mức thuế suất được giữ nguyên đúng nhãn nguồn; không suy thuế suất hoặc tự tính lại tiền thuế.",
            "Hóa đơn điều chỉnh, thay thế, hủy, trùng, ngoài kỳ hoặc có ô công thức cần xử lý thủ công trước khi tổng hợp.",
            "Tệp nguồn chỉ được đọc; workbook XLSX nội bộ không phải mẫu pháp định. Điền mẫu XLSX chính thức và XML chưa bắt đầu.",
        ],
    }


def write_draft(
    draft: dict[str, Any], output_path: str | Path, *, force: bool = False
) -> Path:
    destination = Path(output_path)
    output_format = destination.suffix.casefold()
    if output_format not in {".json", ".xlsx"}:
        raise VatDraftError("Chỉ xuất JSON hoặc workbook XLSX soát xét nội bộ.")
    source_name = str(draft.get("source_file", ""))
    if (
        destination.name == source_name
        and draft.get("input_format") == output_format.lstrip(".")
    ):
        raise VatDraftError("Không được ghi đè workbook hoặc CSV nguồn.")
    if destination.exists() and not force:
        raise VatDraftError("Tệp dự thảo đã tồn tại; dùng --force khi muốn ghi đè.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            if output_format == ".json":
                serialized = json.dumps(draft, ensure_ascii=False, indent=2) + "\n"
                temporary.write(serialized.encode("utf-8"))
            else:
                _write_internal_review_workbook(draft, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
        return destination
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _xml_safe_text(value: Any) -> str:
    text = str(value)
    cleaned = "".join(
        character
        for character in text
        if character in "\t\n\r"
        or " " <= character <= "\ud7ff"
        or "\ue000" <= character <= "\ufffd"
        or "\U00010000" <= character <= "\U0010ffff"
    )
    return html.escape(cleaned, quote=True)


def _xlsx_column_name(number: int) -> str:
    name = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _xlsx_sheet_xml(rows: list[list[Any]]) -> str:
    rendered_rows: list[str] = []
    for row_number, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_number, value in enumerate(row, start=1):
            reference = f"{_xlsx_column_name(column_number)}{row_number}"
            cells.append(
                f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">'
                f"{_xml_safe_text(value)}"
                "</t></is></c>"
            )
        rendered_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/><sheetData>'
        + "".join(rendered_rows)
        + "</sheetData></worksheet>"
    )


def _internal_review_sheets(
    draft: dict[str, Any],
) -> list[tuple[str, list[list[Any]]]]:
    legal_form = draft.get("legal_form", {})
    period = draft.get("period", {})
    form_fields = draft.get("form_field_draft") or {}
    law_watch = legal_form.get("law_watch_review") or {}
    overview = [
        ["BẢN SOÁT XÉT NỘI BỘ — KHÔNG PHẢI TỜ KHAI CHÍNH THỨC"],
        ["Trạng thái dự thảo", draft.get("draft_status", "")],
        ["Kỳ kê khai", period.get("label", "")],
        ["MST người nộp thuế", draft.get("taxpayer_tax_id", "")],
        ["Tệp nguồn", draft.get("source_file", "")],
        ["Phiên bản mẫu được chọn tường minh", legal_form.get("version") or "Chưa chọn"],
        ["Kết quả kiểm tra nguồn pháp luật", law_watch.get("status", "not_run")],
        [
            "Đối chiếu độc lập",
            (draft.get("independent_check") or {}).get("status", "not_run"),
        ],
        ["Sẵn sàng nộp", "KHÔNG — cần người có thẩm quyền rà soát và duyệt"],
        ["Mẫu XLSX pháp định", "NOT STARTED — workbook này không thay thế mẫu 01/GTGT"],
        ["XML/schema", legal_form.get("xml_export", "NOT_STARTED_SCHEMA_NOT_VERIFIED")],
        [
            "Lưu ý",
            "Không tự chọn mẫu, không tự áp dụng công thức pháp lý; giữ nguyên tệp nguồn.",
        ],
    ]
    summary: list[list[Any]] = [["Nhóm", "Chỉ tiêu", "Giá trị", "Ghi chú"]]
    for direction, values in draft.get("totals", {}).get("by_direction", {}).items():
        for key, value in values.items():
            summary.append(
                [direction, key, value, "Tổng trên hóa đơn đủ điều kiện soát xét"]
            )
    for bucket, values in (
        draft.get("totals", {}).get("by_direction_and_invoice_rate_label", {}).items()
    ):
        for key, value in values.items():
            summary.append(
                [bucket, key, value, "Giữ nguyên nhãn thuế suất từ nguồn"]
            )
    if form_fields:
        def field_order(item: tuple[str, Any]) -> tuple[int, str]:
            match = re.match(r"\d+", item[0])
            return (int(match.group()) if match else 999, item[0])

        for code, value in sorted(form_fields.get("amounts", {}).items(), key=field_order):
            summary.append(
                [
                    "Chỉ tiêu mẫu — dự thảo",
                    f"[{code}]",
                    "" if value is None else value,
                    "Cần rà mapping và dữ liệu ngoài hóa đơn",
                ]
            )
    else:
        summary.append(
            ["Chỉ tiêu mẫu — dự thảo", "NOT STARTED", "", "Chưa chọn phiên bản mẫu"]
        )

    invoices: list[list[Any]] = [
        [
            "Dòng nguồn",
            "Ngày hóa đơn",
            "Chiều",
            "MST người bán",
            "Tên người bán",
            "MST người mua",
            "Tên người mua",
            "Ký hiệu",
            "Số hóa đơn",
            "Thuế suất nguồn",
            "Trước thuế",
            "Tiền thuế",
            "Tổng thanh toán",
            "Trạng thái",
            "Đưa vào tổng",
            "Mã chỉ tiêu doanh thu",
            "Mã chỉ tiêu thuế",
        ]
    ]
    for record in draft.get("records", []):
        invoices.append(
            [
                record.get("source_row", ""),
                record.get("invoice_date", ""),
                record.get("direction", ""),
                record.get("seller_tax_id", ""),
                record.get("seller_name", ""),
                record.get("buyer_tax_id", ""),
                record.get("buyer_name", ""),
                record.get("invoice_series", ""),
                record.get("invoice_number", ""),
                record.get("tax_rate_label", ""),
                record.get("net_amount", ""),
                record.get("tax_amount", ""),
                record.get("gross_amount", ""),
                record.get("status", ""),
                "Có" if record.get("eligible_for_draft_totals") else "Không — cần soát",
                record.get("form_line_code", ""),
                record.get("form_tax_line_code", ""),
            ]
        )
    findings: list[list[Any]] = [["Mức độ", "Mã", "Dòng nguồn", "Chi tiết"]]
    for finding in draft.get("findings", []):
        findings.append(
            [
                finding.get("severity", ""),
                finding.get("code", ""),
                finding.get("source_row", ""),
                json.dumps(finding, ensure_ascii=False, sort_keys=True),
            ]
        )
    if len(findings) == 1:
        findings.append(
            [
                "info",
                "no_findings",
                "",
                "Không phát hiện ngoại lệ theo các kiểm tra tự động đã triển khai.",
            ]
        )
    return [
        ("00_Canh bao", overview),
        ("01_Tong hop", summary),
        ("02_Hoa don", invoices),
        ("03_Ngoai le", findings),
    ]


def _write_internal_review_workbook(draft: dict[str, Any], stream: Any) -> None:
    sheets = _internal_review_sheets(draft)
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pkg_rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    content_types_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    workbook_sheets = "".join(
        f'<sheet name="{_xml_safe_text(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _rows) in enumerate(sheets, start=1)
    )
    workbook_rels = "".join(
        f'<Relationship Id="rId{index}" Type="{rel_ns}/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, len(sheets) + 1)
    )
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, len(sheets) + 1)
    )
    parts = {
        "[Content_Types].xml": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Types xmlns="{content_types_ns}">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            f"{sheet_overrides}</Types>"
        ),
        "_rels/.rels": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{pkg_rel_ns}">'
            f'<Relationship Id="rId1" Type="{rel_ns}/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{main_ns}" xmlns:r="{rel_ns}">'
            f"<sheets>{workbook_sheets}</sheets></workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{pkg_rel_ns}">{workbook_rels}</Relationships>'
        ),
    }
    for index, (_name, rows) in enumerate(sheets, start=1):
        parts[f"xl/worksheets/sheet{index}.xml"] = _xlsx_sheet_xml(rows)
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content.encode("utf-8"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Tệp hóa đơn .xlsx, .csv hoặc XML UBL đơn lẻ.")
    parser.add_argument(
        "--taxpayer-tax-id", required=True, help="MST dùng để phân loại bên mua/bán."
    )
    parser.add_argument(
        "--period", required=True, help="Kỳ YYYY-MM hoặc YYYY-Q1..YYYY-Q4."
    )
    parser.add_argument(
        "--form-version",
        choices=("80/2021/TT-BTC", "89/2026/TT-BTC"),
        help="Chọn tường minh phiên bản mẫu; không tự suy ra theo kỳ.",
    )
    parser.add_argument(
        "--law-watch-report",
        help="JSON report từ accounting-law-watch; bắt buộc khi chọn phiên bản mẫu.",
    )
    parser.add_argument("--sheet", help="Tên sheet đầu vào .xlsx.")
    parser.add_argument(
        "--header-row",
        type=int,
        help="Số hàng tiêu đề trong Excel; mặc định hàng có dữ liệu đầu tiên.",
    )
    parser.add_argument(
        "--output", help="Đường dẫn JSON hoặc workbook XLSX soát xét nội bộ."
    )
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
            form_version=args.form_version,
            law_watch_report=args.law_watch_report,
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
