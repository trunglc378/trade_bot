# HƯỚNG DẪN XÂY DỰNG & TÙY BIẾN CHIẾN LƯỢC GIAO DỊCH (`IStrategy`) (TÀI LIỆU VIỆT HÓA)
**Nguồn gốc tài liệu:** `docs/strategy-customization.md` — Kho mã nguồn chính thức `freqtrade/freqtrade`  
**Bản dịch & Biên tập Tiếng Việt:** Dự án FreqBot VN Remote  

---

## 1. Cấu Trúc Giải Phẫu Của Một File Chiến Lược Freqtrade

Mọi chiến lược trong Freqtrade là một lớp Python kế thừa từ `IStrategy` (nằm trong thư mục `user_data/strategies/`). Một chiến lược chuẩn bao gồm **4 phần bắt buộc**:
1. **Khai báo tham số cốt lõi:** Khung thời gian (`timeframe`), Bảng chốt lời tối thiểu theo thời gian (`minimal_roi`), Mức cắt lỗ (`stoploss`), Số nến khởi động (`startup_candle_count`).
2. **`populate_indicators(dataframe, metadata)`:** Tính toán các chỉ báo kỹ thuật (`EMA`, `RSI`, `MACD`, `Bollinger Bands`...) và thêm vào các cột của `DataFrame`.
3. **`populate_entry_trend(dataframe, metadata)`:** Xác định điều kiện **Mua / Vào lệnh** bằng cách gán cột `enter_long = 1` và đặt nhãn lý do mua vào cột `enter_tag`.
4. **`populate_exit_trend(dataframe, metadata)`:** Xác định điều kiện **Bán / Thoát lệnh** bằng cách gán cột `exit_long = 1` và đặt nhãn lý do bán vào cột `exit_tag`.

---

## 2. Giải Thích Chi Tiết Các Thuộc Tính Trong Lớp `IStrategy`

### 2.1. Bảng Chốt Lời Tối Thiểu Theo Thời Gian (`minimal_roi`)
`minimal_roi` là một từ điển quy định mức lợi nhuận tối thiểu (đã tính phí) mà bot sẽ tự động chốt lời sau khi lệnh đã mở được số phút tương ứng:
```python
minimal_roi = {
    "0": 0.06,    # Ngay khi vào lệnh (từ phút thứ 0): Nếu lãi chạm +6% -> Chốt lời ngay
    "30": 0.035,  # Sau 30 phút giữ lệnh: Chỉ cần lãi đạt +3.5% -> Chốt lời
    "60": 0.02,   # Sau 60 phút giữ lệnh: Chỉ cần lãi đạt +2.0% -> Chốt lời
    "120": 0.01   # Sau 120 phút giữ lệnh: Chỉ cần lãi đạt +1.0% -> Chốt lời thu hồi vốn
}
```

### 2.2. Mức Cắt Lỗ Cố Định (`stoploss`) & Cắt Lỗ Trượt (`trailing_stop`)
```python
# Cắt lỗ cứng ở mức -3% (giá giảm 3% so với giá mua vào)
stoploss = -0.03

# Bật chế độ Cắt lỗ trượt (Trailing Stop) để khóa lợi nhuận khi giá tăng
trailing_stop = True
trailing_only_offset_is_reached = True
trailing_stop_positive = 0.01          # Dịch điểm cắt lỗ theo sau giá đỉnh 1.0%
trailing_stop_positive_offset = 0.025  # Chỉ kích hoạt trượt khi lệnh đã lãi từ +2.5% trở lên
```

### 2.3. Số Nến Lịch Sử Cần Tải Khi Khởi Động (`startup_candle_count`)
Nếu chiến lược của bạn sử dụng đường trung bình động dài nhất là `EMA 200`, bạn cần đặt:
```python
startup_candle_count: int = 200
```
Để Freqtrade tải trước tối thiểu 200 cây nến lịch sử trước khi bắt đầu tính toán tín hiệu.

---

## 3. Quy Tắc Vàng Chống Lỗi "Nhìn Trước Tương Lai" (Look-Ahead Bias)

Khi viết hàm `populate_indicators`, `populate_entry_trend` và `populate_exit_trend`, Freqtrade xử lý toàn bộ bảng dữ liệu (`DataFrame`) bằng phép toán vector hóa của `pandas`:
- **TUYỆT ĐỐI KHÔNG** sử dụng `.shift(-1)` (lấy giá của cây nến tương lai), hoặc dùng hàm `.max()`, `.min()`, `.mean()` trên toàn bộ cột mà không dùng cửa sổ trượt `.rolling(window)`.
- Nếu vi phạm, kết quả kiểm thử lịch sử (`Backtesting`) sẽ lãi ảo cực cao nhưng khi chạy thực tế (`Dry-Run` / `Live`) sẽ thua lỗ vì ngoài đời thực không thể biết giá của cây nến tiếp theo.

---

## 4. Các Hàm Callback Nâng Cao & Việt Hóa Cảnh Báo Đẩy

Freqtrade cung cấp các hàm sự kiện (Callbacks) cho phép bạn kiểm duyệt lệnh lần cuối hoặc bắn thông báo Tiếng Việt sang ứng dụng điều khiển / Telegram:

### 4.1. `confirm_trade_entry()` — Xác nhận trước khi đặt lệnh Mua
Được gọi ngay trước khi bot gửi lệnh Mua lên sàn. Nếu trả về `False`, lệnh mua sẽ bị hủy bỏ:
```python
def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                        time_in_force: str, current_time, entry_tag: str | None,
                        side: str, **kwargs) -> bool:
    self.dp.send_msg(
        f"🟢 [VÀO LỆNH MỚI]\n"
        f"• Cặp giao dịch: {pair}\n"
        f"• Giá mua dự kiến: {rate:.4f} USDT\n"
        f"• Khối lượng: {amount:.6f}\n"
        f"• Lý do mua (Tín hiệu): {entry_tag or 'TIN_HIEU_CHINH'}\n"
        f"• Ngưỡng cắt lỗ bảo vệ: {self.stoploss * 100:.1f}%"
    )
    return True
```

### 4.2. `confirm_trade_exit()` — Xác nhận trước khi đặt lệnh Bán
Được gọi ngay trước khi bot đóng lệnh (do chốt lời ROI, tín hiệu bán, cắt lỗ hoặc bán khẩn cấp):
```python
def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float,
                       rate: float, time_in_force: str, exit_reason: str,
                       current_time, **kwargs) -> bool:
    profit_ratio = trade.calc_profit_ratio(rate)
    bieu_tuong = "💰 CHỐT LỜI" if profit_ratio >= 0 else "🛑 CẮT LỖ"
    self.dp.send_msg(
        f"{bieu_tuong} [{pair}]\n"
        f"• Giá mua: {trade.open_rate:.4f} -> Giá bán: {rate:.4f}\n"
        f"• Kết quả dự kiến: {profit_ratio * 100:.2f}%\n"
        f"• Lý do đóng lệnh: {exit_reason}"
    )
    return True
```
