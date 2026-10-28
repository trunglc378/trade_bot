# HƯỚNG DẪN TRIỂN KHAI & VẬN HÀNH HỆ THỐNG (DEPLOYMENT & OPERATIONS GUIDE)
**Tên dự án:** Hệ thống Giao dịch Tiền điện tử Tự động, Phân tích AI Đa nguồn & Ứng dụng Điều khiển Từ xa Tiếng Việt (**FreqBot VN Remote**)<br>
**Phiên bản:** 2.0.0<br>
**Ngày cập nhật:** 28/10/2026<br>

> **Tài liệu liên quan:** Xem thêm [Tài liệu Cài đặt Phần mềm & Hướng dẫn Sử dụng Toàn diện (`08-TAI-LIEU-CAI-DAT-VA-HUONG-DAN-SU-DUNG.md`)](file:///e:/Project/trade_bot/docs/08-TAI-LIEU-CAI-DAT-VA-HUONG-DAN-SU-DUNG.md) và [Đặc tả Lịch giao dịch, Phân tích AI & Kiểm chứng (`07-LICH-GIAO-DICH-AI-VA-PHAN-TICH.md`)](file:///e:/Project/trade_bot/docs/07-LICH-GIAO-DICH-AI-VA-PHAN-TICH.md).

---

## 1. Hướng Dẫn Chạy Thử Nhanh Trên Máy Cá Nhân (Local Quickstart)

Máy chủ giả lập (`mock_api_server.py`) cung cấp API giao dịch và báo cáo nghiên cứu cho kiểm thử giao diện Tiếng Việt. Endpoint `/api/v1/vn_research` chỉ có trên máy chủ giả lập; khi chạy Freqtrade thật, giao diện Web Dashboard xem báo cáo bằng cách chọn tệp `user_data/research/latest.json`.

### Bước 1: Chạy Kiểm thử Tự động (Unit Tests)
Mở PowerShell / Terminal tại thư mục gốc dự án `e:\Project\trade_bot` và chạy:
```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
py -3.12 -m unittest discover -s freqtrade-bot/tests -p "test_*.py" -v
node tests/test_dashboard.js
```

### Bước 2: Khởi chạy Máy chủ Giả lập Freqtrade & AI Advisor (`mock_api_server.py`)
```powershell
py -3.12 freqtrade-bot/mock_api_server.py
```
- Máy chủ khởi động tại: `http://127.0.0.1:8080`
- Giao diện Web Dashboard Tiếng Việt: `http://127.0.0.1:8080/dashboard`
- Tài khoản mặc định: `admin` / Mật khẩu: `mat_khau_manh_cua_ban`

### Bước 3: Trải nghiệm Web Dashboard & Bảng Phân Tích AI
1. Truy cập `http://127.0.0.1:8080/dashboard` trên trình duyệt (hoặc mở [`web-dashboard/index.html`](file:///e:/Project/trade_bot/web-dashboard/index.html)).
2. Nhấn **Kết Nối & Đăng Nhập** để xem lệnh mở, chế độ vận hành (`Giao dịch thử Dry-Run` / `Tiền thật Live`) và trạng thái tài khoản.
3. Chọn tệp [`freqtrade-bot/user_data/research/latest.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/research/latest.json) hoặc nhấn nút **Đồng Bộ Báo Cáo Máy Chủ Giả Lập** để xem điểm kỹ thuật, độ giãn spread, biến động 1h, `RSI(14)`, trạng thái thị trường (`Market Regime`) và nhận định Tiếng Việt từ **ChatGPT** & **Google Gemini**.

---

## 2. Cấu Hình Khung Giờ Giao Dịch & Đề Xuất Coin AI (`config.json` & `config-okx.json`)

Trong file [`freqtrade-bot/user_data/config.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/config.json), khối `"vn_policy"` cho phép bạn tùy chỉnh toàn diện:

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
        "max_history_files": 288,
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
  - Khi muốn giao dịch trên sàn **OKX**, truyền thêm file cấu hình ghi đè [`user_data/config-okx.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/config-okx.json) cho cả dịch vụ `freqtrade` và `research`:
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
py -3.12 freqtrade-bot/user_data/research/run.py --config freqtrade-bot/user_data/config.json
```

### Cách 2: Chạy tự động 24/7 bằng Docker Compose (Cùng với Freqtrade Bot)
1. Sao chép file `.env.example` thành `.env` trong thư mục `freqtrade-bot/`:
   ```bash
   cd freqtrade-bot
   cp .env.example .env
   # Điền OPENAI_API_KEY và GEMINI_API_KEY vào file .env
   ```
2. Khởi chạy đồng thời cả dịch vụ `freqtrade` và dịch vụ `research` (tự động quét thị trường mỗi 5 phút và giữ tối đa `288` bản chụp lịch sử trong `history/`):
   ```bash
   docker compose up -d
   docker compose logs -f
   ```

---

## 4. Lưu Ý Bảo Mật & Vận Hành Thực Tế

- Máy chủ giả lập mặc định chỉ lắng nghe trên `127.0.0.1`; khi kiểm tra qua mạng nội bộ LAN hoặc Tailscale VPN cần đặt `MOCK_HOST` thành địa chỉ IP tương ứng.
- Trong Docker Compose, cổng `8080` mặc định chỉ publish ra `127.0.0.1:8080`. Khi điều khiển từ ứng dụng Android qua mạng riêng Tailscale VPN, hãy bind vào địa chỉ IP Tailscale của VPS.
- Chế độ `advisory` yêu cầu dịch vụ `research` tạo bản chụp `latest.json` còn hạn (`ttl_seconds`) trước khi mở lệnh mua mới.
- Không chuyển sang chạy tiền thật (`Live`) chỉ vì kiểm thử offline thành công; bắt buộc kiểm chứng qua Backtest ngoài mẫu, chạy thử `Dry-Run` nhiều tuần và tách riêng tệp cơ sở dữ liệu `tradesv3.live.sqlite`.
