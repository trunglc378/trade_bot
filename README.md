# Dự Án Hệ Thống Giao Dịch Tiền Điện Tử Tự Động & Điều Khiển Từ Xa Tiếng Việt (FreqBot VN Remote)

> **Mô hình kiến trúc:** Đứng trên vai người khổng lồ — Lõi giao dịch tự động **Freqtrade (Headless Backend Engine)** kết hợp **Ứng dụng Android Điều khiển Từ xa 100% Tiếng Việt (`FreqBot VN Remote`)** & **Web Dashboard Tiếng Việt**.

---

## 1. Bối Cảnh & Mục Tiêu Dự Án

Thị trường tiền điện tử (Crypto) hoạt động liên tục 24/7 với biên độ dao động lớn, mang lại cơ hội gia tăng thu nhập nhưng cũng tiềm ẩn rủi ro cao nếu giao dịch cảm tính hoặc tự viết lại từ đầu các tầng kết nối sàn phức tạp (xử lý rớt mạng WebSocket, làm tròn `tickSize`/`stepSize`, đồng bộ lệnh khớp một phần `Partially Filled`, kiểm soát `Rate Limit`).

Dự án **FreqBot VN Remote** được xây dựng theo triết lý **"Đứng trên vai người khổng lồ"**:
1. **Sử dụng Freqtrade làm Lõi Xử Lý Ngầm (Headless Engine):** Tận dụng hệ thống giao dịch mã nguồn mở uy tín nhất thế giới (hơn 30.000 GitHub Stars) để đảm nhiệm toàn bộ tầng kết nối sàn qua `CCXT`, lưu trữ cơ sở dữ liệu `SQLite`, tính toán chỉ báo kỹ thuật (`pandas`, `TA-Lib`) và đặc biệt là lớp giáp bảo vệ rủi ro tự động (**Protections**: `MaxDrawdown`, `StoplossGuard`, `CooldownPeriod`, `LowProfitPairs`).
2. **Xây dựng Hệ Sinh Thái Điều Khiển 100% Tiếng Việt:**
   - **Ứng dụng di động Android (`FreqBot VN Remote` - Kotlin):** Giao tiếp trực tiếp với REST API của Freqtrade qua mạng riêng ảo an toàn (Tailscale/ZeroTier Mesh VPN), hiển thị trực quan bằng Tiếng Việt toàn bộ số dư, thống kê lãi/lỗ (PnL), danh sách lệnh đang mở, trạng thái giáp bảo vệ rủi ro, chạy ngầm (`WorkManager`) phát cảnh báo khi lỗ chạm ngưỡng và tích hợp nút **"Tạm dừng Mua mới"** cùng nút đỏ **"Cắt lỗ / Bán khẩn cấp (Panic Sell)"**.
   - **Giao diện Web Dashboard Tiếng Việt (`web-dashboard`):** Bảng điều khiển nhanh trên trình duyệt máy tính/điện thoại.
   - **Chiến lược Giao dịch Việt hóa (`VnSmartTrendStrategy.py`):** Chiến lược định lượng mẫu có tích hợp sẵn luồng thông báo đẩy bằng Tiếng Việt rõ ràng mỗi khi vào lệnh, chốt lời hoặc kích hoạt khóa rủi ro.

---

## 2. Kiến Trúc 5 Phân Hệ Chức Năng Cốt Lõi

Hệ thống tuân thủ kiến trúc hướng sự kiện (Event-Driven) gồm 5 phân hệ tách biệt rõ ràng:

