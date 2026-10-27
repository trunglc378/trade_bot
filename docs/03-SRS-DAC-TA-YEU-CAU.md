# ĐẶC TẢ YÊU CẦU PHẦN MỀM (SOFTWARE REQUIREMENTS SPECIFICATION - SRS)
**Tên dự án:** Hệ thống Giao dịch Tiền điện tử Tự động & Ứng dụng Điều khiển Từ xa Tiếng Việt (**FreqBot VN Remote**)  
**Phiên bản:** 1.0.0  
**Ngày lập:** 27/10/2026  

---

## 1. Giới Thiệu Chung

### 1.1. Mục đích tài liệu
Tài liệu SRS này quy định chi tiết toàn bộ các yêu cầu chức năng (Functional Requirements - FR) và yêu cầu phi chức năng (Non-Functional Requirements - NFR) của hệ thống **FreqBot VN Remote**, bao gồm cả **Tầng Lõi Giao Dịch Ngầm (Freqtrade Engine)** và **Tầng Ứng Dụng Điều Khiển Tiếng Việt (Android App & Web Dashboard)**.

### 1.2. Phạm vi hệ thống
Hệ thống cho phép tự động thu thập dữ liệu thị trường tiền điện tử, phân tích tín hiệu mua/bán theo chiến lược định lượng, kiểm duyệt rủi ro đa tầng, thực thi lệnh tự động trên sàn giao dịch (Binance/Bybit/OKX...) và cung cấp giao diện điều khiển từ xa 100% bằng Tiếng Việt trên thiết bị Android cũng như trình duyệt Web.

---

## 2. Yêu Cầu Chức Năng Lõi Giao Dịch (5 Phân Hệ Cốt Lõi)

### 2.1. Phân hệ 1: Thu thập dữ liệu thị trường (Market Data Feed - `FR-MDF`)
- **`FR-MDF-01` (Tải dữ liệu nến & Sổ lệnh):** Hệ thống phải kết nối với sàn giao dịch thông qua thư viện chuẩn hóa `CCXT` để lấy dữ liệu nến (OHLCV/Kline) theo khung thời gian cấu hình (ví dụ `5m`, `15m`, `1h`) và sổ lệnh (`Orderbook`) thời gian thực.
- **`FR-MDF-02` (Tự động kết nối lại & Kiểm tra nhịp tim):** Khi mất kết nối mạng tạm thời với máy chủ sàn, hệ thống phải có cơ chế tự động thử lại (`Auto-reconnect` / `Exponential Backoff`) mà không làm sập tiến trình bot.
- **`FR-MDF-03` (Tải dữ liệu lịch sử khởi động):** Khi khởi động (`Startup`), bot phải tự động tải đủ số lượng nến lịch sử cần thiết (`startup_candle_count`) để tính toán chính xác các chỉ báo kỹ thuật ngay từ chu kỳ đầu tiên.

### 2.2. Phân hệ 2: Bộ não chiến lược (Strategy Engine - `FR-STE`)
- **`FR-STE-01` (Tách biệt hoàn toàn logic chiến lược):** File chiến lược (`VnSmartTrendStrategy.py`) phải tách biệt hoàn toàn khỏi code gọi API sàn để dùng chung một mã nguồn duy nhất cho cả 3 chế độ: Chạy thử lịch sử (`Backtesting`), Chạy giả lập thời gian thực (`Dry-Run`) và Chạy tiền thật (`Live Trade`).
- **`FR-STE-02` (Tính toán chỉ báo & Phát tín hiệu):** Chiến lược phải tính toán các chỉ báo kỹ thuật (`EMA`, `RSI`, `Bollinger Bands`, `Volume`) và phát tín hiệu vào lệnh (`enter_long` kèm nhãn `enter_tag`) hoặc thoát lệnh (`exit_long` kèm nhãn `exit_tag`).
- **`FR-STE-03` (Việt hóa luồng thông báo sự kiện):** Ngay trong chiến lược (`confirm_trade_entry` và `confirm_trade_exit`), hệ thống phải gửi thông báo Tiếng Việt chi tiết mỗi khi mở lệnh mới hoặc đóng lệnh (ghi rõ cặp giao dịch, giá mua/bán, lý do vào lệnh, ngưỡng cắt lỗ bảo vệ).

