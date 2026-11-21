# Kiểm kê dự án

**Mốc kiểm kê:** 20/11/2026  
**Repository:** accoutant67/eigent-viet-hoa  
**Nhánh nền:** main  
**Commit nền:** 643ae05615a119a1cbe49e79c6e51b640731991f

## Phạm vi đã xác nhận

- Đây là fork của Eigent, không phải dự án MausBot; repository có ứng dụng desktop React/TypeScript/Electron và backend Python.
- Backend khai báo Python >=3.11,<3.12. README ghi nhận 12 nhóm tài nguyên giao diện tiếng Việt nhưng bản dịch mới là một phần; chưa xác nhận mức phủ 100%.
- Backend có cơ chế đồng bộ resources/example-skills vào thư mục Skills của người dùng và SkillToolkit để phát hiện Skills. Skill xlsx tổng quát đã có.
- Chưa có bằng chứng trong lần kiểm kê này rằng giao diện kế toán, 10 Agent kế toán hoặc 15 Skill nghiệp vụ đã hoàn thành.

## Kết quả Actions trên commit nền

Workflow Test #5, run 44774491335, hoàn tất với kết quả failure. Trong job Frontend Guardrails, 52/53 tệp test đạt và 1.112/1.113 test đạt. Test lỗi là test/unit/components/ChatBox.spaceModelSelection.test.tsx — “offers Cancel but not Resume after a write with an unknown outcome”. Các job Browser Preview Electron, Python Tests và Web + Local Brain Smoke đều thành công.

Đây là trạng thái của commit nền main trước khi có Skill rà soát Excel; không gán lỗi này cho nhánh phát triển.

## Lát cắt đầu tiên trên nhánh phát triển

Nhánh codex/accounting-workbook-audit-mvp bổ sung Skill accounting-workbook-audit:

- Đọc .xlsx ở chế độ chỉ đọc.
- Phát hiện dòng trùng, khóa trùng theo cột do người dùng chọn, cột bắt buộc trống và ô lỗi Excel.
- Tạo báo cáo JSON riêng; không sửa tệp nguồn và không công khai giá trị ô trong phần phát hiện.
- Kiểm thử bằng workbook giả lập, không dùng dữ liệu doanh nghiệp.
- Có workflow CI riêng chỉ chạy bộ kiểm thử của Skill.

Workflow Accounting workbook audit run 2 (44777831156) đã thành công với 6/6 test. Đây là kết quả của bộ test Skill, không thay thế kiểm thử toàn bộ ứng dụng.

## Việc cần kiểm kê tiếp

1. Theo dõi workflow trên PR sau mỗi cập nhật nhánh.
2. Đối chiếu khóa và cấu trúc của 12 nhóm locale Việt với locale nguồn.
3. Kiểm tra các chuỗi giao diện viết trực tiếp trong mã và các bề mặt Electron.
4. Lần theo điểm mở rộng chính thức cho Space, điều hướng và đăng ký Agent trước khi thêm UI kế toán.
5. Kiểm tra từng nhóm chức năng hiện có bằng test hoặc chạy ứng dụng; không suy ra trạng thái từ tên thư mục.
6. Cập nhật tài liệu này bằng bằng chứng mới, không ghi PASS chỉ vì mã đã được viết.
