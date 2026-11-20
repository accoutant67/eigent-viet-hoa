# Lộ trình Skills kế toán

**Trạng thái:** Một Skill kế toán đã có mã và bộ kiểm thử trên nhánh phát triển; các Skill còn lại chưa bắt đầu.

Backend hiện có cơ chế đồng bộ Skills mẫu từ resources/example-skills và SkillToolkit để phát hiện Skill trong phạm vi làm việc. Skill xlsx hiện có là Skill tổng quát.

## Skill đã bổ sung

### accounting-workbook-audit

- Đường dẫn: resources/example-skills/accounting-workbook-audit/.
- Đầu vào: một hoặc nhiều sheet trong tệp .xlsx; người dùng chỉ định hàng tiêu đề, cột bắt buộc và cột khóa nếu cần.
- Phát hiện: dòng trùng, khóa trùng, ô bắt buộc trống và ô Excel báo lỗi.
- Đầu ra: báo cáo .audit.json riêng.
- An toàn: không sửa workbook; không ghi giá trị định danh vào báo cáo; chỉ dùng dữ liệu giả lập trong test.
- Giới hạn: không tính lại công thức, không kết luận thuế/kiểm toán/pháp lý, không hỗ trợ XML hoặc định dạng .xls.

CI của Skill chạy unittest với workbook giả lập. Trạng thái nghiệm thu cuối cùng phải lấy từ kết quả workflow GitHub của nhánh/PR.

## Danh sách ưu tiên tiếp theo

| # | Skill | Trạng thái |
| --- | --- | --- |
| 1 | Kế toán thuế | Chưa bắt đầu |
| 2 | Bảo hiểm xã hội | Chưa bắt đầu |
| 3 | Tiền lương | Chưa bắt đầu |
| 4 | Hóa đơn điện tử | Chưa bắt đầu |
| 5 | Báo cáo tài chính | Chưa bắt đầu |
| 6 | Kế toán tổng hợp và định khoản | Chưa bắt đầu |
| 7 | Xuất nhập tồn | Chưa bắt đầu |
| 8 | Công nợ phải thu, phải trả | Chưa bắt đầu |
| 9 | Tài sản cố định | Chưa bắt đầu |
| 10 | Tiền mặt và ngân hàng | Chưa bắt đầu |
| 11 | Hồ sơ lao động | Chưa bắt đầu |
| 12 | Đối chiếu mã số thuế | Chưa bắt đầu |
| 13 | Phiếu thu, phiếu chi, bảng kê | Chưa bắt đầu |
| 14 | Kiểm tra và đối chiếu dữ liệu | Chưa bắt đầu |
| 15 | Tự động hóa quy trình kế toán | Chưa bắt đầu |
