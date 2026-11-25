# Báo cáo kiểm thử FreqBot VN Remote

Ngày báo cáo: 27/10/2026. Loại kiểm thử: Unit, Integration, System (dashboard + mock). Trạng thái: **Đạt phạm vi kiểm thử offline đã thực thi; chưa đủ điều kiện nghiệm thu hệ thống giao dịch thật.**

## 1. Kết quả chính

Lần chạy cuối từ **23:00:22 đến 23:00:36 ngày 27/10/2026, UTC+7**, sau khi sửa lỗi mock force-exit và cách đánh giá Docker preflight. Thời gian toàn runner khoảng 14 giây, không phải soak test hoặc benchmark.

| Cấp | Số ca | PASS | FAIL/ERROR | SKIP |
| --- | ---: | ---: | ---: | ---: |
| Unit | 22 | 22 | 0 | 0 |
| Integration | 31 | 31 | 0 | 0 |
| System trên Edge + mock | 8 | 8 | 0 | 0 |
| **Tổng ca thực thi** | **61** | **61** | **0** | **0** |

53 ca Python gồm 22 unit và 31 integration; 8 ca browser được ghi riêng. Không cộng số assert/subcase hoặc các check công cụ vào tổng 61.

Nguồn số liệu: [results.json cuối](../test-results/20261027-final/results.json), [JUnit Python](../test-results/20261027-final/junit.xml), [browser results](../test-results/20261027-final/system/results.json). Danh sách từng ca: [phụ lục 11](11-DANH-MUC-KET-QUA-TEST.md).

## 2. Môi trường và đối tượng kiểm thử

| Thành phần | Môi trường thực tế |
| --- | --- |
| Hệ điều hành | Windows 11, build 26200 |
| Python | 3.12.7, Anaconda; pandas 2.2.2 |
| Browser | Microsoft Edge/Chromium 156.0.4314.42, headless |
| Browser automation | playwright-core 1.64.1, package-lock trong tests/system |
| Viewport | Desktop 1440×1000; mobile smoke 390×844 |
| HTTP system | 127.0.0.1, cổng tạm do hệ điều hành cấp; handler mock sản phẩm + reset/fixture chỉ trong test service |
| Worker CLI | Tiến trình Python thật, CCXT fixture qua PYTHONPATH tạm, file latest/history thực trong thư mục tạm |
| AI/provider | Response fixture hoặc HTTP localhost; không gọi API bên ngoài |
| Strategy | Mã callback thật + pandas; ví/ORM/Freqtrade/TA-Lib dùng test doubles |

Mã nguồn có thay đổi chưa commit tại thời điểm test. [SHA256 manifest](../test-results/20261027-final/source-manifest.json) nhận diện các file nguồn/test/config tham gia, không suy ra trạng thái kiểm thử từ HEAD Git. Manifest không chứa secrets riêng hoặc dữ liệu tài khoản.

## 3. Phạm vi đã kiểm chứng

- Lịch mua UTC+7, biên kết thúc, thứ bắt đầu phiên qua đêm và giờ đóng nến.
- Sizing theo ngân sách lỗ cộng buffer, minimum stake, giới hạn vị thế/exposure và dữ liệu không hữu hạn.
- Bộ lọc thị trường, nến chưa đóng/cũ/thiếu, whitelist/blacklist và kết quả kỹ thuật không bị AI ghi đè.
- Quorum/veto, API output chưa hoàn tất, confidence/cặp không hợp lệ, thiếu nguồn native và nguồn không thuộc allowlist.
- Pipeline Gemini parser → worker → snapshot trên đĩa → entry policy, cả trường hợp được chấp nhận và bị chặn khi thiếu nguồn.
- CLI merge overlay, ghi history, không đưa khóa fixture vào output; JSON HTTP thực và giới hạn response 1 MB.
- Login/dashboard, token giả, dừng/bật mua, Panic Sell hủy/xác nhận, đóng một lệnh và banner lock qua browser/API thật của mock.
- Báo cáo giả lập/hết hạn, link nguồn, HTML/link độc hại trong nghiên cứu và lỗi JSON upload; không phát hiện JavaScript pageerror trong 8 system cases.
- Callback thoát không bị lịch/AI/lỗi gửi thông báo cản trở trong fixture.

Ma trận yêu cầu và bước/mong đợi system test được ghi tại [tài liệu 09](09-KE-HOACH-VA-DAC-TA-KIEM-THU.md). Đây là coverage chức năng được chọn, chưa có phần trăm line/branch coverage và không tuyên bố bao phủ mọi nhánh.

## 4. Lỗi phát hiện và kết quả sửa

