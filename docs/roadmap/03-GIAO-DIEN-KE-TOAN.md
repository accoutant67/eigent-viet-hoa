# Lộ trình giao diện kế toán

**Trạng thái:** Chưa triển khai giao diện kế toán trong lát cắt hiện tại.

## Phạm vi sản phẩm dự kiến

Không gian kế toán trong Eigent sẽ được chia thành các khu vực sau:

1. Tổng quan kế toán.
2. Trợ lý AI kế toán.
3. Hóa đơn.
4. Thuế.
5. Tiền lương.
6. BHXH.
7. Xuất nhập tồn.
8. Công nợ.
9. Chứng từ.
10. Tài sản cố định.
11. Báo cáo tài chính.
12. Phân tích tài chính.
13. Kiểm tra và đối chiếu.
14. Công cụ AI.
15. Quản lý Skills.

## Điều kiện trước khi lập trình UI

- Kiểm tra tuyến điều hướng và cấu trúc Space/Session hiện tại.
- Đọc docs/design-system/design.md và docs/product-terminology.md.
- Tái sử dụng primitive trong src/components/ui, semantic token và pattern hiện có.
- Không tạo nút trang trí. Mỗi thao tác hiển thị phải có hành vi, trạng thái tải, rỗng, lỗi và dữ liệu demo.
- Giữ nguyên API, route và khóa lưu trữ hiện có; tên hiển thị không được làm đổi hợp đồng kỹ thuật.

## Nghiệm thu

UI được xem là hoàn thành khi có điều hướng thật, nội dung tương ứng và test tương tác; đã kiểm tra keyboard, focus, theme sáng/tối, nội dung dài và cửa sổ hẹp. Không tính trang tĩnh hoặc mockup là chức năng hoàn chỉnh.
