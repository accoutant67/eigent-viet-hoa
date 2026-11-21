# Tiến độ dự án

**Cập nhật:** 21/11/2026

**PR #1:** `codex/accounting-workbook-audit-mvp`

**Nhánh GTGT:** `codex/vat-return-mvp`

| Giai đoạn | Nội dung                         | Trạng thái hiện tại                                                                                                                                                                                                             |
| --------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1         | Kiểm kê và hoàn thiện Việt hóa   | Bản dịch còn một phần; kiểm tra tĩnh có bằng chứng, chưa nghiệm thu độ phủ hoặc GUI.                                                                                                                                            |
| 2         | Không gian kế toán và điều hướng | Chưa triển khai giao diện Kế toán; kiểm thử GUI BLOCKED.                                                                                                                                                                        |
| 3         | Agents kế toán                   | Chưa đăng ký 72 Agents rỗng. Các mã vai trò trong Skill GTGT không phải Agent đã tạo.                                                                                                                                           |
| 4         | Skills và xử lý dữ liệu          | Excel audit 7/7; law-watch 15/15; VAT draft 11/11; integration Eigent 1/1; CLI/fixture smoke PASS. Nguồn luật 9/12 PASS, 3 BLOCKED. Full backend cục bộ BLOCKED do exit 137; CI trên commit trước đạt 4.595 passed, 11 skipped. |
| 5         | Kiểm thử đầu-cuối và build       | HTTP web/backend, ChatBox rollback 1.113/1.113, i18n và type-check PASS. Electron preview/relay PASS trên CI trước; GUI thật BLOCKED ở máy cục bộ. Workflow đang chạy lại cho commit `43fde11`.                                 |

## Công việc đang tiếp tục

PR #1 vẫn mở dạng draft, chưa merge. PR #2 là nhánh draft kế tiếp trên `codex/vat-return-mvp`, hiện ở commit `43fde1135808984e69ac2c56414f620b884b617f`; Test, VAT và law-watch Actions đang chạy lại trên thay đổi mở rộng nguồn. Lượt Actions trước đó trên commit `aee2a26` đạt: backend 4.595 passed/11 skipped, ChatBox 1.113/1.113, web/backend smoke, i18n, type-check và Electron preview/relay. Retest cục bộ mới nhất: law-watch 15/15, VAT 11/11, Excel 7/7, Eigent integration 1/1. Toàn bộ backend cục bộ vẫn BLOCKED vì exit 137; không báo PASS từ lượt đó. Báo cáo chi tiết, kể cả lỗi ChatBox đã có trên `main` trước PR, nằm trong [báo cáo kiểm thử](./06-KIEM-THU.md).

Nhánh GTGT tách khỏi PR #1. Skill `accounting-vat-return` hiện đọc `.xlsx`/`.csv`, phân loại theo MST, soát hóa đơn và kỳ, tổng hợp theo nhãn nguồn, đối chiếu độc lập và xuất JSON nội bộ. Chưa điền chỉ tiêu vào mẫu pháp định, chưa xuất XLSX/XML và chưa nộp tờ khai.

Đã xác minh mẫu 01/GTGT trong Phụ lục II TT80 và bản ký số Phụ lục I TT89 (trang PDF 241). Đã rà TT40/2025, TT94/2025, TT21/2026, đính chính 2551/QĐ-BTC và ghi nhận Luật GTGT 48/2024/QH15, NĐ181/2025/NĐ-CP, TT69/2025/TT-BTC trong registry. Cổng Chính phủ ghi TT89 có hiệu lực 01/07/2026; cần hoàn tất đối chiếu điều khoản chuyển tiếp và trường hợp người nộp thuế trước khi chọn mẫu theo kỳ. Cơ sở dữ liệu văn bản Bộ Tài chính hiện truy cập trực tiếp bị BLOCKED (HTTPError/503). Ánh xạ xuất tệp chưa được duyệt; chương trình không tự chọn mẫu.

## Danh mục bot và Skill theo nguồn người dùng

Hai tệp nguồn có chênh số lượng: `DANH_MUC_BOT.md` ghi 72 bot, còn tài liệu 15 Skill ghi 66 vai trò bot. Giữ nguyên cả hai con số cho đến khi đối chiếu được danh tính/ID; không tự tạo 72 Agents rỗng hoặc coi prompt là chức năng đã triển khai.

