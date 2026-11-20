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

## Kết quả đã xác minh

- Run 1 (44777652053) thất bại ở bước import do biểu thức chính quy bị escape thừa. Lỗi đã được sửa trong commit 4a1cd7b0d5d4795d4c5a58a00fad8957989a0025.
- Run 2 (44777831156) thành công; 6 test chạy, kết quả OK. Bộ test dùng Python chuẩn, không tải dữ liệu kế toán thật.
- Workflow Test #5 trên commit nền (44774491335) có 1.112/1.113 test thành công; còn một lỗi ở test/unit/components/ChatBox.spaceModelSelection.test.tsx. Các job Browser Preview Electron, Python Tests và Web + Local Brain Smoke thành công.

## Phạm vi kết quả

Workflow riêng xác nhận các kiểm thử của Skill, không xác nhận giao diện Việt hóa 100%, build ứng dụng, tính lại công thức Excel hay tính hợp lệ nghiệp vụ kế toán/thuế/BHXH. Không dùng tệp kế toán thật trong job CI.
