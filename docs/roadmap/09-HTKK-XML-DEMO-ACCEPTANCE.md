# Kiểm thử nhập XML 01/GTGT vào HTKK trên Windows

## File cần tải

Tải artifact `htkk-01-gtgt-xml-demo-<commit>` từ workflow Accounting VAT return draft trên commit của PR #2, rồi giải nén. Artifact có hai XML và `report.json`.

- XML tháng: TT89, kỳ 07/2026.
- XML quý: TT89, kỳ Q3/2026.
- Bộ mẫu tham chiếu: HTKK 5.8.5.

## Dữ liệu thử nghiệm

Hóa đơn, số tiền và mã đối tác đều giả lập. MST `0000000000` là chuỗi thử nghiệm đúng hình dạng 10 chữ số để kiểm tra giữ số 0 đầu; đây không phải MST đã đăng ký hoặc được xác minh với cơ quan thuế. HTKK có thể từ chối vì MST không tồn tại. Không có tên doanh nghiệp, địa chỉ, cơ quan thuế hoặc người ký thật. XML không có chữ ký và không sẵn sàng nộp.

## Các bước kiểm tra

1. Mở HTKK 5.8.5 trong môi trường thử nghiệm.
2. Chọn tờ khai 01/GTGT và đúng kỳ hiển thị trong tên file.
3. Dùng chức năng nhập XML của HTKK để chọn một file demo.
4. Đối chiếu mã tờ khai, kỳ và các chỉ tiêu có giá trị với `report.json`.
5. Dừng trước khi ký số, kết xuất hồ sơ chính thức hoặc nộp.

Nếu HTKK báo MST không tồn tại, đó là giới hạn của MST giả lập; riêng lỗi đó không kết luận cấu trúc XML sai. Ghi phiên bản HTKK, tên file, thông báo lỗi đầy đủ và ảnh màn hình đã che thông tin ngoài fixture. Không thay bằng dữ liệu doanh nghiệp thật.

## Trạng thái nghiệm thu

- Tạo XML qua CLI/exporter VAT hiện có: được kiểm tra trong workflow.
- Parse, kỳ, kiểu số, chỉ tiêu, công thức và cây phần tử so mẫu: kết quả trong `report.json`.
- XSD: BLOCKED do namespace của instance và schema không khớp.
- Nhập lại HTKK Windows: chưa kiểm thử.
- Cơ quan thuế tiếp nhận: ngoài phạm vi.
