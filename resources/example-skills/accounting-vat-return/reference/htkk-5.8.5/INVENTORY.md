# HTKK 5.8.5 — kiểm kê metadata mẫu tĩnh

Ngày kiểm kê: 2026-11-23. Nguồn: thư mục cục bộ `C:\Users\ADMIN\Downloads\GITHUB\HTKK_SAMPLES_5.8.5`, bản sao các thư mục mẫu tĩnh của HTKK 5.8.5. Báo cáo chỉ ghi đường dẫn, định dạng, SHA-256, tên phần tử gốc/namespace và metadata cấu trúc; không ghi giá trị thuế, tên/mã số thuế, địa chỉ hay nội dung cá nhân.

## Tổng quan

| Định dạng | Số tệp |
| --- | ---: |
| XML | 2.312 |
| XLS | 1.100 |
| XSD | 669 |
| XLSX | 10 |
| JSON | 2 |
| DOC | 1 |
| RAR | 1 |
| DTD | 1 |
| MD | 1 |
| **Tổng** | **4.097** |

Đã thử parse cả 2.312 XML bằng XML parser với external resolver tắt: **0 lỗi parse**. Phân loại theo root/path: 406 XML tờ khai HTKK có root `HSoThueDTu`; 1.904 XML trao đổi/layout có root `Sections` hoặc các root phụ lục; 1 XML kiểm tra biểu mẫu có root `Workbook`; 1 XML khác. Không có tài liệu nào trong 2.312 XML có root/namespace UBL `Invoice` hoặc `CreditNote`; đây là kho mẫu HTKK, không phải bộ XML hóa đơn.

SHA-256 phát hiện 419 nhóm trùng trong các XML (1.248 file thuộc các nhóm đó; 829 bản dư sau khi tính một bản mỗi nhóm). Trên toàn bộ 4.097 tệp có 530 nhóm hash trùng (1.505 file thuộc nhóm; 975 bản dư). Trùng hash là trùng byte, không kết luận tương đương nghiệp vụ.

## Nhóm mẫu ưu tiên

- **01/GTGT:** 27 tên XML có mã này. Gồm 11 XML tờ khai `HSoThueDTu`, 15 layout `Sections`, và 1 XML phụ lục khai bổ sung `PL01_KHBS`. Trong 11 tờ khai có 4 tệp tên `01_GTGT_TT80_xml_{251,268,274,283}.xml` (TT80 theo tên file), 1 tệp `01_GTGT_TT89_xml_309.xml` (TT89 theo tên file), cùng 6 mẫu lịch sử `01_GTGT_xml_{201,212,240,250,251,262}.xml` không gắn số hiệu thông tư trong tên. Các tên suffix không đủ để tự suy ra kỳ áp dụng; các bản cùng hash được nhận diện là bản trùng nội dung.
- **05/KK-TNCN:** 11 XML có tên mẫu, gồm 5 tờ khai `HSoThueDTu`, 5 layout `Sections`, và 1 tài liệu Validate có root `Workbook`. Đây là XML tờ khai/lưu đồ HTKK, không phải XML hóa đơn.
- **TNDN:** 547 XML có “TNDN” trong tên, bao gồm nhiều phụ lục/layout; 44 trong số đó có root `HSoThueDTu`. Cần phân loại từng mã chính/phụ lục và số hiệu văn bản trước khi xây adapter.
- **BCTC:** 134 XML có tên gợi ý BCTC/lưu chuyển tiền tệ/kết quả kinh doanh; nhóm này có thể gồm báo cáo con/phụ lục, không được coi là 134 mẫu báo cáo tài chính chính. Các file định dạng XLS/XSD liên quan vẫn cần ghép theo mã mẫu.

Không tự đưa các nhóm TNCN/TNDN/BCTC vào exporter GTGT. Chúng là hàng đợi phân tích, chưa có mapping/schema adapter được xác minh.

## Mẫu 01/GTGT đã phân tích toàn cấu trúc

Tham chiếu: `InterfaceTemplates/xml/01_GTGT_TT89_xml_309.xml`, SHA-256 `6617D38E8391AD72EDA2874B62E518E812AFC6FD7A2F3B8779D2E41B1AB1E4DD`, kích thước 3.021 byte. Đây là mẫu XML trắng trong bộ HTKK 5.8.5, không phải hồ sơ của doanh nghiệp.

