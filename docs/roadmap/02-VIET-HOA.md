# Lộ trình hoàn thiện Việt hóa

**Trạng thái:** Đang thực hiện một phần; chưa nghiệm thu 100%.

README hiện ghi nhận 12 nhóm locale tiếng Việt: agents, chat, common, connectors, dashboard, folder, layout, markdown, setting, triggers, update và workforce. Tài nguyên đã có không đồng nghĩa mọi chuỗi giao diện đã được dịch.

## Tiêu chí

- Đối chiếu khóa tiếng Việt với locale nguồn, giữ nguyên khóa và biến.
- Kiểm tra chuỗi viết trực tiếp trong giao diện, menu Electron, thông báo, tooltip, hộp thoại và nội dung lỗi.
- Dịch tự nhiên, thống nhất thuật ngữ; giữ tên thương hiệu và định danh kỹ thuật.
- Chạy npm run check:i18n, type-check và các test giao diện liên quan.
- Thử chuyển ngôn ngữ, dấu tiếng Việt, chuỗi dài, trạng thái lỗi và kích thước cửa sổ hẹp.
- Chỉ công bố tỷ lệ hoàn thành sau khi có báo cáo kiểm kê có thể tái lập.

## Trạng thái công việc

| Hạng mục | Trạng thái |
| --- | --- |
| 12 nhóm tài nguyên locale vi | Có trong repository; độ phủ cần kiểm tra |
| Kiểm tra tính đồng nhất khóa và cách dùng locale | Có lệnh kiểm tra; cần ghi log chạy trên nhánh hiện tại |
| Chuỗi giao diện còn viết trực tiếp trong mã | Chưa kiểm kê đầy đủ |
| Kiểm tra giao diện ở các kích thước và theme | Chưa nghiệm thu |
| Việt hóa giao diện kế toán bổ sung | Chưa bắt đầu |

Skill rà soát Excel trong nhánh này không thay đổi locale. Giao diện sản phẩm phải theo docs/design-system/design.md; cách gọi UI phải theo docs/product-terminology.md.
