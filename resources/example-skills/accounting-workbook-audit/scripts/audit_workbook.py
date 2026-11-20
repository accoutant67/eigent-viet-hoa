#!/usr/bin/env python3
"""Read-only structural audit for .xlsx workbooks; standard library only."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import posixpath
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_XML_ENTRY_BYTES = 128 * 1024 * 1024
MAX_FINDINGS_PER_KIND = 200
CELL_REF_RE = re.compile(r"^\$?([A-Z]+)\$?(\d+)$", re.IGNORECASE)
ZERO_FORMAT_RE = re.compile(r"0+")


class WorkbookAuditError(ValueError):
    """Raised when a workbook cannot be audited safely."""


def _tag(name: str) -> str:
    return f"{{{MAIN_NS}}}{name}"


def _parse_xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise WorkbookAuditError(f"Workbook is missing {name}.") from exc
    if info.file_size > MAX_XML_ENTRY_BYTES:
        raise WorkbookAuditError(f"Workbook XML entry is too large: {name}.")
    data = archive.read(name)
    upper = data.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise WorkbookAuditError(f"Unsafe XML declarations are not accepted: {name}.")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise WorkbookAuditError(f"Invalid workbook XML: {name}.") from exc


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = _parse_xml(archive, "xl/sharedStrings.xml")
    values: list[str] = []
    for item in root.findall(_tag("si")):
        values.append("".join(node.text or "" for node in item.iter(_tag("t"))))
    return values


def _style_formats(archive: zipfile.ZipFile) -> dict[int, str]:
    if "xl/styles.xml" not in archive.namelist():
        return {}
    root = _parse_xml(archive, "xl/styles.xml")
    custom_formats: dict[int, str] = {}
    format_root = root.find(_tag("numFmts"))
    if format_root is not None:
        for item in format_root.findall(_tag("numFmt")):
            try:
                custom_formats[int(item.attrib["numFmtId"])] = item.attrib["formatCode"]
            except (KeyError, ValueError):
                continue

    xfs_root = root.find(_tag("cellXfs"))
    if xfs_root is None:
        return {}
    result: dict[int, str] = {}
    for style_index, item in enumerate(xfs_root.findall(_tag("xf"))):
        try:
            number_format_id = int(item.attrib.get("numFmtId", "0"))
        except ValueError:
            continue
        if number_format_id in custom_formats:
            result[style_index] = custom_formats[number_format_id]
    return result


def _column_index(cell_ref: str) -> int | None:
    match = CELL_REF_RE.fullmatch(cell_ref)
    if not match:
        return None
    index = 0
    for character in match.group(1).upper():
        index = index * 26 + ord(character) - ord("A") + 1
    return index


def _display_value(
    cell: ET.Element,
    shared_strings: list[str],
    style_formats: dict[int, str],
) -> tuple[str, bool, str | None]:
    """Return display-like value, formula flag, and Excel error code."""
    cell_type = cell.attrib.get("t", "")
    formula = cell.find(_tag("f"))
    value_element = cell.find(_tag("v"))
    raw_value = value_element.text if value_element is not None else ""

    if cell_type == "inlineStr":
        inline = cell.find(_tag("is"))
        value = (
            "".join(node.text or "" for node in inline.iter(_tag("t")))
            if inline is not None
            else ""
        )
    elif cell_type == "s":
        try:
            value = shared_strings[int(raw_value or "")]
        except (ValueError, IndexError):
            value = ""
    elif cell_type == "b":
        value = "TRUE" if raw_value == "1" else "FALSE" if raw_value == "0" else raw_value
    else:
        value = raw_value or ""

    error_code = value if cell_type == "e" else None

    if not cell_type and value:
        try:
            style_index = int(cell.attrib.get("s", "0"))
        except ValueError:
            style_index = 0
        number_format = style_formats.get(style_index, "").split(";")[0]
        if ZERO_FORMAT_RE.fullmatch(number_format) and re.fullmatch(r"\d+", value):
            value = value.zfill(len(number_format))

    return value, formula is not None, error_code


def _worksheet_path(target: str) -> str:
    target = target.replace("\\", "/")
    path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
    if path.startswith("../") or not path.startswith("xl/"):
        raise WorkbookAuditError("Workbook contains an invalid worksheet path.")
    return path


def _workbook_sheets(archive: zipfile.ZipFile) -> list[tuple[str, str, bool]]:
    workbook = _parse_xml(archive, "xl/workbook.xml")
    relationships = _parse_xml(archive, "xl/_rels/workbook.xml.rels")
    targets: dict[str, str] = {}
    for relationship in relationships.findall(f"{{{PKG_REL_NS}}}Relationship"):
        if relationship.attrib.get("TargetMode") == "External":
            continue
        relationship_id = relationship.attrib.get("Id")
        target = relationship.attrib.get("Target")
        if relationship_id and target:
            targets[relationship_id] = _worksheet_path(target)

    sheet_root = workbook.find(_tag("sheets"))
    if sheet_root is None:
        raise WorkbookAuditError("Workbook does not contain any worksheets.")

    sheets: list[tuple[str, str, bool]] = []
    for sheet in sheet_root.findall(_tag("sheet")):
        name = sheet.attrib.get("name")
        relationship_id = sheet.attrib.get(f"{{{DOC_REL_NS}}}id")
        if not name or not relationship_id or relationship_id not in targets:
            raise WorkbookAuditError("Workbook contains an invalid worksheet relationship.")
        path = targets[relationship_id]
        if path not in archive.namelist():
            raise WorkbookAuditError(f"Worksheet XML is missing for {name}.")
        sheets.append((name, path, sheet.attrib.get("state", "visible") != "visible"))
    return sheets


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _collect_sheet(
    archive: zipfile.ZipFile,
    sheet_name: str,
    path: str,
    hidden: bool,
    shared_strings: list[str],
    style_formats: dict[int, str],
) -> dict:
    root = _parse_xml(archive, path)
    rows: dict[int, dict[int, str]] = {}
    formula_cells: list[str] = []
    excel_errors: list[dict[str, str]] = []
    max_column = 0

    sheet_data = root.find(_tag("sheetData"))
    if sheet_data is not None:
        for row_element in sheet_data.findall(_tag("row")):
            try:
                row_number = int(row_element.attrib.get("r", "0"))
            except ValueError:
                continue
            if row_number < 1:
                continue
            row_values = rows.setdefault(row_number, {})
            for cell in row_element.findall(_tag("c")):
                cell_ref = cell.attrib.get("r", "")
                column = _column_index(cell_ref)
                if column is None:
                    continue
                max_column = max(max_column, column)
                value, has_formula, error_code = _display_value(
                    cell, shared_strings, style_formats
                )
                row_values[column] = value
                if has_formula:
                    formula_cells.append(cell_ref)
                if error_code:
                    excel_errors.append({"cell": cell_ref, "code": error_code})

    return {
        "name": sheet_name,
        "hidden": hidden,
        "rows": rows,
        "max_column": max_column,
        "formula_cells": formula_cells,
        "excel_errors": excel_errors,
    }


def _append_finding(
    findings: dict[str, list[dict]],
    counts: dict[str, int],
    kind: str,
    finding: dict,
) -> None:
    counts[kind] += 1
    if len(findings[kind]) < MAX_FINDINGS_PER_KIND:
        findings[kind].append(finding)


def _audit_sheet(
    sheet: dict,
    header_row: int,
    required_columns: list[str],
    key_columns: list[str],
) -> dict:
    rows = sheet["rows"]
    headers = rows.get(header_row, {})
    max_column = max(sheet["max_column"], max(headers, default=0))
    header_labels = [headers.get(column, "").strip() for column in range(1, max_column + 1)]
    header_map: dict[str, list[int]] = {}
    for column, label in enumerate(header_labels, start=1):
        normalized = _normalize_header(label)
        if normalized:
            header_map.setdefault(normalized, []).append(column)

    kinds = (
        "duplicate_rows",
        "duplicate_keys",
        "missing_required_values",
        "excel_errors",
        "missing_columns",
        "duplicate_headers",
    )
    findings = {kind: [] for kind in kinds}
    counts = {kind: 0 for kind in kinds}

    for columns in header_map.values():
        if len(columns) > 1:
            label = header_labels[columns[0] - 1]
            for column in columns[1:]:
                _append_finding(
                    findings,
                    counts,
                    "duplicate_headers",
                    {"header": label, "first_column": columns[0], "duplicate_column": column},
                )

    resolved_required: list[tuple[str, int]] = []
    for column_name in required_columns:
        matches = header_map.get(_normalize_header(column_name), [])
        if len(matches) == 1:
            resolved_required.append((column_name, matches[0]))
        else:
            _append_finding(
                findings,
                counts,
                "missing_columns",
                {
                    "column": column_name,
                    "purpose": "required",
                    "reason": "not_found" if not matches else "ambiguous_header",
                },
            )

    resolved_keys: list[tuple[str, int]] = []
    for column_name in key_columns:
        matches = header_map.get(_normalize_header(column_name), [])
        if len(matches) == 1:
            resolved_keys.append((column_name, matches[0]))
        else:
            _append_finding(
                findings,
                counts,
                "missing_columns",
                {
                    "column": column_name,
                    "purpose": "key",
                    "reason": "not_found" if not matches else "ambiguous_header",
                },
            )

    duplicate_rows_seen: dict[tuple[str, ...], int] = {}
    duplicate_keys_seen: dict[tuple[str, ...], int] = {}
    data_row_count = 0

    for row_number in sorted(rows):
        if row_number <= header_row:
            continue
        cell_map = rows[row_number]
        values = tuple(cell_map.get(column, "") for column in range(1, max_column + 1))
        if not any(value.strip() for value in values):
            continue
        data_row_count += 1

        first_row = duplicate_rows_seen.get(values)
        if first_row is None:
            duplicate_rows_seen[values] = row_number
        else:
            _append_finding(
                findings,
                counts,
                "duplicate_rows",
                {"first_row": first_row, "duplicate_row": row_number},
            )

        for column_name, column in resolved_required:
            if not cell_map.get(column, "").strip():
                _append_finding(
                    findings,
                    counts,
                    "missing_required_values",
                    {"row": row_number, "column": column_name},
                )

        if key_columns and len(resolved_keys) == len(key_columns):
            key = tuple(cell_map.get(column, "").strip() for _, column in resolved_keys)
            if all(key):
                first_key_row = duplicate_keys_seen.get(key)
                if first_key_row is None:
                    duplicate_keys_seen[key] = row_number
                else:
                    _append_finding(
                        findings,
                        counts,
                        "duplicate_keys",
                        {
                            "first_row": first_key_row,
                            "duplicate_row": row_number,
                            "columns": [name for name, _ in resolved_keys],
                        },
                    )

    for error in sheet["excel_errors"]:
        _append_finding(findings, counts, "excel_errors", error)

    issue_count = sum(counts.values())
    return {
        "name": sheet["name"],
        "hidden": sheet["hidden"],
        "header_row": header_row,
        "data_rows": data_row_count,
        "formula_cell_count": len(sheet["formula_cells"]),
        "formula_cell_sample": sheet["formula_cells"][:MAX_FINDINGS_PER_KIND],
        "findings": findings,
        "finding_counts": counts,
        "findings_truncated": {
            kind: counts[kind] > len(findings[kind]) for kind in kinds
        },
        "issue_count": issue_count,
    }


def audit_workbook(
    input_path: str | Path,
    *,
    sheet_names: list[str] | None = None,
    header_row: int = 1,
    required_columns: list[str] | None = None,
    key_columns: list[str] | None = None,
    max_uncompressed_bytes: int = MAX_UNCOMPRESSED_BYTES,
) -> dict:
    """Inspect workbook structure and return a JSON-serializable report."""
    path = Path(input_path)
    if path.suffix.lower() != ".xlsx":
        raise WorkbookAuditError("Only .xlsx workbooks are supported.")
    if not path.is_file():
        raise WorkbookAuditError("Input workbook does not exist or is not a file.")
    if header_row < 1:
        raise WorkbookAuditError("Header row must be 1 or greater.")
    if max_uncompressed_bytes < 1:
        raise WorkbookAuditError("Maximum workbook size must be positive.")

    required_columns = required_columns or []
    key_columns = key_columns or []

    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise WorkbookAuditError("Workbook contains duplicate ZIP entries.")
            uncompressed_size = sum(info.file_size for info in infos)
            if uncompressed_size > max_uncompressed_bytes:
                raise WorkbookAuditError("Workbook exceeds the configured size limit.")
            if "xl/workbook.xml" not in names or "xl/_rels/workbook.xml.rels" not in names:
                raise WorkbookAuditError("File is not a supported .xlsx workbook.")

            all_sheets = _workbook_sheets(archive)
            if sheet_names:
                by_name = {name.casefold(): (name, sheet_path, hidden) for name, sheet_path, hidden in all_sheets}
                selected: list[tuple[str, str, bool]] = []
                for requested in sheet_names:
                    item = by_name.get(requested.casefold())
                    if item is None:
                        raise WorkbookAuditError(f"Worksheet was not found: {requested}.")
                    if item not in selected:
                        selected.append(item)
                sheets_to_audit = selected
            else:
                sheets_to_audit = all_sheets

            shared_strings = _shared_strings(archive)
            style_formats = _style_formats(archive)
            sheet_reports = [
                _audit_sheet(
                    _collect_sheet(
                        archive,
                        name,
                        sheet_path,
                        hidden,
                        shared_strings,
                        style_formats,
                    ),
                    header_row,
                    required_columns,
                    key_columns,
                )
                for name, sheet_path, hidden in sheets_to_audit
            ]
    except zipfile.BadZipFile as exc:
        raise WorkbookAuditError("Input file is not a valid .xlsx ZIP package.") from exc
    except OSError as exc:
        raise WorkbookAuditError(f"Could not read workbook: {exc}") from exc

    total_issues = sum(sheet["issue_count"] for sheet in sheet_reports)
    total_formulas = sum(sheet["formula_cell_count"] for sheet in sheet_reports)
    total_data_rows = sum(sheet["data_rows"] for sheet in sheet_reports)
    return {
        "tool": "accounting-workbook-audit",
        "status": "review_required" if total_issues else "no_findings",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "input_file": path.name,
        "summary": {
            "sheet_count": len(sheet_reports),
            "data_row_count": total_data_rows,
            "formula_cell_count": total_formulas,
            "issue_count": total_issues,
        },
        "sheets": sheet_reports,
        "limitations": [
            "Đây là rà soát cấu trúc dữ liệu, không phải kết luận kế toán hoặc pháp lý.",
            "Không tính lại công thức; ô công thức được kiểm tra theo giá trị lưu sẵn trong tệp.",
            "Không sửa tệp nguồn, không xóa dòng và không tự điền dữ liệu.",
            "Các dòng trùng là cảnh báo để kế toán xem xét, không phải đề nghị xóa tự động.",
        ],
    }


def write_report(report: dict, output_path: str | Path, *, force: bool = False) -> Path:
    destination = Path(output_path)
    if destination.exists() and not force:
        raise WorkbookAuditError("Report already exists; use --force to replace it.")
    destination.parent.mkdir(parents=True, exist_ok=True)
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
            json.dump(report, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
        return destination
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rà soát cấu trúc .xlsx theo chế độ chỉ đọc, xuất báo cáo JSON riêng."
    )
    parser.add_argument("input", help="Đường dẫn tệp .xlsx cần rà soát.")
    parser.add_argument("--output", help="Đường dẫn báo cáo .audit.json.")
    parser.add_argument("--sheet", action="append", dest="sheets", help="Tên sheet cần rà soát; có thể lặp.")
    parser.add_argument("--header-row", type=int, default=1, help="Hàng tiêu đề (mặc định: 1).")
    parser.add_argument(
        "--required-column",
        action="append",
        default=[],
        help="Tên cột bắt buộc; có thể lặp.",
    )
    parser.add_argument(
        "--key-column",
        action="append",
        default=[],
        help="Cột khóa để phát hiện trùng; có thể lặp để tạo khóa ghép.",
    )
    parser.add_argument(
        "--max-uncompressed-mb",
        type=int,
        default=256,
        help="Giới hạn tổng dung lượng giải nén (mặc định: 256 MiB).",
    )
    parser.add_argument("--force", action="store_true", help="Cho phép thay báo cáo đã tồn tại.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_name(
        f"{input_path.stem}.audit.json"
    )
    try:
        if input_path.exists() and output_path.resolve() == input_path.resolve():
            raise WorkbookAuditError("Report path must not overwrite the input workbook.")
        report = audit_workbook(
            input_path,
            sheet_names=args.sheets,
            header_row=args.header_row,
            required_columns=args.required_column,
            key_columns=args.key_column,
            max_uncompressed_bytes=args.max_uncompressed_mb * 1024 * 1024,
        )
        write_report(report, output_path, force=args.force)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (WorkbookAuditError, OSError, ET.ParseError) as exc:
        print(
            json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
