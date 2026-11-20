# Kế hoạch và kết quả kiểm thử

## Kiểm thử Skill rà soát Excel

Bộ kiểm thử tổng hợp trong resources/example-skills/accounting-workbook-audit/tests/ bao phủ:

- Phát hiện dòng trùng và khóa trùng theo định danh được chọn.
- Phân biệt mã số có định dạng hiển thị số 0 đầu với chuỗi số khác.
- Phát hiện cột bắt buộc trống và cột không tồn tại.
- Ghi nhận ô lỗi Excel và đếm ô công thức mà không tính lại.
- Không để giá trị ô mẫu xuất hiện trong báo cáo; không sửa tệp nguồn.
- Tạo báo cáo JSON riêng và chặn ghi đè nếu không có --force.
- Từ chối đầu vào không phải .xlsx và XML có khai báo DTD/entity.

Workflow: .github/workflows/accounting-workbook-audit.yml  
Lệnh chạy: python -m unittest discover -s resources/example-skills/accounting-workbook-audit/tests -v

## Kết quả đã xác minh

- Run 1 (44777652053) thất bại ở bước import do biểu thức chính quy bị escape thừa. Lỗi đã được sửa trong commit 4a1cd7b0d5d4795d4c5a58a00fad8957989a0025.
- Run 2 (44777831156) thành công; 6 test chạy, kết quả OK. Bộ test dùng Python chuẩn, không tải dữ liệu kế toán thật.
- Workflow Test #5 trên commit nền (44774491335) có 1.112/1.113 test thành công; còn một lỗi ở test/unit/components/ChatBox.spaceModelSelection.test.tsx. Các job Browser Preview Electron, Python Tests và Web + Local Brain Smoke thành công.

## Phạm vi kết quả

Workflow riêng xác nhận các kiểm thử của Skill, không xác nhận giao diện Việt hóa 100%, build ứng dụng, tính lại công thức Excel hay tính hợp lệ nghiệp vụ kế toán/thuế/BHXH. Không dùng tệp kế toán thật trong job CI.

## Quy tắc kiểm thử cho cả 5 giai đoạn

Sau mỗi thay đổi tính năng, lỗi, Agent hoặc Skill: chạy smoke test bằng đường thực thi của phần vừa đổi; nếu FAIL thì sửa và chạy lại; sau đó chạy regression liên quan (ChatBox, i18n, Excel, Agents, Skills), rồi cập nhật PR và báo cáo. Không dùng unit test để kết luận cửa sổ GUI đã hoạt động. Chỉ tính PASS khi có log ở đúng commit; mục chưa triển khai là NOT STARTED; mục chưa có môi trường chạy là BLOCKED. PR chưa được merge khi chưa có phê duyệt.

Workflow `Test` chạy backend/frontend HTTP smoke, i18n, type check, frontend rollback ChatBox, Python và Electron preview trên PR. Workflow `Accounting workbook audit` chạy CLI thực với workbook giả lập rồi chạy regression Excel; workflow này được áp dụng cho mọi PR vào `main` sau khi cập nhật trigger. Các giai đoạn sau phải bổ sung smoke của module mới vào workflow phù hợp trước khi báo hoàn thành.

## Báo cáo PR Excel #1 — 21/11/2026 (giờ Việt Nam)

