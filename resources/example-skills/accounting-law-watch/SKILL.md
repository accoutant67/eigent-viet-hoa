---
name: accounting-law-watch
description: "Theo dõi văn bản pháp luật kế toán, thuế, hóa đơn và BHXH từ nguồn chính thức; phân biệt văn bản mới với danh mục đã biết, tạo đề xuất có ngày hiệu lực/kỳ áp dụng cần duyệt; không tự đổi công thức hoặc biểu mẫu."
---

# Theo dõi văn bản pháp luật kế toán

## Phạm vi hiện có

- Nguồn phát hiện văn bản mới vẫn là trang hệ thống văn bản của Cổng Thông tin điện tử Chính phủ: https://vanban.chinhphu.vn/he-thong-van-ban?classid=0&maxresults=50&mode=1 .
- Các trang Công báo điện tử Chính phủ, cơ sở dữ liệu văn bản pháp quy của Bộ Tài chính và một số trang hỗ trợ pháp lý Bộ Tài chính được kiểm tra để xác nhận tham chiếu đã biết. Chúng hiện là nguồn đối chiếu, chưa phải nguồn feed phát hiện thay đổi riêng.
- Registry ghi lại số hiệu đã biết và metadata nguồn để tránh lặp đề xuất. Registry này không chứa công thức kế toán/thuế và không được sửa tự động.
- Chuỗi nguồn GTGT còn ghi nhận Luật 90/2025/QH15, Nghị quyết 204/2025/QH15, Nghị định 174/2025/NĐ-CP, Luật 149/2025/QH15, Nghị định 359/2025/NĐ-CP, Luật 09/2026/QH16 và Nghị định 144/2026/NĐ-CP theo metadata Cổng Chính phủ. Phạm vi mặt hàng, chuyển tiếp và tác động tới 01/GTGT cần người có chuyên môn rà; không suy ra công thức hoặc phân loại từ việc ghi nhận văn bản.
- Bản hợp nhất 12/VBHN-VPQH và 03/VBHN-BTC được lưu làm tham chiếu lịch sử, không dùng làm nguồn hợp nhất hiện hành vì ban hành trước Luật 09/2026 và Nghị định 144/2026.
- Luật GTGT 48/2024/QH15, Nghị định 181/2025/NĐ-CP và TT69/2025/TT-BTC là căn cứ GTGT nền được ghi nhận bên cạnh TT80/2021, TT40/2025, TT94/2025, TT21/2026, TT89/2026 và đính chính 2551/QĐ-BTC.
- Đã thêm Luật Quản lý thuế 108/2025/QH15, Nghị định 254/2026/NĐ-CP và TT91/2026/TT-BTC vào registry theo metadata Cổng Chính phủ. Luật 108 có mốc hiệu lực chung 01/07/2026 và một số quy định về hộ/cá nhân kinh doanh, hóa đơn điện tử có hiệu lực từ 01/01/2026. Tác động của chuỗi mới đến 01/GTGT, kỳ chuyển tiếp và chuẩn XML vẫn **CHƯA XÁC MINH**; việc ghi nhận nguồn không đồng nghĩa với thay mẫu hay công thức.
- Cơ sở dữ liệu văn bản pháp quy Bộ Tài chính được kiểm tra như nguồn tham chiếu. Nếu máy chủ không phản hồi hoặc trang thay đổi cấu trúc, report phải ghi BLOCKED; điều này không được tính là nguồn đã kiểm chứng hay feed phát hiện mới.
- Kiểm tra nguồn tham chiếu bổ sung được cấu hình trong `registry.json`; mỗi lần chạy trực tiếp ghi PASS, FAIL khi thiếu số hiệu dự kiến hoặc liên kết tệp đính kèm mong đợi, hoặc BLOCKED theo từng nguồn. Với TT89/2026, monitor kiểm tra trang Chính phủ có gắn đúng PDF đính chính 2551/QĐ-BTC hay không. Kiểm tra liên kết không đồng nghĩa với đã xác minh toàn văn PDF hoặc nội dung pháp lý.

## Cách chạy

Kiểm tra trực tiếp nguồn chính thức, tạo report JSON và các đề xuất:

```bash
python resources/example-skills/accounting-law-watch/scripts/watch_official_documents.py \
  --registry resources/example-skills/accounting-law-watch/registry.json \
  --check-source --output law-watch-report.json
```

Chạy bằng fixture giả lập, không truy cập Internet:

```bash
python resources/example-skills/accounting-law-watch/scripts/watch_official_documents.py \
  --registry resources/example-skills/accounting-law-watch/registry.json \
  --fixture resources/example-skills/accounting-law-watch/tests/fixtures/official-listing.html \
  --output law-watch-report.json
```

Publisher hỗ trợ `--dry-run` để kiểm tra Issue sẽ được đề xuất mà không gửi yêu cầu đến GitHub. Chỉ workflow lịch chạy trên `main` được phép xuất bản Issue; workflow không tạo PR sửa mã hay sửa hồ sơ pháp lý.

## Quy trình xử lý đề xuất

1. Xác nhận nguồn thuộc danh sách hostname cơ quan nhà nước qua HTTPS và kiểm tra cả URL cuối sau redirect; nếu không đọc được trang hoặc metadata thì báo lỗi/CHƯA XÁC MINH.
2. So số hiệu với `registry.json`, ngày trên danh sách, ngày ban hành và ngày hiệu lực trên trang văn bản.
3. Tạo Issue đề xuất có liên kết nguồn, số hiệu và ngày; phạm vi kỳ kế toán/thuế vẫn là CHƯA XÁC MINH cho tới khi đọc điều khoản hiệu lực/chuyển tiếp.
4. Người có chuyên môn xác định văn bản cũ bị sửa, thay thế hay vẫn áp dụng cho kỳ cũ; cập nhật mapping/kỳ trong PR riêng sau khi được duyệt.
5. Chạy regression cho các kỳ trước và kỳ mới trước khi chấp nhận thay đổi.

## Giới hạn an toàn

- Không tự sửa công thức, mapping thuế, registry đã duyệt, template, tờ khai hoặc dữ liệu kế toán.
- Không đánh đồng ngày ban hành, ngày hiệu lực và kỳ kế toán/thuế áp dụng.
- Không chuyển một văn bản thành quy tắc nghiệp vụ chỉ bằng cách phát hiện trên trang nguồn.
- Không tự ký, nộp hồ sơ, sửa kỳ cũ hoặc khẳng định XML/mẫu hợp lệ.
- Chỉ dùng fixture giả lập trong test; không đưa tệp doanh nghiệp, CCCD, mã số thuế hoặc token vào repository.
