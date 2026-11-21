# Tiến độ dự án

**Cập nhật:** 21/11/2026

**PR #1:** `codex/accounting-workbook-audit-mvp`

**Nhánh GTGT:** `codex/vat-official-form-draft` (stacked sau PR #3 `codex/vat-form-mapping-draft`)

| Giai đoạn | Nội dung                         | Trạng thái hiện tại                                                                                                                                                                                                            |
| --------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1         | Kiểm kê và hoàn thiện Việt hóa   | Bản dịch còn một phần; kiểm tra tĩnh có bằng chứng, chưa nghiệm thu độ phủ hoặc GUI.                                                                                                                                           |
| 2         | Không gian kế toán và điều hướng | Chưa triển khai giao diện Kế toán; kiểm thử GUI BLOCKED.                                                                                                                                                                       |
| 3         | Agents kế toán                   | Chưa đăng ký 72 Agents rỗng. Các mã vai trò trong Skill GTGT không phải Agent đã tạo.                                                                                                                                          |
| 4         | Skills và xử lý dữ liệu          | Excel audit 8/8; VAT suite 39/39 gồm xuất PDF; Skill integration 1/1; JSON/XLSX nội bộ/PDF dự thảo PASS. Law-watch regression 13/13 cục bộ; nguồn live gần nhất 10/11 PASS, 1 BLOCKED (MOF guide). |
| 5         | Kiểm thử đầu-cuối và build       | Web/backend smoke, ChatBox rollback 1.113/1.113, i18n/type-check, Electron preview/relay PASS trên CI final head `ea6ec66`; GUI Eigent thật vẫn BLOCKED.                                                                       |

## Công việc đang tiếp tục

PR #1 vẫn mở/draft, chưa merge; head `215805fce6c7ed1c48305a6661a48eb9762212eb`, các workflow Test, workbook audit, law-watch, CodeQL, pre-commit và markdown lint đều PASS. PR #2 vẫn mở/draft trên `codex/vat-return-mvp`, head `749c8b1772d61821f69a9823adca3d505fe4e1c2`; VAT, Test và law-watch đều PASS. Không PR nào được merge.

PR #3 [`fix: verify TT94 impact on 01/GTGT applicability`](https://github.com/accoutant67/eigent-viet-hoa/pull/3) là draft, xếp sau PR #2, head `17de3db204418a77af34d72fe1940a2347886fd7`. Test `44895003035`, VAT `44895003041` và law-watch `44895003017` đều PASS. PR #4 tiếp tục trên nhánh riêng sau PR #3 để giữ phạm vi PR #1 gọn.

Nhánh GTGT tách khỏi PR #1. Skill `accounting-vat-return` đọc `.xlsx`/`.csv`, phân loại theo MST, soát hóa đơn/kỳ, tổng hợp và đối chiếu độc lập; xuất JSON/XLSX nội bộ hoặc PDF dự thảo chồng trên đúng mẫu 01/GTGT. PDF lấy tên/MST từ đầu vào tường minh, chỉ điền số tiền đã có, giữ ô thiếu trống, cập nhật nhãn và ghi chú TT40 từ kỳ 07/2025, đồng thời đóng dấu “DỰ THẢO — CHƯA KÝ — CHƯA NỘP”. Workbook pháp định, XML, ký/nộp và khai bổ sung chưa triển khai.

Đã đối chiếu 01/GTGT TT80 (Phụ lục II) và TT89 (Phụ lục I, bản ký số trang PDF 241–243); TT40/2025, toàn văn TT94/2025, TT21/2026, 2551/QĐ-BTC, TT110/2026 cùng Luật GTGT 48/2024/QH15, NĐ181/2025/NĐ-CP, TT69/2025/TT-BTC. TT89 hiệu lực 01/07/2026; hồ sơ có kỳ trước ngày này dùng mẫu trước đó theo điều khoản chuyển tiếp. Toàn văn TT94 không cho thấy thay trường/công thức 01/GTGT; TT80 mapping Q4/2025 không còn bị chặn riêng bởi TT94. Hệ thống không tự chọn mẫu; một nguồn hướng dẫn CSDL của Bộ Tài chính hiện BLOCKED (HTTPError).

## Danh mục bot và Skill theo nguồn người dùng

Hai tệp nguồn có chênh số lượng: `DANH_MUC_BOT.md` ghi 72 bot, còn tài liệu 15 Skill ghi 66 vai trò bot. Giữ nguyên cả hai con số cho đến khi đối chiếu được danh tính/ID; không tự tạo 72 Agents rỗng hoặc coi prompt là chức năng đã triển khai.

Roadmap giữ đủ 15 nhóm Skill gốc:

| Skill                 | Trọng tâm                                                      | Trạng thái                                                          |
| --------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------- |
| `/cap-nhat-phap-luat` | Nguồn chính thức, ngày hiệu lực, thay đổi và đề xuất           | Đang mở rộng trên law-watch hiện có                                 |
| `/hoa-don`            | Nhập hóa đơn, mua vào/bán ra, kiểm tra điều chỉnh/thay thế     | Một phần nhập `.xlsx`/`.csv` cho GTGT; XML/PDF/ảnh NOT STARTED      |
| `/lam-to-khai`        | GTGT, TNCN định kỳ, nghĩa vụ khác, khai bổ sung, kiểm tra/xuất | GTGT đang làm; phần còn lại NOT STARTED                             |
| `/bieu-mau`           | Phân tích mẫu, bản trắng, ánh xạ và xuất bản sao               | Nhận diện mẫu 01/GTGT; có PDF dự thảo có watermark; XLSX pháp định/XML NOT STARTED |
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

1. Xác nhận GitHub Actions cho PR #4 về PDF dự thảo 01/GTGT; xử lý lỗi CI nếu có. Giữ PR #4 dạng draft và xếp sau PR #3.
1. Hoàn tất đối chiếu điều khoản chuyển tiếp; thiết kế bản dự thảo có ánh xạ trường được người có chuyên môn duyệt. Chưa tạo XML cho tới khi schema chính thức được xác minh.
1. Mở rộng nhập hóa đơn theo định dạng và trạng thái được kiểm chứng, rồi thêm quy trình TNCN quý → TNDN tạm nộp/quyết toán năm → bộ BCTC.
1. Chuyển từng vai trò còn lại thành chức năng Eigent có công cụ, phân quyền, đầu vào/đầu ra và test; kiểm soát trùng vai trò trước khi đăng ký Agent.
1. Mở GUI Eigent/Chat AI/đổi ngôn ngữ để nghiệm thu khi có môi trường GUI và cấu hình model hợp lệ; giữ BLOCKED cho tới lúc đó.

Không gộp các trạng thái đã viết mã, test cục bộ, CI đạt, đã chạy ứng dụng và đã nghiệm thu nghiệp vụ thành một kết luận.
