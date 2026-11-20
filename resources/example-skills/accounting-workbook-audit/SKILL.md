---
name: accounting-workbook-audit
description: "Đọc và rà soát tệp Excel .xlsx theo yêu cầu kế toán: kiểm tra dòng trùng, khóa định danh trùng, cột bắt buộc còn trống, ô lỗi Excel và ô công thức; chỉ tạo báo cáo JSON riêng, không sửa sổ nguồn."
---

# Rà soát bảng Excel kế toán

Dùng kỹ năng này khi cần kiểm tra cấu trúc và chất lượng dữ liệu trong tệp .xlsx trước khi đối chiếu hoặc xử lý tiếp.

## Phạm vi

- Chỉ đọc tệp .xlsx; không ghi vào hoặc định dạng lại tệp nguồn.
- Có thể rà soát một hay nhiều sheet.
- Có thể phát hiện dòng dữ liệu trùng hoàn toàn, khóa trùng theo cột người dùng chỉ định, giá trị trống ở cột bắt buộc và ô Excel trả lỗi.
- Ghi một báo cáo .audit.json riêng, mặc định cạnh tệp nguồn.
- Giữ mã dạng văn bản và các số 0 đầu. Với ô số có định dạng chỉ gồm số 0, nhận diện cách hiển thị như 00017.
- Không dùng tên để ghép người lao động. Khi đối chiếu hồ sơ nhân sự, hãy chọn khóa định danh phù hợp như mã nhân viên hoặc CCCD và chỉ thực hiện khi người dùng đã chỉ định.
- Không tự xóa dòng trùng, điền ô trống, sửa số liệu hoặc tính lại công thức.

## Cách chạy

Từ thư mục gốc repository:

    python resources/example-skills/accounting-workbook-audit/scripts/audit_workbook.py "duong-dan/bang-ke.xlsx" --required-column "Mã nhân viên" --key-column "Mã nhân viên"

Dùng --sheet "Tên sheet" để giới hạn sheet. Có thể lặp --sheet, --required-column và --key-column. Đặt --header-row 2 nếu tiêu đề nằm ở hàng khác hàng 1.

Mặc định báo cáo là bang-ke.audit.json. Nếu tệp báo cáo đã tồn tại, chỉ ghi đè khi người dùng yêu cầu và thêm --force. Có thể chọn đường dẫn bằng --output.

## Quy trình

1. Xác nhận đúng tệp nguồn, sheet, hàng tiêu đề và khóa nghiệp vụ người dùng muốn rà soát.
2. Chạy script với các cột bắt buộc và khóa định danh đã xác nhận.
3. Đọc báo cáo JSON, nêu sheet và số hàng cụ thể cho từng phát hiện; không lặp lại giá trị định danh nhạy cảm.
4. Phân biệt cảnh báo kỹ thuật với kết luận nghiệp vụ. Dòng trùng là ứng viên cần xem, không phải lệnh xóa.
5. Chuyển các trường hợp chưa rõ cho kế toán kiểm tra chứng từ gốc.

## Giới hạn

- Không tính lại công thức Excel; nếu ô công thức thiếu giá trị lưu sẵn, báo cáo có thể không có giá trị ô đó.
- Không xác nhận tính hợp lệ của hóa đơn, tờ khai, thuế, BHXH, định khoản hay hồ sơ pháp lý.
- Không xác minh schema XML của cơ quan nhà nước, không ký và không nộp hồ sơ.
- Chỉ dùng dữ liệu giả lập trong kiểm thử repository. Không đưa tệp thật, CCCD, mã số thuế, bảng lương, token hoặc khóa API lên GitHub.