### 2.3. Phân hệ 3: Quản trị rủi ro & Lớp giáp bảo vệ vốn (Risk Management - `FR-RKM`)
- **`FR-RKM-01` (Quyền phủ quyết độc lập):** Phân hệ Quản trị rủi ro hoạt động như một bộ lọc độc lập có quyền từ chối tín hiệu mua từ `Strategy Engine` nếu vi phạm bất kỳ quy tắc an toàn vốn nào.
- **`FR-RKM-02` (Giới hạn số lệnh và phân bổ vốn):** Giới hạn số lệnh mở đồng thời tối đa (`max_open_trades`, ví dụ 3–5 lệnh) và kiểm soát khối lượng vốn vào mỗi lệnh (`stake_amount`) sao cho rủi ro mất vốn tối đa trên mỗi lệnh đơn lẻ chỉ nằm trong khoảng `1% – 2%` tổng tài sản.
- **`FR-RKM-03` (Cắt lỗ cứng trên máy chủ sàn - Hard Stop-Loss):** Ngay khi lệnh mua khớp, bot phải đặt lệnh Stop-Loss trực tiếp lên máy chủ sàn (`stoploss_on_exchange: true`) để bảo vệ tài khoản ngay cả khi VPS mất mạng hoặc sập nguồn.
- **`FR-RKM-04` (Ngắt mạch tự động - Circuit Breaker / Protections):**
  - **`MaxDrawdown`:** Nếu tổng lỗ thực tế trong 24 giờ chạm ngưỡng cho phép (ví dụ `5%` tài khoản), hệ thống tự động khóa toàn bộ giao dịch mua mới trong thời gian quy định (ví dụ 12–24 giờ).
  - **`StoplossGuard`:** Nếu dính chuỗi `N` lệnh bị cắt lỗ liên tiếp (ví dụ 3 lệnh thua liên tiếp trong 6 giờ), tự động khóa bot để tránh thị trường sập dây chuyền (Flash Crash).
  - **`CooldownPeriod`:** Tạm nghỉ một khoảng thời gian sau khi đóng lệnh trên một cặp coin để tránh vào lại lệnh liên tục ở vùng nhiễu.
- **`FR-RKM-05` (Bộ lọc trượt giá & Chênh lệch giá Mua/Bán):** Kiểm tra độ giãn chênh lệch giá (`Bid-Ask Spread` / `check_depth_of_market`) và hủy bỏ việc vào lệnh nếu thị trường thanh khoản kém hoặc biến động bất thường.

### 2.4. Phân hệ 4: Thực thi lệnh (Order Execution - `FR-OEX`)
- **`FR-OEX-01` (Chuẩn hóa quy tắc làm tròn sàn):** Tự động tuân thủ nghiêm ngặt quy tắc `tickSize` (bước giá), `stepSize` (bước khối lượng) và `minNotional` (giá trị lệnh tối thiểu) của từng cặp coin trên sàn.
- **`FR-OEX-02` (Quản lý vòng đời lệnh & Idempotency):** Theo dõi đầy đủ các trạng thái lệnh (`Open`, `Partially Filled`, `Closed/Filled`, `Canceled`, `Expired`) và tránh đặt trùng lệnh khi mạng chập chờn.

### 2.5. Phân hệ 5: Lưu trữ, Đồng bộ trạng thái & Máy chủ API (State & API Server - `FR-SAM`)
- **`FR-SAM-01` (Lưu trữ SQLite & Đối chiếu trạng thái):** Lưu toàn bộ lịch sử giao dịch, vị thế đang mở và khóa bảo vệ vào cơ sở dữ liệu cục bộ (`SQLite`) và tự động đối chiếu đồng bộ với sàn khi khởi động lại (`State Reconciliation`).
- **`FR-SAM-02` (Cung cấp REST API & WebSocket điều khiển):** Bật `api_server` cung cấp các Endpoint chuẩn bảo mật bằng Basic Auth (khi đăng nhập) và Bearer JWT Token (cho các lệnh điều khiển tiếp theo).

---

