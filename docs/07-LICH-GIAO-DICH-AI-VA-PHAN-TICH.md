# Đặc tả triển khai: Lịch giao dịch, nghiên cứu AI và kiểm soát vốn

Ngày: 27/10/2026. Tài liệu này là đặc tả bổ sung cho SRS/SDS và hướng dẫn vận hành mã nguồn hiện tại. Khi có khác biệt với mô tả 1.0, áp dụng tài liệu này và cấu hình thực tế. Mục tiêu là lợi nhuận điều chỉnh theo rủi ro có thể đo lường; không bảo đảm lợi nhuận, mức lỗ tối đa hay bảo toàn vốn tuyệt đối.

## 1. Kết quả rà soát dự án

Dự án đã có nền tảng Freqtrade, chiến lược EMA/RSI/Bollinger, protections, dashboard, Android và mock API. Tài liệu cũ mô tả một số yêu cầu như thể đã được xác minh thực tế. Những điểm cần sửa:

- Chưa có chính sách khung giờ, pipeline đề xuất AI hay kiểm tra spread trực tiếp trong chiến lược. `check_depth_of_market` xét tỷ lệ khối lượng bid/ask, không thay thế giới hạn spread.
- Vốn cố định không tự thích ứng khi ví giảm. Bổ sung sizing và tái kiểm tra vốn ngay trước khi gửi lệnh.
- `MaxDrawdown` dùng lịch sử lệnh đóng trong cửa sổ trượt; không phải cầu dao lỗ equity theo ngày Việt Nam và không bao gồm đầy đủ lỗ chưa thực hiện. `StoplossGuard` đếm stoploss trong cửa sổ, không đòi hỏi chúng phải liên tiếp.
- Binance Spot hỗ trợ stop-limit trên sàn qua Freqtrade; OKX Spot hỗ trợ market/limit. Không thể dùng một loại stoploss và coi như áp dụng cho mọi sàn. Bybit Spot không có stoploss trên sàn theo bảng hỗ trợ hiện tại.
- Docker trước đây publish cổng mọi giao diện; bản mới chỉ bind localhost. Android qua Tailscale cần chủ động bind IP Tailscale trên HOST Docker.
- Mock chỉ là dữ liệu giả, không xác nhận tính tương thích 100% với API thực hay chứng minh lợi nhuận.

## 2. Lịch giao dịch theo giờ Việt Nam

Chính sách tại `freqtrade-bot/user_data/config.json` → `vn_policy.schedule`:

```json
{
  "enabled": true,
  "windows": [
    {"start": "03:00", "end": "04:00", "weekdays": [0, 1, 2, 3, 4, 5, 6]}
  ]
}
```

- Múi giờ cố định UTC+7, tương ứng `Asia/Ho_Chi_Minh`; không phụ thuộc giờ hệ điều hành hoặc container. `weekdays`: thứ Hai = 0, Chủ nhật = 6.
- Bao gồm thời điểm bắt đầu, loại trừ thời điểm kết thúc: 03:00 được xét mua, 04:00 bị chặn.
- Hỗ trợ nhiều cửa sổ. Cửa sổ `23:00–02:00` được gắn với thứ của ngày bắt đầu. Giờ đầu bằng giờ cuối là lỗi; dùng `enabled: false` cho 24/7.
- Tín hiệu nến dùng giờ ĐÓNG nến: nến 02:55–03:00 được xét lúc 03:00. Callback kiểm tra lại giờ đặt lệnh thực tế.
- Chỉ hạn chế tạo lệnh mua mới. Lệnh limit đã đặt trước giờ kết thúc có thể khớp sau đó cho đến `unfilledtimeout.entry` (mặc định 10 phút). Hiện chưa có hủy tất cả lệnh mua đúng cuối phiên.
- Chốt lời, stoploss, trailing và force-exit vẫn hoạt động ngoài khung mua.

03:00–04:00 là cấu hình ví dụ theo yêu cầu, KHÔNG phải kết luận nghiên cứu. USDT thường là đồng định giá/vốn của BTC/USDT, ETH/USDT; không có một giờ tối ưu chung cho mọi cặp. Cần so sánh từng cặp, sàn, thứ trong tuần và giai đoạn thị trường, sau phí và trượt giá.

## 3. Pipeline thị trường và AI

