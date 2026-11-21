# Kế hoạch và kết quả kiểm thử

## Quy tắc smoke và regression cho cả 5 giai đoạn

Sau mỗi thay đổi tính năng, lỗi, Agent hoặc Skill: chạy smoke test theo đường thực thi thật của phần vừa đổi; sửa lỗi và chạy lại; sau đó chạy regression liên quan (ChatBox, i18n, Excel, Agents, Skills). Cập nhật báo cáo bằng log của đúng commit. Không dùng unit test để kết luận GUI hoạt động. Mục chưa triển khai ghi NOT STARTED; mục không có môi trường ghi BLOCKED. PR chưa được merge nếu chưa được duyệt.

Workflow `Test` kiểm tra Python, frontend guardrails, i18n, ChatBox rollback, backend/frontend HTTP smoke và Electron preview. Workflow `Accounting workbook audit` chạy CLI qua tiến trình thật trên workbook giả lập rồi chạy regression Excel. Các giai đoạn tiếp theo cần thêm smoke của module mới vào workflow phù hợp.

## Báo cáo PR Excel #1 — 21/11/2026 (giờ Việt Nam)

- **Commit mã được kiểm thử:** `9de1839dca53fd6fbe5ff940bea6ae59dc544ea7` (head PR).
- **Commit tích hợp do GitHub Actions checkout:** `b9f83141c4561e0c1fdc7f79211660f941e07605`, ghép head PR với `main` tại `643ae05615a119a1cbe49e79c6e51b640731991f`.
- **Môi trường:** GitHub Actions Ubuntu 26.04; Python 3.11; Node.js 20; backend cài bằng `uv sync`; Electron preview chạy qua Xvfb. Máy làm việc không có checkout để khởi động Eigent và không có cửa sổ ứng dụng/model hợp lệ để thao tác GUI thủ công.
- **Dữ liệu:** workbook giả lập trong thư mục tests; không dùng workbook doanh nghiệp, CCCD hoặc dữ liệu thật.
- **Bằng chứng:** [Test run 44793696831](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44793696831), [Excel audit run 44793696810](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44793696810), [Pre-commit 44793696782](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44793696782), [Markdown lint 44793696879](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44793696879), [CodeQL 44793696761](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44793696761), [main baseline Test 44774491335](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44774491335).

| Phần kiểm thử | Lệnh / cách chạy | Kết quả | Bằng chứng và giới hạn |
| --- | --- | --- | --- |
| Khởi động backend + frontend web | `bash scripts/smoke-web-local-brain.sh` | PASS | Backend health/session/capabilities và `/skills`; Vite HTML và route fallback phản hồi. Có lần `curl` báo chưa kết nối trong lúc tiến trình khởi động; script tiếp tục chờ và cả backend/frontend đều PASS. Đây là HTTP smoke, không xác nhận render GUI. |
| Nhận diện và phân quyền Skill | API `GET /skills`, `GET /skills/accounting-workbook-audit/files`; test `cd backend && uv run pytest tests/app/service/test_accounting_workbook_skill_integration.py -v` | PASS | API trả đúng một Skill mẫu và file `SKILL.md`/CLI. Test tích hợp kiểm tra bật/tắt Skill, quyền `single_agent`, Agent được chọn và chặn Agent ngoài phạm vi. Không đại diện cho 15 Skills hay 72 bot. |
| Excel CLI smoke | `python resources/example-skills/accounting-workbook-audit/tests/smoke_cli.py` | PASS | Chạy CLI thật, tạo JSON, giữ nguyên byte workbook nguồn và chặn ghi đè báo cáo. |
| Excel regression | `python -m unittest discover -s resources/example-skills/accounting-workbook-audit/tests -p 'test_*.py' -v` | PASS | 7/7: khóa trùng, mã `00017`, tên trùng không bị coi là cùng người, cột khóa thiếu không tạo khóa một phần, giá trị thiếu/lỗi Excel/công thức, DTD/entity, từ chối tệp sai định dạng và bảo toàn nguồn. |
| i18n | `npm run check:i18n` | PASS | `check-i18n-locale-parity: OK`; `check-i18n-source-usage: OK` (48 occurrence được kiểm tra, 48 ngoại lệ đã ghi nhận). Chỉ là kiểm tra tĩnh, thao tác chuyển ngôn ngữ trên GUI đang BLOCKED. |
| Frontend guardrails | `npm run type-check` và các bước kiểm tra token, Tailwind, Electron access, định dạng, test frontend liên quan | PASS | Các guardrail hoàn tất; test thay đổi frontend 96/96 PASS. |
| ChatBox regression (rollback renderer) | `VITE_CHATBOX_EVENT_BUS=false npx vitest run --config vitest.config.ts test/unit/components/ChatBox test/unit/store/chatStore.test.ts test/unit/store/restoredRunApproval.test.ts test/unit/store/chatEventProjectionBridge.test.ts` | PASS | 53/53 file, 1.113/1.113 test PASS trên run 44793696831. |
| Python regression toàn backend | `cd backend && uv run pytest tests/app -v` | PASS | 4.593 passed, 11 skipped, 110 warnings, 11 subtests passed. Test tích hợp Skill nằm trong bộ này. Warnings không làm job thất bại. |
| Electron preview và stream relay | `xvfb-run --auto-servernum npm run test:preview-browser`; `xvfb-run --auto-servernum npm run test:stream-relay` | PASS | Electron chạy trong Xvfb và các kịch bản preview/relay PASS. Đây là kiểm thử tự động preview, không chứng minh menu/chat/Giao diện Kế toán thực tế. Có cảnh báo PostCSS không truyền `from`; job vẫn PASS. |
| CI/Pre-commit/Markdown lint/CodeQL | GitHub Actions trên head `9de1839` | PASS | Các run được liên kết phía trên đều kết thúc thành công. |
| Menu chính/menu con, chuyển tiếng Việt bằng GUI, Chat AI gửi câu hỏi | Thao tác Eigent thật; cần ứng dụng và cấu hình model hợp lệ | BLOCKED | Không có cửa sổ Eigent hoặc model kiểm thử trong môi trường. Không suy ra PASS từ unit/HTTP/Electron preview. |
| Giao diện Kế toán; bot/Agent nghiệp vụ; 15 Skills hoàn chỉnh | Mở giao diện; đăng ký, công cụ, đầu vào/ra, quyền, phối hợp và xử lý lỗi | NOT STARTED | PR này chỉ đăng ký Skill kiểm toán workbook mẫu; chưa tích hợp bot kế toán hay giao diện nghiệp vụ. |
| Xuất workbook, hóa đơn, GTGT tháng/quý, TNCN quý, TNDN tạm nộp, BCTC, XML | Smoke nghiệp vụ theo mẫu/schema được xác minh | NOT STARTED | Chưa có module tương ứng trong PR; chưa kiểm tra định dạng workbook đầu ra, kỳ khai hay schema XML. |
| Cập nhật pháp luật và biểu mẫu | Workflow với nguồn chính thức và fixture văn bản cũ/mới | NOT STARTED | Chưa triển khai theo dõi nguồn, ngày hiệu lực/kỳ áp dụng, Issue/PR đề xuất hay khóa không tự áp dụng công thức. |