## 3. Yêu Cầu Chức Năng Ứng Dụng Điều Khiển Tiếng Việt (Android App & Web Dashboard)

### 3.1. Bảng ánh xạ API Freqtrade sang Giao diện Tiếng Việt (`FR-UI-MAP`)

Giao diện Android (`FreqBot VN Remote`) và Web Dashboard phải kết nối và dịch toàn bộ dữ liệu từ các Endpoint sau sang Tiếng Việt:

| Mã Yêu Cầu | Đường Dẫn API Freqtrade | Phương Thức | Thành Phần Hiển Thị Trên Giao Diện Tiếng Việt | Dữ Liệu JSON Quan Trọng Cần Xử Lý |
| :--- | :--- | :--- | :--- | :--- |
| **`FR-UI-01`** | `/api/v1/token/login` | `POST` | Màn hình / Hộp thoại Cấu hình & Đăng nhập | Nhận `access_token` và `refresh_token` (JWT) qua `Basic Auth`. |
| **`FR-UI-02`** | `/api/v1/profit` | `GET` | Thẻ Tổng quan Lợi nhuận | `profit_all_coin` (Tổng lãi USDT), `profit_all_percent` (% Lãi tổng), `trade_count` (Tổng số lệnh), `winning_trades` (Lệnh thắng), `losing_trades` (Lệnh thua), `max_drawdown` (Sụt giảm tối đa). |
| **`FR-UI-03`** | `/api/v1/balance` | `GET` | Thẻ Số dư Tài khoản | `total` (Tổng tài sản USDT), `free` (Vốn USDT rảnh), `used` (Vốn đang nằm trong lệnh). |
| **`FR-UI-04`** | `/api/v1/status` | `GET` | Danh sách Lệnh Đang Mở (Thời gian thực) | `trade_id` (Mã lệnh), `pair` (Cặp coin), `stake_amount` (Vốn vào lệnh), `open_rate` (Giá mua), `current_rate` (Giá hiện tại), `profit_ratio` (% Lãi/Lỗ), `profit_abs` (USDT Lãi/Lỗ), `stop_loss_abs` (Mốc cắt lỗ cứng). |
| **`FR-UI-05`** | `/api/v1/locks` | `GET` | Trạng thái Giáp Bảo Vệ (Quản trị rủi ro) | `lock_count` (Số khóa đang bật), `pair` (Cặp bị khóa hoặc `*`), `reason` (Lý do khóa được dịch sang Tiếng Việt), `lock_end_time` (Thời gian mở khóa). |
| **`FR-UI-06`** | `/api/v1/stopbuy` | `POST` | Nút "Tạm dừng Mua mới" | Chuyển bot sang trạng thái ngừng mua thêm lệnh mới, chỉ canh chốt lời/cắt lỗ các lệnh đang giữ. |
| **`FR-UI-07`** | `/api/v1/reload_config` | `POST` | Nút "Khởi động lại Mua / Nạp lại cấu hình" | Đưa bot trở lại chế độ giao dịch mua bán bình thường sau khi đã tạm dừng mua. |
| **`FR-UI-08`** | `/api/v1/forceexit` | `POST` | Nút đỏ "Cắt lỗ / Bán khẩn cấp (Panic Sell)" | Gửi `{"tradeid": "all", "ordertype": "market"}` để bán toàn bộ danh mục về USDT ngay lập tức, hoặc truyền `tradeid` cụ thể để đóng 1 lệnh riêng lẻ. |

