# HƯỚNG DẪN TRIỂN KHAI & VẬN HÀNH HỆ THỐNG (DEPLOYMENT & OPERATIONS GUIDE)
**Tên dự án:** Hệ thống Giao dịch Tiền điện tử Tự động & Ứng dụng Điều khiển Từ xa Tiếng Việt (**FreqBot VN Remote**)  
**Phiên bản:** 1.0.0  
**Ngày lập:** 27/10/2026  

---

## 1. Hướng Dẫn Chạy Thử Nhanh Trên Máy Cá Nhân (Local Quickstart)

Để giúp bạn kiểm nghiệm ngay toàn bộ **Giao diện Web Tiếng Việt** và **Ứng dụng Android (`FreqBot VN Remote`)** mà chưa cần thuê VPS hay cấu hình sàn giao dịch, dự án cung cấp sẵn **Máy chủ giả lập API Freqtrade (`mock_api_server.py`)** mô phỏng đầy đủ các Endpoint (`/api/v1/token/login`, `/profit`, `/balance`, `/status`, `/locks`, `/stopbuy`, `/reload_config`, `/forceexit`).

### Bước 1: Khởi chạy Máy chủ Giả lập Freqtrade (`mock_api_server.py`)
Mở PowerShell / Terminal tại thư mục gốc dự án `e:\Project\trade_bot` và chạy:
```powershell
py freqtrade-bot/mock_api_server.py
```
- Máy chủ sẽ khởi động tại: `http://127.0.0.1:8080` (và `http://0.0.0.0:8080`).
- Tài khoản mặc định: `admin` / Mật khẩu: `mat_khau_manh_cua_ban`

### Bước 2: Mở Giao diện Web Dashboard Tiếng Việt
- Mở trực tiếp file [`web-dashboard/index.html`](file:///e:/Project/trade_bot/web-dashboard/index.html) bằng trình duyệt (Chrome/Edge) hoặc truy cập `http://127.0.0.1:8080/dashboard` (được tích hợp sẵn trên Mock Server).
- Nhấn **Kết nối & Đăng nhập** để xem bảng điều khiển Tiếng Việt cập nhật thời gian thực, thử nghiệm nút **Tạm dừng Mua mới**, **Đóng từng lệnh** hoặc **Bán khẩn cấp toàn bộ (Panic Sell)**.

### Bước 3: Biên dịch & Chạy Ứng dụng Android (`android-app/`)
1. Mở **Android Studio** -> chọn **Open** -> trỏ tới thư mục [`e:\Project\trade_bot\android-app`](file:///e:/Project/trade_bot/android-app).
2. Đợi Gradle đồng bộ thư viện (`Retrofit 2.9.0`, `Coroutines 1.7.3`, `WorkManager 2.9.0`, `Material Design`).
3. Nhấn **Run (`Shift + F10`)** lên máy ảo Android Emulator hoặc điện thoại thật:
   - Nếu chạy trên **Android Emulator** nối với máy tính đang chạy `mock_api_server.py`: địa chỉ IP mặc định là `http://10.0.2.2:8080/`.
   - Nếu chạy trên **Điện thoại Android thật** cùng mạng Wi-Fi: bấm nút **⚙️ Cấu hình Máy chủ** trên góc phải ứng dụng, nhập IP LAN của máy tính (ví dụ `http://192.168.1.x:8080/`) hoặc IP Tailscale của VPS (`http://100.x.y.z:8080/`).

---

## 2. Hướng Dẫn Triển Khai Lõi Freqtrade Thực Tế Bằng Docker (Ubuntu VPS / Local Docker)

### Bước 1: Chuẩn bị môi trường trên Ubuntu VPS (Khuyến nghị Tokyo / Singapore)
1. Đồng bộ thời gian hệ thống chuẩn xác bằng `chrony` để không bị sàn từ chối lệnh do lệch `recvWindow`:
   ```bash
   sudo apt update && sudo apt install -y chrony docker.io docker-compose-plugin
   sudo systemctl enable --now chrony
   chronyc tracking
   ```
2. Cài đặt mạng riêng ảo **Tailscale** để điều khiển an toàn từ điện thoại Android:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   tailscale ip -4   # Ghi nhớ địa chỉ IP 100.x.y.z này
   ```

### Bước 2: Kiểm tra cấu hình Bot (`freqtrade-bot/user_data/config.json`)
Mở file [`freqtrade-bot/user_data/config.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/config.json):
- Mặc định hệ thống đang để `"dry_run": true` và `"dry_run_wallet": 1000` (Chế độ Paper Trading an toàn 100% với 1.000 USDT giả lập theo giá thật của sàn Binance).
- Đổi `"jwt_secret_key"` và `"password"` trong khối `"api_server"` thành mật khẩu mạnh của riêng bạn.

### Bước 3: Tải dữ liệu lịch sử & Chạy Backtest Chiến lược (`Bước 1 Quy trình 3 bước`)
Di chuyển vào thư mục `freqtrade-bot/`:
```bash
cd freqtrade-bot

# 1. Tải dữ liệu nến 5m, 15m, 1h trong 180 ngày gần nhất từ Binance
docker compose run --rm freqtrade download-data \
    --pairs BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT \
    --timeframes 5m 15m 1h \
    --days 180

# 2. Chạy Backtest chiến lược VnSmartTrendStrategy (có tính phí sàn 0.1%)
docker compose run --rm freqtrade backtesting \
    --strategy VnSmartTrendStrategy \
    --timeframe 5m \
    --fee 0.001
```

### Bước 4: Khởi chạy Bot 24/7 ở chế độ Dry-Run (`Bước 2 Quy trình 3 bước`)
```bash
docker compose up -d
docker compose logs -f
```
- Lúc này Freqtrade sẽ chạy ngầm 24/7 và mở cổng API `8080`.
- Mở ứng dụng Android **FreqBot VN Remote** trên điện thoại, nhập địa chỉ IP Tailscale của VPS (`http://100.x.y.z:8080/`), tài khoản và mật khẩu để giám sát và điều khiển bằng Tiếng Việt.

### Bước 5: Chuyển sang Chạy Tiền Thật Vốn Nhỏ (`Bước 3: Live Micro-Capital`)
Chỉ thực hiện sau khi đã chạy ổn định Bước 1 và Bước 2 từ 1–2 tuần:
1. Tạo API Key trên sàn Binance/Bybit (Chỉ bật quyền **Read** và **Spot Trading**, **KHÔNG** bật quyền Withdraw, gắn **IP Whitelist** là IP tĩnh của VPS).
2. Cập nhật `key` và `secret` vào `freqtrade-bot/user_data/config.json`.
3. Đặt `"dry_run": false`, `"max_open_trades": 3`, `"stake_amount": 15` (vốn nhỏ 15 USDT/lệnh).
4. Khởi động lại container:
   ```bash
   docker compose restart
   ```