Tiến trình `user_data/research/run.py` đọc cấu hình, tạo CCXT chỉ với quyền truy cập dữ liệu công khai, sau đó:

1. Chỉ xét danh sách cho phép, trừ regex blacklist; yêu cầu market đang active, Spot và quote USDT. Hỗ trợ Binance, OKX.
2. Lấy 260 nến 5 phút, ticker 24h và 5 mức orderbook. Loại nến chưa đóng, chuỗi thiếu/trùng/sai thứ tự và dữ liệu không hữu hạn.
3. Tính EMA20/50/200, RSI14 theo Wilder, biến động lợi suất log 5m trong 24 khoảng, thay đổi giá 1h, tỷ lệ volume so với 20 nến trước và spread theo mid-price. Thêm nhãn thị trường theo luật xu hướng/thanh khoản/biến động; đây không phải mô hình dự báo đã được huấn luyện. Giá đi ngang hoàn toàn được quy ước RSI = 50.
4. Phủ quyết kỹ thuật nếu xu hướng chưa tăng, volume 24h thấp, spread rộng hoặc biến động vượt giới hạn. Điểm 0–100 chỉ dùng sắp xếp, không là xác suất hay dự báo lợi nhuận.
5. Chỉ gửi các cặp qua bộ lọc kỹ thuật cho OpenAI/Gemini đã cấu hình. Không gửi số dư, vị thế hay khóa sàn. Không gọi AI trong callback giao dịch.
6. Chuẩn hóa `pair`, `action` (`consider`, `avoid`, `wait`), `confidence` trong [0,1] và lý do. Loại phản hồi lỗi, cặp ngoài danh sách, trùng cặp, NaN, từ chối hoặc bị cắt ngắn.
7. Ghi `latest.json` bằng replace nguyên tử và lưu lịch sử snapshot. Không ghi exception message từ upstream vì có thể chứa dữ liệu nhạy cảm. Lịch sử cần dọn theo chính sách lưu trữ của người vận hành.

Các chế độ `vn_policy.research.mode`:

| Chế độ | Snapshot thị trường ở dry-run/live | Vai trò AI |
| --- | --- | --- |
| `off` | Không yêu cầu | Không gọi AI; vẫn kiểm tra nến/spread/vốn tại chiến lược |
| `advisory` (mặc định) | Bắt buộc còn hạn và cặp qua bộ lọc kỹ thuật | Chỉ hiển thị, không quyết định quyền mua; không có API key vẫn chạy kỹ thuật |
| `required` | Bắt buộc còn hạn | Ít nhất `min_ai_votes` provider riêng biệt chọn `consider` đạt ngưỡng; bất kỳ `avoid` nào phủ quyết |

Không đủ đồng thuận thì đứng ngoài. Confidence do AI tự đánh giá, chưa được hiệu chỉnh xác suất. Nhiều AI có thể cùng sai và không được phép vượt qua bộ lọc kỹ thuật, lịch hoặc hạn mức vốn. `eligible: true` chỉ cho phép tiếp tục xét tín hiệu, không tự sinh lệnh mua.

Snapshot có phiên bản, sàn, thời gian tạo/hết hạn và SHA256 của cấu hình nghiên cứu + universe. Đổi sàn/model/ngưỡng/danh sách cần tạo snapshot mới. Callback từ chối snapshot tương lai, quá hạn, sai context, thiếu hoặc JSON hỏng. TTL mặc định 900 giây, worker cập nhật mỗi 300 giây; nếu cả vòng thu thập/AI chậm quá TTL, snapshot không được dùng.

## 4. Chính sách vốn và thực thi

`vn_policy.risk` mặc định:

| Tham số | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `risk_per_trade` | 0.005 | Ngân sách lỗ tính toán mỗi lệnh = 0,5% vốn stake |
| `max_position_fraction` | 0.20 | Một vị thế tối đa 20% vốn stake |
| `max_exposure_fraction` | 0.60 | Tổng stake các lệnh mở tối đa 60% vốn stake |
| `cost_buffer` | 0.004 | Dự phòng phí và trượt giá 0,4% trên stake |
| `max_entry_deviation` | 0.005 | Giá đề xuất lệch tối đa 0,5% so với nến đóng gần nhất |

Vốn lệnh = min(vốn đề xuất, vốn khả dụng do Freqtrade cấp, vốn × giới hạn vị thế, vốn × risk_per_trade / (|stoploss| + cost_buffer), phần hạn mức exposure còn lại).