### 3.2. Yêu cầu riêng cho Ứng dụng Android (`FreqBot VN Remote` - `FR-AND`)
- **`FR-AND-01` (Tự động làm mới thời gian thực):** Khi ứng dụng đang mở trên màn hình, tự động gọi API làm mới dữ liệu mỗi `5 giây` bằng Kotlin Coroutines (`lifecycleScope`) mà không gây giật lag giao diện.
- **`FR-AND-02` (Hiển thị danh sách lệnh trực quan kèm nút đóng từng lệnh):** Sử dụng `RecyclerView` (`OpenTradeAdapter`) hiển thị từng lệnh đang mở với màu sắc phân biệt rõ ràng (`🟢 ĐANG LÃI` màu xanh lá, `🔴 ĐANG LỖ` màu đỏ) và nút **"Đóng lệnh này"** ngay trên từng thẻ lệnh.
- **`FR-AND-03` (Hộp thoại xác nhận chống bấm nhầm Panic Sell):** Khi bấm nút **"BÁN KHẨN CẤP TOÀN BỘ"**, ứng dụng bắt buộc hiển thị `AlertDialog` cảnh báo rõ bằng Tiếng Việt, chỉ khi người dùng nhấn xác nhận **"ĐỒNG Ý BÁN HẾT"** mới phát lệnh gọi API.
- **`FR-AND-04` (Giám sát rủi ro chạy ngầm bằng WorkManager):** Sử dụng `CoroutineWorker` (`RiskMonitorWorker`) định kỳ 15 phút kiểm tra máy chủ bot ngay cả khi đã đóng ứng dụng. Nếu phát hiện:
  1. Có lệnh đang lỗ vượt ngưỡng cảnh báo (ví dụ `<= -3%`), hoặc
  2. Bot vừa kích hoạt khóa bảo vệ rủi ro (`lock_count > 0`), hoặc
  3. Mất kết nối hoàn toàn với máy chủ VPS,
  ứng dụng phải đẩy thông báo (`Notification`) bằng Tiếng Việt lên màn hình khóa điện thoại.
- **`FR-AND-05` (Cấu hình động địa chỉ máy chủ VPS / Tailscale):** Cho phép người dùng nhập và lưu địa chỉ IP máy chủ (ví dụ `http://100.x.y.z:8080/` hoặc `http://10.0.2.2:8080/` khi chạy máy ảo Android Emulator), tài khoản và mật khẩu ngay trên giao diện ứng dụng (lưu vào `SharedPreferences`).

---

## 4. Yêu Cầu Phi Chức Năng (Non-Functional Requirements - `NFR`)

### 4.1. Bảo mật (Security - `NFR-SEC`)
- **`NFR-SEC-01` (Phân quyền API Key sàn tối thiểu):** Khóa API sàn chỉ được bật quyền *Đọc dữ liệu (Read Info)* và *Giao dịch (Spot/Futures Trading)*. Tuyệt đối **không bật quyền Rút tiền (Enable Withdrawals)**.
- **`NFR-SEC-02` (Giới hạn địa chỉ IP - IP Whitelisting):** API Key trên sàn chỉ chấp nhận lệnh gọi từ đúng địa chỉ IP tĩnh của VPS chạy bot.
- **`NFR-SEC-03` (Kết nối điều khiển qua Mesh VPN):** Giao tiếp giữa ứng dụng Android/Web và cổng 8080 của Freqtrade khuyến nghị đi qua mạng riêng ảo **Tailscale** hoặc **ZeroTier** (`100.x.y.z`), không phơi cổng 8080 trực tiếp ra Internet công cộng.
- **`NFR-SEC-04` (Xác thực JWT):** Mọi Endpoint điều khiển bot (trừ `/ping` và `/token/login`) đều yêu cầu `Bearer <access_token>` hợp lệ.

### 4.2. Hiệu năng, Độ tin cậy & Vận hành (`NFR-REL`)
- **`NFR-REL-01` (Độ trễ mạng thấp):** Máy chủ VPS ưu tiên đặt tại Tokyo hoặc Singapore để độ trễ tới máy chủ khớp lệnh của sàn dưới `10–30ms`.
- **`NFR-REL-02` (Đồng bộ thời gian chuẩn xác):** Hệ thống Linux VPS phải đồng bộ thời gian qua NTP (`Chrony`) với sai số dưới `100ms` để tránh lỗi `Timestamp for this request was 1000ms ahead of the server's time` (`recvWindow`).
- **`NFR-REL-03` (Kiểm soát giới hạn gọi API - Rate Limiting):** Bật `enableRateLimit: true` trong CCXT để tự động điều tiết hàng đợi request, ngăn chặn lỗi khóa IP (`HTTP 429` / `HTTP 418`).
- **`NFR-REL-04` (Hoạt động liên tục 24/7):** Tiến trình Freqtrade được quản lý bởi Docker (`restart: unless-stopped`), tự động khởi động lại nếu gặp sự cố ngoài ý muốn.