- **Commit kiểm thử:** `6eb39ae75c3d4d400d5e176dbf26ac72cfbda0d2`.
- **Môi trường:** GitHub Actions `ubuntu-latest`, Python 3.11, Node.js 20, backend `uv sync`; Electron preview chạy trong Xvfb. Máy làm việc trong lượt này không có checkout Python/Git và không có cửa sổ Eigent để kiểm thử GUI thủ công.
- **Dữ liệu:** workbook giả lập trong `tests`; không dùng tệp doanh nghiệp, CCCD hoặc dữ liệu thật.
- **Nguồn bằng chứng:** [Skill run](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44789385715), [Test run](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44789385766), [Pre-commit](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44789385724), [main baseline Test](https://github.com/accoutant67/eigent-viet-hoa/actions/runs/44774491335).

| Phần được kiểm tra | Lệnh hoặc phép thử | Trạng thái | Bằng chứng và giới hạn |
| --- | --- | --- | --- |
| Excel CLI | `python resources/example-skills/accounting-workbook-audit/tests/smoke_cli.py` | PASS | Tiến trình CLI tạo JSON, giữ nguyên byte workbook, chặn ghi đè; chỉ đọc .xlsx. |
| Excel regression | `python -m unittest discover -s resources/example-skills/accounting-workbook-audit/tests -p 'test_*.py' -v` | PASS | 7/7 test: mã 00017 khác 17, tên trùng không đồng nhất định danh, khóa ghép thiếu cột không dùng khóa một phần, ô lỗi, công thức, DTD, tệp nguồn không đổi. |
| Backend và frontend HTTP | `bash scripts/smoke-web-local-brain.sh` | PASS | `/health`, session header, capabilities, Vite HTML và route fallback trả kết quả theo script; không xác nhận render GUI. |
| Đăng ký Skill | `GET /skills`, `GET /skills/accounting-workbook-audit/files` | PASS | Backend trả đúng một Skill mẫu với `SKILL.md` và script; không phải Agent kế toán. |
| Quyền Skill | `cd backend && uv run pytest tests/app/service/test_accounting_workbook_skill_integration.py -v` (nằm trong full Python run) | PASS | Kiểm tra cấu hình bật, phạm vi `single_agent`, chặn Agent không được chọn và tắt Skill; test đã PASS trong full Python run. |
| i18n tĩnh | `npm run check:i18n` | PASS | Locale parity và source usage đạt; 48 ngoại lệ có số lượng xác định. Chưa xác nhận thao tác chuyển tiếng Việt trong GUI. |
| Frontend guardrails | `npm run type-check`, token, Tailwind, changed frontend tests | PASS | Các bước trước rollback ChatBox đều PASS. |
| Electron tự động | `xvfb-run --auto-servernum npm run test:preview-browser`; `test:stream-relay` | PASS | Bài thử preview/relay; không phải smoke menu, chat hay cửa sổ kế toán. |
| ChatBox rollback | `VITE_CHATBOX_EVENT_BUS=false npx vitest run --config vitest.config.ts test/unit/components/ChatBox test/unit/store/chatStore.test.ts test/unit/store/restoredRunApproval.test.ts test/unit/store/chatEventProjectionBridge.test.ts` | FAIL | 1/1.113 test FAIL, 1.112 PASS. Cùng test và cùng lỗi thiếu đoạn tiếng Việt trong DOM đã FAIL trên `main` commit `643ae056` trước PR. Chưa sửa lỗi nền. |
| Python toàn bộ | `cd backend && uv run pytest tests/app -v` | PASS | 4.593 passed, 11 skipped; test tích hợp Skill PASS. |
| CI, Pre-commit, Markdown lint, CodeQL | GitHub Actions trên commit kiểm thử | PASS | Các workflow độc lập đều thành công; workflow tổng Test vẫn FAIL ở ChatBox nền. |
| GUI menu, chuyển tiếng Việt, Chat AI gửi yêu cầu | Thao tác ứng dụng thật với model hợp lệ | BLOCKED | Không có cửa sổ Eigent và cấu hình model kiểm thử trong môi trường hiện tại. |
| Giao diện Kế toán; Agent nghiệp vụ/72 bot | Điều hướng, đăng ký Agent, phối hợp, phân quyền Agent | NOT STARTED | Chưa có module/Agent trong PR; không gán PASS theo tên roadmap. |
| Excel xuất workbook, hóa đơn, GTGT tháng/quý, TNCN quý, TNDN tạm nộp quý, BCTC, XML | Smoke nghiệp vụ | NOT STARTED | PR chỉ có công cụ đọc .xlsx và xuất JSON, chưa có module tương ứng. |
| Theo dõi nguồn pháp luật, kỳ áp dụng, Issue/PR đề xuất | Workflow và fixture văn bản mới/cũ | NOT STARTED | Cơ chế cập nhật pháp luật chưa được triển khai. |

### Lỗi phát hiện, cách khắc phục và kiểm thử lại

- Skill trước đó lỗi regex khi import ở run 44777652053; đã sửa tại `4a1cd7b`, run 44777831156 PASS.
- Lần này pre-commit 44788185117 phát hiện Ruff lint/format tệp test mới; 44788846720 còn format. Áp dụng đúng diff Ruff tại `6eb39ae`; pre-commit 44789385724 PASS.
- Test 44788185096 phát hiện hai tên tự gọi “Tiếng Việt” trong menu là ngoại lệ i18n chưa khai báo. Bổ sung ngoại lệ chính xác cho hai vị trí tại `c2fbcc80`; kiểm tra i18n trong run 44789385766 PASS.
- ChatBox vẫn FAIL ở cùng phép thử trên `main` và nhánh PR. Không gán lỗi cho Skill Excel, nhưng cũng không coi toàn bộ Test workflow là PASS.

### Phạm vi còn thiếu

Không có phép thử GUI thật cho menu chính/menu con, chuyển ngôn ngữ, gửi Chat AI hoặc mở giao diện Kế toán. Các test HTTP, unit và Electron preview không thay thế cho các phép thử đó. Không có schema XML đã xác minh hoặc nguồn văn bản pháp luật chính thức trong module hiện tại; các ca này chỉ được đánh giá khi module được triển khai.
