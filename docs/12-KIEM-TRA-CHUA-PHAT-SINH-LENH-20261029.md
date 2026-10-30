# Kiểm tra nguyên nhân chưa phát sinh lệnh mua

Kiểm tra trực tiếp VPS Sydney ngày 29/10/2026, khoảng 15:50–15:55 giờ Việt Nam.

## Kết luận

Hai bot đã chạy live, nhưng chưa tạo tín hiệu mua. Nguyên nhân quyết định trong khoảng kiểm tra là toàn bộ nến của các cặp được theo dõi đều có giá đóng cửa dưới EMA200. Cả nhánh mua theo xu hướng và nhánh hồi quá bán trong `VnSmartTrendStrategy.py` đều bắt buộc `close > ema200`. Bộ nghiên cứu cũng yêu cầu xu hướng tăng.

Không thay tiêu chí mua, mức vốn, SL, ROI hoặc bật force-entry trong lần kiểm tra này.

## Bằng chứng

| Chỉ tiêu | Binance | OKX |
| --- | --- | --- |
| Bắt đầu live, giờ Việt Nam | 10:21:50 | 10:25:08 |
| Chế độ và trạng thái | dry_run=false, running | dry_run=false, running |
| USDT khả dụng khi kiểm tra | 34,3140516 | 34,26308038446 |
| Vốn cấu hình mỗi bot | 34,16 USDT | 34,16 USDT |
| Cặp đang theo dõi | 7 | 5 |
| Nến đã đóng từ khi bật live, mỗi cặp tại mốc kiểm tra | 66 | 65 |
| Nến có chỉ báo hợp lệ | Toàn bộ 66/cặp | Toàn bộ 65/cặp |
| Nến close > EMA200 | 0 trên mọi cặp | 0 trên mọi cặp |
| Tín hiệu enter_long | 0 trên mọi cặp | 0 trên mọi cặp |
| Lệnh đang mở / tổng trade của bot | 0 / 0 | 0 / 0 |
| Khóa protections | 0 | 0 |
| Lịch mua 24/7 | Bật, schedule.enabled=false | Bật, schedule.enabled=false |
| Context snapshot khớp cấu hình | Có | Có |
| Snapshot nghiên cứu từ lúc bật live đã kiểm tra | 65 | 65 |
| Snapshot có ứng viên được phép mua | 0 | 0 |

Các số đếm lấy từ API `pair_candles`, `health`, `status`, `profit`, `locks` và snapshot/history trên VPS, không phải kết quả backtest. Cặp Binance gồm BTC, ETH, SOL, XRP, ADA, AVAX, LINK; OKX gồm BTC, ETH, SOL, XRP, LINK.

Ví dụ nến Binance BTC/USDT mở lúc 15:45 VN, đóng 15:50 VN: close 79.970,85 USDT, EMA200 của chiến lược khoảng 80.468,18 USDT. Giá chưa vượt EMA200 nên cả hai nhánh mua đều không đạt. Các giá trị là dữ liệu tại thời điểm kiểm tra, không phải giá hiện tại hay dự báo.

Không có lần thử mua, lỗi sizing hoặc lỗi kiểm tra snapshot được ghi nhận trong log đã rà soát. Ngân sách tính toán ngoài giờ ưu tiên khoảng 11,529 USDT/lệnh. Thiếu USDT, giới hạn 03–04 và thiếu đồng thuận AI không phải nguyên nhân hiện tại: AI đang advisory, đồng thời chưa có ứng viên kỹ thuật để gửi AI.

Hai lệnh bán BTC đã dùng để chuẩn bị vốn ban đầu không phải lệnh do chiến lược mở; chúng có receipt riêng nên không làm tăng trade_count trong dashboard Freqtrade.

## Lỗi kết nối phụ đã sửa

Log OKX có 10 lỗi WebSocket trong giai đoạn đầu, gồm thông báo bảo trì 64008 và thông báo 64010 yêu cầu bỏ cổng 8443. Freqtrade đã fallback REST, dữ liệu nến sau đó vẫn mới và đủ chỉ báo. Lỗi này không giải thích việc mọi nến đều dưới EMA200, nhưng cần sửa để tránh gián đoạn.

Đã đặt trong `user_data/config-okx.json`:

```json
{
  "exchange": {
    "ccxt_async_config": {
      "urls": {
        "api": {
          "ws": "wss://ws.okx.com/ws/v5"
        }
      }
    }
  }
}
```

Chỉ đổi endpoint WebSocket sang cổng 443 mặc định; REST, credential, các bộ lọc mua và giới hạn rủi ro giữ nguyên. OKX công bố ngừng cổng 8443 Internet từ 31/10/2026: [changelog chính thức](https://www.okx.com/docs-v5/log_en/).

Đã thử kết nối `ccxt.pro.watch_ohlcv` thực tế qua endpoint mới, nhận nến BTC/USDT thành công. Đã sao lưu cấu hình trên VPS, xác nhận không có trade mở trước khi restart riêng bot OKX. Sau restart lúc 15:54:14 VN, API trả live/running, vòng xử lý mới, không còn lỗi hoặc notice 64010 trong đoạn log sau restart đã kiểm tra. Binance không bị restart.

Kiểm thử offline: 41 tests tại `tests` và 6 tests chính sách đạt; Compose trên VPS kiểm tra hợp lệ. Việc sửa kết nối không tạo tín hiệu mua. Hai bot tiếp tục đợi điều kiện của chiến lược; SL/ROI sẽ quản lý vị thế sau khi có lệnh mua khớp, chưa có vị thế nên chưa có stoploss của chiến lược để xác minh trên sàn.
