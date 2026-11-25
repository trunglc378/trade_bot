# Kế hoạch và đặc tả kiểm thử FreqBot VN Remote

Ngày: 27/10/2026. Phạm vi: lịch mua VN, quản trị vốn, nghiên cứu AI/Gemini đa nguồn, snapshot, mock API và dashboard. Tham chiếu [đặc tả 07](07-LICH-GIAO-DICH-AI-VA-PHAN-TICH.md), [Gemini đa nguồn](08-GEMINI-PRO-VA-NGHIEN-CUU-DA-NGUON.md) và [báo cáo thực thi](10-BAO-CAO-KIEM-THU.md).

## 1. Mục tiêu và phạm vi

Kiểm tra tính đúng đắn của phần mềm trong môi trường kiểm soát, ưu tiên không mở mua sai giờ/vượt hạn mức, không dùng nghiên cứu lỗi/hết hạn và không thực hiện thao tác đóng lệnh khi yêu cầu chưa hợp lệ. Kiểm thử này không đo lợi nhuận và không chứng nhận sẵn sàng chạy vốn thật.

| Cấp | Biên kiểm thử | Thành phần thật | Thành phần thay thế |
| --- | --- | --- | --- |
| Unit | Hàm/chính sách và hợp đồng adapter | Python, logic lịch/vốn/schema/nguồn | HTTP/AI response mock nếu cần |
| Integration | Ghép module, CLI, file, HTTP, callback chiến lược | Worker, provider parser, filesystem, HTTP localhost, pandas, mã callback | CCXT/sàn, ví/ORM/Freqtrade/TA-Lib và AI trả phí dùng test doubles |
| System | Luồng thao tác người dùng từ browser tới API và trạng thái | Edge headless, HTML/CSS/JS sản phẩm, mock API HTTP thật | Sàn và lệnh tiền thật không có; mock test service có dữ liệu cố định/reset riêng |

Các test tích hợp callback không chứng minh tương thích Freqtrade runtime hoặc phép tính TA-Lib. System test chỉ chứng nhận luồng dashboard + mock, không phải toàn hệ thống sản xuất gồm VPS, sàn, AI thật và điện thoại.

## 2. Điều kiện và cách tái chạy

- Windows với Python 3.12 và pandas để chạy toàn bộ test callback; máy chạy lần này có Python 3.12.7/pandas 2.2.2. Nếu không có pandas, unittest sẽ skip callback tests, phải đọc kết quả SKIP.
- Node.js, npm và Chromium/Edge/Chrome tương thích Playwright. Playwright Core được pin trong `tests/system/package-lock.json`; không tự tải browser khi cài.
- Docker CLI dùng kiểm tra cú pháp Compose. Kiểm tra runtime cần Docker Engine thật, không được suy ra từ việc CLI tồn tại.
- Build Android cần JDK, Gradle/wrapper và Android SDK; XML parse không thay thế build.

Từ thư mục gốc:

```powershell
npm ci --prefix tests/system --ignore-scripts --no-audit --no-fund
py -3.12 tests/run_tests.py
```

Runner tạo thư mục UTC riêng trong `test-results/`. Có thể chọn đường dẫn mới, không ghi đè bằng chứng lần chạy cũ:

```powershell
py -3.12 tests/run_tests.py --output test-results/my-new-run
```

