from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_law_proposals as publisher
import watch_official_documents as watch


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "official-listing.html"
VAT_FIXTURE = ROOT / "tests" / "fixtures" / "vat-law-change.html"


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
        self.assertEqual(
            watch.official_url("https://congbao.chinhphu.vn/van-ban/example"),
            "https://congbao.chinhphu.vn/van-ban/example",
        )
        self.assertEqual(
            watch.official_url("https://thanhtrabtc.mof.gov.vn/hoidapcstc/1"),
            "https://thanhtrabtc.mof.gov.vn/hoidapcstc/1",
        )
        with self.assertRaises(ValueError):
            watch.official_url("https://vanban.chinhphu.vn.evil.example/law")

    def test_new_vat_change_is_proposed_and_known_law_is_not_repeated(self) -> None:
        data = registry()
        original = json.dumps(data, ensure_ascii=False, sort_keys=True)
        report = watch.build_report(
            VAT_FIXTURE.read_text(encoding="utf-8"),
            data,
            detail_fetcher=lambda _url: (
                "<div>Ngày ban hành 22-11-2099</div>"
                "<div>Ngày có hiệu lực 01-01-2100</div>"
            ),
            checked_at="2099-11-23T00:00:00+00:00",
        )
        self.assertEqual(
            [item["citation"] for item in report["proposals"]],
            ["999/2099/TT-BTC"],
        )
        proposal = report["proposals"][0]
        self.assertEqual(proposal["issued_on"], "2099-11-22")
        self.assertEqual(proposal["effective_from"], "2100-01-01")
        self.assertEqual(proposal["period_scope_status"], "needs_human_review")
        self.assertEqual(proposal["approval_state"], "proposal")
        self.assertIn("không sửa công thức", proposal["issue"]["body"])
        self.assertFalse(report["auto_applied"])
        self.assertEqual(json.dumps(data, ensure_ascii=False, sort_keys=True), original)

    def test_official_reference_checks_are_allowlisted_and_record_access_status(
        self,
    ) -> None:
        data = registry()
        sources = data["source_checks"]
        responses = [str(item["expected_marker"]) for item in sources]
        with patch.object(watch, "fetch_official_page", side_effect=responses) as fetch:
            result = watch.check_reference_sources(data)
        self.assertEqual([item["status"] for item in result], ["pass"] * len(sources))
        self.assertEqual(fetch.call_count, len(sources))
        data["source_checks"] = [
            {
                "name": "untrusted",
                "url": "https://example.com/fake-law",
                "expected_marker": "fake",
            }
        ]
        self.assertEqual(watch.check_reference_sources(data)[0]["status"], "blocked")

    def test_registry_tracks_official_vat_form_amendment_sources(self) -> None:
        data = registry()
        names = [item["name"] for item in data["source_checks"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(
            {
                "vanban_law_vat_48_2024",
                "vanban_decree_vat_181_2025",
                "vanban_circular_vat_69_2025",
                "vanban_tt40_2025_tt80_form_update",
                "vanban_tt94_2025_tt80_update",
                "vanban_tt21_2026_tt80_update",
                "mof_vbpq_official_database_guide",
                "vanban_tt89_2026",
                "vanban_tt110_2026",
                "congbao_correction_2551_2026",
                "vanban_law_tax_admin_108_2025",
                "vanban_decree_invoice_254_2026",
                "vanban_circular_invoice_91_2026",
            }.issubset(names)
        )
        self.assertNotIn("mof_official_answer_tt80_01_gtgt", names)
        self.assertNotIn("mof_question_reference_tt89_form_only", names)
        documents = {item["citation"]: item for item in data["known_documents"]}
        self.assertEqual(documents["48/2024/QH15"]["effective_from"], "2025-07-01")
        self.assertEqual(documents["181/2025/NĐ-CP"]["effective_from"], "2025-07-01")
        self.assertEqual(documents["69/2025/TT-BTC"]["effective_from"], "2025-07-01")
        self.assertEqual(documents["108/2025/QH15"]["effective_from"], "2026-07-01")
        self.assertIn(
            "2026-01-01",
            documents["108/2025/QH15"]["period_scope_status"],
        )
        self.assertEqual(documents["254/2026/NĐ-CP"]["effective_from"], "2026-07-01")
        self.assertEqual(documents["91/2026/TT-BTC"]["effective_from"], "2026-07-01")
        self.assertIn(
            "not_reviewed", documents["254/2026/NĐ-CP"]["period_scope_status"]
        )
        self.assertIn("01_GTGT", documents["89/2026/TT-BTC"]["period_scope_status"])
        self.assertIn(
            "does_not_include_80_or_89",
            documents["110/2026/TT-BTC"]["period_scope_status"],
        )
        self.assertIn("no_01_GTGT", documents["110/2026/TT-BTC"]["period_scope_status"])
        self.assertIn(
            "human_review", documents["21/2026/TT-BTC"]["period_scope_status"]
        )

    def test_finance_ministry_legal_database_host_is_allowlisted_over_https(
        self,
    ) -> None:
        source = next(
            item
            for item in registry()["source_checks"]
            if item["name"] == "mof_vbpq_official_database_guide"
        )
        self.assertEqual(
            watch.official_url(source["url"]),
            "https://vbpq.mof.gov.vn/Huongdankhaithac",
        )

    def test_tt110_official_metadata_domain_is_allowlisted_over_https(self) -> None:
        source = next(
            item
            for item in registry()["source_checks"]
            if item["name"] == "vanban_tt110_2026"
        )
        self.assertEqual(watch.official_url(source["url"]), source["url"])

    def test_official_source_redirect_cannot_leave_the_allowlisted_host(self) -> None:
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
        allowed = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://congbao.chinhphu.vn/van-ban/official",
        )
        self.assertEqual(
            allowed.full_url, "https://congbao.chinhphu.vn/van-ban/official"
        )

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
