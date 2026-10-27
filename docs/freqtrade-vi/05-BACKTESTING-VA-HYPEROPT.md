# KIỂM THỬ LỊCH SỬ (`BACKTESTING`) & TỐI ƯU HÓA THAM SỐ (`HYPEROPT`) (TÀI LIỆU VIỆT HÓA)
**Nguồn gốc tài liệu:** `docs/backtesting.md` — Kho mã nguồn chính thức `freqtrade/freqtrade`  
**Bản dịch & Biên tập Tiếng Việt:** Dự án FreqBot VN Remote  

---

## 1. Tải Dữ Liệu Lịch Sử Từ Sàn (`download-data`)

Trước khi chạy kiểm thử lịch sử (`Backtesting`), bạn cần tải dữ liệu nến lịch sử (OHLCV) từ sàn giao dịch về thư mục `user_data/data/`:

```bash
# Tải dữ liệu 180 ngày gần nhất cho các khung thời gian 5m, 15m, 1h từ sàn cấu hình trong config.json
docker compose run --rm freqtrade download-data \
    --config /freqtrade/user_data/config.json \
    --days 180 \
    --timeframes 5m 15m 1h
```
Hoặc tải theo khoảng thời gian cố định (`--timerange`):
```bash
docker compose run --rm freqtrade download-data \
    --config /freqtrade/user_data/config.json \
    --timerange 20260101-20261027 \
    --timeframes 5m 1h
```

---

## 2. Chạy Kiểm Thử Lịch Sử (`backtesting`)

Lệnh `backtesting` mô phỏng chính xác việc mua/bán, khớp lệnh ROI, cắt lỗ (`stoploss`) và kích hoạt giáp bảo vệ (`protections` khi thêm cờ `--enable-protections`) trên dữ liệu quá khứ:

```bash
docker compose run --rm freqtrade backtesting \
    --config /freqtrade/user_data/config.json \
    --strategy VnSmartTrendStrategy \
    --timeframe 5m \
    --fee 0.001 \
    --enable-protections
```

### Giải thích các cờ quan trọng:
- `--strategy VnSmartTrendStrategy`: Tên lớp chiến lược cần kiểm thử.
- `--timeframe 5m`: Khung thời gian nến chính (5 phút).
- `--fee 0.001`: Phí giao dịch mỗi chiều (`0.001` = `0.1%`, chuẩn phí Spot trên Binance).
- `--enable-protections`: Bật kiểm tra luôn cả các bộ khóa rủi ro (`MaxDrawdown`, `StoplossGuard`, `CooldownPeriod`) trong quá trình Backtest để kết quả sát với thực tế nhất.

---

## 3. Cách Đọc Bảng Báo Cáo Kết Quả Backtest (Dịch Sang Tiếng Việt)

Sau khi chạy xong `backtesting`, Freqtrade xuất ra bảng thống kê chi tiết. Dưới đây là cách giải nghĩa các chỉ số quan trọng nhất:

| Chỉ số trên bảng Backtest | Ý nghĩa Tiếng Việt & Tiêu chuẩn đánh giá |
| :--- | :--- |
| **`Trades`** | Tổng số lệnh đã thực hiện trong kỳ kiểm thử (nên có tối thiểu `> 100 lệnh` để có ý nghĩa thống kê). |
| **`Avg Profit %`** | Tỷ lệ lãi/lỗ trung bình trên mỗi lệnh (sau khi đã trừ phí sàn). Cần lớn hơn `0.3% - 0.5%`. |
| **`Tot Profit USDT` / `Tot Profit %`** | Tổng lợi nhuận thu được tính bằng USDT và tỷ lệ % tăng trưởng tài khoản. |
| **`Win / Draw / Loss` & `Win%`** | Số lệnh Thắng / Hòa / Thua và Tỷ lệ thắng (`Winrate`). |
| **`Max Drawdown` (Account %)** | **Mức sụt giảm tài khoản tối đa từ đỉnh xuống đáy.** Chỉ số sống còn để đánh giá rủi ro (khuyến nghị giữ `< 15%`). |
| **`Profit Factor`** | Tổng tiền lãi từ các lệnh thắng chia cho tổng tiền lỗ từ các lệnh thua. Cần đạt `> 1.3`. |
| **`Sharpe Ratio` / `Sortino`** | Tỷ suất lợi nhuận điều chỉnh theo rủi ro (càng cao càng ổn định). |
| **`EXIT REASON STATS`** | Thống kê kết quả theo từng lý do đóng lệnh (`roi`, `stop_loss`, `trailing_stop_loss`, `exit_signal`). |
