# MASTER PROMPT V3.0 — EIGENT KẾ TOÁN VIỆT NAM

> Dùng để giao nhiệm vụ cho Codex / AI coding agent có quyền truy cập repository. **Đây là đặc tả phát triển**, không phải bằng chứng rằng các tính năng đã được xây dựng hoặc kiểm thử.

## 0. Repository và nhiệm vụ

- **Repository cần phát triển:** https://github.com/accoutant67/eigent-viet-hoa
- **Nền tảng gốc:** https://github.com/eigent-ai/eigent
- **Tên sản phẩm:** Eigent Kế Toán Việt Nam
- **Ngôn ngữ mặc định mong muốn:** Tiếng Việt
- **Hướng phát triển:** Tiếp tục bộ Việt hóa Eigent đang có, rồi mở rộng thành nền tảng AI đa tác nhân phục vụ kế toán Việt Nam.

Bạn là nhóm kỹ thuật gồm Full-stack Engineer, Electron Engineer, Python Engineer, AI Multi-Agent Architect, QA Engineer và chuyên gia quy trình kế toán Việt Nam.

**Yêu cầu tối quan trọng: HÃY THỰC SỰ LÀM VIỆC VỚI REPOSITORY.** Không dừng ở kế hoạch. Đọc mã nguồn thực tế, xác định khả năng đang có, triển khai mã nguồn thành từng thay đổi nhỏ, chạy kiểm thử, rồi cập nhật GitHub. Không bịa kết quả chạy thử.

## 1. Giới hạn bắt buộc

- **Không làm MISA SME, Smart Pro, SQL Server hay kết nối phần mềm kế toán bên thứ ba trong giai đoạn này.**
- Không sửa hoặc sao chép sang repository MausBot; chỉ sửa `accoutant67/eigent-viet-hoa`.
- Không tạo repository mới, không reset hoặc force-push `main`, không viết lại Eigent từ đầu.
- Không sửa/xóa chức năng chính của Eigent chỉ để thêm menu kế toán.
- Không dùng chứng từ, CCCD, bảng lương, dữ liệu thuế, mật khẩu, token hay API key thật làm dữ liệu thử nghiệm hoặc đưa lên GitHub.
- Không tự nộp tờ khai, ký số, gửi BHXH hay sửa dữ liệu sản xuất.
- Không coi văn bản pháp luật, thuế suất, mã biểu mẫu là đúng nếu chưa kiểm tra nguồn chính thức, hiệu lực và kỳ áp dụng.
- Mọi dữ liệu kế toán trong fixture phải hoàn toàn giả lập, dễ nhận biết là DEMO.

## 2. Bắt đầu bằng kiểm kê mã nguồn thật

Trên repository đang có:
1. Đọc `README.md`, `package.json`, các thư mục `src/`, `electron/`, `backend/`, `resources/example-skills/`, `test/` và `.github/workflows/` có liên quan.
2. Kiểm tra `src/i18n/locales/vi/`, đăng ký locale, bộ chọn ngôn ngữ, menu Electron, workflow dịch tiếng Việt và các commit gần nhất.
3. Kiểm tra hệ thống tác nhân, Skills, MCP, file upload, quản lý phiên, tính năng Terminal và cách gọi backend.
4. Kiểm tra chức năng Excel, PDF, Word, XML, CSV đã thực sự tồn tại tới mức nào; không lặp lại chức năng tốt.
5. Chạy kiểm tra phù hợp với môi trường trước khi sửa mã nguồn. Ghi chính xác lệnh, môi trường, đầu ra và lỗi.
6. Tạo `docs/roadmap/01-KIEM-KE-DU-AN.md`: từng hạng mục, đường dẫn mã nguồn, đã chạy/chưa chạy, vấn đề, việc cần làm.

**Phải kiểm kê trước nhưng sau đó tiếp tục lập trình trong cùng phiên, không kết thúc chỉ với tài liệu.**

## 3. Hoàn thiện Việt hóa Eigent

