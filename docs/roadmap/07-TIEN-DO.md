# Tiến độ dự án

**Cập nhật:** 20/11/2026  
**Nhánh phát triển:** codex/accounting-workbook-audit-mvp

| Giai đoạn | Nội dung | Trạng thái hiện tại |
| --- | --- | --- |
| 1 | Kiểm kê và hoàn thiện Việt hóa | Kiểm kê ban đầu đã ghi; độ phủ tiếng Việt chưa nghiệm thu |
| 2 | Không gian kế toán và điều hướng | Chưa triển khai UI |
| 3 | AI Agents kế toán | Chưa tích hợp Agent nghiệp vụ |
| 4 | Skills và xử lý dữ liệu | Skill rà soát .xlsx đã có mã; 6/6 test CI thành công |
| 5 | Kiểm thử đầu-cuối và build | CI Skill đạt; chưa xác nhận build hoặc nghiệm thu toàn ứng dụng |

## Tình trạng kiểm thử nền

Workflow Test #5 trên main có 1.112/1.113 test thành công; một test giao diện lựa chọn model trong ChatBox còn lỗi. Các job Python, smoke test backend và Electron preview trong cùng workflow đều thành công. Lỗi này đã được ghi nhận là trạng thái nền và chưa được sửa trong nhánh Skill.

## Việc kế tiếp

1. Mở PR nháp và kiểm tra các workflow được kích hoạt trên PR.
2. Đối chiếu toàn bộ locale tiếng Việt với nguồn, rồi xử lý chuỗi UI còn thiếu theo từng nhóm.
3. Kiểm tra đăng ký navigation/Space hiện tại trước khi thêm không gian kế toán đầu tiên.
4. Chọn một Skill nghiệp vụ ưu tiên tiếp theo và hoàn thiện luồng thực thi + test trước khi tạo thêm Skill khác.
5. Cập nhật tiến độ bằng link commit, PR, log kiểm thử và những giới hạn còn lại.

Không gộp các trạng thái đã viết mã, CI đạt, đã chạy ứng dụng và đã nghiệm thu nghiệp vụ thành một kết luận.
