---
name: accounting-vat-return
description: "Nhập và kiểm tra dữ liệu hóa đơn mua vào/bán ra, tổng hợp dự thảo GTGT theo tháng/quý; xuất JSON hoặc workbook XLSX soát xét nội bộ, không thay mẫu pháp định."
---

# Dự thảo kê khai thuế GTGT tháng/quý

Skill này chạy trong hạ tầng Skill hiện có của Eigent. Các mã HD/TK/BM/PL/KTT bên dưới là **vai trò nghiệp vụ từ danh mục người dùng cung cấp**, không phải Agent mới được đăng ký. Không tạo thêm Agent trùng chức năng.

## Luồng thực hiện

1. `HD01` đọc bảng hóa đơn `.xlsx` hoặc `.csv`. `HD02` phân luồng mua vào, `HD03` phân luồng bán ra dựa trên MST người nộp thuế và MST hai bên; không ghép theo tên.
2. `HD04` kiểm tra khóa hóa đơn trùng, ngày, trạng thái được khai báo, số tiền, thuế suất ghi trên nguồn, kỳ và ô công thức. Trạng thái thiếu/không nhận diện, hóa đơn trùng, điều chỉnh, thay thế, hủy, sai số học, ngoài kỳ hoặc có công thức được giữ lại để soát và không cộng vào dự thảo.
3. `PL01`–`PL04` tái sử dụng Skill `accounting-law-watch`; không tạo watcher thứ hai. Trước khi chọn phiên bản, truyền JSON report của law-watch bằng `--law-watch-report`. Báo cáo phải cho thấy đã đọc nguồn chính thức, không có đề xuất văn bản mới chưa duyệt, không tự áp dụng quy tắc và các nguồn bắt buộc của phiên bản đều PASS. Mọi kết luận về kỳ vẫn cần người duyệt.
4. `TK01` tổng hợp doanh số và tiền thuế theo chiều mua/bán và **nhãn thuế suất trên nguồn**. Công cụ không suy diễn diện chịu thuế, điều kiện khấu trừ hoặc số thuế phải nộp.
5. `BM01` kiểm tra kỳ hiệu lực, phạm vi người nộp thuế, loại hồ sơ và law-watch trước khi ánh xạ. Người dùng xác nhận `--taxpayer-case credit_method_production_business` và `--filing-type first`; hồ sơ bổ sung bị chặn vì quy trình 01/KHBS chưa triển khai. `BM03` chỉ ánh xạ dòng bán ra qua `form_line_code`/`form_tax_line_code` đã được rà soát; hóa đơn mua vào phải gán tường minh `[23]`/`[24]` hoặc `[23a]`/`[24a]`. `[23a]` nằm trong `[23]`, `[24a]` nằm trong `[24]`; không cộng phần nhập khẩu lần nữa. Không tự suy mã từ tên hàng, tên khách hàng hoặc thuế suất. `BM02` sao chép workbook mẫu chính thức hiện **NOT STARTED**.
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
  --taxpayer-case credit_method_production_business \
  --filing-type first \
  --invoice-data-complete \
  --supplemental-form-inputs "duong-dan/du-lieu-ngoai-hoa-don.json" \
  --sheet "HoaDon" \
  --header-row 1
