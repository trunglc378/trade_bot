# ĐẶC TẢ YÊU CẦU PHẦN MỀM (SOFTWARE REQUIREMENTS SPECIFICATION - SRS)
**Tên dự án:** Hệ thống Giao dịch Tiền điện tử Tự động, Phân tích AI Đa nguồn & Ứng dụng Điều khiển Từ xa Tiếng Việt (**FreqBot VN Remote**)<br>
**Phiên bản:** 2.0.0<br>
**Ngày cập nhật:** 27/10/2026<br>

---

## 1. Giới Thiệu Chung

### 1.1. Mục đích tài liệu
Tài liệu SRS này quy định chi tiết toàn bộ các yêu cầu chức năng (Functional Requirements - FR) và yêu cầu phi chức năng (Non-Functional Requirements - NFR) của hệ thống **FreqBot VN Remote v2.0**, bao gồm:
1. **Tầng Lõi Giao Dịch Ngầm Đa Sàn (Freqtrade Engine trên Binance & OKX)**
2. **Bộ Lọc Khung Giờ Giao Dịch Vàng (`Asia/Ho_Chi_Minh`, mặc định `03:00–04:00` sáng)**
3. **Phân Hệ Phân Tích Thị Trường & Đề Xuất Coin Đa Nguồn AI (`ChatGPT` + `Google Gemini`)**
4. **Tầng Ứng Dụng Điều Khiển Tiếng Việt (`Android App` & `Web Dashboard`)**

---

## 2. Yêu Cầu Chức Năng Lõi Giao Dịch & Phân Tích AI (6 Phân Hệ Cốt Lõi)

### 2.1. Phân hệ 1: Thu thập dữ liệu thị trường đa sàn (Market Data Feed - `FR-MDF`)
- **`FR-MDF-01` (Hỗ trợ đa sàn thương mại Binance & OKX):** Hệ thống phải kết nối chuẩn xác với các sàn giao dịch lớn gồm **Binance** (`config.json`) và **OKX** (`config-okx.json`) thông qua thư viện `CCXT` trên thị trường Spot với đồng tiền định giá `USDT`.
- **`FR-MDF-02` (Tải dữ liệu nến, Ticker 24h & Sổ lệnh):** Lấy dữ liệu nến (OHLCV/Kline) khung `5m`, khối lượng giao dịch 24h (`quoteVolume`) và sổ lệnh (`Orderbook` Bids/Asks) thời gian thực.
- **`FR-MDF-03` (Loại bỏ nến chưa đóng & Kiểm tra độ tươi dữ liệu):** Chỉ phân tích trên các cây nến đã đóng hoàn toàn (`closed candles`), từ chối dữ liệu nếu thiếu đủ tối thiểu 200 nến liên tiếp hoặc nến cuối cùng bị trễ quá `600 giây` (10 phút).

### 2.2. Phân hệ 2: Bộ lọc Khung Giờ Giao Dịch Vàng (`Session Time Window Filter` - `FR-SCH`)
- **`FR-SCH-01` (Cấu hình khung giờ theo giờ Việt Nam `UTC+7`):** Hệ thống phải cho phép định nghĩa một hoặc nhiều khung giờ giao dịch trong khối `vn_policy.schedule.windows` theo múi giờ `Asia/Ho_Chi_Minh` (`HH:MM` bắt đầu, `HH:MM` kết thúc, và danh sách ngày trong tuần `weekdays: [0..6]` với Thứ Hai = `0`). Mặc định cấu hình sẵn khung giờ **03:00 đến 04:00 sáng** hàng ngày theo kinh nghiệm giao dịch các cặp `*/USDT`.
- **`FR-SCH-02` (Hỗ trợ khung giờ vắt qua nửa đêm):** Nếu cấu hình `start > end` (ví dụ `23:00` đến `04:00` sáng hôm sau), hàm kiểm tra `in_session` phải xử lý chính xác phần thời gian trước và sau `00:00` theo ngày bắt đầu phiên.
- **`FR-SCH-03` (Cơ chế Bất đối xứng An toàn Vốn - Entry-Only Gate):**
  - Khi nằm **ngoài** khung giờ cấu hình: Hệ thống bắt buộc **chặn 100% lệnh Mua mới (`enter_long = 0` và `_entry_allowed = False`)**.
  - Khi đang có lệnh mở: Hệ thống vẫn phải duy trì hoạt động **24/7** cho toàn bộ các cơ chế thoát lệnh: Chốt lời theo bảng `minimal_roi`, Cắt lỗ trượt `trailing_stop`, Tín hiệu thoát kỹ thuật `exit_long`, Cắt lỗ cứng trên sàn `stoploss_on_exchange` và lệnh Bán khẩn cấp `forceexit`.

