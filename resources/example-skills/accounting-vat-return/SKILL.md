---
name: accounting-vat-return
description: "Nhập và kiểm tra dữ liệu hóa đơn mua vào/bán ra, tổng hợp dự thảo GTGT theo tháng/quý; chỉ xuất bản JSON nội bộ cho tới khi mẫu pháp định và schema được xác minh."
---

# Dự thảo kê khai thuế GTGT tháng/quý

Skill này chạy trong hạ tầng Skill hiện có của Eigent. Các mã HD/TK/BM/PL/KTT bên dưới là **vai trò nghiệp vụ từ danh mục người dùng cung cấp**, không phải Agent mới được đăng ký. Không tạo thêm Agent trùng chức năng.

## Luồng thực hiện

1. `HD01` đọc bảng hóa đơn `.xlsx` hoặc `.csv`. `HD02` phân luồng mua vào, `HD03` phân luồng bán ra dựa trên MST người nộp thuế và MST hai bên; không ghép theo tên.
2. `HD04` kiểm tra khóa hóa đơn trùng, ngày, trạng thái được khai báo, số tiền, thuế suất ghi trên nguồn, kỳ và ô công thức. Trạng thái thiếu/không nhận diện, hóa đơn trùng, điều chỉnh, thay thế, hủy, sai số học, ngoài kỳ hoặc có công thức được giữ lại để soát và không cộng vào dự thảo.
3. `PL01`–`PL04` sử dụng Skill `accounting-law-watch` hiện có để tra nguồn chính thức, ngày ban hành/ngày hiệu lực, văn bản sửa đổi và kỳ cần rà soát. Mọi kết luận về kỳ phải có người duyệt.
4. `TK01` tổng hợp doanh số và tiền thuế theo chiều mua/bán và **nhãn thuế suất trên nguồn**. Công cụ không suy diễn diện chịu thuế, điều kiện khấu trừ hoặc số thuế phải nộp.
5. `BM01` đọc mẫu chính thức; `BM02` chuẩn bị bản sao biểu mẫu khi đã có bản nguồn; `BM03` điền đúng ánh xạ đã được kiểm chứng. Ở trạng thái hiện tại, ánh xạ 01/GTGT chưa được bật và không tạo tệp pháp định.
6. `TK05` kiểm tra độc lập phép tổng hợp. `KTT03` tổng hợp ngoại lệ, trạng thái nguồn và trình người dùng duyệt.
7. Xuất JSON dự thảo nội bộ. Không ký, nộp, tự đổi mẫu hoặc tạo XML.

## Chạy

```bash
uv run --project backend python resources/example-skills/accounting-vat-return/scripts/vat_return_draft.py \
  "duong-dan/hoa-don.xlsx" \
  --taxpayer-tax-id "0100000001" \
  --period "2026-Q3" \
  --sheet "HoaDon" \
  --header-row 1
```

`--period` nhận `YYYY-MM` hoặc `YYYY-Q1` đến `YYYY-Q4`. `--header-row` chọn hàng tiêu đề Excel (mặc định là hàng có dữ liệu đầu tiên). Nếu không chọn `--output`, chương trình tạo tệp `.vat-draft.json` cạnh nguồn, không ghi vào workbook. Kỳ được lọc tạm theo ngày hóa đơn và cần người rà soát quy tắc kỳ.

## Tình trạng mẫu pháp định

- Nguồn Công báo/Chính phủ xác nhận 01/GTGT thuộc Phụ lục II TT80/2021. Trên tờ khai này, TT40/2025 cập nhật địa chỉ [11a] thành xã/phường/đặc khu và bỏ trường huyện [11b]; TT94/2025 tiếp tục sửa các cụm thông tin trên biểu mẫu nhưng không thay mẫu 01/GTGT. TT21/2026 thay mẫu 02/TNDN và 05/TNDN, không thay 01/GTGT.
- TT89/2026 có hiệu lực từ 2026-07-01. Đã kiểm tra tệp ký số chính thức: Phụ lục I, trang PDF 241 là mẫu 01/GTGT; trang này có [32b], [34a] và công thức tổng doanh thu mới. Mốc hiệu lực chưa tự quyết định biểu mẫu cho mọi hồ sơ chuyển tiếp; phải rà kỳ tính thuế, thời điểm khai và trường hợp người nộp thuế.
- Q&A Bộ Tài chính ngày 2026-09-28 viện dẫn Phụ lục I TT89 khi hỏi về [37]/[38]. Đây là câu hỏi đang chờ trả lời, không được coi là hướng dẫn chính thức của Bộ.
- Đã đọc bản PDF đính chính 2551/QĐ-BTC đính kèm trên Cổng Chính phủ: phần Điều 1 sửa danh sách mẫu được thay thế tại Điều 99 TT89; danh sách sửa không nêu 01/GTGT. Việc này không xác nhận nội dung hoặc phạm vi kỳ của mẫu 01/GTGT.
- TT89 Annex I liệt kê các phụ lục GTGT 01-2, 01-3, 01-6, 01-7 và 01-8. 01-8 là phụ lục thông tin đề nghị hoàn thuế; các phụ lục phân bổ còn lại phụ thuộc ngành, địa bàn hoặc chi nhánh. Chưa ánh xạ các phụ lục vào tệp đầu ra.
- Mẫu pháp định và phiên bản ứng viên đã được nhận diện, nhưng lựa chọn theo kỳ, ánh xạ trường đầu ra và mẫu XLSX/XML vẫn cần kiểm chứng/duyệt. `legal_form.version` để trống và `auto_form_selection` là false.

## Giới hạn hiện tại

- Đã hỗ trợ nhập `.xlsx`/`.csv`, giữ mã số dạng chuỗi và định dạng số 0 đầu, phân loại theo MST, kiểm tra các trường/số học cơ bản, loại dòng cần duyệt khỏi phép tổng hợp, chạy đối chiếu tổng độc lập và xuất JSON dự thảo. JSON ghi cả mẫu/phiên bản ứng viên và trạng thái cần người rà soát; chưa điền các chỉ tiêu tờ khai.
- Đọc XML hóa đơn/PDF/ảnh, đồng bộ sổ 133/33311, mẫu Excel chính thức, xuất Excel, kiểm tra XML theo schema, tạo/ký/gửi tờ khai và xử lý khai bổ sung là **NOT STARTED**.
- Không dùng dữ liệu thực trong test. Không đưa tệp hóa đơn, mã số thuế, tên doanh nghiệp hoặc token lên repository.
