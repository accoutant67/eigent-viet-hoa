"""Exercise the installed CLI on a synthetic workbook, not an in-process call."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from test_audit_workbook import write_demo_workbook

SKILL_ROOT = Path(__file__).resolve().parents[1]
CLI = SKILL_ROOT / "scripts" / "audit_workbook.py"


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workbook = root / "synthetic.xlsx"
        output = root / "synthetic.audit.json"
        write_demo_workbook(workbook)
        original_digest = hashlib.sha256(workbook.read_bytes()).hexdigest()

        command = [
            sys.executable,
            str(CLI),
            str(workbook),
            "--sheet",
            "Bảng lương",
            "--required-column",
            "Tên",
            "--key-column",
            "Mã NV",
            "--output",
            str(output),
        ]
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        assert completed.returncode == 0, completed.stderr
        report = json.loads(output.read_text(encoding="utf-8"))
        sheet = report["sheets"][0]
        assert report["tool"] == "accounting-workbook-audit"
        assert report["status"] == "review_required"
        assert report["summary"]["data_row_count"] == 7
        assert sheet["findings"]["duplicate_keys"] == [
            {"first_row": 2, "duplicate_row": 4, "columns": ["Mã NV"]}
        ]
        assert sheet["findings"]["missing_required_values"] == [
            {"row": 5, "column": "Tên"}
        ]
        assert sheet["findings"]["excel_errors"] == [
            {"cell": "C8", "code": "#VALUE!"}
        ]
        assert "Trùng tên" not in json.dumps(report, ensure_ascii=False)
        assert "00017" not in json.dumps(report, ensure_ascii=False)
        assert hashlib.sha256(workbook.read_bytes()).hexdigest() == original_digest
        original_report = output.read_bytes()

        blocked = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        assert blocked.returncode == 2, blocked.stderr
        assert json.loads(blocked.stderr)["status"] == "error"
        assert output.read_bytes() == original_report
        assert hashlib.sha256(workbook.read_bytes()).hexdigest() == original_digest

        print("[smoke] PASS: CLI ran, reported findings, preserved source and output")


if __name__ == "__main__":
    run()
