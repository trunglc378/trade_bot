# HƯỚNG DẪN CẤU HÌNH FREQTRADE (`config.json`) TOÀN DIỆN (TÀI LIỆU VIỆT HÓA)
**Nguồn gốc tài liệu:** `docs/configuration.md` — Kho mã nguồn chính thức `freqtrade/freqtrade`  
**Bản dịch & Biên tập Tiếng Việt:** Dự án FreqBot VN Remote  

---

## 1. Tổng Quan Về File Cấu Hình `config.json`

Freqtrade sử dụng định dạng **JSON** cho file cấu hình chính (`user_data/config.json`). Bạn có thể truyền một hoặc nhiều file cấu hình khi khởi chạy bot (ví dụ: tách riêng file `config-secrets.json` chứa API Key của sàn để bảo mật).

---

## 2. Bảng Giải Thích Chi Tiết Các Tham Số Cốt Lõi

| Tham số (Parameter) | Kiểu dữ liệu | Ý nghĩa & Khuyến nghị cấu hình (Tiếng Việt) |
| :--- | :--- | :--- |
| **`max_open_trades`** | Số nguyên (`int` hoặc `-1`) | **Số lệnh mở tối đa cùng lúc.** Ví dụ đặt `3` hoặc `5` để bot không bao giờ giữ quá 3–5 đồng coin cùng một thời điểm. Đặt `-1` là không giới hạn (không khuyến nghị). |
| **`stake_currency`** | Chuỗi (`string`) | **Đồng tiền gốc dùng làm vốn giao dịch.** Thường là `"USDT"`, `"USDC"` hoặc `"FDUSD"`. |
| **`stake_amount`** | Số thực (`float`) hoặc `"unlimited"` | **Số vốn vào cho mỗi lệnh đơn lẻ.**<br>- Nếu đặt số cố định (ví dụ `50`): mỗi lệnh mua đúng 50 USDT.<br>- Nếu đặt `"unlimited"`: bot tự chia đều tổng vốn khả dụng cho `max_open_trades`. |
| **`tradable_balance_ratio`** | Số thực (`0.1` đến `1.0`) | **Tỷ lệ tổng số dư trên sàn được phép đưa vào giao dịch.** Mặc định là `0.99` (99% số dư, giữ lại 1% dự phòng phí/trượt giá). |
| **`fiat_display_currency`** | Chuỗi (`string`) | Đơn vị tiền pháp định để quy đổi hiển thị tham khảo (ví dụ `"USD"`). |
| **`dry_run`** | Logic (`true` / `false`) | **Chế độ giao dịch giả lập (Paper Trading).**<br>- `true`: Chạy với giá thật thời gian thực nhưng dùng tiền giả lập (mặc định bắt buộc khi mới thử nghiệm).<br>- `false`: Giao dịch bằng tiền thật trên sàn. |
| **`dry_run_wallet`** | Số thực (`float`) | Số vốn khởi tạo trong ví giả lập khi `dry_run: true` (ví dụ `1000` tương đương 1.000 USDT). |
| **`cancel_open_orders_on_exit`** | Logic (`true` / `false`) | Tự động hủy các lệnh đang挂 (chờ khớp) trên sàn khi tắt bot. |
| **`unfilledtimeout`** | Khối JSON | Thời gian tối đa chờ khớp lệnh Limit trước khi tự động hủy lệnh (`entry`: 10 phút, `exit`: 10 phút). |

---

## 3. Cấu Hình Giá Đặt Lệnh & Kiểm Tra Sổ Lệnh (`entry_pricing` & `exit_pricing`)

Để tránh mua giá quá cao hoặc bán giá quá thấp khi chênh lệch giá Mua/Bán (`Bid-Ask Spread`) giãn rộng, Freqtrade cung cấp khối cấu hình định giá:

```json
"entry_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1,
    "price_last_balance": 0.0,
    "check_depth_of_market": {
        "enabled": true,
        "bids_to_ask_delta": 1
    }
},
"exit_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1
}
```
- **`use_order_book: true` & `order_book_top: 1`:** Lấy giá đặt lệnh dựa trên mức giá tốt nhất thứ 1 trong sổ lệnh (Orderbook) hiện tại.
- **`check_depth_of_market`:** Kiểm tra thanh khoản sổ lệnh trước khi vào lệnh.

---

## 4. Cấu Hình Kết Nối Sàn Giao Dịch (`exchange`) & Danh Sách Coin (`pairlists`)

```json
"exchange": {
    "name": "binance",
    "key": "API_KEY_SAN_CUA_BAN",
    "secret": "SECRET_KEY_SAN_CUA_BAN",
    "ccxt_config": {
        "enableRateLimit": true
    },
    "ccxt_async_config": {
        "enableRateLimit": true,
        "rateLimit": 100
    },
    "pair_whitelist": [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BNB/USDT",
        "XRP/USDT",
        "ADA/USDT",
        "AVAX/USDT",
        "LINK/USDT"
    ],
    "pair_blacklist": [
        "BNB/.*",
        ".*(_PREMIUM|BEAR|BULL|DOWN|UP|[1235][SL])/.*"
    ]
}
```

> [!WARNING]
> - Luôn để `"enableRateLimit": true` để thư viện CCXT tự động điều tiết tốc độ gọi API, tránh bị sàn Binance/Bybit khóa IP (`HTTP 429` hoặc `418`).
> - Trong `pair_blacklist`, luôn chặn các token đòn bẩy (`UP`, `DOWN`, `BULL`, `BEAR`). Nếu bạn dùng `BNB` để giảm 25% phí giao dịch trên Binance, hãy giữ `BNB/.*` trong `pair_blacklist` để bot không bán mất số BNB làm phí.

---

## 5. Cấu Hình Máy Chủ API (`api_server`) Phục Vụ App Android & Web Tiếng Việt

Để ứng dụng Android **FreqBot VN Remote** và Web Dashboard có thể kết nối vào điều khiển bot, khối `api_server` trong `config.json` cần được bật như sau:

```json
"api_server": {
    "enabled": true,
    "listen_ip_address": "0.0.0.0",
    "listen_port": 8080,
    "verbosity": "error",
    "enable_openapi": true,
    "jwt_secret_key": "chuoi_khoa_bi_mat_jwt_cua_rieng_ban_hay_doi_ngay",
    "CORS_origins": ["*"],
    "username": "admin",
    "password": "mat_khau_manh_cua_ban"
}
```

- **`enabled: true`:** Kích hoạt máy chủ REST API & WebSocket nội bộ.
- **`listen_ip_address`:**
  - Để `"0.0.0.0"` khi chạy trong Docker container hoặc mạng nội bộ.
  - Khi chạy trên VPS có cài **Tailscale VPN**, nên bind cổng Docker vào địa chỉ IP Tailscale (`100.x.y.z:8080:8080`).
- **`jwt_secret_key`:** Chuỗi ngẫu nhiên dùng để ký mã xác thực JWT (`access_token`).
- **`username` / `password`:** Tài khoản đăng nhập từ ứng dụng Android và Web Dashboard.