### Lỗi ghi nhận, xử lý và kiểm thử lại

- **ChatBox trên `main` trước PR:** Test run 44774491335 có 1.112/1.113 test PASS và một test fail tại `ChatBox.spaceModelSelection.test.tsx`. Log báo `TestingLibraryElementError` không tìm thấy câu tiếng Việt trong DOM. Đây là lỗi kỳ vọng của test: `test/setup.ts` mock `useTranslation()` bằng locale en-US, nhưng assertion lại lấy chuỗi qua i18next singleton có thể đang ở locale khác. Log xác nhận lỗi đã tồn tại trên `main` trước PR.
- **Khắc phục và retest:** sửa assertion DOM trong test để dùng chuỗi từ bundle en-US đúng với React render; giữ kiểm tra riêng cho error mapping. Không sửa hành vi UI. Chạy lại rollback ChatBox trên head `9de1839`: 53 file, 1.113/1.113 test PASS; toàn bộ workflow Test PASS. Không còn fail ChatBox mới do PR.
- **Khởi động smoke:** các dòng `curl: (7) Failed to connect` xuất hiện trong vòng chờ trước khi backend/Vite sẵn sàng; sau đó script ghi PASS cho danh sách Skill và hoàn thành web/local-brain smoke. Không có lỗi kết thúc chưa khắc phục.
- **Log cảnh báo:** Python job ghi 110 warning (bao gồm warning/deprecation trong test phụ thuộc); Electron preview ghi cảnh báo PostCSS. Các job vẫn kết thúc thành công. Một số test frontend cố ý mô phỏng lỗi model/kết nối để kiểm tra hiển thị và recovery; đây không phải lỗi test chưa xử lý.
- **Lỗi Skill cũ:** run 44777652053 từng lỗi import do regex bị escape thừa, đã sửa tại `4a1cd7b0d5d4795d4c5a58a00fad8957989a0025`; run 44777831156 xác nhận 6 test PASS.
- **Kiểm tra i18n cũ:** test phát hiện hai nhãn menu tự hiển thị “Tiếng Việt” chưa khai báo ngoại lệ source-usage. Đã khai báo chính xác; kiểm tra i18n hiện PASS.

### Giới hạn và phạm vi còn thiếu

Không có thao tác GUI thật cho menu, đổi ngôn ngữ, gửi Chat AI hoặc mở giao diện Kế toán; các ca GUI tương ứng là BLOCKED. Bộ kiểm thử hiện tại không chứng minh workbook được xuất và giữ định dạng, hóa đơn/tờ khai/BCTC đúng nghiệp vụ, XML hợp lệ theo schema đã xác minh, hoặc nguồn pháp luật/biểu mẫu đúng phiên bản. Những module chưa triển khai ở trên phải tiếp tục ghi NOT STARTED cho đến khi có code và bằng chứng smoke thực tế.