| Phân hệ (Module) | Nhiệm vụ chính | Giải pháp kỹ thuật trong dự án |
| :--- | :--- | :--- |
| **1. Thu thập dữ liệu (Market Data Feed)** | Nhận giá thời gian thực, sổ lệnh (Orderbook) và dữ liệu nến (Kline/OHLCV) từ sàn. | Lõi Freqtrade + CCXT kết nối sàn (Binance/Bybit/OKX), tự động kết nối lại (Auto-reconnect) và đồng bộ thời gian chuẩn NTP (`Chrony`). |
| **2. Bộ não chiến lược (Strategy Engine)** | Phân tích dữ liệu đầu vào và phát tín hiệu giao dịch (`BUY`, `SELL`, `EXIT`, `HOLD`). | Module chiến lược Python (`VnSmartTrendStrategy.py`) tách biệt hoàn toàn khỏi code API sàn, dùng chung cho cả Backtest, Dry-Run và Live Trade. |
| **3. Quản trị rủi ro (Risk Management)** | Duyệt hoặc từ chối tín hiệu từ Strategy Engine trước khi cho phép đặt lệnh. | Kết hợp Hard Stop-Loss trên máy chủ sàn (`stoploss_on_exchange`) + Bộ 4 lớp giáp `Protections` (`MaxDrawdown`, `StoplossGuard`, `CooldownPeriod`, `LowProfitPairs`). |
| **4. Thực thi lệnh (Order Execution)** | Gửi lệnh lên sàn (Limit, Market), theo dõi trạng thái khớp lệnh (`Filled`, `Partially Filled`, `Canceled`). | Chuẩn hóa tự động `tickSize`, `stepSize`, `minNotional` qua CCXT và chống đặt trùng lệnh (Idempotency). |
| **5. Lưu trữ & Giám sát (State & Monitoring)** | Lưu lịch sử lệnh, số dư, trạng thái vị thế và điều khiển từ xa bằng Tiếng Việt. | Cơ sở dữ liệu SQLite (`tradesv3.sqlite`) + Máy chủ REST API nội bộ (`/api/v1/*`) + **App Android Tiếng Việt (`FreqBot VN Remote`)** & **Web Dashboard Tiếng Việt**. |

---

## 3. Cấu Trúc Thư Mục Toàn Dự Án

```text
e:\Project\trade_bot\
├── README.md                                   # Tổng quan dự án và chỉ mục tài liệu
├── docs/                                       # Bộ tài liệu kỹ thuật & quản lý dự án (Tiếng Việt)
│   ├── 01-GIOI-THIEU-DU-AN.md                  # Tài liệu Giới thiệu dự án chi tiết
│   ├── 02-KE-HOACH-DU-AN.md                    # Kế hoạch triển khai & Quy trình kiểm thử 3 bước
│   ├── 03-SRS-DAC-TA-YEU-CAU.md                # Đặc tả yêu cầu phần mềm (SRS)
│   ├── 04-SDS-THIET-KE-HE-THONG.md             # Đặc tả thiết kế hệ thống (SDS)
│   ├── 05-QUAN-TRI-RUI-RO-VA-BAO-MAT.md        # Thiết kế Lớp giáp Rủi ro & Bảo mật vận hành
│   ├── 06-HUONG-DAN-TRIEN-KHAI-VA-VAN-HANH.md  # Hướng dẫn cài đặt, chạy thử và vận hành thực tế
│   └── freqtrade-vi/                           # Bộ tài liệu Freqtrade chính thức đã Việt hóa
│       ├── 00-TONG-QUAN-FREQTRADE.md           # Tổng quan & Kiến trúc Freqtrade
│       ├── 01-CAI-DAT-VA-DOCKER.md             # Hướng dẫn cài đặt & Docker Quickstart
│       ├── 02-CAU-HINH-CONFIG.md               # Hướng dẫn cấu hình config.json toàn diện
│       ├── 03-XAY-DUNG-CHIEN-LUOC-STRATEGY.md  # Hướng dẫn lập trình chiến lược (IStrategy)
│       ├── 04-QUAN-TRI-RUI-RO-PROTECTIONS.md   # Cắt lỗ (Stoploss) & Giáp bảo vệ (Protections)
│       ├── 05-BACKTESTING-VA-HYPEROPT.md       # Kiểm thử lịch sử (Backtesting) & Tối ưu tham số
│       └── 06-REST-API-VA-WEBSOCKET.md         # Tài liệu REST API & WebSocket điều khiển Bot
├── freqtrade-bot/                              # Phân hệ Backend Lõi Freqtrade & Mock Server
│   ├── docker-compose.yml                      # Cấu hình Docker triển khai Freqtrade 24/7
│   ├── mock_api_server.py                      # Máy chủ giả lập API Freqtrade để test nhanh App Android/Web
│   └── user_data/
│       ├── config.json                         # Cấu hình Freqtrade (bật api_server, Protections, Dry-Run)
│       └── strategies/
│           └── VnSmartTrendStrategy.py         # Chiến lược giao dịch hoàn chỉnh + Cảnh báo Tiếng Việt
├── android-app/                                # Ứng dụng Android Điều khiển Từ xa (Kotlin)
│   ├── settings.gradle.kts
│   ├── build.gradle.kts
│   └── app/
│       ├── build.gradle.kts
│       └── src/main/
│           ├── AndroidManifest.xml
│           ├── java/com/freqbot/vnremote/
│           │   ├── data/model/TradeModels.kt   # Data classes ánh xạ JSON Freqtrade sang Tiếng Việt
│           │   ├── data/api/FreqtradeApi.kt    # Retrofit Interface gọi các Endpoint điều khiển Bot
│           │   ├── data/api/RetrofitClient.kt  # Quản lý HTTP Client, Basic Auth & Bearer JWT Token
│           │   ├── worker/RiskMonitorWorker.kt # WorkManager chạy ngầm cảnh báo rủi ro mỗi 15 phút
│           │   └── ui/
│           │       ├── MainActivity.kt         # Màn hình điều khiển chính & Nút Bán khẩn cấp
│           │       └── OpenTradeAdapter.kt     # RecyclerView Adapter hiển thị thẻ lệnh đang mở
│           └── res/                            # Giao diện XML Tiếng Việt (Layouts, Strings, Colors, Themes)
└── web-dashboard/                              # Giao diện Web Dashboard Tiếng Việt gọn nhẹ
    ├── index.html                              # Giao diện điều khiển Tiếng Việt trên trình duyệt
    ├── styles.css                              # Thiết kế giao diện Dark Mode chuẩn tài chính
    └── app.js                                  # Logic kết nối API Freqtrade & Bán khẩn cấp
```