Nếu thấp hơn minimum stake sàn: trả 0, bỏ lệnh; không nâng lên minimum làm vượt ngân sách. Callback kiểm tra lại để chống việc Freqtrade clamp hoặc làm tròn vượt hạn mức. Chỉ Spot long, không đòn bẩy/DCA. Các vị thế coin tương quan vẫn có thể cùng giảm; exposure cap không thay thế mô hình tương quan.

Ví dụ vốn stake 1.000 USDT, stoploss 3%, buffer 0,4%: stake theo rủi ro khoảng 147,06 USDT, rồi tiếp tục áp dụng các giới hạn còn lại. Equity ở đây là `wallets.get_total_stake_amount()` của Freqtrade, không phải bộ đánh dấu NAV mọi tài sản thời gian thực.

Trước mua trong dry-run/live: yêu cầu nến đóng không cũ quá 10 phút, giá không lệch quá ngưỡng, orderbook hợp lệ và spread không quá 0,2%. Bộ lọc không mô phỏng đầy đủ giá khớp theo kích thước lệnh. Stop-limit, gap giá, phí thay đổi và sự cố sàn có thể làm lỗ vượt ngân sách tính toán.

## 5. Chạy local và Docker

Mặc định vẫn `dry_run: true`, không có khóa sàn và không giao dịch tiền thật. Mật khẩu/JWT trong config là mẫu, phải thay trước khi cho máy khác truy cập.

Từ thư mục gốc dự án, chạy unit tests không gọi mạng:

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 -m unittest discover -s freqtrade-bot/tests -v
node tests/test_dashboard.js
node --check web-dashboard/app.js
docker compose -f freqtrade-bot/docker-compose.yml config --quiet
```

Python 3.12 có pandas dùng để kiểm tra callback với Freqtrade test doubles. Python không có pandas chỉ chạy core tests và skip callback tests. Các test này không thay thế kiểm thử tích hợp Freqtrade thật/TA-Lib/sàn.

Khởi chạy giả lập dashboard (không có khớp lệnh thật):

```powershell
python freqtrade-bot/mock_api_server.py
```

Mở `http://127.0.0.1:8080/dashboard`, nhập tài khoản mẫu và bấm kết nối. Mock có endpoint riêng `/api/v1/vn_research`: trả snapshot trên đĩa nếu có, hoặc dữ liệu giả đánh dấu `is_mock: true` để thử UI. Dữ liệu giả không được chiến lược chấp nhận. Có thể tải snapshot bằng ô chọn JSON mà không đăng nhập; dữ liệu tệp được render bằng textContent.

Chạy cả research và bot giả lập với giá công khai thật:

```powershell
cd freqtrade-bot
docker compose up -d
docker compose logs --tail 100 research freqtrade
```

Nếu dùng Python riêng, cài CCXT vào virtualenv và chạy worker; Freqtrade vẫn dùng môi trường theo yêu cầu upstream:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install ccxt
.venv/Scripts/python freqtrade-bot/user_data/research/run.py --loop 300
```

Freqtrade thật trao đổi với worker bằng tệp, không có endpoint research mở rộng. Để xem snapshot trên dashboard, lấy `user_data/research/latest.json` qua kênh riêng (SCP/VPN) rồi chọn tệp. Nút đồng bộ máy chủ chỉ hoạt động khi dùng mock. Android có thẻ tóm tắt nghiên cứu từ endpoint mock, kiểm tra TTL và đánh dấu dữ liệu giả; Freqtrade thật chưa có endpoint này. Dashboard tính trạng thái phiên theo lịch trong snapshot và đồng hồ trình duyệt; bot luôn kiểm tra bằng giờ máy chủ khi đặt lệnh.

Với Freqtrade thật, phục vụ dashboard riêng tại gốc dự án:

```powershell
python -m http.server 8090 --bind 127.0.0.1 --directory web-dashboard
```

Mở `http://127.0.0.1:8090`. CORS mẫu chỉ cho origin localhost:8090. Không dùng `*` khi deploy. Trong Docker để `listen_ip_address: 0.0.0.0` bên trong container và bind `127.0.0.1:8080:8080` ở host; muốn Android kết nối từ xa, bind IP Tailscale của host và giới hạn truy cập VPN.