```

`--period` nhận `YYYY-MM` hoặc `YYYY-Q1` đến `YYYY-Q4`. `--form-version` chỉ nhận `80/2021/TT-BTC` hoặc `89/2026/TT-BTC`, bắt buộc khi muốn tạo dòng tờ khai và được kiểm tra theo ngày hiệu lực; không tự chọn theo kỳ. `--law-watch-report` bắt buộc khi chọn mẫu. Phải xác nhận phạm vi người nộp thuế và hồ sơ lần đầu. Chỉ dùng `--invoice-data-complete` sau khi xác nhận nguồn bao phủ đầy đủ kỳ; nếu thiếu cờ, dòng không có hóa đơn giữ `null`, không đổi thành 0. Tệp `--supplemental-form-inputs` phải là JSON có `amount` và `source` cho từng chỉ tiêu ngoài hóa đơn `[22]`, `[25]`, `[37]`, `[38]`, `[39a]`, `[40b]`, `[42]`; không tự điền 0. Cột `form_line_code`/`form_tax_line_code` phải được kế toán/BM03 rà soát. Thuế suất không được dùng để suy loại hàng. Nếu thiếu mã, phần tờ khai được đánh dấu thiếu ánh xạ. Nếu không chọn `--output`, chương trình tạo `.vat-draft.json` cạnh nguồn, không ghi vào workbook.

Để xuất workbook soát xét nội bộ, dùng `--output "ket-qua-soat-xet.xlsx"`. Các ô được ghi dưới dạng chuỗi, workbook không chứa công thức và tệp nguồn chỉ được đọc. Workbook này không sao chép mẫu pháp định, không sẵn sàng nộp và không thay cho bước `BM02`.

## Tình trạng mẫu pháp định

- Nguồn Công báo/Chính phủ xác nhận 01/GTGT thuộc Phụ lục II TT80/2021; TT40/2025 cập nhật địa chỉ [11a] và bỏ trường huyện [11b]. Đã đọc toàn văn bản ký số TT94/2025 tại Công báo: phần sửa TT80 thay đổi thủ tục tiếp nhận/giải quyết hoàn thuế và cách ghi định danh cá nhân ở trường biểu mẫu có thông tin giấy tờ cá nhân; phần mẫu TT40 áp dụng cho bộ mẫu của TT40. Mẫu 01/GTGT của tổ chức không có trường giấy tờ định danh cá nhân; rà soát không thấy TT94 đổi trường hoặc công thức 01/GTGT. Kỳ TT80 từ 14/10/2025 không bị chặn riêng bởi TT94; các nguồn luật khác vẫn phải đạt kiểm tra.
- TT89/2026 có hiệu lực từ 2026-07-01. Đã kiểm tra tệp ký số chính thức: Phụ lục I, trang PDF 241 là mẫu 01/GTGT; trang này có [32b], [34a] và công thức tổng doanh thu mới. Mốc hiệu lực chưa tự quyết định biểu mẫu cho mọi hồ sơ chuyển tiếp; phải rà kỳ tính thuế, thời điểm khai và trường hợp người nộp thuế.
- Với kỳ TT89, law-watch còn yêu cầu truy cập nguồn chính thức cho Luật Quản lý thuế 108/2025/QH15, Nghị định 254/2026/NĐ-CP và TT91/2026/TT-BTC. Metadata cho thấy các mốc hiệu lực chung từ 01/07/2026; Luật 108 có một số quy định về hộ/cá nhân kinh doanh và hóa đơn điện tử hiệu lực từ 01/01/2026. Chưa xác minh toàn bộ tác động chuyển tiếp hoặc ảnh hưởng tới trường/công thức 01/GTGT; không dùng các nguồn này để tự đổi mẫu.
- XML hóa đơn đầu vào và định dạng dữ liệu/schema XML theo pháp luật hóa đơn hiện hành chưa triển khai. Dù Nghị định 254/2026 và TT91/2026 thuộc chuỗi hóa đơn điện tử hiện hành, không tạo parser hoặc khẳng định schema hợp lệ trước khi đối chiếu tài liệu kỹ thuật chính thức và test bằng hóa đơn mẫu đã xác minh.
- Một trang hỏi đáp của Bộ Tài chính có câu hỏi về [37]/[38]; trang hỏi của người dùng không được coi là câu trả lời hay hướng dẫn chính thức của Bộ.
- Đã đọc bản PDF đính chính 2551/QĐ-BTC đính kèm trên Cổng Chính phủ: phần Điều 1 sửa danh sách mẫu được thay thế tại Điều 99 TT89; danh sách sửa không nêu 01/GTGT. Việc này không xác nhận nội dung hoặc phạm vi kỳ của mẫu 01/GTGT.
- TT89 Annex I liệt kê các phụ lục GTGT 01-2, 01-3, 01-6, 01-7 và 01-8. 01-8 là phụ lục thông tin đề nghị hoàn thuế; các phụ lục phân bổ còn lại phụ thuộc ngành, địa bàn hoặc chi nhánh. Chưa ánh xạ các phụ lục vào tệp đầu ra.
- Danh mục có công thức của hai phiên bản; các điều kiện `[40a] ≥ 0` và `[41] ≤ 0` được giữ nguyên theo mẫu. TT80 có hiệu lực đến 30/06/2026; TT89 bắt đầu từ 01/07/2026. CLI chỉ lập mapping khi kỳ, phạm vi người nộp thuế, hồ sơ và law-watch vượt kiểm tra. Đây chưa phải lựa chọn tự động; `auto_form_selection` luôn false.

## Giới hạn hiện tại

- Đã hỗ trợ nhập `.xlsx`/`.csv`, giữ mã dạng chuỗi và số 0 đầu, phân loại theo MST, kiểm tra hóa đơn, tổng hợp, ánh xạ mã dòng được chỉ định tường minh, tính công thức và soát độc lập. Các chỉ tiêu ngoài hóa đơn `[22]`, `[25]`, `[37]`, `[38]`, `[39a]`, `[40b]`, `[42]` không có nguồn sẽ để trống và khiến phép tính chưa hoàn tất. Dòng hóa đơn không gán được chỉ tiêu không được tự đổi thành 0.
- Đọc XML hóa đơn/PDF/ảnh, đối chiếu sổ 133/33311, sao chép/điền workbook pháp định bảo toàn định dạng, ánh xạ phụ lục, xuất XLSX pháp định, kiểm tra XML theo schema, tạo/ký/gửi tờ khai và xử lý khai bổ sung là **NOT STARTED**.
- Không dùng dữ liệu thực trong test. Không đưa tệp hóa đơn, mã số thuế, tên doanh nghiệp hoặc token lên repository.
