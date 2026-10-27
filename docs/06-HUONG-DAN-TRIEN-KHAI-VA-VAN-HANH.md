# HƯỚNG DẪN TRIỂN KHAI & VẬN HÀNH HỆ THỐNG (DEPLOYMENT & OPERATIONS GUIDE)
**Tên dự án:** Hệ thống Giao dịch Tiền điện tử Tự động, Phân tích AI Đa nguồn & Ứng dụng Điều khiển Từ xa Tiếng Việt (**FreqBot VN Remote**)<br>
**Phiên bản:** 2.0.0<br>
**Ngày cập nhật:** 27/10/2026<br>

---

## 1. Hướng Dẫn Chạy Thử Nhanh Trên Máy Cá Nhân (Local Quickstart)

Mock cung cấp một phần API giao dịch và báo cáo nghiên cứu cho kiểm thử UI. Endpoint `/api/v1/vn_research` chỉ có trên mock. Freqtrade thật xem báo cáo bằng cách chọn tệp `user_data/research/latest.json`.

### Bước 1: Chạy Kiểm thử Tự động (Unit Tests)
Mở PowerShell / Terminal tại thư mục gốc dự án `d:\Project\trade_bot` và chạy:
```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

### Bước 2: Khởi chạy Máy chủ Giả lập Freqtrade & AI Advisor (`mock_api_server.py`)
```powershell
py freqtrade-bot/mock_api_server.py
```
- Máy chủ khởi động tại: `http://127.0.0.1:8080`
- Giao diện Web Dashboard Tiếng Việt: `http://127.0.0.1:8080/dashboard`
- Tài khoản mặc định: `admin` / Mật khẩu: `mat_khau_manh_cua_ban`

### Bước 3: Trải nghiệm Web Dashboard & Bảng Phân Tích AI
1. Truy cập `http://127.0.0.1:8080/dashboard` trên trình duyệt (hoặc mở `web-dashboard/index.html`).
2. Nhấn **Kết Nối & Đăng Nhập** để xem lệnh mở và trạng thái tài khoản. Báo cáo AI được tải riêng qua chọn tệp.
3. Chọn tệp `user_data/research/latest.json` để xem điểm kỹ thuật, spread, biến động 1h và nhận định AI. Nút đồng bộ máy chủ dùng endpoint riêng của mock; Freqtrade thật vẫn dùng chọn tệp. Worker có RSI14 và nhãn regime theo luật.

---

## 2. Cấu Hình Khung Giờ Giao Dịch & Đề Xuất Coin AI (`config.json` & `config-okx.json`)

Trong file [`freqtrade-bot/user_data/config.json`](file:///d:/Project/trade_bot/freqtrade-bot/user_data/config.json), khối `"vn_policy"` cho phép bạn tùy chỉnh toàn diện:

```json
"vn_policy": {
    "schedule": {
        "enabled": true,
        "windows": [
            {
                "start": "03:00",
                "end": "04:00",
                "weekdays": [0, 1, 2, 3, 4, 5, 6]
            }
        ]
    },
    "risk": {
        "risk_per_trade": 0.005,
        "max_position_fraction": 0.2,
        "max_exposure_fraction": 0.6,
        "cost_buffer": 0.004,
        "max_entry_deviation": 0.005
    },
    "research": {
        "mode": "advisory",
        "ttl_seconds": 900,
        "min_quote_volume": 10000000,
        "max_spread": 0.002,
        "max_volatility": 0.02,
        "max_hour_change": 0.06,
        "providers": {
            "openai": "gpt-4.1-mini",
            "gemini": "MODEL_ID_GEMINI_CUA_BAN"
        },
        "min_ai_votes": 2,
        "min_ai_confidence": 0.7
    }
}
```

- **Mở rộng thêm khung giờ giao dịch:** Bạn có thể thêm nhiều khung giờ vào mảng `"windows"`, ví dụ thêm khung giờ phiên tối `{"start": "20:00", "end": "22:00", "weekdays": [0, 1, 2, 3, 4]}` hoặc tắt giới hạn giờ bằng `"enabled": false`.
- **Chuyển đổi giữa sàn Binance và OKX:**
  - Mặc định `config.json` sử dụng sàn **Binance**.
  - Khi muốn giao dịch trên sàn **OKX**, truyền thêm file cấu hình ghi đè [`user_data/config-okx.json`](file:///d:/Project/trade_bot/freqtrade-bot/user_data/config-okx.json):
    ```bash
    docker compose run --rm freqtrade trade \
        --config /freqtrade/user_data/config.json \
        --config /freqtrade/user_data/config-okx.json \
        --strategy VnSmartTrendStrategy
    ```

---

## 3. Chạy Bộ Phân Tích Thị Trường & Đề Xuất Coin AI (`research/run.py`)

### Cách 1: Chạy trực tiếp bằng Python trên máy
```powershell
# Thiết lập khóa API AI (Tùy chọn - nếu muốn nhận khuyến nghị từ ChatGPT & Gemini)
$env:OPENAI_API_KEY="sk-..."
$env:GEMINI_API_KEY="AIza..."

# Chạy 1 lần xuất báo cáo ra freqtrade-bot/user_data/research/latest.json
py freqtrade-bot/user_data/research/run.py --config freqtrade-bot/user_data/config.json
```

### Cách 2: Chạy tự động 24/7 bằng Docker Compose (Cùng với Freqtrade Bot)
1. Sao chép file `.env.example` thành `.env` trong thư mục `freqtrade-bot/`:
   ```bash
   cd freqtrade-bot
   cp .env.example .env
   # Điền OPENAI_API_KEY và GEMINI_API_KEY vào file .env
   ```
2. Khởi chạy đồng thời cả dịch vụ `freqtrade` và dịch vụ `research` (tự động quét thị trường mỗi 5 phút):
   ```bash
   docker compose up -d
   docker compose logs -f
   ```
# Hướng dẫn cập nhật ngày 27/10/2026

Ưu tiên [hướng dẫn 07](07-LICH-GIAO-DICH-AI-VA-PHAN-TICH.md) cho research sidecar, cấu hình AI, overlay OKX trên cả worker/bot, xem snapshot web, tests và kiểm chứng giờ giao dịch.

Mock mặc định bind localhost; khi kiểm tra qua LAN/VPN cần đặt `MOCK_HOST` thành IP tương ứng. Docker cũng chỉ publish localhost. Trong container giữ listen IP `0.0.0.0`, bind IP Tailscale tại host nếu cần Android truy cập. Dashboard riêng phục vụ tại port 8090 theo CORS mẫu. Advisory cần worker tạo snapshot còn hạn trước khi mua.

Không chuyển live chỉ vì tests offline thành công. Cần kiểm thử Freqtrade thật, dữ liệu ngoài mẫu, dry-run và xác minh loại stop sàn. Nếu về sau chuyển live, dùng database riêng, không dùng `tradesv3.dryrun.sqlite` hiện được Compose cấu hình. Không commit khóa thật vào config mẫu.
