---
name: accounting-law-watch
description: "Theo dõi văn bản pháp luật kế toán, thuế, hóa đơn và BHXH từ nguồn chính thức; phân biệt văn bản mới với danh mục đã biết, tạo đề xuất có ngày hiệu lực/kỳ áp dụng cần duyệt; không tự đổi công thức hoặc biểu mẫu."
---

# Theo dõi văn bản pháp luật kế toán

## Phạm vi hiện có

- Nguồn tự động ban đầu là trang hệ thống văn bản của Cổng Thông tin điện tử Chính phủ: https://vanban.chinhphu.vn/he-thong-van-ban?classid=0&maxresults=50&mode=1 .
- Registry ghi lại số hiệu đã biết và metadata nguồn để tránh lặp đề xuất. Registry này không chứa công thức kế toán/thuế và không được sửa tự động.
- TT99/2025/TT-BTC và TT89/2026/TT-BTC được ghi nhận làm dữ liệu nền. Với TT89, phạm vi kỳ áp dụng cho từng tờ khai còn phải được xác minh; không suy luận từ ngày hiệu lực.
- Theo dõi thêm nguồn Bộ Tài chính, CSDL quốc gia về VBPL, cơ quan thuế và BHXH cần được tích hợp riêng sau khi xác minh được trang/API ổn định.

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

1. Xác nhận nguồn thuộc `vanban.chinhphu.vn` qua HTTPS; nếu không đọc được trang hoặc metadata thì báo lỗi/CHƯA XÁC MINH.
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
