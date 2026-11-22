---
name: accounting-vat-return
description: "Nhập và kiểm tra dữ liệu hóa đơn .xlsx/.csv và XML UBL đơn lẻ theo profile hỗ trợ, tổng hợp dự thảo GTGT tháng/quý; xuất JSON hoặc workbook XLSX soát xét nội bộ, không thay mẫu pháp định."
---

# Dự thảo kê khai thuế GTGT tháng/quý

Skill này chạy trong hạ tầng Skill hiện có của Eigent. Các mã HD/TK/BM/PL/KTT bên dưới là **vai trò nghiệp vụ từ danh mục người dùng cung cấp**, không phải Agent mới được đăng ký. Không tạo thêm Agent trùng chức năng.

## Luồng thực hiện

1. `HD01` đọc bảng hóa đơn `.xlsx`/`.csv` hoặc một XML UBL `Invoice`/`CreditNote` đơn lẻ theo profile đã hỗ trợ. XML không được coi là đã xác thực theo schema hóa đơn điện tử Việt Nam hoặc schema tờ khai HTKK/eTax; hóa đơn nhiều mức thuế bị chặn, CreditNote được giữ để soát, trường ký hiệu chỉ lấy khi XML có cung cấp rõ. Dòng VAT sau chuẩn hóa tuân theo hợp đồng `resources/accounting-data-model/v1/invoice-record.schema.json`; thông tin hàng hóa và tham chiếu điều chỉnh chưa trích xuất được phải ghi rõ trạng thái `not_extracted`. `HD02` phân luồng mua vào, `HD03` phân luồng bán ra dựa trên MST người nộp thuế và MST hai bên; không ghép theo tên.
2. `HD04` kiểm tra khóa hóa đơn trùng, ngày, trạng thái được khai báo, số tiền, thuế suất ghi trên nguồn, kỳ và ô công thức. Trạng thái thiếu/không nhận diện, hóa đơn trùng, điều chỉnh, thay thế, hủy, sai số học, ngoài kỳ hoặc có công thức được giữ lại để soát và không cộng vào dự thảo.
3. `PL01`–`PL04` tái sử dụng Skill `accounting-law-watch`; không tạo watcher thứ hai. Trước khi chọn phiên bản, truyền JSON report của law-watch bằng `--law-watch-report`. Báo cáo phải cho thấy đã đọc nguồn chính thức, không có đề xuất văn bản mới chưa duyệt, không tự áp dụng quy tắc và các nguồn bắt buộc của phiên bản đều PASS. Mọi kết luận về kỳ vẫn cần người duyệt.
4. `TK01` tổng hợp doanh số và tiền thuế theo chiều mua/bán và **nhãn thuế suất trên nguồn**. Công cụ không suy diễn diện chịu thuế, điều kiện khấu trừ hoặc số thuế phải nộp.
5. `BM01` dùng danh mục mẫu đã xác minh. Khi đã rà soát, người dùng chọn phiên bản tường minh qua `--form-version`. `BM03` chỉ ánh xạ các dòng bán ra qua `form_line_code`/`form_tax_line_code` đã được rà soát; hóa đơn mua vào phải được gán tường minh `[23]`/`[24]` (mua trong nước) hoặc `[23a]`/`[24a]` (nhập khẩu). `[23a]` là phần nằm trong `[23]`, `[24a]` là phần nằm trong `[24]`; không cộng phần nhập khẩu lần nữa vào tổng. Không tự suy mã chỉ tiêu từ tên hàng, tên khách hàng hoặc thuế suất. `BM02` sao chép workbook mẫu chính thức hiện **NOT STARTED**.
6. `TK05` tính lại độc lập tổng hóa đơn và các chỉ tiêu công thức trong danh mục mẫu. `KTT03` tổng hợp ngoại lệ và trạng thái; người dùng duyệt. Không có Agent mới nào được đăng ký.
7. Xuất JSON hoặc workbook XLSX soát xét nội bộ. Workbook có cảnh báo, tổng hợp, dòng hóa đơn và ngoại lệ; không phải mẫu 01/GTGT. XLSX chính thức, ký, nộp và XML chưa triển khai.

## Chạy

```bash
uv run --project backend python resources/example-skills/accounting-vat-return/scripts/vat_return_draft.py \
  "duong-dan/hoa-don.xlsx" \
  --taxpayer-tax-id "0100000001" \
  --period "2026-Q3" \
  --form-version "89/2026/TT-BTC" \
  --law-watch-report "duong-dan/law-watch-report.json" \
  --sheet "HoaDon" \
  --header-row 1
```