---

## 4. Danh Mục Tài Liệu Dự Án

1. [01 - Giới Thiệu Dự Án](file:///e:/Project/trade_bot/docs/01-GIOI-THIEU-DU-AN.md)
2. [02 - Kế Hoạch Dự Án](file:///e:/Project/trade_bot/docs/02-KE-HOACH-DU-AN.md)
3. [03 - Đặc Tả Yêu Cầu Phần Mềm (SRS)](file:///e:/Project/trade_bot/docs/03-SRS-DAC-TA-YEU-CAU.md)
4. [04 - Đặc Tả Thiết Kế Hệ Thống (SDS)](file:///e:/Project/trade_bot/docs/04-SDS-THIET-KE-HE-THONG.md)
5. [05 - Quản Trị Rủi Ro & Bảo Mật Vận Hành](file:///e:/Project/trade_bot/docs/05-QUAN-TRI-RUI-RO-VA-BAO-MAT.md)
6. [06 - Hướng Dẫn Triển Khai & Vận Hành](file:///e:/Project/trade_bot/docs/06-HUONG-DAN-TRIEN-KHAI-VA-VAN-HANH.md)

### Bộ Tài Liệu Freqtrade Việt Hóa (`docs/freqtrade-vi/`)
- [00 - Tổng Quan Freqtrade](file:///e:/Project/trade_bot/docs/freqtrade-vi/00-TONG-QUAN-FREQTRADE.md)
- [01 - Cài Đặt & Docker Quickstart](file:///e:/Project/trade_bot/docs/freqtrade-vi/01-CAI-DAT-VA-DOCKER.md)
- [02 - Cấu Hình Hệ Thống (`config.json`)](file:///e:/Project/trade_bot/docs/freqtrade-vi/02-CAU-HINH-CONFIG.md)
- [03 - Xây Dựng Chiến Lược Giao Dịch (`IStrategy`)](file:///e:/Project/trade_bot/docs/freqtrade-vi/03-XAY-DUNG-CHIEN-LUOC-STRATEGY.md)
- [04 - Quản Trị Rủi Ro: Stoploss & Protections](file:///e:/Project/trade_bot/docs/freqtrade-vi/04-QUAN-TRI-RUI-RO-PROTECTIONS.md)
- [05 - Kiểm Thử Lịch Sử (Backtesting) & Tối Ưu Tham Số (Hyperopt)](file:///e:/Project/trade_bot/docs/freqtrade-vi/05-BACKTESTING-VA-HYPEROPT.md)
- [06 - Tài Liệu REST API & WebSocket Server](file:///e:/Project/trade_bot/docs/freqtrade-vi/06-REST-API-VA-WEBSOCKET.md)
