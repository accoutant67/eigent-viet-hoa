# Lộ trình AI Agents kế toán

**Trạng thái:** Chưa tích hợp Agent kế toán trong lát cắt hiện tại.

## Nhóm Agent mục tiêu

1. Kế toán tổng hợp.
2. Kế toán thuế.
3. Tiền lương.
4. BHXH.
5. Hóa đơn.
6. Xuất nhập tồn.
7. Công nợ.
8. Tài sản cố định.
9. Báo cáo tài chính.
10. Kiểm soát dữ liệu.

## Điều kiện để một Agent được nghiệm thu

Mỗi Agent cần có vai trò và phạm vi dữ liệu rõ ràng, công cụ/Skill thực sự gọi được, giới hạn nghiệp vụ, quy trình bàn giao cho Agent khác và bài kiểm thử bằng dữ liệu giả lập. Chỉ tạo tên hoặc prompt mô tả không được tính là hoàn thành.

## Nguyên tắc

- Dùng cơ chế đăng ký Agent sẵn có của Eigent; không tạo kiến trúc song song.
- Không tự suy luận số liệu, kỳ kế toán, chế độ kế toán hay quy định còn thiếu.
- Gắn kết quả với dữ liệu đầu vào và nêu phần cần kế toán duyệt.
- Không tự ký, nộp hồ sơ hoặc đưa ra xác nhận pháp lý.
- Chỉ mở rộng quyền đọc/ghi sau khi có ranh giới tệp và phê duyệt phù hợp.
