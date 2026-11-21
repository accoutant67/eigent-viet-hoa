#!/usr/bin/env python3
"""CLI smoke for fixture detection and the non-publishing Issue dry run."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry.json"
FIXTURE = ROOT / "tests" / "fixtures" / "official-listing.html"


def main() -> int:
    before = REGISTRY.read_bytes()
    with tempfile.TemporaryDirectory(prefix="accounting-law-watch-") as folder:
        report_path = Path(folder) / "report.json"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "watch_official_documents.py"),
            "--registry",
            str(REGISTRY),
            "--fixture",
            str(FIXTURE),
            "--output",
            str(report_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        proposals = report["proposals"]
        if len(proposals) != 1 or proposals[0]["citation"] != "121/2026/TT-BTC":
            raise AssertionError("Fixture must produce exactly one new-document proposal")
        if report["auto_applied"] or report["source_accessed"]:
            raise AssertionError("Fixture run cannot apply rules or claim live source access")
        if proposals[0]["period_scope_status"] != "needs_human_review":
            raise AssertionError("New document period scope must remain unapproved")

        dry_run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "publish_law_proposals.py"),
                "--report",
                str(report_path),
                "--repo",
                "accoutant67/eigent-viet-hoa",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if dry_run.returncode != 0:
            raise RuntimeError(dry_run.stderr or dry_run.stdout)
        payload = json.loads(dry_run.stdout)
        if payload["mode"] != "dry-run" or len(payload["issues"]) != 1:
            raise AssertionError("Issue publisher dry-run did not prepare one proposal")
    if REGISTRY.read_bytes() != before:
        raise AssertionError("Monitoring must not modify the approved registry")
    print("[smoke] PASS: fixture detected one proposal; Issue dry-run did not publish or alter rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
