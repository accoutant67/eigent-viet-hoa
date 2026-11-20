# Kế hoạch và kết quả kiểm thử

## Kiểm thử Skill rà soát Excel

Bộ kiểm thử tổng hợp trong resources/example-skills/accounting-workbook-audit/tests/ bao phủ:

- Phát hiện dòng trùng và khóa trùng theo định danh được chọn.
- Phân biệt mã số có định dạng hiển thị số 0 đầu với chuỗi số khác.
- Phát hiện cột bắt buộc trống và cột không tồn tại.
- Ghi nhận ô lỗi Excel và đếm ô công thức mà không tính lại.
- Không để giá trị ô mẫu xuất hiện trong báo cáo; không sửa tệp nguồn.
- Tạo báo cáo JSON riêng và chặn ghi đè nếu không có --force.
- Từ chối đầu vào không phải .xlsx và XML có khai báo DTD/entity.

Workflow: .github/workflows/accounting-workbook-audit.yml  
Lệnh chạy: python -m unittest discover -s resources/example-skills/accounting-workbook-audit/tests -v

## Trạng thái xác minh

- Mã nguồn và bộ test đã được thêm lên nhánh codex/accounting-workbook-audit-mvp.
- Chưa ghi PASS cho đến khi GitHub Actions hoàn tất thành công trên nhánh này.
- Các workflow tổng của dự án cần tiếp tục được xem riêng; workflow Skill không thay thế type-check, test frontend, smoke test backend hoặc build ứng dụng.
- Không dùng tệp kế toán thật trong bất kỳ job CI nào.
