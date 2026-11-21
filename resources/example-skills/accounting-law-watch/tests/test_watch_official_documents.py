from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_law_proposals as publisher
import watch_official_documents as watch


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "official-listing.html"
sys.path.insert(0, str(ROOT.parent / "accounting-vat-return" / "scripts"))
import vat_return_draft as vat


def registry() -> dict[str, object]:
    return json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))


class OfficialLawWatchTests(unittest.TestCase):
    def test_listing_parser_extracts_document_id_citation_title_and_date(self) -> None:
        entries = watch.parse_listing(FIXTURE.read_text(encoding="utf-8"))
        found = next(item for item in entries if item["document_id"] == "220001")
        self.assertEqual(found["citation"], "121/2026/TT-BTC")
        self.assertEqual(found["published_on"], "2026-11-22")
        self.assertEqual(found["title"], "Hướng dẫn hồ sơ khai thuế giá trị gia tăng")
        self.assertEqual(
            found["source_url"],
            "https://vanban.chinhphu.vn/?docid=220001&pageid=27160",
        )

    def test_listing_parser_falls_back_to_official_document_links(self) -> None:
        html = (
            '<a href="/?docid=220002&amp;pageid=27160">'
            "122/2026/TT-BTC 23/11/2026</a>"
            '<a href="/?docid=220002&amp;pageid=27160">'
            "Quy định hồ sơ kê khai thuế</a>"
        )
        found = watch.parse_listing(html)[0]
        self.assertEqual(found["document_id"], "220002")
        self.assertEqual(found["citation"], "122/2026/TT-BTC")
        self.assertEqual(found["published_on"], "2026-11-23")
        self.assertEqual(found["title"], "Quy định hồ sơ kê khai thuế")

    def test_listing_parser_recognizes_qh15_law_and_proposes_new_law(self) -> None:
        html = (
            "<table><tr>"
            "<td>123/2026/QH15</td>"
            "<td>Luật sửa đổi quy định thuế</td>"
            "<td>24/11/2026</td>"
            '<td><a href="/?docid=220003&amp;pageid=27160">123/2026/QH15</a></td>'
            "</tr></table>"
        )
        report = watch.build_report(
            html,
            registry(),
            checked_at="2026-11-24T00:00:00+00:00",
        )
        self.assertEqual(len(report["proposals"]), 1)
        proposal = report["proposals"][0]
        self.assertEqual(proposal["citation"], "123/2026/QH15")
        self.assertEqual(proposal["published_on"], "2026-11-24")
        self.assertEqual(proposal["period_scope_status"], "needs_human_review")
        self.assertFalse(report["auto_applied"])

    def test_old_known_and_pre_monitor_documents_are_not_new_proposals(self) -> None:
        report = watch.build_report(
            FIXTURE.read_text(encoding="utf-8"),
            registry(),
            checked_at="2026-11-22T00:00:00+00:00",
        )
        proposals = report["proposals"]
        self.assertEqual([item["document_id"] for item in proposals], ["220001"])
        self.assertFalse(report["source_accessed"])
        self.assertFalse(report["auto_applied"])

    def test_detail_page_dates_do_not_choose_or_apply_period_rules(self) -> None:
        html = (
            "<div>Số ký hiệu 121/2026/TT-BTC</div>"
            "<div>Ngày ban hành 22-11-2026</div>"
            "<div>Ngày có hiệu lực 01-01-2027</div>"
        )
        metadata = watch.parse_detail_metadata(html)
        self.assertEqual(metadata["issued_on"], "2026-11-22")
        self.assertEqual(metadata["effective_from"], "2027-01-01")
        self.assertNotIn("period_start_from", metadata)

    def test_approved_period_metadata_preserves_old_period_rules(self) -> None:
        data = registry()
        data["approved_period_metadata"] = [
            {
                "topic": "vat",
                "citation": "OLD-VAT-RULE",
                "approval_state": "approved",
                "period_start_from": "2025-01-01",
                "period_start_to": "2025-12-31",
            },
            {
                "topic": "vat",
                "citation": "NEW-VAT-RULE",
                "approval_state": "approved",
                "period_start_from": "2026-01-01",
                "period_start_to": None,
            },
            {
                "topic": "vat",
                "citation": "UNAPPROVED-PROPOSAL",
                "approval_state": "proposal",
                "period_start_from": "2025-01-01",
                "period_start_to": None,
            },
        ]
        original = json.dumps(data, ensure_ascii=False, sort_keys=True)
        old_year = watch.approved_rules_for_period(data, "vat", "2025-01-01")
        current_year = watch.approved_rules_for_period(data, "vat", "2026-01-01")
        self.assertEqual([item["citation"] for item in old_year], ["OLD-VAT-RULE"])
        self.assertEqual([item["citation"] for item in current_year], ["NEW-VAT-RULE"])
        self.assertEqual(json.dumps(data, ensure_ascii=False, sort_keys=True), original)

    def test_issue_proposal_has_source_effective_period_review_and_no_auto_apply(
        self,
    ) -> None:
        report = watch.build_report(
            FIXTURE.read_text(encoding="utf-8"),
            registry(),
            detail_fetcher=lambda _url: (
                "<div>Ngày ban hành 22-11-2026</div>"
                "<div>Ngày có hiệu lực 01-01-2027</div>"
            ),
            checked_at="2026-11-22T00:00:00+00:00",
        )
        proposal = report["proposals"][0]
        issue = proposal["issue"]
        self.assertIn("121/2026/TT-BTC", issue["title"])
        self.assertIn("https://vanban.chinhphu.vn/?docid=220001", issue["body"])
        self.assertIn("2027-01-01", issue["body"])
        self.assertIn("CHƯA XÁC MINH", issue["body"])
        self.assertIn("không sửa công thức", issue["body"])
        self.assertEqual(proposal["period_scope_status"], "needs_human_review")
        self.assertEqual(proposal["approval_state"], "proposal")
        self.assertFalse(report["auto_applied"])

    def test_only_official_https_host_is_allowed(self) -> None:
        self.assertEqual(
            watch.official_url("/?docid=1&pageid=27160"),
            "https://vanban.chinhphu.vn/?docid=1&pageid=27160",
        )
        with self.assertRaises(ValueError):
            watch.official_url("https://example.com/fake-law")

    def test_official_source_redirect_cannot_leave_the_allowlisted_host(self) -> None:
        with patch.object(watch, "build_opener") as build_opener:
            response = (
                build_opener.return_value.open.return_value.__enter__.return_value
            )
            response.geturl.return_value = "https://example.com/redirected-law"
            with self.assertRaises(ValueError):
                watch.fetch_official_page(watch.OFFICIAL_LISTING_URL)

    def test_external_redirect_is_rejected_before_following(self) -> None:
        handler = watch._AllowlistedRedirectHandler()
        request = watch.Request(watch.OFFICIAL_LISTING_URL)
        with self.assertRaises(ValueError):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://example.com/redirected-law",
            )

    def test_reference_check_requires_allowlisted_https_and_matches_page_marker(
        self,
    ) -> None:
        source = {
            "source_checks": [
                {
                    "name": "official_law",
                    "url": "https://vanban.chinhphu.vn/?docid=1",
                    "expected_marker": "149/2025/QH15",
                }
            ]
        }
        passed = watch.check_official_references(
            source, lambda _url: "<p>Luật số 149/2025/QH15</p>"
        )
        self.assertEqual(passed[0]["status"], "pass")
        failed = watch.check_official_references(
            source, lambda _url: "<p>Trang Chính phủ nhưng không có số hiệu</p>"
        )
        self.assertEqual(failed[0]["status"], "fail")
        self.assertEqual(failed[0]["reason"], "expected_marker_not_found")

    def test_reference_check_blocks_unapproved_host_and_external_redirect(self) -> None:
        source = {
            "source_checks": [
                {
                    "name": "untrusted",
                    "url": "https://example.com/fake",
                    "expected_marker": "149/2025/QH15",
                }
            ]
        }
        with patch.object(watch, "fetch_official_reference") as fetcher:
            result = watch.check_official_references(source)
        self.assertEqual(result[0]["status"], "blocked")
        fetcher.assert_not_called()

        handler = watch._AllowlistedRedirectHandler(watch.REFERENCE_HOSTS)
        request = watch.Request("https://mof.gov.vn/")
        with self.assertRaises(ValueError):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://example.com/redirected-law",
            )

    def test_live_report_reference_checks_feed_vat_period_gate(self) -> None:
        data = registry()
        listing = (
            "<table><tr><td>80/2021/TT-BTC</td>"
            "<td>Thông tư hướng dẫn hồ sơ thuế</td><td>29/09/2021</td>"
            '<td><a href="/?docid=210080&pageid=27160">80/2021/TT-BTC</a></td>'
            "</tr></table>"
        )
        markers = {
            item["url"]: item["expected_marker"] for item in data["source_checks"]
        }
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "registry.json"
            report_path = Path(directory) / "law-watch-report.json"
            registry_path.write_text(json.dumps(data), encoding="utf-8")
            with (
                patch.object(watch, "fetch_official_page", return_value=listing),
                patch.object(
                    watch,
                    "fetch_official_reference",
                    side_effect=lambda url: f"<p>{markers[url]}</p>",
                ),
            ):
                with redirect_stdout(io.StringIO()):
                    status = watch.main(
                        [
                            "--registry",
                            str(registry_path),
                            "--check-source",
                            "--output",
                            str(report_path),
                        ]
                    )
            self.assertEqual(status, 0)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            decision = vat._review_law_watch_report(
                report_path, "89/2026/TT-BTC", "2026-Q3"
            )
        self.assertEqual(report["official_reference_summary"]["pass"], len(markers))
        self.assertEqual(report["official_reference_summary"]["fail"], 0)
        self.assertEqual(report["official_reference_summary"]["blocked"], 0)
        self.assertEqual(decision["status"], "pass")
        self.assertFalse(decision["auto_applied"])

    def test_issue_publisher_dry_run_builds_issue_without_network(self) -> None:
        issue = {
            "title": "Đề xuất rà soát văn bản: 121/2026/TT-BTC",
            "body": "<!-- accounting-law-watch:220001 -->\nReview before applying.",
        }
        with patch.object(publisher, "_request_json", side_effect=AssertionError):
            planned = publisher.publish(
                {"proposals": [{"issue": issue}]},
                "owner/repo",
                token=None,
                dry_run=True,
            )
        self.assertEqual(planned, [issue["title"]])

    def test_issue_publisher_rejects_fixture_reports_for_live_publication(self) -> None:
        issue = {
            "title": "Fixture proposal",
            "body": "<!-- accounting-law-watch:fixture -->\nReview before applying.",
        }
        with patch.object(publisher, "_request_json", side_effect=AssertionError):
            with self.assertRaisesRegex(ValueError, "nguồn trực tiếp"):
                publisher.publish(
                    {
                        "source_accessed": False,
                        "source_host": watch.OFFICIAL_HOST,
                        "proposals": [{"issue": issue}],
                    },
                    "owner/repo",
                    token="synthetic-token",
                )

    def test_issue_publisher_deduplicates_and_creates_only_new_proposal(self) -> None:
        old_issue = {
            "title": "Existing proposal",
            "body": "<!-- accounting-law-watch:old-id -->",
        }
        new_issue = {
            "title": "New proposal",
            "body": "<!-- accounting-law-watch:new-id -->\nReview before applying.",
        }
        with patch.object(
            publisher,
            "_request_json",
            side_effect=[[{"body": old_issue["body"]}], {"number": 42}],
        ) as request:
            created = publisher.publish(
                {
                    "source_accessed": True,
                    "source_host": watch.OFFICIAL_HOST,
                    "proposals": [{"issue": old_issue}, {"issue": new_issue}],
                },
                "owner/repo",
                token="synthetic-token",
            )
        self.assertEqual(created, ["New proposal"])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[0].args[0], "GET")
        self.assertEqual(
            request.call_args_list[1],
            call(
                "POST",
                "https://api.github.com/repos/owner/repo/issues",
                "synthetic-token",
                {"title": "New proposal", "body": new_issue["body"]},
            ),
        )


if __name__ == "__main__":
    unittest.main()