### 2.3. Phân hệ 3: Phân tích Thị trường & Đề xuất Coin Đa nguồn AI (`Market Research & Multi-AI Advisor` - `FR-AIR`)
- **`FR-AIR-01` (Sàng lọc Định lượng & Chấm điểm Kỹ thuật 0–100):** Tiến trình `research/run.py` phải tự động phân tích từng cặp coin trong `pair_whitelist` (sau khi loại trừ `pair_blacklist`) và tính toán:
  - Đồng thuận xu hướng: `Close > EMA(200)` và `EMA(20) > EMA(50)`.
  - Chỉ số động lượng `RSI(14)` và tỷ lệ đột biến khối lượng `volume_ratio` so với trung bình 20 phiên.
  - Bộ lọc vi cấu trúc thị trường: Thanh khoản 24h (`quote_volume_24h >= min_quote_volume`), độ giãn chênh lệch giá (`spread <= max_spread`), độ biến động nến 5m (`volatility_5m <= max_volatility`) và biên độ biến động 1 giờ (`|hour_change| <= max_hour_change`).
- Điểm tổng hợp `score` (0–100) để sắp xếp; regime phân loại bằng luật EMA/RSI/volume/spread, chưa phải mô hình dự báo được kiểm chứng.
- **`FR-AIR-02` (Tích hợp Đa nguồn AI — OpenAI ChatGPT & Google Gemini):**
  - Module `research/providers.py` gửi dữ liệu kỹ thuật của các đồng coin đạt chuẩn tới các nhà cung cấp AI cấu hình trong `vn_policy.research.providers` (hỗ trợ `openai` qua Responses API và `gemini` qua Interactions API / model hỗ trợ structured output do tài khoản cho phép).
  - Ép kiểu dữ liệu trả về theo `JSON Schema` nghiêm ngặt: mỗi cặp coin nhận một khuyến nghị `action` thuộc `["consider", "avoid", "wait"]`, độ tự tin `confidence` (`0.0 – 1.0`) và lý do giải thích `reason` bằng Tiếng Việt.
- **`FR-AIR-03` (Cơ chế Đồng thuận AI & Quyền Phủ quyết - Quorum & Veto):**
  - Hỗ trợ 3 chế độ vận hành trong `vn_policy.research.mode`:
    1. `"off"`: Tắt kiểm tra báo cáo nghiên cứu.
    2. `"advisory"`: Yêu cầu cặp coin vượt qua bộ lọc định lượng kỹ thuật (`technical_eligible = True`) trong báo cáo còn hạn, đồng thời hiển thị nhận định của ChatGPT/Gemini lên Dashboard/App để nhà đầu tư tham khảo.
    3. `"required"`: Bắt buộc cặp coin vừa đạt chuẩn kỹ thuật, vừa có ít nhất `min_ai_votes` mô hình AI bỏ phiếu `"consider"` với `confidence >= min_ai_confidence`, và **không có bất kỳ mô hình AI nào bỏ phiếu `"avoid"` (Veto)**.
- **`FR-AIR-04` (Ràng buộc Ngữ cảnh Mật mã & Chống dữ liệu cũ):**
  - Mỗi báo cáo `user_data/research/latest.json` phải đính kèm `context_id` (mã băm `SHA-256` của cấu hình sàn, danh sách coin và tham số nghiên cứu) cùng thời gian hiệu lực `expires_at` (`ttl_seconds`). Nếu báo cáo hết hạn hoặc cấu hình thay đổi làm lệch `context_id`, hàm `report_allows` phải lập tức từ chối mở lệnh mới (Fail-Closed).

### 2.4. Phân hệ 4: Bộ não chiến lược (`Strategy Engine` - `FR-STE`)
- **`FR-STE-01` (Tín hiệu Mua đa kịch bản trên khung 5m):**
  - Kịch bản 1 (`XU_HUONG_TANG_EMA_RSI`): `Close > EMA200`, `EMA20 > EMA50`, `Close > EMA20`, `RSI` trong vùng khỏe (`45–68`) và `Volume > 1.15 * Volume_SMA20`.
  - Kịch bản 2 (`BAT_NHIP_HOI_BOLLINGER_RSI`): Xu hướng lớn vẫn giữ trên `EMA200` (`Close > EMA200`), giá chạm dải dưới Bollinger (`Close < bb_lowerband * 1.003`), `RSI < 30`, nến xanh rút chân (`Close > Open`) kèm khối lượng vượt trung bình 20 phiên.
- **`FR-STE-02` (Việt hóa luồng thông báo sự kiện):** Trong `confirm_trade_entry` và `confirm_trade_exit`, hệ thống gửi thông báo Tiếng Việt chi tiết mỗi khi mở lệnh hoặc đóng lệnh.