Dựa trên bộ `src/i18n/locales/vi/` hiện có:
- Kiểm tra 12 namespace và mọi khóa so với `en-us`; không giả định workflow dịch thành công nghĩa là nội dung đã dịch tự nhiên hoặc đủ 100%.
- Rà soát các chuỗi hiển thị trực tiếp chưa dùng i18n ở frontend và menu Electron.
- Việt hóa toàn bộ giao diện người dùng do mã nguồn ứng dụng kiểm soát: chào mừng, đăng nhập, trang chủ, Chat, Agents, Skills, Tasks, Automation, MCP, Settings, tài khoản, chọn mô hình, quản lý tệp, hộp thoại, menu ngữ cảnh, tooltip, thông báo lỗi và menu con.
- Sửa câu dịch máy thiếu tự nhiên, sai thuật ngữ hoặc gây hiểu nhầm nghiệp vụ.
- Chuẩn hóa thuật ngữ: Dashboard=Tổng quan; Chat=Trò chuyện; Agents=Tác nhân AI; Skills=Kỹ năng; Tasks=Tác vụ; Automation=Tự động hóa; Settings=Cài đặt; Accounting=Kế toán; Reconciliation=Đối chiếu; Validation=Kiểm tra tính hợp lệ.
- Giữ nguyên mọi khóa JSON, placeholders `{{name}}`, `{appName}`, thẻ rich-text, URI, số kỹ thuật, định danh model, thương hiệu và cấu trúc đa ngôn ngữ.
- Không sửa hành vi chương trình nhằm che lỗi dịch.

Kiểm thử: `npm run check:i18n`, `npm run type-check`, test liên quan, kiểm tra thủ công hoặc UI automation nếu có môi trường. Ghi lỗi tràn chữ, font và hành vi chuyển ngôn ngữ.

**Giới hạn kỹ thuật:** Các nút Code / Issues / Actions / Settings và dòng commit trên *website GitHub* không thuộc giao diện Eigent, không thể dịch từ bộ locale của dự án.

## 4. Không gian làm việc Kế toán Việt Nam

Bổ sung khu vực **Kế toán** trong giao diện Eigent hiện tại. Đừng viết một ứng dụng thứ hai. Giữ các lối vào chức năng Eigent gốc.

Các hạng mục kế toán dự kiến:
1. Tổng quan kế toán
2. Trợ lý AI kế toán
3. Hóa đơn
4. Thuế
5. Tiền lương
6. BHXH
7. Xuất nhập tồn
8. Công nợ
9. Chứng từ
10. Tài sản cố định
11. Báo cáo tài chính
12. Phân tích tài chính
13. Kiểm tra và đối chiếu
14. AI Agents
15. Skills

Yêu cầu UI:
- Tiếng Việt, thống nhất với design system hiện tại; hỗ trợ dark/light nếu bản gốc đã hỗ trợ.
- Route/điều hướng có thể thực sự mở, breadcrumb, tiêu đề, trạng thái loading/empty/error.
- Với tính năng đã làm: nút bấm chạy được và hiển thị kết quả nguồn demo.
- Với tính năng chưa làm: hiển thị “Đang phát triển” minh bạch, không tạo nút giả hoặc dashboard giả.
- Bảng biểu phải giữ tiền âm, số thập phân, mã có số 0 ở đầu; tìm kiếm/lọc/sắp xếp khi phù hợp.
- UI không được phá vỡ Chat, Agents, Skills, MCP, Settings hoặc bất kỳ phần gốc nào.

Triển khai **một vertical slice hoàn chỉnh đầu tiên**: màn hình nhập Excel/CSV demo → kiểm tra dữ liệu → bảng kết quả và lỗi → tải kết quả. Khi có vertical slice PASS mới mở rộng các module khác.

## 5. AI Agents chuyên về kế toán

Tái sử dụng engine đa tác nhân của Eigent, không giả vờ đã tích hợp bằng cách chỉ viết prompt hệ thống. Các tác nhân mục tiêu:
- Kế toán tổng hợp
- Thuế
- Tiền lương
- BHXH
- Hóa đơn
- Kho
- Công nợ
- Tài sản cố định
- Báo cáo tài chính
- Kiểm soát dữ liệu

Mỗi agent phải mô tả: vai trò, dữ liệu cần thiết, giới hạn thao tác, tool/skill được phép gọi, hình thức đầu ra, logic kiểm tra và tình huống cần chuyển người duyệt.

Ưu tiên quy trình **đọc nguồn → chuẩn hóa dữ liệu → tính toán xác định bằng code → kiểm tra độc lập → xuất tệp → báo sai lệch**, không dùng LLM làm phép tính tiền cuối cùng khi có thể dùng code deterministic.

Xác minh agent thực sự được tải, hiện trong UI hoặc cấu hình thích hợp và gọi được tool. Không tuyên bố tích hợp nếu chỉ có mô tả.

## 6. Skills kế toán (15 nhóm)

Tạo theo cơ chế `resources/example-skills/<slug>/SKILL.md` hoặc cơ chế được repo thực tế xác nhận; giữ nguyên Skills gốc:

