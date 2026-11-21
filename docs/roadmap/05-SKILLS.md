# Lộ trình Skills kế toán

**Trạng thái:** Ba Skill kế toán mẫu có mã trong `resources/example-skills/`: kiểm toán workbook, theo dõi pháp luật và dự thảo GTGT. Skill GTGT mới xử lý dữ liệu đầu vào đến JSON nội bộ; các biểu mẫu pháp định, XML và 12 nhóm Skill còn lại chưa hoàn tất.

Backend hiện có cơ chế đồng bộ Skills mẫu từ resources/example-skills và SkillToolkit để phát hiện Skill trong phạm vi làm việc. Skill xlsx hiện có là Skill tổng quát.

## Skills đã có mã

### accounting-workbook-audit

- Đường dẫn: resources/example-skills/accounting-workbook-audit/.
- Đầu vào: một hoặc nhiều sheet trong tệp .xlsx; người dùng chỉ định hàng tiêu đề, cột bắt buộc và cột khóa nếu cần.
- Phát hiện: dòng trùng, khóa trùng, ô bắt buộc trống và ô Excel báo lỗi.
- Đầu ra: báo cáo .audit.json riêng.
- An toàn: không sửa workbook; không ghi giá trị định danh vào báo cáo; chỉ dùng dữ liệu giả lập trong test.
- Giới hạn: không tính lại công thức, không kết luận thuế/kiểm toán/pháp lý, không hỗ trợ XML hoặc định dạng .xls.

CI của Skill chạy unittest với workbook giả lập. Trạng thái nghiệm thu cuối cùng phải lấy từ kết quả workflow GitHub của nhánh/PR.

### accounting-law-watch

- Đường dẫn: resources/example-skills/accounting-law-watch/.
- Đầu vào: danh sách văn bản từ Cổng Thông tin điện tử Chính phủ và trang chi tiết chính thức trong allowlist HTTPS.
- Đầu ra: phát hiện văn bản ứng viên, đọc ngày ban hành/ngày hiệu lực khi trang chi tiết có thông tin, và tạo nội dung Issue đề xuất để người có chuyên môn duyệt.
- An toàn: fixture chạy offline; watcher không cập nhật công thức/mẫu/quy tắc kỳ đã duyệt; kiểm tra redirect trước khi theo liên kết; publisher có dry-run và chống trùng.
- Giới hạn: nguồn Bộ Tài chính hỏi đáp bị HTTPError trong lần kiểm tra trực tiếp hiện tại; chưa có Issue thật nào được tạo trong lượt này.

### accounting-vat-return

- Đường dẫn: resources/example-skills/accounting-vat-return/.
- Đầu vào: `.xlsx`/`.csv` giả lập hoặc dữ liệu người dùng chạy cục bộ; giữ nguyên tệp nguồn, mã `00017`, định danh đối chiếu theo MST.
- Luồng hiện có: nhập → phân loại mua/bán → kiểm tra → tổng hợp theo nhãn thuế suất nguồn → đối chiếu độc lập → xuất JSON dự thảo nội bộ.
- Kiểm thử hiện tại: 11/11 test đơn vị, CLI smoke và test tích hợp Eigent 1/1 PASS; full backend regression cục bộ đang BLOCKED do bị hệ thống kết thúc mã 137.
- Giới hạn: các vai trò HD01–HD04, TK01, TK05, BM01–BM03, PL01–PL04 và KTT03 là bản đồ quy trình trong Skill, chưa phải Agents đăng ký; chưa ánh xạ chỉ tiêu pháp định, chưa xuất XLSX/XML hoặc nộp tờ khai.

## Danh sách ưu tiên tiếp theo

| #   | Skill                          | Trạng thái                                                          |
| --- | ------------------------------ | ------------------------------------------------------------------- |
| 1   | Kế toán thuế                   | GTGT một phần; TNCN/TNDN chưa bắt đầu                               |
| 2   | Bảo hiểm xã hội                | Chưa bắt đầu                                                        |
| 3   | Tiền lương                     | Chưa bắt đầu                                                        |
| 4   | Hóa đơn điện tử                | GTGT nhập `.xlsx`/`.csv` một phần; XML/PDF/ảnh chưa bắt đầu         |
| 5   | Báo cáo tài chính              | Chưa bắt đầu                                                        |
| 6   | Kế toán tổng hợp và định khoản | Chưa bắt đầu                                                        |
| 7   | Xuất nhập tồn                  | Chưa bắt đầu                                                        |
| 8   | Công nợ phải thu, phải trả     | Chưa bắt đầu                                                        |
| 9   | Tài sản cố định                | Chưa bắt đầu                                                        |
| 10  | Tiền mặt và ngân hàng          | Chưa bắt đầu                                                        |
| 11  | Hồ sơ lao động                 | Chưa bắt đầu                                                        |
| 12  | Đối chiếu mã số thuế           | Chưa bắt đầu                                                        |
| 13  | Phiếu thu, phiếu chi, bảng kê  | Chưa bắt đầu                                                        |
| 14  | Kiểm tra và đối chiếu dữ liệu  | GTGT có soát cơ bản và tổng độc lập; nghiệp vụ còn lại chưa bắt đầu |
| 15  | Tự động hóa quy trình kế toán  | Chưa bắt đầu                                                        |
