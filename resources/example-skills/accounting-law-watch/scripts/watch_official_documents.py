#!/usr/bin/env python3
"""Proposal-only monitor for relevant documents on the Government portal."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

OFFICIAL_LISTING_URL = (
    "https://vanban.chinhphu.vn/he-thong-van-ban?classid=0&maxresults=50&mode=1"
)
OFFICIAL_HOST = "vanban.chinhphu.vn"
USER_AGENT = "EigentAccountingLawWatch/0.1 (+read-only official-source monitor)"
MAX_RESPONSE_BYTES = 5_000_000
MAX_DETAIL_PAGES = 20

_CITATION_RE = re.compile(
    r"(?<![\w])\d{1,4}\s*/\s*\d{4}\s*/\s*"
    r"(?:TT|NĐ|ND|QĐ|QD|VBHN|L|CT|QH|NQ|NĐ-CP|ND-CP)"
    r"(?:[-/][A-ZĐ0-9]+)*(?![\w])",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?!\d)")
_EFFECTIVE_LABEL_RE = re.compile(
    r"Ngày\s+có\s+hiệu\s+lực\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
    re.IGNORECASE,
)
_ISSUED_LABEL_RE = re.compile(
    r"Ngày\s+ban\s+hành\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
    re.IGNORECASE,
)
_TOPIC_TERMS = (
    "thue",
    "ke toan",
    "bao hiem xa hoi",
    "hoa don",
    "gia tri gia tang",
    "thu nhap ca nhan",
    "thu nhap doanh nghiep",
    "to khai",
    "bao cao tai chinh",
    "che do ke toan",
)


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return " ".join(
        "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        .replace("đ", "d")
        .split()
    )


def normalize_citation(value: str) -> str:
    return re.sub(r"\s+", "", value.upper().replace("Đ", "D"))


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        pass
    match = _DATE_RE.search(value)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def citation_from_text(value: str) -> str | None:
    match = _CITATION_RE.search(value)
    return normalize_citation(match.group(0)) if match else None


def is_relevant_document(citation: str | None, title: str) -> bool:
    normalized = normalize_text(f"{citation or ''} {title}")
    return any(term in normalized for term in _TOPIC_TERMS)


def official_url(value: str, base_url: str = OFFICIAL_LISTING_URL) -> str:
    resolved = urljoin(base_url, value)
    parsed = urlparse(resolved)
    if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
        raise ValueError("Chỉ cho phép truy cập vanban.chinhphu.vn qua HTTPS")
    return resolved


class _AllowlistedRedirectHandler(HTTPRedirectHandler):
    """Reject redirects before the client contacts a non-allowlisted host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl, req.full_url)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _PortalListingParser(HTMLParser):
    """Collect table rows and links without relying on portal CSS classes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, object]] = []
        self.links: list[dict[str, str]] = []
        self._row: dict[str, object] | None = None
        self._cell: dict[str, object] | None = None
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "tr":
            self._row = {"cells": [], "links": []}
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = {"parts": [], "links": []}
        elif tag == "a":
            href = attr_map.get("href")
            self._anchor_href = href or ""
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["parts"].append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            link = {"href": self._anchor_href, "text": " ".join(self._anchor_text)}
            self.links.append(link)
            if self._row is not None:
                self._row["links"].append(link)
            if self._cell is not None:
                self._cell["links"].append(link)
            self._anchor_href = None
            self._anchor_text = []
        elif tag in {"td", "th"} and self._cell is not None:
            self._cell["text"] = " ".join(self._cell.pop("parts")).strip()
            if self._row is not None:
                self._row["cells"].append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def _doc_id(url: str) -> str | None:
    try:
        values = parse_qs(urlparse(url).query).get("docid", [])
        return values[0] if values else None
    except (TypeError, ValueError):
        return None


def parse_listing(
    html: str, base_url: str = OFFICIAL_LISTING_URL
) -> list[dict[str, str | None]]:
    parser = _PortalListingParser()
    parser.feed(html)
    rows = parser.rows
    if not rows:
        rows = [{"cells": [], "links": parser.links}]

    documents: dict[str, dict[str, str | None]] = {}
    for row in rows:
        cells = row["cells"]
        links = row["links"]
        if not isinstance(cells, list) or not isinstance(links, list):
            continue
        normalized_links: list[dict[str, str]] = []
        for link in links:
            try:
                resolved = official_url(link.get("href", ""), base_url)
            except ValueError:
                continue
            if _doc_id(resolved):
                normalized_links.append(
                    {"href": resolved, "text": link.get("text", "")}
                )
        if not normalized_links:
            continue

        grouped: dict[str, list[dict[str, str]]] = {}
        for link in normalized_links:
            identifier = _doc_id(link["href"])
            if identifier:
                grouped.setdefault(identifier, []).append(link)

        cell_texts = [str(cell.get("text", "")) for cell in cells]
        row_texts = cell_texts + [link["text"] for link in normalized_links]
        citation = next(
            (found for value in row_texts if (found := citation_from_text(value))),
            None,
        )
        dates = [parsed for value in row_texts if (parsed := parse_date(value))]
        published_on = dates[0] if dates else None

        title_candidates = [
            link["text"].strip()
            for link in normalized_links
            if len(link["text"].strip()) > 8
            and not citation_from_text(link["text"])
            and not parse_date(link["text"])
        ]
        title = max(title_candidates, key=len, default="").strip()
        if not title:
            title = next(
                (
                    text.strip()
                    for text in cell_texts
                    if len(text.strip()) > 8
                    and not citation_from_text(text)
                    and not parse_date(text)
                ),
                "",
            )

        for identifier, doc_links in grouped.items():
            detail_url = doc_links[0]["href"]
            record = documents.setdefault(
                identifier,
                {
                    "document_id": identifier,
                    "citation": citation,
                    "title": title,
                    "published_on": published_on,
                    "source_url": detail_url,
                },
            )
            if not record.get("citation") and citation:
                record["citation"] = citation
            if len(title) > len(str(record.get("title") or "")):
                record["title"] = title
            if not record.get("published_on") and published_on:
                record["published_on"] = published_on

    if not documents:
        grouped_links: dict[str, list[dict[str, str]]] = {}
        for link in parser.links:
            try:
                resolved = official_url(link.get("href", ""), base_url)
            except ValueError:
                continue
            identifier = _doc_id(resolved)
            if identifier:
                grouped_links.setdefault(identifier, []).append(
                    {"href": resolved, "text": link.get("text", "")}
                )
        for identifier, links in grouped_links.items():
            texts = [link["text"] for link in links]
            citation = next(
                (found for value in texts if (found := citation_from_text(value))),
                None,
            )
            title_candidates = [
                value.strip()
                for value in texts
                if len(value.strip()) > 8
                and not citation_from_text(value)
                and not parse_date(value)
            ]
            documents[identifier] = {
                "document_id": identifier,
                "citation": citation,
                "title": max(title_candidates, key=len, default=""),
                "published_on": next(
                    (parsed for value in texts if (parsed := parse_date(value))),
                    None,
                ),
                "source_url": links[0]["href"],
            }
    return list(documents.values())


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def parse_detail_metadata(html: str) -> dict[str, str | None]:
    parser = _TextCollector()
    parser.feed(html)
    text = " ".join(parser.parts)
    issued = _ISSUED_LABEL_RE.search(text)
    effective = _EFFECTIVE_LABEL_RE.search(text)
    return {
        "issued_on": parse_date(issued.group(1)) if issued else None,
        "effective_from": parse_date(effective.group(1)) if effective else None,
    }


def _matches_period(rule: dict[str, object], period_start: str) -> bool:
    if rule.get("approval_state") != "approved":
        return False
    start = rule.get("period_start_from")
    end = rule.get("period_start_to")
    if start and period_start < str(start):
        return False
    if end and period_start > str(end):
        return False
    return True


def approved_rules_for_period(
    registry: dict[str, object], topic: str, period_start: str
) -> list[dict[str, object]]:
    """Return only manually approved metadata; never mutates registry or formulas."""
    rules = registry.get("approved_period_metadata", [])
    if not isinstance(rules, list):
        return []
    return [
        rule
        for rule in rules
        if isinstance(rule, dict)
        and rule.get("topic") == topic
        and _matches_period(rule, period_start)
    ]


def issue_proposal(document: dict[str, object]) -> dict[str, str]:
    citation = str(document.get("citation") or "Văn bản chưa rõ số hiệu")
    title = str(document.get("title") or "Chưa đọc được trích yếu")
    url = str(document.get("source_url") or "")
    published = str(document.get("published_on") or "CHƯA XÁC MINH")
    issued = str(document.get("issued_on") or "CHƯA XÁC MINH")
    effective = str(document.get("effective_from") or "CHƯA XÁC MINH")
    marker = f"<!-- accounting-law-watch:{document.get('document_id') or normalize_citation(citation)} -->"
    body = "\n".join(
        [
            marker,
            "## Đề nghị rà soát văn bản mới",
            "",
            f"- **Số hiệu:** {citation}",
            f"- **Trích yếu:** {title}",
            f"- **Ngày trên danh sách nguồn:** {published}",
            f"- **Ngày ban hành đã đọc:** {issued}",
            f"- **Ngày hiệu lực đã đọc:** {effective}",
            f"- **Nguồn chính thức:** {url}",
            "- **Kỳ kế toán/thuế áp dụng:** CHƯA XÁC MINH; cần đọc điều khoản chuyển tiếp và phạm vi văn bản.",
            "",
            "## Việc cần người có chuyên môn xác nhận",
            "",
            "1. Tải và lưu bản văn bản gốc cùng phụ lục/mẫu đính kèm.",
            "2. Đối chiếu ngày ban hành, ngày hiệu lực, đối tượng, kỳ áp dụng và văn bản bị sửa đổi/thay thế.",
            "3. Xác định module, mẫu và phiên bản có thể bị ảnh hưởng; ghi nguồn cho từng kết luận.",
            "4. Chỉ sau khi duyệt mới đề xuất cập nhật registry/quy tắc trong một PR riêng.",
            "",
            "**Tự động hóa an toàn:** workflow chỉ tạo đề xuất này. Workflow không sửa công thức, mapping, biểu mẫu hay quy tắc đã duyệt; không thay đổi cách xử lý kỳ cũ.",
        ]
    )
    return {"title": f"Đề xuất rà soát văn bản: {citation}", "body": body}


def build_report(
    html: str,
    registry: dict[str, object],
    detail_fetcher=None,
    checked_at: str | None = None,
    source_accessed: bool = False,
) -> dict[str, object]:
    entries = parse_listing(html)
    known = {
        normalize_citation(str(item.get("citation", "")))
        for item in registry.get("known_documents", [])
        if isinstance(item, dict) and item.get("citation")
    }
    monitor_from = parse_date(str(registry.get("monitor_from", "")))
    proposals: list[dict[str, object]] = []
    deferred: list[dict[str, object]] = []
    details_read = 0
    for entry in entries:
        citation = str(entry.get("citation") or "")
        normalized_citation = normalize_citation(citation)
        title = str(entry.get("title") or "")
        if (
            not citation
            or normalized_citation in known
            or not is_relevant_document(citation, title)
        ):
            continue
        published_on = entry.get("published_on")
        if not published_on:
            deferred.append(
                {
                    **entry,
                    "reason": "Không đọc được ngày trên danh sách nguồn; chưa kết luận văn bản mới.",
                }
            )
            continue
        if monitor_from and str(published_on) < monitor_from:
            continue
        metadata: dict[str, object] = dict(entry)
        if detail_fetcher and details_read < MAX_DETAIL_PAGES:
            try:
                detail_html = detail_fetcher(str(entry["source_url"]))
                metadata.update(parse_detail_metadata(detail_html))
                details_read += 1
            except (
                Exception
            ) as exc:  # Network/detail-page issues must not invent dates.
                metadata["detail_error"] = type(exc).__name__
                details_read += 1
        elif detail_fetcher:
            metadata["detail_error"] = "detail_page_limit"
        metadata.setdefault("issued_on", None)
        metadata.setdefault("effective_from", None)
        metadata["period_scope_status"] = "needs_human_review"
        metadata["approval_state"] = "proposal"
        metadata["issue"] = issue_proposal(metadata)
        proposals.append(metadata)

    return {
        "checked_at": checked_at or datetime.now(timezone.utc).isoformat(),
        "source_url": OFFICIAL_LISTING_URL,
        "source_host": OFFICIAL_HOST,
        "source_accessed": source_accessed,
        "listing_entries": len(entries),
        "proposals": proposals,
        "deferred_unverified_dates": deferred,
        "approved_period_metadata_unchanged": True,
        "auto_applied": False,
    }


def fetch_official_page(url: str, timeout: int = 20) -> str:
    safe_url = official_url(url)
    request = Request(safe_url, headers={"User-Agent": USER_AGENT})
    opener = build_opener(_AllowlistedRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        official_url(response.geturl(), safe_url)
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"Nguồn trả về loại nội dung không hỗ trợ: {content_type}")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("Nguồn vượt giới hạn kích thước đọc an toàn")
        encoding = response.headers.get_content_charset() or "utf-8"
    return payload.decode(encoding, errors="replace")


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON phải là object: {path}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-source", action="store_true")
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args(argv)
    if args.check_source == bool(args.fixture):
        parser.error("Chọn đúng một trong --check-source hoặc --fixture")

    try:
        registry = load_json(args.registry)
        if args.check_source:
            html = fetch_official_page(OFFICIAL_LISTING_URL)
            report = build_report(
                html,
                registry,
                detail_fetcher=fetch_official_page,
                source_accessed=True,
            )
            if not report["listing_entries"]:
                raise RuntimeError(
                    "Đã truy cập nguồn nhưng không đọc được văn bản từ danh sách"
                )
        else:
            html = args.fixture.read_text(encoding="utf-8")
            report = build_report(html, registry)
        serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized, encoding="utf-8")
        print(serialized, end="")
        return 0
    except Exception as exc:
        print(f"law-watch: ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