1. `ke-toan-thue`: chuẩn bị dữ liệu thuế, kiểm tra chỉ tiêu
2. `bao-hiem-xa-hoi`: kiểm tra hồ sơ BHXH từ mẫu đã xác minh
3. `tien-luong`: chấm công, lương, thu nhập chịu thuế
4. `hoa-don`: đọc, trích xuất, đối chiếu hóa đơn
5. `bao-cao-tai-chinh`: tổng hợp và kiểm tra báo cáo
6. `dinh-khoan`: xác định nghiệp vụ và gợi ý hạch toán theo chế độ được cấu hình
7. `xuat-nhap-ton`: tính số lượng, giá và tồn
8. `cong-no`: phải thu, phải trả và kỳ thu/trả
9. `tai-san-co-dinh`: nguyên giá, khấu hao và giảm tài sản
10. `tien-ngan-hang`: đối chiếu quỹ và giao dịch
11. `ho-so-lao-dong`: kiểm tra mẫu hợp đồng/quyết định
12. `doi-chieu-mst`: chỉ đối chiếu dữ liệu được cấp phép
13. `chung-tu-bang-ke`: phiếu thu, phiếu chi, bảng kê
14. `kiem-tra-du-lieu`: phát hiện thiếu/trùng/lệch
15. `tu-dong-hoa-ke-toan`: điều phối các bước được phê duyệt

Mỗi Skill cần metadata hợp lệ, quy trình rõ, input/output, mức độ tin cậy, điều kiện cần xác minh, ví dụ demo, script/tool nếu cần và test. Phải xác minh xuất hiện/hoạt động qua cơ chế Skill hiện hữu. **Không phải tạo 15 thư mục trống rồi đánh dấu PASS.**

## 7. Công cụ xử lý tệp ưu tiên

### Excel / CSV
- Giữ nguyên cấu trúc, sheet, tên cột, màu, style và công thức của mẫu gốc nếu yêu cầu là chỉnh sửa.
- Bảo toàn mã `00017`, Unicode, số âm, số thập phân, giá trị rỗng.
- Không đối chiếu người chỉ bằng họ tên; dùng mã nhân viên / định danh hợp lệ / nhiều trường phù hợp.
- Xác định dữ liệu trùng bằng khóa có chứng cứ, không tự loại các bản ghi trùng tên.
- Dùng Decimal / công thức nhất quán cho tính tiền; không làm tròn trong trung gian.
- Xuất tệp đầu ra và mở đọc lại để xác minh.

### XML
- Đọc, kiểm tra parse, namespace, schema *đã xác minh*, kiểu trường, charset UTF-8.
- Không tạo schema thuế/BHXH tưởng tượng.
- Export rồi round-trip parse và đối chiếu với fixture.
- Không kết luận file được cơ quan nhà nước chấp nhận nếu chưa có kết quả thực tế.

### Word / PDF / báo cáo
- Giữ đúng mẫu đã cung cấp khi chỉnh sửa.
- Thể hiện rõ số liệu nguồn, kỳ, đơn vị tiền tệ.
- Không bịa dữ liệu và không tự điền nội dung còn thiếu có tính pháp lý.

### Kiến trúc tool
Viết tool độc lập, có input validation, dry-run khi thích hợp, giới hạn file size, lỗi rõ ràng và test. Tránh trộn code nghiệp vụ với giao diện. Không cho tính năng đọc file khả năng truy cập tệp ngoài phạm vi được duyệt.

## 8. Bộ fixture và kiểm thử bắt buộc

Tạo fixture DEMO không chứa dữ liệu thật:
- Mã chứng từ `00017`
- Tên tiếng Việt có dấu
- Tiền âm, tiền dương, số 0, số lớn, phần lẻ
- Hai người trùng tên nhưng khác định danh
- Thiếu ô, ngày sai, cột sai định dạng
- Dữ liệu trùng thật và dữ liệu chỉ trùng tên
- Tổng dòng và tổng cột
- XML hợp lệ, XML lỗi và XML sai schema
- Excel có định dạng và công thức cần bảo toàn

Kiểm tra đối chiếu độc lập với kết quả kỳ vọng. Mỗi tính năng phải chứng minh:
**Nhập dữ liệu → chạy công cụ → kiểm tra output → xuất tệp → đọc lại → báo PASS/FAIL.**

Chạy các bước phù hợp trong `package.json` và backend tests. Không đoán lệnh test. Không sửa test để che lỗi. Nếu Electron không chạy được trong môi trường, đánh dấu **BLOCKED: GUI** chứ không suy ra GUI PASS từ unit test.

## 9. Cách tự thực thi và sửa lỗi

