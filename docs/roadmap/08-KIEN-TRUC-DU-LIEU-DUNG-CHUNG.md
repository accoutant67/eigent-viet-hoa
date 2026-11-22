# Kiến trúc dữ liệu và biểu mẫu dùng chung

**Phạm vi:** bổ sung tăng dần trên PR #2; không thay hoặc viết lại kiến trúc Eigent.  
**Trạng thái rà soát:** 22/11/2026.

## Kết luận rà soát

| Yêu cầu nền tảng | Trạng thái hiện tại |
| --- | --- |
| Mô hình dữ liệu dùng chung, truy vết nguồn | Trước thay đổi, VAT dùng dict nội bộ và trace; chưa có schema chung. Bổ sung hợp đồng hóa đơn phiên bản 1.0.0 và chiếu record VAT sang hợp đồng này. Các loại record sổ kế toán, bảng lương, hồ sơ nhân sự và doanh nghiệp chưa được triển khai. |
| Pháp luật/biểu mẫu theo phiên bản và hiệu lực | Catalog GTGT đã tách TT80/TT89, giữ nguồn và công thức; CLI bắt chọn version, dùng law-watch và tắt tự chọn. Chưa có registry chung thể hiện đầy đủ đối tượng áp dụng/kỳ chuyển tiếp cho các nhóm nghiệp vụ. |
| Ánh xạ/điền mẫu dùng chung, quy tắc riêng | Chưa có bộ ánh xạ mẫu dùng chung. Quy tắc VAT và ánh xạ 01/GTGT đang thuộc Skill VAT; chưa có adapter riêng cho BHXH/BCTC. |
| Định dạng xuất chính thức | Có JSON và XLSX soát xét nội bộ. Chưa có workbook/PDF pháp định hoặc XML tờ khai theo schema chính thức đã xác minh. |
| Kiểm tra độc lập/đọc lại | VAT có lượt tổng hợp độc lập và test đọc lại XLSX nội bộ; không chứng minh chấp nhận của HTKK/eTax. XML hóa đơn parse được cũng không xác minh chữ ký số hay tính hợp lệ của hóa đơn trên hệ thống thuế. |
| Tái sử dụng | Hợp đồng schema dưới đây tạo điểm nối chung; parser XML vẫn là profile UBL riêng và không thay Excel/CSV importer. |

## Bổ sung trong bước hiện tại

`resources/accounting-data-model/v1/invoice-record.schema.json` định nghĩa record hóa đơn đã chuẩn hóa và các cấu phần có thể tái sử dụng: bên giao dịch, tổ chức, cá nhân, tiền dạng chuỗi thập phân, khoảng hiệu lực, tham chiếu chứng từ và truy vết nguồn.

Skill VAT tiếp tục giữ phép tính, kết luận kiểm tra và ánh xạ theo quy định thuế. Nó chỉ phát ra `normalized_document` theo schema chung; lớp định dạng/biểu mẫu cho từng nghiệp vụ vẫn tách biệt. Các trường chưa trích xuất như dòng hàng và liên kết hóa đơn gốc được đánh dấu `not_extracted`, không tạo tham chiếu rỗng hoặc suy diễn.

## Giới hạn còn lại và thứ tự

1. Mở rộng parser hóa đơn Việt Nam theo từng profile có mẫu/tài liệu chính thức; UBL hiện tại không đại diện cho mọi XML hóa đơn tại Việt Nam.
2. Bổ sung kiểm tra quan hệ điều chỉnh/thay thế và dòng hàng khi profile có trường tương ứng; giữ file nguồn/hash.
3. Hoàn thiện registry version hóa quy định và biểu mẫu với cơ quan ban hành, nguồn, ngày hiệu lực, kỳ, đối tượng, điều khoản chuyển tiếp và quy tắc bị tác động; không tự áp dụng.
4. Phát triển adapter ánh xạ/điền mẫu chung, sau đó giữ riêng adapter xuất và logic nghiệp vụ Thuế, BHXH, BCTC.
5. Tiếp tục roadmap sau GTGT: TNCN → TNDN → BCTC → BHXH; chạy regression khi mỗi slice được thêm.

Bản ghi thử nghiệm chỉ dùng fixture tổng hợp. Không có dữ liệu doanh nghiệp thật trong repository.
