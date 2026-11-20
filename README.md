# Eigent Việt hóa — Trợ lý AI đa tác nhân trên máy tính

> **Bản Việt hóa cộng đồng** của [Eigent](https://github.com/eigent-ai/eigent), phát triển độc lập dựa trên mã nguồn mở theo giấy phép Apache 2.0. Đây không phải bản phát hành chính thức của Eigent.ai.

**[Tài liệu gốc bằng tiếng Anh](./README_EN.md)** · [Giấy phép](./LICENSE) · [Dự án của tác giả](https://github.com/eigent-ai/eigent)

## Giới thiệu

Eigent là ứng dụng AI trên máy tính cho phép người dùng quản lý các **tác nhân AI (agents)** phối hợp thực hiện công việc. Các tác nhân có thể hỗ trợ nghiên cứu, viết nội dung, lập trình, quản lý tệp, thao tác qua trình duyệt và thực hiện quy trình có nhiều bước.

Mục tiêu của bản Việt hóa này là giúp người dùng Việt Nam dễ dàng sử dụng Eigent mà vẫn **giữ nguyên những chức năng và mã nguồn cơ bản**.

## Chức năng chính

- **Trò chuyện với AI:** đặt yêu cầu, theo dõi tác vụ và xem kết quả.
- **Đội ngũ tác nhân AI:** tạo và phân công nhiều tác nhân để phối hợp xử lý công việc.
- **Không gian và phiên làm việc:** tổ chức phiên, tệp và tiến độ.
- **Tự động hóa:** đặt lịch cho tác vụ lặp lại.
- **Kỹ năng và kết nối MCP:** mở rộng chức năng thông qua công cụ tích hợp.
- **Tùy chọn mô hình AI:** kết nối mô hình được hỗ trợ phù hợp với cấu hình.
- **Triển khai cục bộ:** có thể tự quản lý dịch vụ khi cài đúng theo hướng dẫn gốc.

## Những phần đã được Việt hóa

- Bổ sung ngôn ngữ **Tiếng Việt (vi/vi-VN)**.
- Thêm tiếng Việt vào màn hình thiết lập ban đầu, menu tài khoản và trang cài đặt.
- Thêm bản dịch cho 12 nhóm giao diện, bao gồm trò chuyện, tác nhân, kỹ năng, cài đặt, kết nối, menu ứng dụng.
- Đặt tiếng Việt làm ngôn ngữ mặc định cho tài khoản mới trong bản Fork này; vẫn tôn trọng lựa chọn ngôn ngữ đã lưu.
- Giữ các thẻ kỹ thuật và biến `{{placeholder}}` để tránh làm hỏng hành vi ứng dụng.

**Tiến độ:** Bản hiện tại dịch một phần chuỗi giao diện. Các nội dung chưa dịch vẫn có thể hiển thị tiếng Anh. Đây **chưa phải bản Việt hóa hoàn chỉnh 100% và chưa phải bản cài Windows được kiểm thử**.

## Cách tải mã nguồn và chạy thử

Yêu cầu cơ bản: Git, Node.js phiên bản **18–22**, npm; môi trường backend có thể yêu cầu công cụ Python và cấu hình bổ sung.

```powershell
git clone https://github.com/accoutant67/eigent-viet-hoa.git
cd eigent-viet-hoa
npm install
npm run check:i18n
npm run type-check
npm run dev
```

Vào ứng dụng, mở **Cài đặt → Chung → Ngôn ngữ → Tiếng Việt** nếu muốn chọn thủ công. Nếu dùng backend đám mây trong chế độ xem nhanh, bạn có thể phải tạo tài khoản Eigent. Để chạy độc lập trên máy, xem [hướng dẫn triển khai cục bộ](./server/README_EN.md).

## Kiểm thử

```bash
npm run check:i18n
npm run type-check
npm test
```

Các lệnh này cần chạy trên máy có đầy đủ môi trường và thư viện. Không đăng khóa API, token hay tệp cấu hình chứa bí mật vào GitHub.

## Phân biệt GitHub và Eigent

Các nút **Code, Issues, Pull requests, Actions, Settings** ở phía trên trang này là giao diện của **website GitHub**, nên không thể Việt hóa bằng cách sửa mã nguồn Eigent. Nội dung README này và giao diện ứng dụng Eigent là hai phần có thể thay đổi trong repository.

## Bản quyền

Nguồn: [eigent-ai/eigent](https://github.com/eigent-ai/eigent). Giữ nguyên [LICENSE](./LICENSE), ghi nhận tác giả và tuân thủ giấy phép Apache 2.0. Bản dịch cộng đồng không đại diện hoặc được chứng nhận bởi chủ sở hữu dự án gốc.