- XML 1.0, encoding UTF-8; root `HSoThueDTu`; không khai báo namespace/prefix trong instance; 139 phần tử; một thuộc tính `id` trên `HSoKhaiThue`. Các lá trong mẫu trắng không chứa giá trị dữ liệu. Mã phiên bản pháp lý TT89 và code 309 nhận diện từ tên mẫu/đường dẫn bộ HTKK, không phải kỳ thuế bên trong XML trắng.
- Nhánh chính: `HSoKhaiThue/TTinChung/TTinDVu`, `TTinTKhaiThue/TKhaiThue`, `KyKKhaiThue`, `NNT`, `DLyThue`, rồi `CTieuTKhaiChinh`. Mẫu chứa metadata phần mềm/dịch vụ, mã/tên tờ khai, loại/số lần, kỳ, cơ quan thuế, ngày lập/ký; NNT và đại lý thuế; mã/tên đơn vị, trường địa chỉ cấp xã/tỉnh; các nhóm chỉ tiêu GTGT; phần tử `PLuc` nhưng không có payload phụ lục trong mẫu này.
- Namespace instance rỗng. XSD tham chiếu: `InterfaceTemplates/Validate/01_GTGT_TT89_309.xsd` cùng `InterfaceTemplates/TKhaiThue_DBHC.xsd`. README của bộ tham chiếu ghi nhận mẫu nguồn validate với XSD đi kèm **PASS**. Điều đó xác thực mẫu nguồn, không tự xác thực mọi XML do exporter tạo.
- Trường kỳ: `kieuKy` nhận `M` hoặc `Q`; `kyKKhai` có dạng `MM/YYYY` hoặc `Qn/YYYY`; tháng dùng `kyKKhaiTuThang`/`kyKKhaiDenThang` dạng `MM/YYYY`; quý dùng `kyKKhaiTuNgay`/`kyKKhaiDenNgay` dạng `DD/MM/YYYY`. Mẫu trắng không xác định năm/kỳ khai.
- MST là text ở `NNT/mst`, phải bảo toàn số 0 đầu. Tên/địa chỉ NNT, cơ quan thuế, đại lý thuế, thông tin người ký, ngày lập/ký và các trường bổ sung không có trong đầu vào hiện tại thì giữ trống; không tự tạo.
- Chỉ tiêu chính thấy trong XML: `ct21`–`ct43`, theo nhóm không phát sinh, mua vào/nhập khẩu, bán ra theo phân loại biểu mẫu, tổng doanh thu/thuế, điều chỉnh, phải nộp/khấu trừ/hoàn. Các trường hậu tố `_Cqt` và `_Ghichu` là trường cơ quan thuế/giải trình; exporter không tự điền.
- XSD khai báo tiền cốt lõi dưới dạng số nguyên (ví dụ `xs:long` hoặc `xs:nonNegativeInteger`), không phải số thập phân. Vì vậy exporter không làm tròn: giá trị có phần lẻ bị từ chối trước khi ghi file; giá trị nguyên dạng `100.00` được chuẩn hóa thành `100` theo kiểu trường.
- Các quan hệ số học được giữ trong `legal/form_catalog.json`: TT80 [27]=[29]+[30]+[32]+[32a], [28]=[31]+[33], [34]=[26]+[27], [35]=[28], [36]=[35]-[25], [40]=[40a]-[40b], [41]=[36]-[22]+[37]-[38]-[39a], [43]=[41]-[42]. TT89 thêm [32b] vào [27] với dấu trừ và [34a] vào [34]; các quy tắc khác được lưu trong catalog. Không suy chỉ tiêu từ tên hàng/thuế suất.
- Mapping hiện tại từ `form_field_draft`: `form_number=01/GTGT` sang mã/tên tờ khai; `taxpayer_tax_id` sang `NNT/mst`; khoảng `period.start/end/type` sang nhóm `KyKKhaiThue`; từng `amounts[code]` sang phần tử `CTieuTKhaiChinh/**/ct{code}` nếu phần tử tồn tại trong đúng mẫu. Dòng bán ra cần mã chỉ tiêu đã duyệt; mua vào cần cặp [23]/[24] hoặc [23a]/[24a] đã xác nhận. Các trường thiếu không được tự điền.
- Test đối chiếu cấu trúc so sánh cây phần tử/thuộc tính với mẫu TT89, đọc lại XML, kiểm tra MST, kỳ và chỉ tiêu; test quý dùng mẫu TT80. Test dùng số liệu giả lập. Không có thao tác nhập XML trở lại HTKK/eTax trong môi trường này.

## Trạng thái

- Exporter XML 01/GTGT nháp đã có trong PR #2 và tái sử dụng pipeline VAT hiện có; không tạo pipeline VAT thứ hai.
- Mapping GTGT khác nhau theo TT80/TT89; catalog và mẫu giữ phiên bản riêng, không auto-select.
- XSD cho toàn bộ đầu ra và khả năng nhập HTKK/eTax: **chưa xác minh**. Trạng thái nộp hồ sơ: **không sẵn sàng**.
- TNCN/TNDN/BCTC: metadata kiểm kê ở trên, mapping chi tiết/schema/adapter: **chưa triển khai**.
- XML hóa đơn: không có trong kho HTKK này; hỗ trợ XML hóa đơn thuộc profile/phần mềm khác và chưa được xác minh từ các mẫu HTKK.
