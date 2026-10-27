# ĐẶC TẢ THIẾT KẾ HỆ THỐNG (SOFTWARE DESIGN SPECIFICATION - SDS)
**Tên dự án:** Hệ thống Giao dịch Tiền điện tử Tự động & Ứng dụng Điều khiển Từ xa Tiếng Việt (**FreqBot VN Remote**)  
**Phiên bản:** 1.0.0  
**Ngày lập:** 27/10/2026  

---

## 1. Thiết Kế Kiến Trúc Tổng Thể (System Architecture)

Hệ thống được thiết kế theo mô hình **Client-Server phân tán kết hợp Kiến trúc hướng sự kiện (Event-Driven Architecture)**:
- **Server-side (Headless Trading Engine):** Lõi **Freqtrade** đóng gói trong Docker Container, tích hợp chiến lược Python [`VnSmartTrendStrategy.py`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/strategies/VnSmartTrendStrategy.py), cơ sở dữ liệu `SQLite` và máy chủ `FastAPI/REST API` nội bộ cổng `8080`.
- **Client-side (Vietnamese Remote Controllers):**
  1. **Ứng dụng Android Native (`FreqBot VN Remote` - Kotlin):** Sử dụng kiến trúc phân tầng rõ ràng (`ui`, `data/api`, `data/model`, `worker`), giao tiếp bất đồng bộ qua `Retrofit2 + OkHttp3 + Kotlin Coroutines`, giám sát ngầm bằng `WorkManager`.
  2. **Ứng dụng Web Dashboard Tiếng Việt (`web-dashboard`):** Giao diện SPA gọn nhẹ viết bằng HTML5/CSS3/Vanilla JS gọi trực tiếp vào REST API của Freqtrade.

```mermaid
flowchart TB
    subgraph ExchangeLayer["Tầng Sàn Giao Dịch (Binance / Bybit / OKX)"]
        EX_REST["REST API (Lịch sử nến, Đặt/Hủy lệnh)"]
        EX_WS["WebSocket Stream (Giá & Sổ lệnh thời gian thực)"]
    end

    subgraph CoreEngine["Tầng Lõi Giao Dịch Ngầm (Freqtrade Engine - Docker)"]
        MDF["1. Market Data Feed\n(CCXT + DataProvider)"]
        STE["2. Strategy Engine\n(VnSmartTrendStrategy.py)"]
        RKM["3. Risk Management\n(StoplossGuard, MaxDrawdown,\nHard Stop-Loss)"]
        OEX["4. Order Execution\n(Tick/Step Size Normalizer)"]
        SAM["5. State & API Server\n(SQLite + FastAPI Port 8080)"]
    end

    subgraph AndroidApp["Ứng Dụng Android (com.freqbot.vnremote)"]
        UI_MAIN["MainActivity.kt\n(Bảng điều khiển Tiếng Việt)"]
        UI_ADAPTER["OpenTradeAdapter.kt\n(RecyclerView Thẻ lệnh mở)"]
        WORKER["RiskMonitorWorker.kt\n(WorkManager chạy ngầm 15p)"]
        RETROFIT["RetrofitClient.kt & FreqtradeApi.kt\n(JWT Interceptor)"]
        MODELS["TradeModels.kt\n(Gson Data Classes)"]
    end

    subgraph WebApp["Web Dashboard Tiếng Việt (web-dashboard)"]
        WEB_UI["index.html + styles.css"]
        WEB_JS["app.js (Fetch API + JWT)"]
    end

    EX_WS --> MDF
    EX_REST <--> MDF
    MDF --> STE
    STE --> RKM
    RKM --> OEX
    OEX <--> EX_REST
    OEX <--> SAM
    RKM <--> SAM

    SAM <==>|"HTTP/JSON qua Tailscale VPN\n(Basic Auth & Bearer JWT)"| RETROFIT
    RETROFIT --> MODELS
    RETROFIT --> UI_MAIN
    UI_MAIN --> UI_ADAPTER
    RETROFIT --> WORKER

    SAM <==>|"HTTP/JSON"| WEB_JS
    WEB_JS --> WEB_UI
```

---

## 2. Thiết Kế Luồng Tương Tác & Xử Lý Sự Kiện (Sequence Diagrams)

### 2.1. Luồng xử lý tín hiệu giao dịch và kiểm duyệt rủi ro qua 5 phân hệ