Roadmap giữ đủ 15 nhóm Skill gốc:

| Skill                 | Trọng tâm                                                      | Trạng thái                                                          |
| --------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------- |
| `/cap-nhat-phap-luat` | Nguồn chính thức, ngày hiệu lực, thay đổi và đề xuất           | Đang mở rộng trên law-watch hiện có                                 |
| `/hoa-don`            | Nhập hóa đơn, mua vào/bán ra, kiểm tra điều chỉnh/thay thế     | Một phần nhập `.xlsx`/`.csv` cho GTGT; XML/PDF/ảnh NOT STARTED      |
| `/lam-to-khai`        | GTGT, TNCN định kỳ, nghĩa vụ khác, khai bổ sung, kiểm tra/xuất | GTGT đang làm; phần còn lại NOT STARTED                             |
| `/bieu-mau`           | Phân tích mẫu, bản trắng, ánh xạ và xuất bản sao               | Nhận diện nguồn mẫu GTGT; điền/xuất pháp định NOT STARTED           |
| `/kiem-tra`           | Soát chứng từ, sổ sách, thuế và BCTC độc lập                   | Chỉ có so tổng độc lập trong VAT slice; phạm vi còn lại NOT STARTED |
| `/quyet-toan`         | TNCN/TNDN và dữ liệu năm                                       | NOT STARTED; sẽ tiếp tục sau GTGT                                   |
| `/hach-toan`          | Định khoản, ghi sổ, điều chỉnh/khóa sổ                         | NOT STARTED                                                         |
| `/tao-ma`             | Mã hàng, đối tượng, chứng từ                                   | NOT STARTED                                                         |
| `/nhap-xuat-ton`      | Kho, giá vốn, giá thành                                        | NOT STARTED                                                         |
| `/ngan-hang-cong-no`  | Ngân hàng, tiền và công nợ                                     | NOT STARTED                                                         |
| `/tien-luong`         | Chấm công, tính lương, thuế/bảo hiểm lương                     | NOT STARTED                                                         |
| `/bao-hiem-xa-hoi`    | Hồ sơ BHXH và chế độ                                           | NOT STARTED                                                         |
| `/tai-san`            | TSCĐ, CCDC, khấu hao và phân bổ                                | NOT STARTED                                                         |
| `/bao-cao-tai-chinh`  | Sổ cái và bộ BCTC                                              | NOT STARTED; sau TNDN theo lộ trình                                 |
| `/ke-toan-truong`     | Chọn Skill, điều phối, tổng hợp và trình duyệt                 | Chưa có Agent điều phối; KTT03 là vai trò quy trình trong VAT slice |

Các nhóm người dùng bổ sung như hồ sơ nhân sự, hợp đồng/quyết định, đối chiếu MST, bảng kê/phiếu chi, công văn, hồ sơ doanh nghiệp, phân ca, quản lý hồ sơ và vận hành MausBot được giữ trong lộ trình mở rộng; chưa đánh dấu đã tích hợp.

## Lộ trình kế tiếp

1. Hoàn tất test và CI của nhánh GTGT; cập nhật bằng chứng và mở PR riêng dạng draft, xếp sau PR #1.
1. Hoàn tất đối chiếu điều khoản chuyển tiếp; thiết kế bản dự thảo có ánh xạ trường được người có chuyên môn duyệt. Chưa tạo XML cho tới khi schema chính thức được xác minh.
1. Mở rộng nhập hóa đơn theo định dạng và trạng thái được kiểm chứng, rồi thêm quy trình TNCN quý → TNDN tạm nộp/quyết toán năm → bộ BCTC.
1. Chuyển từng vai trò còn lại thành chức năng Eigent có công cụ, phân quyền, đầu vào/đầu ra và test; kiểm soát trùng vai trò trước khi đăng ký Agent.
1. Mở GUI Eigent/Chat AI/đổi ngôn ngữ để nghiệm thu khi có môi trường GUI và cấu hình model hợp lệ; giữ BLOCKED cho tới lúc đó.

Không gộp các trạng thái đã viết mã, test cục bộ, CI đạt, đã chạy ứng dụng và đã nghiệm thu nghiệp vụ thành một kết luận.