### Bật AI

Copy `.env.example` thành `.env` trong `freqtrade-bot`, điền `OPENAI_API_KEY` / `GEMINI_API_KEY`. Các khóa này chỉ được truyền cho service research. ChatGPT qua API OpenAI là tích hợp riêng, cần quyền truy cập/billing API; tài khoản chat không tự tạo khóa API.

Đặt trong `vn_policy.research`:

```json
{
  "mode": "required",
  "providers": {
    "openai": "MODEL_ID_HO_TRO_STRUCTURED_OUTPUT_CUA_BAN",
    "gemini": "MODEL_ID_HO_TRO_STRUCTURED_OUTPUT_CUA_BAN"
  },
  "min_ai_votes": 2,
  "min_ai_confidence": 0.7
}
```

Đây là phần thay đổi bên trong khối research, giữ các ngưỡng thị trường còn lại. Thay MODEL_ID bằng model được tài khoản cho phép, hỗ trợ schema JSON. Không tự chọn model đắt tiền hoặc gọi API trả phí trong lần triển khai mã nguồn này. Có thể chỉ dùng một provider và `min_ai_votes: 1`. Nếu không có/không đúng khóa hoặc model, required sẽ không mua.

Sau sửa config/env: `docker compose up -d --force-recreate`. Mỗi provider được gọi tối đa một lần mỗi vòng khi có ứng viên kỹ thuật; timeout HTTP 25 giây, giới hạn output 4.000 token và response 1 MB. Không retry dồn trong cùng vòng; vòng tiếp theo thử lại. Đặt quota/budget ở nhà cung cấp theo nhu cầu.

### Chuyển Binance sang OKX

File `user_data/config-okx.json` là overlay, dùng SAU config gốc ở CẢ bot lẫn worker:

```powershell
docker compose run --rm freqtrade trade --config user_data/config.json --config user_data/config-okx.json --strategy VnSmartTrendStrategy
docker compose run --rm research --config /freqtrade/user_data/config.json --config /freqtrade/user_data/config-okx.json --loop 300
```

Hai lệnh chạy foreground riêng, không chạy song song hai bot dùng chung database. Khi dùng Compose lâu dài, sửa command cho cả hai service để cùng có overlay. Không đặt overlay OKX chỉ ở một phía: context không khớp sẽ chặn mua. Dry-run không cần private key; nếu về sau dùng private API OKX cần key, secret và passphrase (`exchange.password`) qua secrets riêng.

Binance mẫu dùng `stoploss: limit` và ratio 0,99; OKX overlay dùng market. Dry-run là khớp lệnh giả của Freqtrade trên dữ liệu công khai; không đồng nghĩa Binance Spot Testnet hoặc OKX Demo. Chưa cung cấp cấu hình kết nối testnet/demo trong bản này.

## 6. Kiểm chứng lợi thế theo giờ và hiệu quả AI

Không nạp snapshot AI hiện tại vào backtest quá khứ. Trong backtest/hyperopt, advisory/off bỏ qua snapshot và orderbook live; required bị từ chối. Vì vậy kết quả baseline lịch sử không chứng minh hiệu quả của bộ lọc AI/thanh khoản live. Lịch và sizing vẫn áp dụng theo thời gian mô phỏng.

Từ `freqtrade-bot`:

```powershell
docker compose run --rm freqtrade download-data --config user_data/config.json --days 365 --timeframes 5m
docker compose run --rm freqtrade backtesting --config user_data/config.json --strategy VnSmartTrendStrategy --fee 0.001 --enable-protections --export trades
docker compose run --rm freqtrade lookahead-analysis --config user_data/config.json --strategy VnSmartTrendStrategy --fee 0.001
docker compose run --rm freqtrade recursive-analysis --config user_data/config.json --strategy VnSmartTrendStrategy
```

Chạy các kỳ train/validation/test theo thứ tự thời gian; chọn giờ chỉ trên train, đánh giá một lần trên test chưa dùng, gồm bull/bear/sideways. So sánh 24/7 với 03–04 và các phiên khác bằng overlay cấu hình riêng. Tính phí thực của tài khoản mỗi chiều, trượt giá thận trọng, số giao dịch, expectancy, profit factor, max drawdown và tỷ lệ vốn tham gia. Hạn chế khung giờ có thể làm ít mẫu và giảm hiệu quả.