### 2.5. Phân hệ 5: Quản trị rủi ro & Phân bổ vốn động (`Risk Management` - `FR-RKM`)
- **`FR-RKM-01` (Công thức tính vốn động theo rủi ro - `stake_size`):**
  Trong `custom_stake_amount`, khối lượng vốn cấp cho mỗi lệnh được tính tự động theo giá trị nhỏ nhất của:
  1. Hạn mức rủi ro mỗi lệnh: $\frac{\text{Tổng vốn (Equity)} \times \text{risk\_per\_trade}}{|\text{stoploss}| + \text{cost\_buffer}}$
  2. Tỷ trọng tối đa mỗi vị thế: $\text{Equity} \times \text{max\_position\_fraction}$
  3. Hạn mức tổng vốn phơi nhiễm còn lại: $\max(0, \text{Equity} \times \text{max\_exposure\_fraction} - \text{Vốn đang mở lệnh})$
- **`FR-RKM-02` (Kiểm tra độ lệch giá khớp & Spread ngay trước khi đặt lệnh):** Tại thời điểm `confirm_trade_entry`, nếu giá khớp dự kiến lệch quá `max_entry_deviation` (mặc định `0.5%`) so với giá đóng cửa nến gần nhất hoặc `Bid-Ask Spread` thực tế vượt quá `max_spread` (mặc định `0.2%`), bot tự động hủy lệnh mua.
- **`FR-RKM-03` (Cắt lỗ cứng trên sàn & 4 lớp giáp Protections):** Bật `stoploss_on_exchange: true` (`-3%`), `Trailing Stop` và 4 lớp giáp `MaxDrawdown`, `StoplossGuard`, `LowProfitPairs`, `CooldownPeriod`.

### 2.6. Phân hệ 6: Giao diện Điều khiển Tiếng Việt (`Android App` & `Web Dashboard` - `FR-UI`)
- **`FR-UI-01` đến `FR-UI-08`:** Giữ nguyên toàn bộ các chức năng Đăng nhập JWT, Thẻ Lợi nhuận, Số dư, Bảng lệnh mở thời gian thực, Trạng thái Giáp bảo vệ rủi ro, Nút Tạm dừng Mua mới (`/api/v1/stopbuy`), Nút Bật lại Mua (`/api/v1/reload_config`) và Nút Bán khẩn cấp toàn bộ (`/api/v1/forceexit`).
- **`FR-UI-09` (Hiển thị Trạng thái Khung Giờ Cấu Hình & Bảng Đề Xuất Coin AI):**
  - Giao diện Web Dashboard và App Android phải hiển thị rõ trạng thái khung giờ giao dịch hiện tại (theo giờ Việt Nam `UTC+7`), danh sách các đồng coin đang được bộ phận nghiên cứu chấm điểm kỹ thuật (`0–100`), mức `Spread`, biến động `1h`, kết quả sàng lọc (`Qua bộ lọc` / `Không đủ điều kiện`) và nhận định chi tiết từ **ChatGPT (`openai`)** & **Google Gemini (`gemini`)**.
# Yêu cầu bổ sung ngày 27/10/2026

Đặc tả và tiêu chí chi tiết: [tài liệu 07](07-LICH-GIAO-DICH-AI-VA-PHAN-TICH.md).

| Mã | Yêu cầu bổ sung |
| --- | --- |
| FR-SES-01 | Nhiều cửa sổ UTC+7, thứ trong tuần, qua nửa đêm; chỉ lọc mua mới; loại trừ biên cuối. |
| FR-RES-01 | Market Spot USDT active, whitelist trừ blacklist; nến đã đóng và còn mới; ngưỡng volume/spread/volatility. |
| FR-AI-01 | OpenAI Responses/Gemini với JSON được xác thực; loại cặp lạ/trùng, NaN, phản hồi lỗi/cắt ngắn; không gửi secrets ra frontend. |
| FR-AI-02 | Off/advisory/required; required cần provider đồng thuận đạt ngưỡng, avoid phủ quyết; không vượt lịch/vốn/kỹ thuật. |
| FR-RES-02 | Snapshot có TTL/context, ghi nguyên tử và lưu lịch sử; thiếu/quá hạn/sai cấu hình chặn mua khi advisory/required. |
| FR-RKM-06 | Sizing theo stoploss cộng buffer, cap vị thế/tổng exposure; không nâng stake vượt ngân sách để đạt minimum sàn. |
| FR-UI-09 | Web đọc snapshot qua file picker, đánh dấu hết hạn và giải thích AI; không tự đặt lệnh từ tệp. |
| FR-EVAL-01 | Tổng hợp PnL ròng theo giờ VN; không dùng snapshot AI hiện tại cho backtest quá khứ. |

Hiệu chỉnh FR-RKM-04: MaxDrawdown xét lịch sử lệnh đóng trong cửa sổ trượt, không là giới hạn equity/lỗ ngày VN; StoplossGuard không yêu cầu liên tiếp. FR-RKM-03 phụ thuộc khả năng sàn, không bảo đảm khớp stop hoặc mức lỗ tuyệt đối.
