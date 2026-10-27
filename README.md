# Dự Án Hệ Thống Giao Dịch Tiền Điện Tử Tự Động, Phân Tích AI Đa Nguồn & Điều Khiển Từ Xa Tiếng Việt (FreqBot VN Remote)

> **Trạng thái triển khai 27/10/2026:** Xem [đặc tả và hướng dẫn 07](docs/07-LICH-GIAO-DICH-AI-VA-PHAN-TICH.md) để biết hành vi thực tế. Mặc định dry-run, AI tham khảo, chưa có provider/API key. 03:00–04:00 là giả thuyết cần backtest, chưa phải “giờ vàng” đã được chứng minh. Worker có RSI14 và nhãn regime theo luật; Android có thẻ nghiên cứu qua mock, chưa có endpoint tương ứng trên Freqtrade thật; web đọc tệp, có thể đồng bộ qua endpoint riêng của mock. Tên model cần cấu hình theo quyền truy cập tài khoản. Chưa có kết quả lợi nhuận hoặc kiểm thử khớp lệnh thật.

Kiểm tra từ thư mục gốc: `py -3.12 -m unittest discover -s tests -v` và `node tests/test_dashboard.js`. Chạy pipeline giả lập bằng `docker compose up -d` trong `freqtrade-bot` khi Docker Engine sẵn sàng. Cấu hình, cách bật AI và quy trình kiểm chứng nằm trong tài liệu 07.

> **Mô hình kiến trúc:** Đứng trên vai người khổng lồ — Lõi giao dịch tự động **Freqtrade (Headless Backend Engine trên Binance & OKX)** kết hợp **Bộ lọc Khung Giờ Cấu Hình (03:00–04:00 VN)**, **Trợ lý Phân tích Thị trường & Đề xuất Coin Đa nguồn AI (ChatGPT + Google Gemini)** cùng **Ứng dụng Android (`FreqBot VN Remote`) & Web Dashboard 100% Tiếng Việt**.

---

## 1. Bối Cảnh & Mục Tiêu Dự Án

Thị trường tiền điện tử (Crypto) hoạt động liên tục 24/7 với biên độ dao động lớn, mang lại cơ hội gia tăng lợi nhuận nhưng cũng tiềm ẩn rủi ro cao nếu giao dịch cảm tính, vào lệnh vào các khung giờ nhiễu thanh khoản hoặc tự viết lại từ đầu các tầng kết nối sàn phức tạp (xử lý rớt mạng WebSocket, làm tròn `tickSize`/`stepSize`, đồng bộ lệnh khớp một phần `Partially Filled`, kiểm soát `Rate Limit`).

Dự án **FreqBot VN Remote (Phiên bản 2.0)** được xây dựng nhằm tối ưu hóa lợi nhuận và hạn chế tối đa rủi ro giao dịch cho nhà đầu tư thông qua 4 trụ cột:
1. **Lõi Xử Lý Ngầm Freqtrade Đa Sàn (Binance & OKX):** Tận dụng hệ thống giao dịch mã nguồn mở uy tín nhất thế giới để đảm nhiệm tầng kết nối sàn qua `CCXT`, lưu trữ cơ sở dữ liệu `SQLite`, tính toán chỉ báo kỹ thuật (`EMA 20/50/200`, `RSI 14`, `Bollinger Bands`, `Volume`) và lớp giáp bảo vệ rủi ro tự động (**Protections**: `MaxDrawdown`, `StoplossGuard`, `CooldownPeriod`, `LowProfitPairs`).
2. **Chiến Lược Tập Trung Khung Giờ Giao Dịch Vàng (`vn_policy.schedule`):**
   - Cho phép cấu hình tập trung mở vị thế mua mới vào các khung giờ cấu hình theo múi giờ Việt Nam (`Asia/Ho_Chi_Minh`, mặc định **03:00 – 04:00 sáng** cho các cặp `*/USDT` để kiểm chứng bằng backtest, không mặc định có lợi thế thanh khoản).
   - **Cơ chế Bất đối xứng An toàn Vốn:** Khung giờ chỉ khóa chiều **Mua mới (`enter_long`)** ngoài giờ; trong khi việc **Canh chốt lời (`ROI` / `Trailing Stop`), Cắt lỗ cứng trên sàn (`Hard Stop-Loss`) và Bán khẩn cấp (`Panic Sell`)** vẫn hoạt động **24/7**.