Công cụ tổng hợp theo giờ nhận CSV UTF-8 gồm `open_date` (ISO có timezone) và `profit_abs` (PnL ròng đã trừ phí/trượt giá):

```csv
open_date,profit_abs
2026-10-26T20:10:00+00:00,1.25
2026-10-26T20:45:00+00:00,-0.80
```

```powershell
python freqtrade-bot/user_data/research/hourly.py trades-net.csv --min-trades 30
```

Đây không phải parser JSON/ZIP của Freqtrade; cần xuất/chuyển các lệnh đóng sang CSV trước. Công cụ không tự trừ phí lần nữa. `profit_factor: null` khi không có lệnh lỗ, không kết luận vô hạn hay chắc chắn có lãi. Chia theo cặp/sàn bằng CSV riêng; 30 mẫu là ngưỡng cảnh báo sơ bộ, không đủ tự động xác nhận ý nghĩa thống kê.

Với AI: lưu snapshot theo đúng thời điểm, chạy forward dry-run đối chứng technical-only/advisory/required trên cùng giai đoạn, tính cả chi phí API. Đánh giá thêm tỷ lệ thiếu dữ liệu, API timeout, bỏ lỡ lệnh và độ ổn định. Chưa có engine replay lịch sử AI; không báo cáo performance AI trước khi có forward evidence.

## 7. Trạng thái bàn giao và giới hạn

- Có code lịch mua, sizing/exposure cap, kiểm tra nến/spread/deviation, worker phân tích dữ liệu công khai, adapter OpenAI Responses/Gemini, snapshot/history, tổng hợp giờ VN và bảng xem snapshot trên web.
- Có tests offline cho quy tắc, request/response provider bằng mock, worker với dữ liệu giả, callback chiến lược với pandas/test doubles và render báo cáo JS.
- Chưa có kết quả backtest thị trường thật, lợi nhuận AI, chạy dry-run dài ngày hay xác minh khớp lệnh/stoploss trên sàn. Docker Engine tại máy triển khai mã nguồn hiện chưa chạy; cần thực hiện bước tích hợp khi Engine sẵn sàng. Android mới được kiểm tra nguồn/XML; chưa build vì môi trường chưa có Gradle wrapper/Gradle và Android SDK. Không tự bật live trading.
- Chưa có news/macro calendar, sentiment có nguồn kiểm chứng, portfolio correlation optimizer, equity kill-switch theo ngày VN hoặc cơ chế duyệt tay từng đề xuất. Nhãn regime hiện tại chỉ theo quy tắc EMA/RSI/volume/spread. Các hạng mục tiếp theo cần dữ liệu và tiêu chí riêng, không coi như đã triển khai.
- Không thay chiến lược bằng lời khuyên AI, không tự mở rộng universe hay tắt protections từ AI. Mock server không được dùng cho tiền thật.

## 8. Nguồn kỹ thuật đã đối chiếu

- [Freqtrade Strategy callbacks](https://www.freqtrade.io/en/stable/strategy-callbacks/): hợp đồng callback sizing và xác nhận lệnh.
- [Freqtrade Stoploss](https://www.freqtrade.io/en/stable/stoploss/): ma trận loại stoploss và rủi ro stop-limit.
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs): Responses API với `text.format` JSON schema.
- [Gemini Interactions API](https://ai.google.dev/api/interactions-api) và [hướng dẫn thay đổi schema tháng 5/2026](https://ai.google.dev/gemini-api/docs/interactions-breaking-changes-may-2026): adapter dùng `/v1beta/interactions`, `Api-Revision: 2026-05-20`, `response_format` và đọc `steps` khi status completed; tương thích parser candidates của GenerateContent, không tự gọi endpoint thay thế.
- [Binance Spot API chính thức](https://github.com/binance/binance-spot-api-docs): filters và Testnet.
- [OKX API chính thức](https://www.okx.com/docs-v5/): Demo dùng `x-simulated-trading: 1`; không nhầm với Freqtrade dry-run.

Các nguồn trên xác nhận API/hành vi kỹ thuật, không xác nhận 03:00–04:00 có lợi thế sinh lời. Cần ghi lại image digest/phiên bản CCXT/Freqtrade khi hoàn tất kiểm thử tích hợp để lần chạy sau có thể tái lập.