```mermaid
sequenceDiagram
    autonumber
    participant Sàn as Sàn Giao Dịch (Binance)
    participant MDF as 1. Market Data Feed
    participant STE as 2. Strategy Engine (VnSmartTrend)
    participant RKM as 3. Risk Management (Protections)
    participant OEX as 4. Order Execution
    participant SAM as 5. State & Monitoring (SQLite/API)

    Sàn->>MDF: Đẩy dữ liệu nến mới (OHLCV) & Orderbook
    MDF->>STE: Cung cấp DataFrame đã chuẩn hóa
    STE->>STE: Tính EMA20/50, RSI, Bollinger Bands, Volume
    STE->>RKM: Phát tín hiệu MUA (enter_long, tag="EMA_RSI_BREAKOUT")
    alt Đang bị khóa bởi Protections (MaxDrawdown / StoplossGuard) hoặc đầy max_open_trades
        RKM-->>STE: TỪ CHỐI LỆNH (Veto Signal)
        RKM->>SAM: Ghi nhận trạng thái khóa vào bảng PairLocks
    else Đủ điều kiện an toàn vốn & Spread hợp lệ
        RKM->>OEX: Duyệt lệnh + Cấp vốn (stake_amount)
        OEX->>OEX: Chuẩn hóa giá (tickSize) & khối lượng (stepSize, minNotional)
        OEX->>Sàn: Gửi lệnh Mua + Gắn Hard Stop-Loss trên sàn
        Sàn-->>OEX: Xác nhận khớp lệnh (Order Filled)
        OEX->>SAM: Lưu vị thế mở vào SQLite (tradesv3.sqlite)
        STE->>SAM: Gửi thông báo Tiếng Việt (confirm_trade_entry)
    end
```

### 2.2. Luồng Đăng nhập JWT, Đồng bộ thời gian thực & Bán khẩn cấp (Panic Sell) từ App Android

```mermaid
sequenceDiagram
    autonumber
    actor User as Người Vận Hành (App Android)
    participant UI as MainActivity.kt
    participant API as RetrofitClient / FreqtradeApi
    participant Bot as Freqtrade API Server (:8080)
    participant Sàn as Sàn Giao Dịch

    User->>UI: Mở ứng dụng FreqBot VN Remote
    UI->>API: dangNhap("Basic base64(user:pass)")
    API->>Bot: POST /api/v1/token/login
    Bot-->>API: 200 OK {"access_token": "eyJ...", "refresh_token": "..."}
    API->>API: Lưu jwtToken vào Interceptor

    loop Mỗi 5 giây khi mở App (lifecycleScope)
        UI->>API: Gọi song song: /profit, /balance, /status, /locks
        API->>Bot: GET /api/v1/profit, /balance, /status, /locks (Header: Bearer JWT)
        Bot-->>API: Trả về JSON dữ liệu thực tế
        API-->>UI: Ánh xạ sang TradeModels.kt & hiển thị Tiếng Việt
    end

    User->>UI: Bấm nút đỏ "BÁN KHẨN CẤP TOÀN BỘ (PANIC SELL)"
    UI->>User: Hiển thị AlertDialog xác nhận chống bấm nhầm
    User->>UI: Nhấn "ĐỒNG Ý BÁN HẾT"
    UI->>API: banKhanCap(ForceExitRequest(tradeId="all", orderType="market"))
    API->>Bot: POST /api/v1/forceexit {"tradeid": "all", "ordertype": "market"}
    Bot->>Sàn: Hủy lệnh chờ & Bán Market toàn bộ vị thế đang mở
    Sàn-->>Bot: Khớp lệnh bán thu hồi USDT
    Bot-->>API: 200 OK {"status": "Đã đóng toàn bộ lệnh"}
    API-->>UI: Hiển thị Toast Tiếng Việt & cập nhật lại bảng lệnh
```

---

## 3. Thiết Kế Cơ Sở Dữ Liệu (Database Design - ERD)

Lõi Freqtrade sử dụng cơ sở dữ liệu quan hệ **SQLite (`tradesv3.sqlite`)** thông qua SQLAlchemy ORM với 3 bảng thực thể cốt lõi phục vụ giao dịch và quản trị rủi ro:

```mermaid
erDiagram
    TRADES ||--o{ ORDERS : "co_nhieu_lenh_san"
    TRADES {
        int id PK "Mã lệnh (trade_id)"
        string exchange "Sàn giao dịch (binance)"
        string pair "Cặp giao dịch (BTC/USDT)"
        boolean is_open "Đang mở (true/false)"
        float stake_amount "Vốn vào lệnh (USDT)"
        float amount "Khối lượng coin"
        float open_rate "Giá mua vào"
        float close_rate "Giá bán ra"
        float close_profit "Tỷ lệ lãi/lỗ khi đóng"
        float close_profit_abs "Lãi/lỗ tuyệt đối (USDT)"
        float stop_loss "Giá cắt lỗ hiện tại (stop_loss_abs)"
        float initial_stop_loss "Giá cắt lỗ ban đầu"
        string strategy "Tên chiến lược (VnSmartTrendStrategy)"
        string enter_tag "Lý do mua (enter_tag)"
        string exit_reason "Lý do thoát lệnh (exit_reason)"
        datetime open_date "Thời gian mở lệnh"
        datetime close_date "Thời gian đóng lệnh"
    }

    ORDERS {
        int id PK "Mã bản ghi"
        int ft_trade_id FK "Liên kết tới TRADES.id"
        string order_id "Order ID trên sàn"
        string ft_pair "Cặp coin"
        string ft_order_side "Chiều lệnh (buy/sell/stoploss)"
        string order_type "Loại lệnh (limit/market/stop_loss_limit)"
        string status "Trạng thái (open/closed/canceled)"
        float price "Giá đặt"
        float average "Giá khớp trung bình"
        float amount "Khối lượng đặt"
        float filled "Khối lượng đã khớp"
        datetime order_date "Thời gian tạo lệnh"
    }

    PAIRLOCKS {
        int id PK "Mã khóa bảo vệ"
        string pair "Cặp bị khóa ('*' là khóa toàn bộ Bot)"
        string reason "Lý do khóa (MaxDrawdown, StoplossGuard...)"
        datetime lock_time "Thời điểm bắt đầu khóa"
        datetime lock_end_time "Thời điểm mở khóa"
        boolean active "Đang hiệu lực (true/false)"
    }
```

---

## 4. Thiết Kế Chi Tiết Phân Hệ Chiến Lược Backend (`VnSmartTrendStrategy.py`)

File chiến lược [`VnSmartTrendStrategy.py`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/strategies/VnSmartTrendStrategy.py) kế thừa lớp `IStrategy` của Freqtrade và được thiết kế gồm 5 khối:
1. **Tham số quản trị rủi ro & ROI động (`minimal_roi`, `stoploss`, `trailing_stop`):**
   - `stoploss = -0.03` (Cắt lỗ cứng ở mức `-3%` cho mỗi vị thế).
   - `trailing_stop = True`, `trailing_stop_positive = 0.01`, `trailing_stop_positive_offset = 0.025` (Khi lệnh lãi đạt `+2.5%`, tự động dịch chuyển mốc cắt lỗ trượt theo sau `1%` để khóa lợi nhuận).
2. **Cấu hình Bộ Giáp Bảo Vệ (`protections` property):**
   - `CooldownPeriod`: Khóa cặp coin 30 phút sau khi vừa đóng lệnh.
   - `MaxDrawdown`: Nếu lỗ thực tế vượt `5%` trong 24 giờ gần nhất, khóa toàn bộ bot trong `12 giờ`.
   - `StoplossGuard`: Nếu dính `3 lệnh` cắt lỗ trong vòng `6 giờ`, khóa toàn bộ bot trong `6 giờ`.
   - `LowProfitPairs`: Nếu 1 cặp coin có từ 2 lệnh đóng với tổng lỗ `<= -3%` trong 12 giờ, tạm khóa riêng cặp coin đó 6 giờ.
3. **Tính toán chỉ báo (`populate_indicators`):**
   - Đường trung bình động `EMA 20`, `EMA 50`, `EMA 200`.
   - Chỉ số sức mạnh tương đối `RSI (14)`.
   - Dải `Bollinger Bands (20, 2.0)`.
   - Khối lượng giao dịch trung bình `Volume SMA (20)`.
4. **Quy tắc vào lệnh (`populate_entry_trend`) & Thoát lệnh (`populate_exit_trend`):**
   - **Tín hiệu Mua 1 (`XU_HUONG_TANG_EMA_RSI`):** Xu hướng chính tăng (`close > EMA200`, `EMA20 > EMA50`), `RSI` nằm trong vùng tích lũy khỏe (`45 < RSI < 68`) và khối lượng đột biến (`volume > 1.2 * volume_mean_20`).
   - **Tín hiệu Mua 2 (`BAT_DAY_BOLLINGER_RSI`):** Giá chạm dải dưới Bollinger (`close < bb_lowerband * 1.005`) trong khi `RSI < 32` và bắt đầu rút chân tăng trở lại (`close > open`).
   - **Tín hiệu Bán (`CHOT_LOI_QUA_MUA_RSI` / `GA_Y_XU_HUONG_EMA`):** Khi `RSI > 78` chạm dải trên Bollinger hoặc `EMA20` cắt xuống dưới `EMA50`.
