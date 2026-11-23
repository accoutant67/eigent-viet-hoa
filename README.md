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

## Hỗ trợ nghiệp vụ kế toán (đang phát triển)

Repository hiện có ba Skill kế toán mẫu trong hạ tầng Skill hiện tại của Eigent: `accounting-workbook-audit` (đọc và báo cáo lỗi `.xlsx`), `accounting-law-watch` (theo dõi danh sách văn bản chính thức và tạo đề xuất cần duyệt), và `accounting-vat-return` (nhập hóa đơn `.xlsx`/`.csv`, phân loại theo MST, kiểm tra cơ bản, tổng hợp và xuất JSON dự thảo GTGT tháng/quý). Đây là ba Skill, không phải 72 Agent đã đăng ký.

`accounting-vat-return` giữ nguyên tệp nguồn, yêu cầu kiểm tra trạng thái hóa đơn, ghép bên mua/bán theo MST chứ không theo tên, đánh dấu hóa đơn trùng/công thức/sai số học để soát và so tổng bằng lượt tính độc lập. Mẫu 01/GTGT TT80 và TT89 đã được xác minh từ nguồn chính thức; lựa chọn theo kỳ và ánh xạ trường đầu ra chưa được duyệt. Xuất XLSX/XML và nộp tờ khai đang NOT STARTED. Không dùng kết quả JSON để nộp thuế.

Chạy trong môi trường có Python 3.11:

Kiểm tra workbook chỉ đọc:

```
python resources/example-skills/accounting-workbook-audit/scripts/audit_workbook.py "bang-ke.xlsx" --required-column "Mã nhân viên" --key-column "Mã nhân viên"
```

Có thể thêm --sheet "Tên sheet", --header-row 2 hoặc --output "duong-dan/bao-cao.audit.json". Công cụ không sửa workbook, không tính lại công thức, không tự xóa hoặc điền dữ liệu và không xác nhận tính hợp lệ kế toán/thuế/pháp lý. Chỉ dùng dữ liệu giả lập trong CI. Xem lộ trình kế toán tại docs/roadmap/01-KIEM-KE-DU-AN.md.

Chạy dự thảo nội bộ GTGT:

```
uv run --project backend python resources/example-skills/accounting-vat-return/scripts/vat_return_draft.py "hoa-don.xlsx" --taxpayer-tax-id "0100000001" --period "2026-Q3" --sheet "HoaDon"
```

Lộ trình và trạng thái kiểm thử hiện tại nằm trong [tiến độ dự án](./docs/roadmap/07-TIEN-DO.md) và [báo cáo kiểm thử](./docs/roadmap/06-KIEM-THU.md). Chỉ dùng dữ liệu giả lập; không đưa hóa đơn, MST, dữ liệu kế toán hoặc token thực lên repository.