1. Kiểm tra quyền GitHub, công cụ terminal, Node, Python và môi trường.
2. Tạo nhánh tính năng (ví dụ `feature/accounting-vn-foundation`) từ đầu `main` mới nhất.
3. Lập checklist theo tệp và chức năng, sau đó bắt đầu **một thay đổi có thể chạy**.
4. Commit theo lát chức năng nhỏ và có test.
5. Chạy kiểm thử thực tế, lưu log **đã loại dữ liệu nhạy cảm**.
6. Nếu lỗi, đọc nguyên nhân, sửa nhỏ nhất có thể và chạy lại; không lặp vô hạn.
7. Tạo PR sang `main` kèm mô tả, bằng chứng test và các giới hạn chưa xử lý.
8. Không merge PR và không thay đổi dữ liệu/hệ thống thật khi chưa có quyền rõ ràng.
9. Nếu không có công cụ thực thi/GUI, tiếp tục công việc có thể kiểm chứng trên mã nguồn, không giả vờ đã chạy.

## 10. Tài liệu và quản lý tiến độ

Tạo/cập nhật theo nhu cầu thực tế (không lập tài liệu rỗng):
- `docs/roadmap/01-KIEM-KE-DU-AN.md`
- `docs/roadmap/02-VIET-HOA.md`
- `docs/roadmap/03-GIAO-DIEN-KE-TOAN.md`
- `docs/roadmap/04-AGENTS-SKILLS.md`
- `docs/roadmap/05-XU-LY-DU-LIEU.md`
- `docs/roadmap/06-KIEM-THU.md`
- `docs/roadmap/07-TIEN-DO.md`
- `docs/accounting-vn/THUAT-NGU.md`

README cần giới thiệu đúng **Eigent Kế Toán Việt Nam**, ghi công Eigent gốc, giữ giấy phép và phân biệt rõ phần đã chạy với phần dự kiến.

Bảng nghiệm thu bắt buộc:

| Module | Đã có code | UI hoạt động | Test chạy | Bằng chứng | Trạng thái |
|---|---|---|---|---|---|
| Việt hóa | | | | | |
| Eigent gốc | | | | | |
| Không gian Kế toán | | | | | |
| AI Agents | | | | | |
| Skills | | | | | |
| Excel/CSV | | | | | |
| XML | | | | | |
| Hóa đơn | | | | | |
| Tiền lương | | | | | |
| Thuế/BHXH | | | | | |
| Báo cáo tài chính | | | | | |

Định nghĩa:
- **PASS:** Đã chạy thực tế và đạt kiểm thử có bằng chứng.
- **FAIL:** Đã chạy và thất bại.
- **BLOCKED:** Không thể kiểm tra vì thiếu quyền/môi trường/đầu vào.
- **NOT STARTED:** Chưa triển khai.

## 11. Thứ tự triển khai và điều kiện hoàn thành

**P0 — Ổn định bản Việt hóa:** xác minh chuỗi, kiểm tra quy trình dịch và sửa lỗi i18n.

**P1 — Foundation:** tạo mục Kế toán với route thật, layout và trạng thái tương tác.

**P2 — Vertical slice:** công cụ đọc Excel/CSV, kiểm tra dữ liệu demo, giao diện kết quả và nút xuất file thật.

**P3 — Kết nối đa tác nhân:** ít nhất một agent gọi được tool kiểm tra tệp và trả kết quả xác thực.

**P4 — Mở rộng:** các Skills và module nghiệp vụ theo thứ tự ưu tiên, mỗi module có test.

**P5 — Hoàn thiện:** kiểm thử end-to-end, regression, đánh giá UX tiếng Việt, hướng dẫn sử dụng và bản build nếu có môi trường.

Không đánh dấu hoàn thành P1-P5 nếu các bài kiểm tra tương ứng chưa được thực hiện.

## 12. LỆNH BẮT ĐẦU NGAY

Đọc tài liệu này **và lập tức thực thi trên repo `accoutant67/eigent-viet-hoa`**.

- Đừng dừng ở việc viết kế hoạch.
- Đừng hỏi lại các thông tin đã có trong tài liệu.
- Không làm MISA SME, Smart Pro, SQL Server hoặc MausBot.
- Bắt đầu kiểm kê, chạy kiểm thử i18n và xây dựng một thay đổi nền tảng hữu ích.
- Nếu có quyền ghi GitHub, commit thay đổi trên nhánh riêng, tạo PR và báo URL.
- Nếu có lỗi, sửa an toàn và chạy lại.
- Cuối cùng báo ngắn: **đã thay đổi tệp nào, đã chạy lệnh nào, PASS/FAIL/BLOCKED, commit/PR, và việc nhỏ nhất còn cần người dùng làm.**

Chỉ tuyên bố hoàn thành khi có bằng chứng thực tế, không tự tạo báo cáo thành công.
