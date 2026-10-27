# TỔNG QUAN VỀ DỰ ÁN MÃ NGUỒN MỞ FREQTRADE (TÀI LIỆU VIỆT HÓA)
**Nguồn gốc tài liệu:** [Freqtrade Official Documentation](https://www.freqtrade.io/en/stable/) — Kho mã nguồn: `github.com/freqtrade/freqtrade`  
**Bản dịch & Biên tập Tiếng Việt:** Dự án FreqBot VN Remote  

---

## 1. Freqtrade Là Gì?

**Freqtrade** là phần mềm giao dịch tiền điện tử tự động bằng thuật toán (Crypto Algorithmic Trading Bot) miễn phí và mã nguồn mở hàng đầu thế giới, được viết bằng ngôn ngữ **Python (3.10+)**. Hệ thống được thiết kế để hỗ trợ đầy đủ mọi sàn giao dịch lớn (Binance, Bybit, OKX, Gate.io, Bitget, Kraken, KuCoin...) thông qua thư viện chuẩn hóa **CCXT**, và có thể được điều khiển hoàn toàn từ xa thông qua **REST API / WebSocket**, **Telegram Bot** hoặc **Ứng dụng Di động / Web UI tùy biến**.

Ngoài việc thực thi lệnh tự động 24/7, Freqtrade tích hợp sẵn bộ công cụ hoàn chỉnh cho toàn bộ vòng đời phát triển chiến lược định lượng:
- **Tải dữ liệu lịch sử (`download-data`):** Tải dữ liệu nến (OHLCV) và dữ liệu khớp lệnh từ sàn.
- **Kiểm thử lịch sử (`Backtesting`):** Chạy mô phỏng chiến lược trên dữ liệu quá khứ với độ chính xác cao và tốc độ nhanh.
- **Tối ưu hóa tham số (`Hyperopt`):** Tìm kiếm bộ tham số mua/bán/cắt lỗ tối ưu bằng thuật toán máy học (Scikit-Optimize / Optuna).
- **Trí tuệ nhân tạo thích ứng (`FreqAI`):** Huấn luyện lại mô hình Machine Learning định kỳ theo dữ liệu thị trường mới nhất.
- **Giao dịch giả lập thời gian thực (`Dry-Run` / Paper Trading):** Kiểm thử chiến lược với luồng giá thật của sàn nhưng không tốn tiền thật.
- **Giao dịch thực tế (`Live Trading`):** Hỗ trợ cả giao dịch giao ngay (**Spot**) và hợp đồng tương lai (**Futures / Vĩnh cửu** với đòn bẩy).

---

## 2. Các Tính Năng Cốt Lõi Của Freqtrade

1. **Phát triển Chiến lược bằng Python (`IStrategy`):**
   - Viết chiến lược giao dịch dễ dàng dựa trên thư viện `pandas` DataFrame.
   - Hỗ trợ hàng trăm chỉ báo phân tích kỹ thuật từ `TA-Lib`, `pandas-ta`, `technical`.
2. **Danh sách cặp giao dịch linh hoạt (`Pairlists`):**
   - Hỗ trợ danh sách cố định (`StaticPairList`) hoặc danh sách lọc tự động theo khối lượng giao dịch lớn nhất 24h (`VolumePairList`), lọc theo biến động giá (`VolatilityFilter`), lọc theo chênh lệch giá (`SpreadFilter`).
3. **Quản trị Rủi ro & Bảo vệ Vốn chuyên sâu (`Stoploss` & `Protections`):**
   - Hỗ trợ cắt lỗ tĩnh (`Static Stoploss`), cắt lỗ trượt khóa lợi nhuận (`Trailing Stoploss`), cắt lỗ động tùy chỉnh theo công thức riêng (`custom_stoploss`) và đặt lệnh cắt lỗ cứng trực tiếp trên máy chủ sàn (`stoploss_on_exchange`).
   - Tích hợp sẵn 4 lớp giáp bảo vệ tự động (`Protections`):
     - `MaxDrawdown`: Khóa bot khi lỗ vượt hạn mức cho phép trong khoảng thời gian nhất định.
     - `StoplossGuard`: Khóa bot hoặc cặp coin khi dính chuỗi lệnh cắt lỗ liên tiếp.
     - `CooldownPeriod`: Tạm nghỉ sau khi đóng lệnh để tránh mua đuổi lặp lại.
     - `LowProfitPairs`: Tạm khóa các cặp coin có hiệu suất kém.
4. **Lưu trữ Bền vững & Đồng bộ Trạng thái (`SQLite Persistence`):**
   - Toàn bộ trạng thái lệnh đang mở (`Trades`), lịch sử khớp lệnh (`Orders`) và trạng thái khóa bảo vệ (`PairLocks`) được lưu vào cơ sở dữ liệu `SQLite` (`tradesv3.sqlite` hoặc `tradesv3.dryrun.sqlite`).
   - Khi máy chủ VPS khởi động lại sau sự cố, Freqtrade tự động đối chiếu trạng thái trong SQLite với trạng thái thực tế trên sàn giao dịch để tiếp tục quản lý vị thế mà không bị mất dấu lệnh.
5. **Máy chủ REST API & WebSocket tích hợp (`api_server`):**
   - Cho phép kết nối từ ứng dụng Android tiếng Việt (`FreqBot VN Remote`), Web Dashboard tiếng Việt hoặc bất kỳ hệ thống giám sát bên ngoài nào thông qua xác thực JWT (`Bearer Token`).

---

## 3. Các Sàn Giao Dịch Được Hỗ Trợ Chính Thức

Freqtrade kết nối qua thư viện `CCXT` và đã được kiểm thử chuyên sâu (bao gồm cả tính toán phí, bước giá `tickSize`, bước khối lượng `stepSize` và lệnh cắt lỗ trên sàn) với các sàn lớn:
- **Binance** (Spot & USDT-M Futures)
- **Bybit** (Spot & Perpetual Futures)
- **OKX** (Spot & Futures)
- **Bitget**, **Gate.io**, **HTX (Huobi)**, **Kraken**, **KuCoin**, **Bitmart**, **BingX**
- Sàn phi tập trung (**Hyperliquid DEX**)

---

## 4. Cấu Trúc Thư Mục `user_data/` Tiêu Chuẩn Trong Freqtrade

Khi làm việc với Freqtrade (đặc biệt qua Docker), toàn bộ dữ liệu người dùng, cấu hình và chiến lược được gói gọn trong thư mục `user_data/`:

```text
user_data/
├── config.json                 # File cấu hình chính của Bot (Sàn, Vốn, API Server, Protections)
├── tradesv3.sqlite             # Cơ sở dữ liệu SQLite lưu lệnh chạy thật (Live)
├── tradesv3.dryrun.sqlite      # Cơ sở dữ liệu SQLite lưu lệnh chạy thử (Dry-Run)
├── data/                       # Chứa dữ liệu nến lịch sử tải về phục vụ Backtest (Feather/JSON)
├── logs/                       # Nhật ký hoạt động chi tiết của Bot (freqtrade.log)
├── strategies/                 # Chứa các file chiến lược Python (.py)
│   └── VnSmartTrendStrategy.py # Chiến lược giao dịch Tiếng Việt của dự án
├── backtest_results/           # Lưu kết quả các lần chạy kiểm thử lịch sử
└── hyperopt_results/           # Lưu kết quả tối ưu hóa tham số
```
