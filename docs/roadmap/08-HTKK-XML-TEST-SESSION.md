# Ghi nhận tiếp nối — kiểm thử đầu-cuối XML HTKK 01/GTGT

Ngày: 2026-11-23 (Asia/Saigon)  
Repository: `accoutant67/eigent-viet-hoa`  
Nhánh/PR: `codex/vat-return-mvp` / PR #2 (open, draft, chưa merge)

## CI

Head kiểm thử trước thay đổi demo `5014be08a52d9f3ad67dbfe8e7db413458719e80`: Test tổng thể, Accounting VAT return draft và Accounting law watch đều SUCCESS.

Trên commit `b8904efb9b144abb393290eeb70b477cd4f4c231`, cả ba workflow đều SUCCESS:
- [Test tổng thể](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45105073191)
- [Accounting VAT return draft](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45105073263)
- [Accounting law watch](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45105073249)

VAT workflow chạy VAT unit, CLI E2E smoke, sinh hai XML demo, law-watch regression/CLI smoke và Excel audit regression. Artifact demo: [htkk-01-gtgt-xml-demo](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45105073263).

## Mẫu và XSD

- Dùng inventory HTKK 5.8.5 hiện có; không quét lại 4.097 tệp.
- Đối chiếu hồ sơ TT80 `01_GTGT_TT80_xml_283.xml` và TT89 `01_GTGT_TT89_xml_309.xml`; phân biệt layout `Sections` với XML hồ sơ `HSoThueDTu`.
- Instance XML tham chiếu và exporter không namespace. XSD `InterfaceTemplates/Validate/01_GTGT_TT89_309.xsd` tồn tại, đặt target namespace `http://kekhaithue.gdt.gov.vn/TKhaiThue`, `elementFormDefault=qualified`, và redefine `../TKhaiThue_DBHC.xsd`. Chưa xác nhận schema này phù hợp với instance không namespace; do đó XSD validation **BLOCKED**, không sửa schema hoặc tự thêm namespace.
- TT80 và TT89 giữ cấu trúc riêng; TT89 bổ sung [32b]/[34a] và có công thức [27]/[34] riêng.
- Ma trận từng chỉ tiêu, đường dẫn và giới hạn nằm tại [01-GTGT-INDICATOR-MATRIX.md](../../resources/example-skills/accounting-vat-return/reference/htkk-5.8.5/01-GTGT-INDICATOR-MATRIX.md).

## Thay đổi và kiểm thử đầu-cuối

- Runner tạo CSV giả lập rồi gọi CLI và exporter VAT hiện có cho tháng 07/2026 và quý III/2026, đều theo TT89; không tạo pipeline thứ hai.
- Runner parse output, so cây phần tử với mẫu, kiểm tra mã/kỳ/MST placeholder/Unicode/số nguyên/công thức và hash mẫu nguồn.
- Trên commit `b8904ef`, workflow xác nhận tạo XML và sinh report/artifact thành công. XML demo đã được đóng gói cùng hướng dẫn nhập thử trên Windows. MST `0000000000` chỉ là placeholder có dạng 10 chữ số; không phải MST đã đăng ký.
- Artifact CI chứa hai XML cùng `report.json`: [tải ở workflow VAT](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45105073263) (mục Artifacts).
- XML được parse và đối chiếu cây phần tử theo test của workflow. Đây chưa phải xác minh XSD, nhập lại HTKK hoặc tiếp nhận của cơ quan thuế.

## Trạng thái nghiệm thu

- PASS 1 — XML được tạo qua CLI/exporter VAT hiện có.
- PASS 2 — parse lại và kiểm tra round-trip theo runner.
- PASS 3 — cây phần tử so với mẫu HTKK được kiểm tra trong runner.
- BLOCKED 4 — chưa xác minh XSD phù hợp do namespace/redefine nêu trên.
- NOT TESTED 5 — chưa nhập lại vào HTKK Windows.
- NOT TESTED / ngoài phạm vi 6 — chưa nộp hoặc kiểm tra tiếp nhận của cơ quan thuế.

Hướng dẫn thao tác và giới hạn của MST giả lập: [09-HTKK-XML-DEMO-ACCEPTANCE.md](09-HTKK-XML-DEMO-ACCEPTANCE.md). Dừng trước ký số hoặc nộp hồ sơ.