Chạy riêng từng phần:

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 -m unittest discover -s freqtrade-bot/tests -v
node tests/test_dashboard.js
node tests/system/dashboard.e2e.cjs
docker compose -f freqtrade-bot/docker-compose.yml config --quiet
```

`TEST_BROWSER_PATH` chọn browser executable; `TEST_PYTHON` chọn Python cho mock system service khi chạy JS riêng; `TEST_ARTIFACT_DIR` chọn thư mục bằng chứng browser. Runner tự truyền Python hiện tại cho browser test. Browser chỉ được request tới localhost origin của test, các request ngoài origin bị chặn.

## 3. Thiết kế dữ liệu và oracle

- Lịch: mốc UTC tương ứng 03:00, 03:30, 04:00 VN; thứ bắt đầu phiên qua nửa đêm; nến 02:55 đóng lúc 03:00. Oracle là quy tắc `[start, end)` UTC+7.
- Vốn: equity 1.000, risk 0,5%, stoploss 3%, cost buffer 0,4%; stake tính toán 147,0588 trước các cap khác. Có trường hợp minimum sàn, exposure đầy, giá trị NaN/Infinity/bool.
- Nến: chuỗi 5m có kiểm soát, có nến đang chạy, thiếu/trùng/cũ và giá trị không hữu hạn. Oracle kiểm tra chỉ dùng nến đóng, thứ tự và độ mới.
- AI: payload giả completed/incomplete/refusal/timeout, consider/wait/avoid, cặp ngoài whitelist, confidence sai, thiếu quorum. Không gọi API thật.
- Grounding: native `url_citation` và sources của từng cặp; nguồn bịa, HTTPS giả mạo domain, hai subdomain cùng một miền và thiếu nguồn phải không cấp phiếu mua.
- Snapshot: tệp JSON UTF-8 trong thư mục tạm, roundtrip, TTL, context khác sàn/cấu hình và `is_mock`. Không thay snapshot hay database vận hành.
- Worker CLI: tiến trình Python thật với module CCXT fixture trên PYTHONPATH tạm; nhận nhiều config, ghi latest/history và không lộ khóa fixture. Trường hợp loop sai phải thoát trước khi import CCXT.
- Transport: HTTP server localhost kiểm tra JSON/header và giới hạn response 1 MB; không giả danh endpoint bên ngoài hoặc dùng khóa thật.
- System: fixture service gọi handler sản phẩm, bind 127.0.0.1/cổng hệ điều hành cấp. Mỗi ca reset trạng thái bằng endpoint riêng chỉ nằm trong test service, không thêm endpoint reset vào sản phẩm.

## 4. Ma trận bao phủ chức năng

| Yêu cầu | Nhóm ca/chứng cứ | Kết quả cần đạt |
| --- | --- | --- |
| FR-SES-01 / FR-SCH | PolicyTests, callback lịch đóng nến, JS phiên qua đêm | Đúng UTC+7/weekday/biên; chỉ chặn mua |
| FR-RKM-06 | Sizing, exposure, minimum, callback lỗi ví | Không nâng vốn vượt ngân sách; lỗi trả từ chối |
| FR-RES-01 | ResearchTests, CLI fixture | Loại dữ liệu thiếu/cũ/non-spot/blacklist |
| FR-AI-01/02 | ProviderTests, GroundingTests, quorum integration | JSON hợp lệ, đủ nguồn/phiếu, avoid phủ quyết trong required |
| FR-RES-02 | Snapshot roundtrip/context/TTL, pipeline integration | Báo cáo sai/cũ/mock không cấp quyền mua |
| FR-UI-01..08 | MockApiTests và SYS-01..06 | Login, đọc trạng thái, dừng/bật mua, xác nhận force-exit |
| FR-UI-09 | JS regression, SYS-07/08 | Phân biệt dữ liệu giả/cũ, nguồn HTTPS, không thực thi HTML từ AI |
| FR-EVAL-01 | Tổng hợp PnL theo giờ VN | Đúng chuyển giờ và thống kê mẫu PnL ròng |
| Thoát lệnh | StrategyHookTests | Lịch, báo cáo và lỗi thông báo không cản callback thoát |

Đây là bao phủ theo hành vi/chức năng, không phải phần trăm line/branch coverage. Chưa thu thập số liệu coverage bằng công cụ đo.

## 5. Đặc tả system test

| ID | Thao tác | Kiểm tra mong đợi |
| --- | --- | --- |
| SYS-01 | Login đúng, tải dashboard | Badge kết nối; số lệnh DOM khớp API; có số dư; không pageerror |
| SYS-02 | Login sai; GET status không token | Báo lỗi trên UI; API trả 401 |
| SYS-03 | Dừng mua rồi bật lại | `stopbuy_active` thay đổi; dừng mua không xóa lệnh mở |
| SYS-04 | Hủy rồi chấp nhận hộp thoại Panic Sell | Hủy giữ nguyên số lệnh; chấp nhận đóng hết trong mock |
| SYS-05 | Đóng một lệnh | Số lệnh DOM/API giảm đúng một |
| SYS-06 | Bật khóa rủi ro fixture | Banner cảnh báo và API có một lock |
| SYS-07 | Đồng bộ báo cáo, chuyển viewport 390×844 | Hiện nhãn giả lập, link nguồn HTTPS, tiêu đề nhìn thấy; chụp ảnh mobile |
| SYS-08 | Upload JSON hết hạn có HTML/link độc hại, rồi JSON hỏng | Không có img/script thực thi hoặc link javascript; báo hết hạn; dữ liệu hỏng xóa bảng và hiện lỗi |

SYS-07 là smoke responsive, chưa kiểm tra toàn bộ thao tác trên mobile hoặc chuẩn accessibility. Test XSS giới hạn ở trường nhận định/nguồn nghiên cứu, không phải pentest toàn bộ ứng dụng.

## 6. Regression cho lỗi tìm thấy

`test_malformed_forceexit_does_not_close_positions`: login token fixture; gửi `{broken`, `{}`, `[]`, tradeid null/bool/0 vào `/forceexit`; mong đợi HTTP 400 và danh sách vị thế giữ nguyên. Một unittest method có nhiều subcase, không tăng số ca tổng theo mỗi assert/subcase.

Docker preflight phải vừa nhận mã thoát hợp lệ vừa có chuỗi ServerVersion, vì quan sát được CLI trên máy này trả code 0 nhưng in lỗi kết nối named pipe. Không phân loại PASS chỉ dựa mã thoát.

## 7. Tiêu chí đánh giá và bằng chứng

- PASS: assertions của ca đạt. FAIL/ERROR: sai kết quả hoặc lỗi ngoài dự kiến. SKIP: ca không thực thi. BLOCKED: thiếu điều kiện môi trường. NOT_RUN: ngoài phạm vi lần chạy hoặc chưa thực hiện.
- Một ca có subtest được tính một lần; hai thư mục Python được discover riêng, runner phân cấp rõ. Các check JS syntax/DOM/Compose/XML không cộng thêm vào số ca Python/System.
- Điều kiện đạt cho phạm vi offline: không FAIL/ERROR/SKIP trong các ca bắt buộc và không FAIL trong system browser. Điều kiện này không đủ phê duyệt live khi Docker/Android/sàn thật chưa nghiệm thu.
- Runner trả exit 1 khi có FAIL/ERROR, nhưng có thể trả 0 khi tồn tại BLOCKED/NOT_RUN. Luôn đọc `results.json`, không dùng exit code đơn lẻ để phê duyệt release.
- Lưu `results.json` từng ca/duration/environment, `junit.xml` Python, log theo cấp, browser results, ảnh desktop/mobile và SHA256 nguồn/test. JUnit hiện không chứa ca browser; browser dùng JSON riêng.
- Báo cáo bảo toàn log lần trước lỗi và kết quả sau sửa; không xóa lỗi cũ để báo toàn bộ lịch sử là PASS.

## 8. Các bước nghiệm thu còn lại

Khi Docker Engine sẵn sàng: pin image/digest, load strategy/config bằng Freqtrade thật, chạy lookahead/recursive analysis, backtest ngoài mẫu với phí/trượt giá và protections. Tiếp theo forward dry-run, kiểm chứng stoploss/khớp lệnh ở môi trường thử phù hợp của từng sàn. Xác thực contract API OpenAI/Gemini, native citations, quota và timeout bằng request nhỏ có quyền truy cập hợp lệ. Build/cài Android, kiểm tra login/TTL/giả lập/cảnh báo trên emulator hoặc thiết bị.

Các bước này phải có báo cáo và bằng chứng riêng; không tự đổi `dry_run` sang false. Chưa thực hiện soak/load test dài ngày, đánh giá lợi nhuận hoặc pentest toàn diện trong lần chạy hiện tại.
