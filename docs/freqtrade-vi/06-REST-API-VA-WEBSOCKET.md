# TÀI LIỆU REST API & WEBSOCKET SERVER CỦA FREQTRADE (TÀI LIỆU VIỆT HÓA)
**Nguồn gốc tài liệu:** `docs/rest-api.md` — Kho mã nguồn chính thức `freqtrade/freqtrade`  
**Bản dịch & Biên tập Tiếng Việt:** Dự án FreqBot VN Remote  

---

## 1. Cơ Chế Xác Thực (`Authentication` — Basic Auth & JWT Bearer Token)

Máy chủ REST API của Freqtrade (mặc định chạy trên cổng `8080`, đường dẫn gốc `/api/v1`) sử dụng cơ chế xác thực 2 bước:
1. **Bước 1 (Đăng nhập lấy Token — `POST /api/v1/token/login`):**
   - Gửi yêu cầu `POST` kèm Header `Authorization: Basic <base64(username:password)>`.
   - Máy chủ trả về chuỗi JSON chứa `access_token` (có hiệu lực 15 phút) và `refresh_token` (có hiệu lực 30 ngày):
     ```json
     {
       "access_token": "eyJhbGciOiJIUzI1NiIs...",
       "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
     }
     ```
2. **Bước 2 (Gọi các lệnh điều khiển tiếp theo):**
   - Đính kèm Header `Authorization: Bearer <access_token>` vào mọi yêu cầu HTTP tiếp theo.

---

## 2. Danh Sách Các Endpoint Cốt Lõi Phục Vụ Điều Khiển Từ Xa

| Đường dẫn Endpoint | Phương thức | Cần xác thực? | Chức năng & Ý nghĩa Tiếng Việt |
| :--- | :--- | :--- | :--- |
| `/api/v1/ping` | `GET` | Không | Kiểm tra máy chủ Bot còn sống hay không (`{"status": "pong"}`). |
| `/api/v1/token/login` | `POST` | Basic Auth | Đăng nhập để lấy JWT `access_token` và `refresh_token`. |
| `/api/v1/token/refresh` | `POST` | Bearer (`refresh_token`) | Cấp lại `access_token` mới mà không cần gửi lại mật khẩu. |
| `/api/v1/show_config` | `GET` | Bearer JWT | Lấy trạng thái hiện tại của Bot (`state`: `running`/`stopped`, `dry_run`, `strategy`, `max_open_trades`). |
| `/api/v1/profit` | `GET` | Bearer JWT | Lấy thống kê tổng quan lợi nhuận, tỷ lệ thắng/thua và mức sụt giảm tối đa (`max_drawdown`). |
| `/api/v1/balance` | `GET` | Bearer JWT | Lấy số dư từng đồng coin và tổng tài sản quy đổi ra USDT (`total`, `free`, `used`). |
| `/api/v1/status` | `GET` | Bearer JWT | **Lấy danh sách các lệnh đang mở theo thời gian thực** (cặp coin, giá mua, giá hiện tại, % lãi/lỗ, mốc cắt lỗ). |
| `/api/v1/locks` | `GET` | Bearer JWT | Kiểm tra danh sách các khóa bảo vệ rủi ro (`Protections`) đang kích hoạt (`MaxDrawdown`, `StoplossGuard`...). |
| `/api/v1/stopbuy` | `POST` | Bearer JWT | **Tạm dừng Mua mới:** Đặt `max_open_trades = 0`, ngừng mở lệnh mới nhưng vẫn canh chốt lời/cắt lỗ lệnh đang giữ. |
| `/api/v1/reload_config` | `POST` | Bearer JWT | **Khởi động lại chế độ mua bán bình thường** (khôi phục cấu hình sau khi đã `stopbuy`). |
| `/api/v1/forceexit` | `POST` | Bearer JWT | **Bán khẩn cấp (Panic Sell):** Đóng một lệnh cụ thể (`tradeid: "1"`) hoặc bán toàn bộ danh mục (`tradeid: "all"`, `ordertype: "market"`). |
| `/api/v1/start` | `POST` | Bearer JWT | Khởi chạy vòng lặp giao dịch nếu bot đang ở trạng thái `stopped`. |
| `/api/v1/stop` | `POST` | Bearer JWT | Tạm dừng hoàn toàn vòng lặp giao dịch của bot. |

---

## 3. Cấu Trúc JSON Trả Về Của Các Endpoint Quan Trọng

### 3.1. `GET /api/v1/profit` (Tổng quan lợi nhuận)
```json
{
  "profit_closed_coin": 48.25,
  "profit_closed_percent": 4.82,
  "profit_all_coin": 62.40,
  "profit_all_percent": 6.24,
  "trade_count": 24,
  "closed_trade_count": 22,
  "winning_trades": 17,
  "losing_trades": 5,
  "max_drawdown": 0.0185,
  "max_drawdown_abs": 18.50
}
```

### 3.2. `GET /api/v1/status` (Danh sách lệnh đang mở)
```json
[
  {
    "trade_id": 101,
    "pair": "BTC/USDT",
    "is_open": true,
    "stake_amount": 200.0,
    "amount": 0.002941,
    "open_rate": 68000.0,
    "current_rate": 69258.0,
    "profit_ratio": 0.0185,
    "profit_abs": 3.70,
    "stop_loss_abs": 65960.0,
    "stoploss_current_dist_ratio": -0.0476,
    "open_date": "2026-10-27 06:30:00",
    "enter_tag": "XU_HUONG_TANG_EMA_RSI"
  }
]
```

### 3.3. `GET /api/v1/locks` (Trạng thái khóa bảo vệ rủi ro)
```json
{
  "lock_count": 1,
  "locks": [
    {
      "id": 1,
      "pair": "*",
      "lock_time": "2026-10-27 07:00:00",
      "lock_end_time": "2026-10-27 19:00:00",
      "reason": "MaxDrawdown",
      "active": true
    }
  ]
}
```

### 3.4. `POST /api/v1/forceexit` (Đóng lệnh khẩn cấp)
- **Payload gửi lên để đóng toàn bộ danh mục theo giá thị trường:**
  ```json
  {
    "tradeid": "all",
    "ordertype": "market"
  }
  ```
- **Payload gửi lên để đóng riêng 1 lệnh theo mã lệnh (`trade_id`):**
  ```json
  {
    "tradeid": "101",
    "ordertype": "market"
  }
  ```