`--period` nhận `YYYY-MM` hoặc `YYYY-Q1` đến `YYYY-Q4`. `--form-version` chỉ nhận `80/2021/TT-BTC` hoặc `89/2026/TT-BTC`, bắt buộc khi muốn tạo các dòng tờ khai và không được tự chọn theo kỳ. `--law-watch-report` bắt buộc khi chọn mẫu; đây phải là đầu ra của Skill pháp luật hiện có. Cột `form_line_code`/`form_tax_line_code` phải được kế toán/BM03 rà soát: dòng bán ra dùng chỉ tiêu doanh thu/thuế đã xác nhận; dòng mua vào dùng cặp `23`/`24` cho hàng mua trong nước hoặc `23a`/`24a` cho hàng nhập khẩu. Thuế suất không được dùng để suy loại hàng. Nếu thiếu mã, báo cáo vẫn giữ tổng hóa đơn nhưng phần tờ khai được đánh dấu thiếu ánh xạ. Nếu không chọn `--output`, chương trình tạo `.vat-draft.json` cạnh nguồn, không ghi vào workbook. Kỳ được lọc theo ngày hóa đơn và vẫn cần người rà soát.

Để xuất workbook soát xét nội bộ, dùng `--output "ket-qua-soat-xet.xlsx"`. Các ô được ghi dưới dạng chuỗi, workbook không chứa công thức và tệp nguồn chỉ được đọc. Workbook này không sao chép mẫu pháp định, không sẵn sàng nộp và không thay cho bước `BM02`.

## Tình trạng mẫu pháp định

- Nguồn Công báo/Chính phủ xác nhận 01/GTGT thuộc Phụ lục II TT80/2021. Trên tờ khai này, TT40/2025 cập nhật địa chỉ [11a] thành xã/phường/đặc khu và bỏ trường huyện [11b]; TT94/2025 tiếp tục sửa các cụm thông tin trên biểu mẫu nhưng không thay mẫu 01/GTGT. TT21/2026 thay mẫu 02/TNDN và 05/TNDN, không thay 01/GTGT.
- TT89/2026 có hiệu lực từ 2026-07-01. Đã kiểm tra tệp ký số chính thức: Phụ lục I, trang PDF 241 là mẫu 01/GTGT; trang này có [32b], [34a] và công thức tổng doanh thu mới. Mốc hiệu lực chưa tự quyết định biểu mẫu cho mọi hồ sơ chuyển tiếp; phải rà kỳ tính thuế, thời điểm khai và trường hợp người nộp thuế.
- Một trang hỏi đáp của Bộ Tài chính có câu hỏi về [37]/[38]; trang hỏi của người dùng không được coi là câu trả lời hay hướng dẫn chính thức của Bộ.
- Đã đọc bản PDF đính chính 2551/QĐ-BTC đính kèm trên Cổng Chính phủ: phần Điều 1 sửa danh sách mẫu được thay thế tại Điều 99 TT89; danh sách sửa không nêu 01/GTGT. Việc này không xác nhận nội dung hoặc phạm vi kỳ của mẫu 01/GTGT.
- TT89 Annex I liệt kê các phụ lục GTGT 01-2, 01-3, 01-6, 01-7 và 01-8. 01-8 là phụ lục thông tin đề nghị hoàn thuế; các phụ lục phân bổ còn lại phụ thuộc ngành, địa bàn hoặc chi nhánh. Chưa ánh xạ các phụ lục vào tệp đầu ra.
- Danh mục có công thức đã kiểm chứng của hai phiên bản; CLI chỉ tạo field draft khi người dùng chọn phiên bản và đưa report law-watch hợp lệ. Đây chưa phải lựa chọn pháp lý tự động; `auto_form_selection` luôn false.

## Giới hạn hiện tại

- Đã hỗ trợ nhập `.xlsx`/`.csv` và profile XML UBL đơn lẻ `Invoice`/`CreditNote` (một `TaxSubtotal` VAT), chiếu dữ liệu vào hợp đồng hóa đơn dùng chung phiên bản 1.0.0, giữ truy vết tên tệp/dòng/hash, phân loại theo MST, kiểm tra hóa đơn, tổng hợp, ánh xạ mã dòng được chỉ định tường minh, tính công thức trong catalog và đối chiếu độc lập. Parser từ chối DTD/entity, XML sai cấu trúc, thiếu `PayableAmount` và hồ sơ nhiều mức thuế; không tự sinh ký hiệu hóa đơn. Kết quả JSON/XLSX vẫn là bản soát xét nội bộ.
- Đọc XML nhà cung cấp ngoài profile UBL đơn lẻ này, xử lý hóa đơn nhiều mức thuế, đọc PDF/ảnh, đối chiếu sổ 133/33311, sao chép/điền workbook pháp định bảo toàn định dạng, ánh xạ phụ lục, xuất XLSX pháp định, kiểm tra XML theo schema, tạo/ký/gửi tờ khai và xử lý khai bổ sung là **NOT STARTED**.
- Không dùng dữ liệu thực trong test. Không đưa tệp hóa đơn, mã số thuế, tên doanh nghiệp hoặc token lên repository.