| ID | Mức độ/phạm vi | Hiện tượng trước sửa | Xử lý và kết quả |
| --- | --- | --- | --- |
| DEF-001 | P2, mock API/test môi trường giả lập | `/forceexit` nhận JSON hỏng hoặc thiếu tradeid vẫn trả 200 và có thể đóng toàn bộ lệnh giả; JSON array gây AttributeError/đóng kết nối | Parser trả 400 cho JSON hỏng/non-object; force-exit yêu cầu tradeid all hoặc số nguyên dương; regression có 6 payload lỗi và xác nhận không thay đổi vị thế. PASS sau sửa |
| QA-001 | P2, bộ thu thập kết quả kiểm thử | Docker CLI trả code 0 dù stderr báo không kết nối được named pipe; preflight ban đầu báo PASS sai | Runner yêu cầu ServerVersion đúng định dạng; lần cuối phân loại BLOCKED và giữ log kết nối. Đã sửa cách phân loại |

Bằng chứng trước sửa DEF-001: [log tái hiện](../test-results/20261027-validation/defect-mock-forceexit-before-fix.log). Lần tái hiện có hai subcase FAIL và một ERROR trong một method; không được mô tả là toàn bộ lịch sử chạy đều PASS.

Bằng chứng sau sửa: `test_mock_api.MockApiTests.test_malformed_forceexit_does_not_close_positions` trong [integration.log](../test-results/20261027-final/integration.log) và results cuối. Đây là sửa mock server của dự án, không phải sửa/kiểm chứng endpoint của Freqtrade upstream.

Thư mục `20261027-validation` là lần chạy trước cùng log tái hiện lỗi, đã bị thay thế bởi `20261027-final`. Kết quả Docker PASS trong JSON cũ không được dùng để kết luận Engine sẵn sàng; xem ghi chú superseded trong thư mục đó.

## 5. Kiểm tra bổ sung và giới hạn môi trường

| Hạng mục | Kết quả | Diễn giải |
| --- | --- | --- |
| JavaScript syntax | PASS | `node --check` |
| DOM regression harness | PASS | Bổ trợ cho browser thật, không cộng như ca system riêng |
| Docker Compose config | PASS | Đúng cú pháp/merge Compose; không chứng minh container chạy được |
| Docker Engine | **BLOCKED** | Không kết nối `dockerDesktopLinuxEngine`; không có ServerVersion hợp lệ |
| XML Android | PASS | Parse 7 file XML; không phải build APK |
| Build và thiết bị Android | **BLOCKED** | Không có Gradle/wrapper và Android SDK được cấu hình trong môi trường kiểm thử |
| Contract API OpenAI/Gemini thật | **NOT_RUN** | Không dùng khóa thật hoặc request trả phí; native citations được kiểm tra bằng fixture |
| Freqtrade/TA-Lib runtime, khớp lệnh và stoploss trên sàn | **NOT_RUN / phụ thuộc Docker** | Chưa xác minh bằng container hoặc sàn thật |
| Backtest, lookahead/recursive, forward dry-run dài ngày | **NOT_RUN** | Không có dữ liệu/kết quả hiệu quả giao dịch trong lần chạy này |

Chi tiết check, command, exit code và log nằm trong `results.json`. Runner trả code 0 cho lần cuối vì không có test FAIL/ERROR; điều đó không xóa các trạng thái BLOCKED/NOT_RUN.

## 6. Bằng chứng hệ thống và xem ảnh

- [Ảnh dashboard desktop](../test-results/20261027-final/system/desktop.png).
- [Ảnh dashboard mobile](../test-results/20261027-final/system/mobile.png).
- [Log system browser](../test-results/20261027-final/system-browser.log).
- [Log unit](../test-results/20261027-final/unit.log), [log integration](../test-results/20261027-final/integration.log), [log Docker](../test-results/20261027-final/docker-engine.log).

Ảnh đã được xem lại: layout xếp cột ở viewport mobile, bảng dữ liệu rộng dùng vùng cuộn ngang; báo cáo fixture có nhãn giả lập. Chưa đánh giá accessibility/độ tương phản toàn diện hoặc mọi thao tác trên điện thoại. Tài khoản và PnL trong ảnh là dữ liệu mẫu.

## 7. Kết luận và bước tiếp theo

Các chức năng trong phạm vi offline đã thực thi đạt 61/61 ca sau sửa lỗi; chưa phát hiện lỗi assertion còn mở trong tập ca này. Có thể tiếp tục phát triển và kiểm thử trên dữ liệu giả lập. **Chưa đề nghị chuyển sang giao dịch vốn thật hoặc coi kết quả này là chứng minh lợi nhuận.**

Cần mở Docker Engine để kiểm thử Freqtrade thực, pin phiên bản/image và xác nhận strategy/config/TA-Lib. Sau đó chạy backtest ngoài mẫu, lookahead/recursive, forward dry-run; xác minh loại stoploss/khớp lệnh của từng sàn trong môi trường phù hợp. Hoàn thiện toolchain Android để build/cài và kiểm tra trên thiết bị. Xác minh Gemini/OpenAI API thật với quota/billing được phép và request nhỏ trước khi mở vòng lặp nghiên cứu.

Chưa đo load, latency percentile, soak dài ngày, chất lượng dự báo AI hoặc lợi nhuận điều chỉnh theo rủi ro. Các kết quả đó cần báo cáo bổ sung riêng.
