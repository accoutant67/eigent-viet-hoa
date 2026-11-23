# Ghi nhận tiếp nối — kiểm thử đầu-cuối XML HTKK 01/GTGT

Ngày: 2026-11-23 (Asia/Saigon)  
Repository: `accoutant67/eigent-viet-hoa`  
Nhánh/PR: `codex/vat-return-mvp` / PR #2 (open, draft, chưa merge)

## CI trước thay đổi

Head `5014be08a52d9f3ad67dbfe8e7db413458719e80` được xác minh lại: Test tổng thể, Accounting VAT return draft và Accounting law watch đều **SUCCESS**. Không chạy lại trước khi có thay đổi.

## Mẫu và XSD

- Dùng inventory HTKK 5.8.5 hiện có; không quét lại 4.097 tệp.
- Đối chiếu hồ sơ TT80 `01_GTGT_TT80_xml_283.xml` và TT89 `01_GTGT_TT89_xml_309.xml`; phân biệt layout `Sections` với XML hồ sơ `HSoThueDTu`.
- Instance XML tham chiếu và exporter không namespace. XSD `InterfaceTemplates/Validate/01_GTGT_TT89_309.xsd` đặt target namespace `http://kekhaithue.gdt.gov.vn/TKhaiThue`, `elementFormDefault=qualified`, và redefine `../TKhaiThue_DBHC.xsd`. Schema tồn tại, nhưng không xác nhận được cho instance không namespace; không sửa schema hoặc tự thêm namespace.
- TT80 và TT89 giữ cấu trúc riêng; TT89 bổ sung [32b]/[34a], thay đổi công thức [27]/[34].

## Thay đổi

- Runner E2E tạo CSV giả lập rồi gọi CLI và exporter VAT hiện có cho 07/2026 tháng và Q3/2026 quý, đều theo TT89.
- Runner parse output, so cây phần tử với mẫu, kiểm tra form/kỳ/MST placeholder/Unicode/số nguyên/formula/source hash.
- Workflow tạo artifact gồm hai XML và report.json. Hướng dẫn Windows và ma trận chỉ tiêu được thêm cạnh skill.

## Kết quả

Được cập nhật sau khi Actions hoàn tất trên commit mới. XSD còn **BLOCKED** như mô tả trên; nhập HTKK Windows **NOT TESTED** cho tới khi chạy trên máy có HTKK.
