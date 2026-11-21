#!/usr/bin/env python3
"""Publish proposal-only GitHub Issues; never changes repository files."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

GITHUB_API = "https://api.github.com"
USER_AGENT = "EigentAccountingLawWatch/0.1"


def _request_json(
    method: str, url: str, token: str, payload: object | None = None
) -> object:
    data = (
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if payload is not None
        else None
    )
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Content-Type": "application/json"} if data is not None else {}),
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"GitHub API trả HTTP {exc.code}") from exc


def _marker(issue: dict[str, object]) -> str | None:
    body = str(issue.get("body") or "")
    match = re.search(r"<!-- accounting-law-watch:[^>]+ -->", body)
    return match.group(0) if match else None


def publish(
    report: dict[str, object],
    repo: str,
    token: str | None,
    dry_run: bool = False,
) -> list[str]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Repository phải có dạng owner/name")
    proposals = report.get("proposals", [])
    if not isinstance(proposals, list):
        raise ValueError("proposals phải là danh sách")
    if dry_run:
        return [
            str(issue.get("title", ""))
            for item in proposals
            if isinstance(item, dict)
            and isinstance((issue := item.get("issue")), dict)
        ]
    if not report.get("source_accessed"):
        raise ValueError("Chỉ xuất bản đề xuất được tạo từ lần đọc nguồn trực tiếp")
    if report.get("source_host") != "vanban.chinhphu.vn":
        raise ValueError("Report không xác nhận nguồn Cổng Thông tin điện tử Chính phủ")
    if not token:
        raise ValueError("Thiếu GITHUB_TOKEN để xuất bản Issue")

    owner, name = repo.split("/", maxsplit=1)
    page_number = 1
    existing: set[str] = set()
    while True:
        url = f"{GITHUB_API}/repos/{owner}/{name}/issues?state=all&per_page=100&page={page_number}"
        page = _request_json("GET", url, token)
        if not isinstance(page, list):
            raise ValueError("GitHub API issues response phải là danh sách")
        for item in page:
            if isinstance(item, dict) and not item.get("pull_request"):
                marker = _marker(item)
                if marker:
                    existing.add(marker)
        if len(page) < 100:
            break
        page_number += 1

    created: list[str] = []
    for item in proposals:
        if not isinstance(item, dict):
            continue
        issue = item.get("issue")
        if not isinstance(issue, dict) or not issue.get("title") or not issue.get("body"):
            raise ValueError("Mỗi proposal cần issue.title và issue.body")
        marker = _marker(issue)
        if not marker:
            raise ValueError("Issue body thiếu marker chống trùng")
        if marker in existing:
            continue
        _request_json(
            "POST",
            f"{GITHUB_API}/repos/{owner}/{name}/issues",
            token,
            {"title": issue["title"], "body": issue["body"]},
        )
        existing.add(marker)
        created.append(str(issue["title"]))
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise ValueError("Report phải là JSON object")
        created = publish(report, args.repo, os.environ.get("GITHUB_TOKEN"), args.dry_run)
        mode = "dry-run" if args.dry_run else "published"
        print(
            json.dumps(
                {
                    "mode": mode,
                    "proposal_count": len(report.get("proposals", [])),
                    "issues": created,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(f"law-watch-publisher: ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
