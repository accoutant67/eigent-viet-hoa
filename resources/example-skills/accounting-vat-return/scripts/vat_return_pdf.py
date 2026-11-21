"""Create a review-only overlay on an officially published 01/GTGT PDF."""

from __future__ import annotations

import datetime as dt
import io
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATES = _ROOT / "templates"
_FONT_PATH = _TEMPLATES / "NotoSans-Regular.ttf"
_FONT_NAME = "VatNotoSans"
_TT40_UPDATED_NOTE = (
    "2. Chỉ tiêu [09], [10], [11]: Khai thông tin của đơn vị phụ thuộc, "
    "địa điểm kinh doanh đóng tại địa bàn khác tỉnh nơi đóng trụ sở chính "
    "đối với các trường hợp quy định tại điểm b, c khoản 1 Điều 11 Nghị "
    "định số 126/2020/NĐ-CP ngày 19/10/2020 của Chính phủ. Trường hợp có "
    "nhiều đơn vị phụ thuộc, địa điểm kinh doanh đóng trên nhiều "
    "xã/phường/đặc khu do Cục Thuế quản lý thì chọn 1 đơn vị đại diện để "
    "kê khai vào chỉ tiêu này. Trường hợp có nhiều đơn vị phụ thuộc, địa "
    "điểm kinh doanh đóng trên nhiều xã/phường/đặc khu do Chi cục Thuế khu "
    "vực quản lý thì chọn 1 đơn vị đại diện cho xã/phường/đặc khu do Chi "
    "cục Thuế khu vực quản lý để kê khai vào chỉ tiêu này."
)

# Coordinates are in PDF points. They were read from the official TT80 page
# text layer and visually checked against the official scanned TT89 pages.
_TT80_ROWS = {
    "22": (0, 513.0, 345.1),
    "23": (0, 440.5, 297.1),
    "24": (0, 513.0, 297.1),
    "23a": (0, 440.5, 281.1),
    "24a": (0, 513.0, 281.1),
    "25": (0, 513.0, 265.1),
    "26": (0, 440.5, 233.1),
    "27": (0, 440.5, 211.3),
    "28": (0, 513.0, 211.3),
    "29": (0, 440.5, 189.6),
    "30": (0, 440.5, 173.6),
    "31": (0, 513.0, 173.6),
    "32": (0, 440.5, 157.6),
    "33": (0, 513.0, 157.6),
    "32a": (0, 440.5, 141.6),
    "34": (0, 440.5, 119.8),
    "35": (0, 513.0, 119.8),
    "36": (0, 513.0, 98.1),
    "37": (1, 513.0, 681.8),
    "38": (1, 513.0, 666.8),
    "39a": (1, 513.0, 651.8),
    "40a": (1, 513.0, 615.4),
    "40b": (1, 513.0, 588.1),
    "40": (1, 513.0, 567.3),
    "41": (1, 513.0, 552.3),
    "42": (1, 513.0, 537.3),
    "43": (1, 513.0, 522.3),
}

_TT89_ROWS = {
    "22": (0, 510.0, 391.0),
    "23": (0, 428.0, 352.7),
    "24": (0, 510.0, 352.7),
    "23a": (0, 428.0, 339.2),
    "24a": (0, 510.0, 339.2),
    "25": (0, 510.0, 325.5),
    "26": (0, 428.0, 297.8),
    "27": (0, 428.0, 276.7),
    "28": (0, 510.0, 276.7),
    "29": (0, 428.0, 263.6),
    "30": (0, 428.0, 250.6),
    "31": (0, 510.0, 250.6),
    "32": (0, 428.0, 237.6),
    "33": (0, 510.0, 237.6),
    "32a": (0, 428.0, 224.6),
    "32b": (0, 428.0, 211.2),
    "34a": (0, 428.0, 194.4),
    "34": (0, 428.0, 172.5),
    "35": (0, 510.0, 172.5),
    "36": (0, 510.0, 159.0),
    "37": (0, 510.0, 132.0),
    "38": (0, 510.0, 118.5),
    "39a": (0, 510.0, 105.0),
    "40a": (0, 510.0, 74.5),
    "40b": (1, 510.0, 771.0),
    "40": (1, 510.0, 757.0),
    "41": (1, 510.0, 743.5),
    "42": (1, 510.0, 730.0),
    "43": (1, 510.0, 716.5),
}


