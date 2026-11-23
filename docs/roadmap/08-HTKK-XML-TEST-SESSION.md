# Ghi nhận tiếp nối — kiểm tra XML HTKK 01/GTGT

Ngày: 2026-11-23 (Asia/Saigon)  
Repository: `accoutant67/eigent-viet-hoa`  
Nhánh/PR: `codex/vat-return-mvp` / PR #2 (open, draft, chưa merge)

## Điểm xuất phát và mẫu đã kiểm tra

- Không kiểm kê lại gói HTKK. Dùng kết quả trong [INVENTORY.md](../../resources/example-skills/accounting-vat-return/reference/htkk-5.8.5/INVENTORY.md): 4.097 tệp, 2.312 XML; 27 XML có tên 01/GTGT (11 hồ sơ `HSoThueDTu`, 15 layout `Sections`, 1 phụ lục `PL01_KHBS`).
- Đối chiếu trực tiếp hai mẫu hồ sơ trắng trong kho tham chiếu: `01_GTGT_TT80_xml_283.xml` và `01_GTGT_TT89_xml_309.xml`. Cả hai là root `HSoThueDTu`, không namespace. TT80 có cấu trúc địa chỉ [11a]/[11b]/[11c]; TT89 giữ [11a]/[11c], thêm các trường metadata CQT/ghi chú và [32b]/[34a].
- Phân biệt `01_GTGT_TT89_309.xml` (root `Sections`, giao diện HTKK) với `01_GTGT_TT89_xml_309.xml` (XML hồ sơ). File layout không phải XML xuất.
- Mã bộ xuất hiện trỏ TT80 và TT89 lần lượt đến hai tệp XML hồ sơ trắng ở trên. Catalog giữ riêng công thức: TT80 [27]=[29]+[30]+[32]+[32a]; TT89 trừ thêm [32b]; TT89 [34] cộng [34a]. Việc chọn mẫu vẫn tường minh, không tự chọn theo kỳ.

## Thay đổi trong phiên này

- Commit `b81d23e13481098022c736de22b4cf3eae83a25d`: exporter từ chối khi đường dẫn đích resolve trùng với XML tham chiếu được chọn, trước khi tạo thư mục/tệp tạm. Đây là bảo vệ tệp mẫu khỏi bị thay thế.
- Commit `8d1d7826ed7e59b438ff024f8ab9108e87642efa`: thêm `test_htkk_xml_source_protection.py`, dùng MST và kỳ giả lập; kiểm tra ngoại lệ và byte của mẫu không đổi.
- Không sửa XML tham chiếu hoặc dữ liệu hóa đơn. Không thực hiện ký số, gửi hay nộp tờ khai.

## CI và giới hạn xác minh

Trên commit `8d1d7826ed7e59b438ff024f8ab9108e87642efa`:

- Accounting VAT return draft: **SUCCESS** (run [45100160843](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45100160843)).
- Accounting law watch: **SUCCESS** (run [45100160858](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45100160858)).
- Test tổng thể: **IN_PROGRESS** (run [45100160791](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45100160791)); chưa kết luận PASS.
- CI cũ trên `b00260b`: VAT và law-watch SUCCESS; Test còn IN_PROGRESS tại lần xác minh này (run [45099439419](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/45099439419)). Không gán kết quả cũ cho mã mới.
- Máy làm việc hiện tại không có Git/checkout repository, nên chưa chạy được lệnh unit/CLI cục bộ. Actions VAT PASS là bằng chứng workflow, nhưng số test cụ thể và regression mới cần đọc log job; chưa xác nhận riêng test mới bằng log.
- Đã kiểm thử theo cấu trúc mẫu HTKK — chưa xác minh khả năng nhập lại vào HTKK. Chưa xác minh cơ quan thuế tiếp nhận. Không có GUI HTKK được kiểm chứng trong phiên này.

## Ma trận tính năng hiện tại

| Phạm vi | Trạng thái |
| --- | --- |
| XML tháng/quý trong exporter hiện có | Có logic; test và mapping theo commit hiện hành cần đối chiếu log/fixture trước khi xác nhận đầy đủ. |
| TT80 và TT89 | Hai mẫu được chọn tách phiên bản; chỉ mẫu trắng đã kiểm kê nêu trên làm tham chiếu. |
| Parse/đọc lại và so cây XML | Đã có test trong bộ VAT trước phiên này; chưa xác nhận XSD trên XML đầu ra trong phiên này. |
| Mapping chỉ tiêu | Chỉ tiêu/quan hệ đã được xác minh trong catalog; chưa có ma trận bao phủ đầy đủ từng mã, nguồn dữ liệu, công thức và test. |
| Dữ liệu hóa đơn đến XML | Chưa có bằng chứng trong phiên này cho một lượt chạy E2E trên fixture từ nhập hóa đơn qua tổng hợp tới XML. |
| Nhập lại HTKK | Chưa xác minh; cần chạy thử file giả lập trong HTKK trên máy người dùng, không nộp hồ sơ. |
| TNCN/TNDN/BCTC/BHXH | Chỉ có metadata kiểm kê trước đó; adapter/mapping riêng chưa triển khai. |

Không coi XML parse được, đạt XSD, khớp cấu trúc mẫu, nhập được vào HTKK và được cơ quan thuế tiếp nhận là cùng một trạng thái.