3. **Phân Hệ Phân Tích Thị Trường & Đề Xuất Coin Đa Nguồn AI (`ChatGPT` + `Gemini`):**
   - Tiến trình nghiên cứu độc lập (`freqtrade-bot/user_data/research/run.py` & `providers.py`) quét toàn bộ danh sách coin trên **Binance / OKX**, chấm điểm kỹ thuật (`0–100`), phân loại trạng thái thị trường (`Market Regime`), kiểm tra thanh khoản 24h, độ giãn `Bid-Ask Spread`, biến động 1h và `RSI(14)`.
   - Tham vấn đồng thời các mô hình AI hàng đầu (**OpenAI ChatGPT** và **Google Gemini model hỗ trợ structured output do tài khoản cho phép**) qua cấu trúc JSON Schema nghiêm ngặt (`consider` / `avoid` / `wait` + độ tự tin `confidence` + giải thích Tiếng Việt).
   - Cơ chế **Bỏ phiếu Đồng thuận & Quyền Phủ quyết (`AI Quorum & Veto`)** kết hợp mã băm ngữ cảnh `SHA-256` (`context_id`) và thời hạn hiệu lực (`TTL`), tự động chặn mở lệnh nếu bất kỳ AI nào cảnh báo `avoid` hoặc báo cáo quá hạn.
4. **Hệ Sinh Thái Điều Khiển Từ Xa 100% Tiếng Việt (`Android App` & `Web Dashboard`):**
   - **Ứng dụng di động Android (`FreqBot VN Remote` - Kotlin):** Hiển thị trực quan bằng Tiếng Việt số dư, thống kê lãi/lỗ (PnL), trạng thái khung giờ giao dịch, bảng đề xuất coin từ AI (ChatGPT/Gemini), danh sách lệnh đang mở, trạng thái giáp bảo vệ rủi ro, chạy ngầm (`WorkManager`) phát cảnh báo và tích hợp nút **"Tạm dừng Mua mới"** cùng nút đỏ **"Cắt lỗ / Bán khẩn cấp (Panic Sell)"**.
   - **Giao diện Web Dashboard Tiếng Việt (`web-dashboard`):** Bảng điều khiển trực tuyến kèm bảng theo dõi Điểm kỹ thuật & Nhận định AI thời gian thực.

---

## 2. Kiến Trúc 6 Phân Hệ Chức Năng Cốt Lõi

Hệ thống tuân thủ kiến trúc hướng sự kiện (Event-Driven) gồm 6 phân hệ tách biệt rõ ràng:

| Phân hệ (Module) | Nhiệm vụ chính | Giải pháp kỹ thuật trong dự án |
| :--- | :--- | :--- |
| **1. Thu thập dữ liệu (Market Data Feed)** | Nhận giá thời gian thực, sổ lệnh (Orderbook) và dữ liệu nến (Kline/OHLCV) từ sàn **Binance & OKX**. | Lõi Freqtrade + CCXT kết nối sàn (Binance/OKX), tự động kết nối lại (Auto-reconnect) và đồng bộ thời gian chuẩn NTP (`Chrony`). |
| **2. Nghiên cứu Thị trường & Cố vấn AI (Market Research & Multi-AI Advisor)** | Sàng lọc định lượng, chấm điểm coin (0–100) và tổng hợp đề xuất từ **ChatGPT + Gemini**. | Dịch vụ đọc độc lập `research/run.py` + `providers.py`, xuất bản chụp `latest.json` có gắn mã băm ngữ cảnh `SHA-256` và thời hạn `TTL`. |
| **3. Bộ não chiến lược & Bộ lọc Khung giờ (Strategy & Session Engine)** | Phân tích chỉ báo kỹ thuật, lọc khung giờ cấu hình (`03:00–04:00 VN`) và phát tín hiệu (`BUY`, `SELL`, `HOLD`). | Module chiến lược [`VnSmartTrendStrategy.py`](file:///d:/Project/trade_bot/freqtrade-bot/user_data/strategies/VnSmartTrendStrategy.py) + [`vn_support.py`](file:///d:/Project/trade_bot/freqtrade-bot/user_data/strategies/vn_support.py) dùng chung cho Backtest, Dry-Run và Live Trade. |
| **4. Quản trị rủi ro đa tầng (Multi-Layer Risk Management)** | Tính toán khối lượng vốn động theo rủi ro (`stake_size`), kiểm tra Spread/Slippage và duyệt lệnh. | Hard Stop-Loss trên sàn (`stoploss_on_exchange`) + Bộ 4 lớp giáp `Protections` + Giới hạn rủi ro `0.5%–2%` vốn/lệnh & tổng phơi nhiễm `60%`. |
| **5. Thực thi lệnh (Order Execution)** | Gửi lệnh lên sàn (Limit, Market), theo dõi trạng thái khớp lệnh (`Filled`, `Partially Filled`, `Canceled`). | Chuẩn hóa tự động `tickSize`, `stepSize`, `minNotional` qua CCXT và chống đặt trùng lệnh (Idempotency). |
| **6. Lưu trữ & Giám sát (State & Monitoring)** | Lưu lịch sử lệnh, số dư, báo cáo AI và điều khiển từ xa bằng Tiếng Việt. | Cơ sở dữ liệu SQLite (`tradesv3.sqlite`) + REST API (`/api/v1/*`) + **App Android Tiếng Việt** & **Web Dashboard Tiếng Việt**. |

---

## 3. Cấu Trúc Thư Mục Toàn Dự Án

```text
d:\Project\trade_bot\
├── README.md                                   # Tổng quan dự án và chỉ mục tài liệu
├── docs/                                       # Bộ tài liệu kỹ thuật & quản lý dự án (Tiếng Việt)
│   ├── 01-GIOI-THIEU-DU-AN.md                  # Tài liệu Giới thiệu dự án chi tiết
│   ├── 02-KE-HOACH-DU-AN.md                    # Kế hoạch triển khai & Quy trình kiểm thử 3 bước
│   ├── 03-SRS-DAC-TA-YEU-CAU.md                # Đặc tả yêu cầu phần mềm (SRS)
│   ├── 04-SDS-THIET-KE-HE-THONG.md             # Đặc tả thiết kế hệ thống (SDS)
│   ├── 05-QUAN-TRI-RUI-RO-VA-BAO-MAT.md        # Thiết kế Lớp giáp Rủi ro, Khung giờ & Bảo mật AI
│   ├── 06-HUONG-DAN-TRIEN-KHAI-VA-VAN-HANH.md  # Hướng dẫn cài đặt Binance/OKX, AI Advisor & Vận hành
│   └── freqtrade-vi/                           # Bộ tài liệu Freqtrade chính thức đã Việt hóa
├── freqtrade-bot/                              # Phân hệ Backend Lõi Freqtrade, AI Research & Mock Server
│   ├── .env.example                            # Mẫu biến môi trường chứa khóa OPENAI_API_KEY & GEMINI_API_KEY
│   ├── docker-compose.yml                      # Cấu hình Docker chạy song song Freqtrade + AI Research Worker
│   ├── mock_api_server.py                      # Máy chủ giả lập API Freqtrade + AI Research để test nhanh UI
│   ├── tests/
│   │   └── test_research.py                   # Bộ kiểm thử tự động Khung giờ VN, Vốn động & Đồng thuận AI
│   └── user_data/
│       ├── config.json                         # Cấu hình chuẩn cho sàn Binance + Chính sách vn_policy
│       ├── config-okx.json                     # Cấu hình mở rộng cho sàn OKX Spot USDT
│       ├── research/
│       │   ├── providers.py                    # Kết nối OpenAI (ChatGPT) & Google Gemini với JSON Schema
│       │   └── run.py                          # Bộ phân tích kỹ thuật, chấm điểm coin & tổng hợp phiếu bầu AI
│       └── strategies/
│           ├── vn_support.py                   # Lõi kiểm tra Khung giờ VN (03:00-04:00), Vốn động & Báo cáo AI
│           └── VnSmartTrendStrategy.py         # Chiến lược giao dịch hoàn chỉnh + Cảnh báo Tiếng Việt
├── android-app/                                # Ứng dụng Android Điều khiển Từ xa (Kotlin)
└── web-dashboard/                              # Giao diện Web Dashboard Tiếng Việt + Bảng Phân tích AI
```

---

## 4. Danh Mục Tài Liệu Dự Án

1. [01 - Giới Thiệu Dự Án](file:///d:/Project/trade_bot/docs/01-GIOI-THIEU-DU-AN.md)
2. [02 - Kế Hoạch Dự Án](file:///d:/Project/trade_bot/docs/02-KE-HOACH-DU-AN.md)
3. [03 - Đặc Tả Yêu Cầu Phần Mềm (SRS)](file:///d:/Project/trade_bot/docs/03-SRS-DAC-TA-YEU-CAU.md)
4. [04 - Đặc Tả Thiết Kế Hệ Thống (SDS)](file:///d:/Project/trade_bot/docs/04-SDS-THIET-KE-HE-THONG.md)
5. [05 - Quản Trị Rủi Ro & Bảo Mật Vận Hành](file:///d:/Project/trade_bot/docs/05-QUAN-TRI-RUI-RO-VA-BAO-MAT.md)
6. [06 - Hướng Dẫn Triển Khai & Vận Hành](file:///d:/Project/trade_bot/docs/06-HUONG-DAN-TRIEN-KHAI-VA-VAN-HANH.md)

### Bộ Tài Liệu Freqtrade Việt Hóa (`docs/freqtrade-vi/`)
- [00 - Tổng Quan Freqtrade](file:///d:/Project/trade_bot/docs/freqtrade-vi/00-TONG-QUAN-FREQTRADE.md)
- [01 - Cài Đặt & Docker Quickstart](file:///d:/Project/trade_bot/docs/freqtrade-vi/01-CAI-DAT-VA-DOCKER.md)
- [02 - Cấu Hình Hệ Thống (`config.json`)](file:///d:/Project/trade_bot/docs/freqtrade-vi/02-CAU-HINH-CONFIG.md)
- [03 - Xây Dựng Chiến Lược Giao Dịch (`IStrategy`)](file:///d:/Project/trade_bot/docs/freqtrade-vi/03-XAY-DUNG-CHIEN-LUOC-STRATEGY.md)
- [04 - Quản Trị Rủi Ro: Stoploss & Protections](file:///d:/Project/trade_bot/docs/freqtrade-vi/04-QUAN-TRI-RUI-RO-PROTECTIONS.md)
- [05 - Kiểm Thử Lịch Sử (Backtesting) & Tối Ưu Tham Số (Hyperopt)](file:///d:/Project/trade_bot/docs/freqtrade-vi/05-BACKTESTING-VA-HYPEROPT.md)
- [06 - Tài Liệu REST API & WebSocket Server](file:///d:/Project/trade_bot/docs/freqtrade-vi/06-REST-API-VA-WEBSOCKET.md)