def _register_font() -> None:
    if _FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_FONT_NAME, str(_FONT_PATH)))


def _period(period: dict[str, Any]) -> tuple[str, dt.date]:
    label = str(period.get("label", "")).upper()
    month = re.fullmatch(r"(\d{4})-(\d{2})", label)
    quarter = re.fullmatch(r"(\d{4})-Q([1-4])", label)
    if month:
        year, month_number = map(int, month.groups())
        if not 1 <= month_number <= 12:
            raise ValueError("Kỳ tháng không hợp lệ cho xuất PDF.")
        return f"Tháng {month_number:02d} năm {year}", dt.date(year, month_number, 1)
    if quarter:
        year, quarter_number = map(int, quarter.groups())
        return f"Quý {quarter_number} năm {year}", dt.date(
            year, quarter_number * 3 - 2, 1
        )
    raise ValueError("Kỳ phải có dạng YYYY-MM hoặc YYYY-Q1 đến YYYY-Q4.")


def _validate_draft(draft: dict[str, Any]) -> tuple[str, str]:
    form = draft.get("legal_form") or {}
    fields = draft.get("form_field_draft") or {}
    version = form.get("version")
    if version not in {"80/2021/TT-BTC", "89/2026/TT-BTC"}:
        raise ValueError("PDF chỉ xuất khi đã chọn rõ phiên bản mẫu 01/GTGT.")
    if form.get("status") != "APPLICABILITY_AND_LAW_REVIEW_PASS_FOR_INTERNAL_DRAFT":
        raise ValueError("Rà soát phạm vi mẫu hoặc pháp lý chưa đạt; không xuất PDF.")
    applicability = form.get("applicability_review") or {}
    law_review = form.get("law_watch_review") or {}
    if (
        applicability.get("status") != "pass"
        or applicability.get("filing_type") != "first"
    ):
        raise ValueError("Chỉ hỗ trợ hồ sơ lần đầu đã qua rà soát phạm vi.")
    if law_review.get("status") != "pass":
        raise ValueError("Báo cáo law-watch chưa đạt; không xuất PDF.")
    if fields.get("mapping_status") == "blocked_applicability_or_legal_review":
        raise ValueError("Mẫu đang bị chặn theo rà soát pháp lý/phạm vi.")
    if draft.get("draft_status") == "blocked_review_required":
        raise ValueError("Dự thảo có lỗi chặn; cần xử lý trước khi xuất PDF.")
    if any(item.get("severity") == "block" for item in draft.get("findings", [])):
        raise ValueError("Dự thảo có phát hiện mức chặn; không xuất PDF.")
    if (
        fields.get("submission_ready") is not False
        or form.get("submission_ready") is not False
    ):
        raise ValueError("Tệp không phải hồ sơ có thể nộp; trạng thái không hợp lệ.")
    period_label, period_start = _period(draft.get("period") or {})
    if version == "80/2021/TT-BTC" and not (
        dt.date(2022, 1, 1) <= period_start < dt.date(2026, 7, 1)
    ):
        raise ValueError("Kỳ này nằm ngoài thời gian áp dụng mẫu TT80 đã rà soát.")
    if version == "89/2026/TT-BTC" and period_start < dt.date(2026, 7, 1):
        raise ValueError("Kỳ này nằm trước thời gian áp dụng mẫu TT89.")
    return version, period_label


def _fit_text(canvas: Canvas, text: str, x: float, y: float, max_width: float) -> None:
    text = " ".join(str(text).split())
    if not text:
        return
    size = 8.5
    while size > 5.5 and pdfmetrics.stringWidth(text, _FONT_NAME, size) > max_width:
        size -= 0.25
    canvas.setFont(_FONT_NAME, size)
    canvas.drawString(x, y, text)