5. **Hàm Callback Việt hóa thông báo đẩy (`confirm_trade_entry`, `confirm_trade_exit`):**
   - Phát tin nhắn định dạng Tiếng Việt qua `self.dp.send_msg(...)` mỗi khi vào lệnh hoặc đóng lệnh.

---

## 5. Thiết Kế Chi Tiết Ứng Dụng Android (`com.freqbot.vnremote`)

### 5.1. Sơ đồ Lớp (Class Diagram) của Ứng dụng Android

```mermaid
classDiagram
    class TradeModels {
        +TokenResponse(accessToken, refreshToken)
        +ProfitSummary(tongLaiUsdt, phanTramLaiTong, tongSoLenh, soLenhThang, soLenhThua, sutGiamToiDa)
        +BalanceResponse(currencies, tongTaiSanUsdt, kyHieuTienTe)
        +OpenTrade(maLenh, capCoin, vonVaoLenh, giaMua, giaHienTai, tyLeLaiLo, laiLoUsdt, giaCatLo, thoiGianMo, lyDoMua)
        +ProtectionLocksResponse(soKhoaDangBat, danhSachKhoa)
        +ForceExitRequest(tradeId, orderType)
        +StatusMsgResponse(trangThai)
    }

    class FreqtradeApi {
        <<interface>>
        +dangNhap(basicAuth) TokenResponse
        +layThongKeLoiNhuan() ProfitSummary
        +laySoDuTaiKhoan() BalanceResponse
        +layDanhSachLenhDangMo() List~OpenTrade~
        +kiemTraKhoaRuiRo() ProtectionLocksResponse
        +tamDungMuaMoi() StatusMsgResponse
        +khoiDongLaiBot() StatusMsgResponse
        +banKhanCap(request) StatusMsgResponse
    }

    class RetrofitClient {
        -baseUrl: String
        +jwtToken: String?
        +taoChuoiBasicAuth(user, pass) String
        +getApi(serverUrl) FreqtradeApi
        +luuCauHinh(context, url, user, pass)
        +docCauHinh(context) ServerConfig
    }

    class OpenTradeAdapter {
        -dsLenh: List~OpenTrade~
        -onForceExitClick: (OpenTrade) -> Unit
        +capNhatDuLieu(dsMoi)
    }

    class MainActivity {
        -adapter: OpenTradeAdapter
        +onCreate(savedInstanceState)
        -khoiDongKetNoiVaCapNhat()
        -taiDuLieuBangDieuKhien()
        -hienThiHopThoaiBanKhanCapToanBo()
        -hienThiHopThoaiDongMotLenh(trade)
        -hienThiHopThoaiCauHinhMayChu()
        -kichHoatGiamSatNgam()
    }

    class RiskMonitorWorker {
        +doWork() Result
        -phatThongBaoCanhBao(tieuDe, noiDung)
    }

    MainActivity --> RetrofitClient
    MainActivity --> OpenTradeAdapter
    MainActivity --> RiskMonitorWorker
    RetrofitClient --> FreqtradeApi
    FreqtradeApi --> TradeModels
    OpenTradeAdapter --> TradeModels
    RiskMonitorWorker --> RetrofitClient
```

### 5.2. Thiết kế Cơ chế Chạy ngầm & Cảnh báo (`RiskMonitorWorker.kt`)
- Sử dụng `PeriodicWorkRequestBuilder<RiskMonitorWorker>(15, TimeUnit.MINUTES)` với điều kiện `NetworkType.CONNECTED`.
- Trong `doWork()`:
  1. Đọc thông tin cấu hình máy chủ (`baseUrl`, `username`, `password`) từ `SharedPreferences`.
  2. Gọi API đăng nhập lấy `jwtToken` mới nhất, sau đó truy vấn `/api/v1/status` và `/api/v1/locks`.
  3. Kiểm tra nếu có bất kỳ lệnh nào có `tyLeLaiLo <= -0.03` (lỗ từ `3%` trở lên) hoặc `soKhoaDangBat > 0` (đang kích hoạt khóa rủi ro), lập tức tạo kênh thông báo `NotificationChannel` mức ưu tiên cao (`IMPORTANCE_HIGH`) và phát cảnh báo Tiếng Việt lên điện thoại.
  4. Nếu không thể kết nối tới máy chủ VPS, phát thông báo cảnh báo kiểm tra kết nối mạng/VPS và trả về `Result.retry()`.
