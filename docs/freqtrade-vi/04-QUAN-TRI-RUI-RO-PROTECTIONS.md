# QUẢN TRỊ RỦI RO TRONG FREQTRADE: CẮT LỖ (`STOPLOSS`) & GIÁP BẢO VỆ (`PROTECTIONS`) (TÀI LIỆU VIỆT HÓA)
**Nguồn gốc tài liệu:** `docs/stoploss.md` & `docs/includes/protections.md` — Kho mã nguồn chính thức `freqtrade/freqtrade`  
**Bản dịch & Biên tập Tiếng Việt:** Dự án FreqBot VN Remote  

---

## 1. Cơ Chế Cắt Lỗ (`Stoploss`) Trong Freqtrade

Cắt lỗ (`Stoploss`) là giới hạn thua lỗ tối đa mà bạn chấp nhận cho một vị thế giao dịch trước khi bot tự động đóng lệnh để bảo toàn phần vốn còn lại.

### 1.1. Cắt lỗ nằm trên máy chủ sàn (`stoploss_on_exchange`) vs Cắt lỗ trong bộ nhớ Bot
- **Cắt lỗ trong bộ nhớ Bot (`stoploss_on_exchange: false`):** Bot liên tục kiểm tra giá hiện tại mỗi vài giây. Khi giá giảm chạm mốc `stop_loss_abs`, bot mới gửi lệnh bán lên sàn. *Nhược điểm:* Nếu đúng lúc thị trường sập mạnh mà máy chủ VPS bị mất mạng hoặc mất điện, lệnh sẽ không được đóng.
- **Cắt lỗ cứng nằm trên máy chủ sàn (`stoploss_on_exchange: true` — KHUYẾN NGHỊ BẮT BUỘC):** Ngay sau khi lệnh mua hoàn tất, Freqtrade lập tức đặt một lệnh `STOP_LOSS_LIMIT` hoặc `STOP_MARKET` trực tiếp lên máy chủ của sàn giao dịch (Binance/Bybit). Khi dùng kết hợp với `trailing_stop`, cứ mỗi `stoploss_on_exchange_interval` giây (ví dụ 60 giây), bot sẽ tự động cập nhật nâng mức giá cắt lỗ trên sàn lên cao hơn theo đà tăng của giá.

---

## 2. Bộ Giáp Bảo Vệ Tự Động (`Protections`)

**Protections** là hệ thống "Cầu dao ngắt mạch tự động" (Circuit Breaker) tích hợp sẵn trong Freqtrade nhằm bảo vệ tài khoản của bạn trước những biến động bất thường của thị trường (như cú sập dây chuyền Flash Crash) bằng cách tạm thời khóa không cho mở lệnh mới trên một cặp coin hoặc khóa toàn bộ bot.

Hiện tại Freqtrade cung cấp **4 bộ bảo vệ chính** được cấu hình ngay trong thuộc tính `protections` của lớp Chiến lược (`IStrategy`):

### 2.1. `StoplossGuard` — Chống dính chuỗi lệnh cắt lỗ liên tiếp
Khi thị trường chung (Bitcoin) bất ngờ sập mạnh, hầu hết các đồng Altcoin sẽ giảm theo cùng lúc. `StoplossGuard` giúp tự động khóa bot nếu phát hiện có `N` lệnh bị dính Stop-Loss trong một khoảng thời gian nhìn lại (`lookback_period_candles`).

```python
{
    "method": "StoplossGuard",
    "lookback_period_candles": 72,   # Nhìn lại 72 cây nến (6 giờ với nến 5m)
    "trade_limit": 3,                # Nếu có từ 3 lệnh bị cắt lỗ trở lên
    "stop_duration_candles": 72,     # Khóa bot trong 72 nến tiếp theo (6 giờ)
    "only_per_pair": False           # False = Khóa toàn bộ Bot; True = Chỉ khóa cặp coin đó
}
```

### 2.2. `MaxDrawdown` — Giới hạn mức sụt giảm tài khoản tối đa trong ngày
Nếu tổng mức thua lỗ thực tế (Realized Drawdown) của các lệnh đã đóng trong khoảng thời gian nhìn lại vượt quá tỷ lệ phần trăm cho phép (`max_allowed_drawdown`), toàn bộ bot sẽ bị khóa không cho vào lệnh mới.

```python
{
    "method": "MaxDrawdown",
    "lookback_period_candles": 288,  # Nhìn lại 288 cây nến (24 giờ với nến 5m)
    "trade_limit": 2,                # Tính khi có ít nhất 2 lệnh đã đóng
    "stop_duration_candles": 144,    # Khóa toàn bộ giao dịch mua mới trong 12 giờ (144 nến 5m)
    "max_allowed_drawdown": 0.05     # Hạn mức lỗ tối đa cho phép: 5% (0.05)
}
```

### 2.3. `LowProfitPairs` — Cách ly các cặp Coin đang có hiệu suất kém
Nếu một cặp coin cụ thể liên tục gây lỗ vượt quá ngưỡng `required_profit` (ví dụ `-3%`), `LowProfitPairs` sẽ chỉ khóa riêng cặp coin đó mà vẫn cho phép bot giao dịch các cặp coin tốt khác.

```python
{
    "method": "LowProfitPairs",
    "lookback_period_candles": 144,  # Nhìn lại 12 giờ (144 nến 5m)
    "trade_limit": 2,                # Có từ 2 lệnh đóng trên cặp coin này
    "stop_duration_candles": 72,     # Khóa riêng cặp coin này trong 6 giờ
    "required_profit": -0.03         # Nếu tổng lợi nhuận của cặp này thấp hơn -3%
}
```

### 2.4. `CooldownPeriod` — Thời gian nghỉ ngơi sau khi đóng lệnh
Ngăn không cho bot vừa bán chốt lời hoặc cắt lỗ một cặp coin xong lại lập tức mua lại chính cặp coin đó ngay ở cây nến tiếp theo.

```python
{
    "method": "CooldownPeriod",
    "stop_duration_candles": 6       # Nghỉ 6 cây nến (30 phút với nến 5m) sau khi đóng lệnh
}
```

---

## 3. Cách Ứng Dụng Android (`FreqBot VN Remote`) Giám Sát Trạng Thái Khóa `Protections`

Mọi trạng thái khóa do `Protections` kích hoạt đều được Freqtrade lưu vào bảng `pairlocks` trong SQLite và trả về qua Endpoint `GET /api/v1/locks`.
- Khi `pair == "*"` (dấu sao): Toàn bộ Bot đang bị khóa mua mới (do `MaxDrawdown` hoặc `StoplossGuard` toàn cục).
- Khi `pair == "SOL/USDT"`: Chỉ riêng cặp `SOL/USDT` đang bị tạm khóa (do `CooldownPeriod` hoặc `LowProfitPairs`).
Ứng dụng Android **FreqBot VN Remote** tự động dịch các lý do khóa này sang Tiếng Việt và hiển thị ngay trên thẻ **Trạng thái Giáp Bảo Vệ Rủi Ro** kèm thời gian mở khóa chính xác.