def _draw_header(
    canvas: Canvas, draft: dict[str, Any], version: str, period_label: str
) -> None:
    if version == "80/2021/TT-BTC":
        period_box = (258.0, 604.5, 278.0, 14.0)
        period_x, period_y = 260.0, 610.7
        name_x, name_y, name_width = 158.0, 576.7, 368.0
        id_y = 560.4
        # The official 10-digit cells and the 3-digit branch code cells.
        digit_centers = [187.7 + 17.35 * idx for idx in range(10)] + [
            374.0,
            385.8,
            397.5,
        ]
        canvas.setFillColorRGB(1, 1, 1)
        canvas.rect(*period_box, fill=1, stroke=0)
        if period_start_is_tt40(period_label):
            canvas.rect(76.0, 452.5, 455.0, 13.0, fill=1, stroke=0)
            canvas.setFillColorRGB(0, 0, 0)
            canvas.setFont(_FONT_NAME, 7.2)
            canvas.drawString(
                78.0,
                457.9,
                "[11a] Xã/phường/đặc khu .......................... [11c] Tỉnh/Thành phố .................................",
            )
    else:
        period_box = (258.0, 650.0, 180.0, 16.0)
        period_x, period_y = 260.0, 657.0
        name_x, name_y, name_width = 168.0, 620.0, 362.0
        id_y = 602.5
        digit_centers = []
        canvas.setFillColorRGB(1, 1, 1)
        canvas.rect(*period_box, fill=1, stroke=0)

    canvas.setFillColorRGB(0, 0, 0)
    _fit_text(canvas, period_label, period_x, period_y, 170.0)
    _fit_text(canvas, draft.get("taxpayer_name") or "", name_x, name_y, name_width)
    tax_id = re.sub(r"\D", "", str(draft.get("taxpayer_tax_id") or ""))
    if version == "80/2021/TT-BTC":
        if len(tax_id) > len(digit_centers):
            raise ValueError("MST có độ dài vượt quá số ô của mẫu TT80.")
        canvas.setFont(_FONT_NAME, 8.5)
        for digit, center_x in zip(tax_id, digit_centers):
            canvas.drawCentredString(center_x, id_y, digit)
    else:
        _fit_text(canvas, tax_id, 121.0, id_y, 365.0)
    # Form [02] is marked only for the first filing, which is the sole
    # filing type currently supported by the form applicability review.
    canvas.setFont(_FONT_NAME, 10.0)
    canvas.drawString(
        258.0 if version == "80/2021/TT-BTC" else 249.0,
        595.0 if version == "80/2021/TT-BTC" else 641.0,
        "X",
    )


def period_start_is_tt40(period_label: str) -> bool:
    match = re.search(r"(\d{4})", period_label)
    year = int(match.group(1)) if match else 0
    month_match = re.search(r"Tháng (\d{2})", period_label)
    if month_match:
        return (year, int(month_match.group(1))) >= (2025, 7)
    quarter_match = re.search(r"Quý (\d)", period_label)
    return bool(quarter_match and (year, int(quarter_match.group(1))) >= (2025, 3))


def _draw_watermark(canvas: Canvas, width: float, height: float) -> None:
    canvas.saveState()
    canvas.setFillAlpha(0.13)
    canvas.setFillColorRGB(0.74, 0.06, 0.06)
    canvas.translate(width / 2, height / 2)
    canvas.rotate(28)
    canvas.setFont(_FONT_NAME, 26)
    canvas.drawCentredString(0, 8, "DỰ THẢO")
    canvas.setFont(_FONT_NAME, 11)
    canvas.drawCentredString(0, -12, "CHƯA KÝ — CHƯA NỘP")
    canvas.restoreState()


def _draw_tt40_updated_note(canvas: Canvas) -> None:
    """Replace the old district wording in TT80's printed instructions."""
    x, top, width, box_height = 64.0, 331.5, 468.0, 82.5
    bottom = top - box_height
    canvas.saveState()
    canvas.setFillColorRGB(1, 1, 1)
    canvas.rect(x, bottom, width, box_height, fill=1, stroke=0)
    style = ParagraphStyle(
        "tt40_updated_note",
        fontName=_FONT_NAME,
        fontSize=8.0,
        leading=9.6,
        textColor="black",
        alignment=4,
        spaceAfter=0,
        spaceBefore=0,
    )
    paragraph = Paragraph(_TT40_UPDATED_NOTE, style)
    _wrapped_width, paragraph_height = paragraph.wrap(width, box_height)
    if paragraph_height > box_height:
        raise ValueError("Ghi chú TT40 không vừa vùng mẫu đã xác minh.")
    paragraph.drawOn(canvas, x, top - paragraph_height)
    canvas.restoreState()


def _amount_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Số tiền chỉ tiêu không hợp lệ: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError("Số tiền chỉ tiêu phải là số hữu hạn.")
    return format(amount, "f")


def _draw_amounts(
    canvas: Canvas,
    amounts: dict[str, Any],
    rows: dict[str, tuple[int, float, float]],
    page_index: int,
    version: str,
) -> None:
    if version == "80/2021/TT-BTC":
        right_edge = {"value": 467.0, "tax": 530.0}
        value_codes = {
            "23",
            "23a",
            "26",
            "27",
            "29",
            "30",
            "32",
            "32a",
            "32b",
            "34a",
            "34",
        }
        cell_widths = {"value": 51.0, "tax": 34.0}
    else:
        right_edge = {"value": 454.0, "tax": 536.0}
        value_codes = {
            "23",
            "23a",
            "26",
            "27",
            "29",
            "30",
            "32",
            "32a",
            "32b",
            "34a",
            "34",
        }
        cell_widths = {"value": 49.0, "tax": 49.0}
    for code, value in amounts.items():
        position = rows.get(str(code))
        text = _amount_text(value)
        if position is None or position[0] != page_index or not text:
            continue
        column = "value" if str(code) in value_codes else "tax"
        edge = right_edge[column] - 3.0
        cell_width = cell_widths[column]
        font_size = 8.0
        while (
            font_size > 5.5
            and pdfmetrics.stringWidth(text, _FONT_NAME, font_size) > cell_width
        ):
            font_size -= 0.25
        canvas.setFillColorRGB(0, 0, 0)
        canvas.setFont(_FONT_NAME, font_size)
        canvas.drawRightString(edge, position[2], text)


def _overlay_page(
    page_index: int,
    page_size: tuple[float, float],
    draft: dict[str, Any],
    version: str,
    period_label: str,
) -> bytes:
    width, height = page_size
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=page_size, pageCompression=1)
    _register_font()
    if page_index == 0:
        _draw_header(canvas, draft, version, period_label)
    if (
        page_index == 1
        and version == "80/2021/TT-BTC"
        and period_start_is_tt40(period_label)
    ):
        _draw_tt40_updated_note(canvas)
    _draw_watermark(canvas, width, height)
    fields = draft.get("form_field_draft") or {}
    rows = _TT89_ROWS if version == "89/2026/TT-BTC" else _TT80_ROWS
    _draw_amounts(canvas, fields.get("amounts") or {}, rows, page_index, version)
    canvas.save()
    return stream.getvalue()


def write_official_template_pdf(draft: dict[str, Any], destination: Path) -> None:
    """Overlay reviewed values onto the verified official form pages."""
    version, period_label = _validate_draft(draft)
    template_name = (
        "tt89-01-gtgt-template.pdf"
        if version == "89/2026/TT-BTC"
        else "tt80-01-gtgt-template.pdf"
    )
    template = _TEMPLATES / template_name
    if not template.is_file():
        raise ValueError(f"Không tìm thấy mẫu PDF chính thức: {template_name}")
    reader = PdfReader(str(template))
    if len(reader.pages) != 2:
        raise ValueError("Mẫu 01/GTGT đã lưu không có đủ 2 trang đã xác minh.")
    writer = PdfWriter()
    for page_index, page in enumerate(reader.pages):
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        overlay = PdfReader(
            io.BytesIO(
                _overlay_page(
                    page_index,
                    (page_width, page_height),
                    draft,
                    version,
                    period_label,
                )
            )
        ).pages[0]
        writer.add_page(page)
        writer.pages[-1].merge_page(overlay)
    writer.add_metadata(
        {
            "/Title": f"Dự thảo 01/GTGT — {period_label}",
            "/Subject": "DỰ THẢO — CHƯA KÝ — CHƯA NỘP; cần kế toán rà soát",
            "/Author": "",
        }
    )
    with destination.open("wb") as output:
        writer.write(output)
