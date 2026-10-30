# Vận hành Binance và OKX live trên AWS Sydney

> Kiểm tra bổ sung 15:50–15:55 ngày 29/10: xem [báo cáo nguyên nhân chưa có lệnh](12-KIEM-TRA-CHUA-PHAT-SINH-LENH-20261029.md). Đã sửa WebSocket OKX từ 8443 sang 443; các điều kiện giao dịch giữ nguyên.

Triển khai ngày 29/10/2026, kiểm tra trạng thái lúc khoảng 10:25 giờ Việt Nam.

## Máy chủ và phiên bản

- EC2 `i-053cea1c286785e60`, vùng Sydney `ap-southeast-2`.
- Public IP hiện tại: `54.66.15.21`; SSH user `ubuntu`.
- Thư mục máy chủ: `/home/ubuntu/trade_bot/freqtrade-bot`.
- Freqtrade `2026.9`, CCXT `4.5.84`; image được pin tại digest `sha256:9d67afb8eb5f4e1210f4fb067efcbd5e005bd4f1c27f6f3888b8b9fc7f9b5199`.
- Docker và Chrony đã bật tự khởi động. Các container dùng `restart: unless-stopped`.

## Kết quả kiểm chứng thực tế

- API Spot công khai Binance và OKX đều trả HTTP 200 từ Sydney.
- API tài khoản Binance xác thực thành công; quyền Spot bật, quyền rút tiền tắt.
- OKX ban đầu từ chối do whitelist, mã 50110. Sau khi chủ tài khoản thêm IP VPS, API xác thực thành công với quyền `read_only,trade`.
- Hai bot trả `dry_run: false`, `state: running`, chiến lược `VnSmartTrendStrategy`, tối đa 2 trade/sàn; health báo vòng xử lý mới.
- Tại thời điểm kiểm tra cuối chưa có lệnh chiến lược mở. Hai lệnh bán BTC chuẩn bị vốn dưới đây được thực hiện độc lập, không thuộc database trade của chiến lược.
- Worker ghi snapshot Binance/OKX riêng, mỗi 300 giây; snapshot hết hạn sẽ chặn mua mới. Đã sửa lỗi worker OKX ghi đè `latest.json` của Binance và bổ sung regression test.
- Dashboard HTTP trả 200. API bot và dashboard chỉ bind localhost của VPS; truy cập qua SSH tunnel.
- Đã tạo bản sao SQLite nhất quán bằng SQLite backup API cho hai database live và tải về `freqtrade-bot/user_data/backups/` trên máy cá nhân. Đây là backup tại thời điểm bàn giao, không phải lịch backup định kỳ.
- Chưa có xác minh khớp lệnh mua và đặt stoploss trên sàn của chiến lược vì chưa xuất hiện tín hiệu mua; không force-buy để tạo kết quả kiểm thử.
- Chưa thử reboot toàn VPS sau khi bật live. Tự khởi động đã được cấu hình, không đồng nghĩa mọi sự cố VPS/sàn đều tự phục hồi.

## Vốn và các giao dịch chuẩn bị vốn đã được ủy quyền

Mỗi bot được cấu hình `available_capital: 34.16` USDT, `max_open_trades: 2`. Không tăng vốn lên toàn bộ danh mục.

| Sàn | Thao tác chuẩn bị vốn | USDT khả dụng ngay sau chuyển đổi |
| --- | --- | --- |
| Binance | Hoàn trả 0,00043 BTC từ Flexible Earn về Spot, bán 0,00043 BTC | 34,3140516 |
| OKX | Bán 0,00042735 BTC có sẵn trong ví Trading | 34,26308038446 |

Các con số là ảnh chụp sau chuyển đổi, sẽ thay đổi khi bot giao dịch. Phiếu kết quả riêng lưu trong `user_data/binance-initial-funding.private.json` và `user_data/okx-initial-funding.private.json` trên VPS và bản sao máy cá nhân. Script cấp vốn chỉ dùng một lần, không chạy định kỳ và có receipt chống thực hiện lại khi trạng thái chưa được đối soát.

Các coin còn lại không được tự đưa vào danh mục trade của Freqtrade. `available_capital` là hạn mức tính toán trong bot, không phải khóa tài sản tại sàn.

## Cấu hình đang hoạt động

- Binance: config gốc + `user_data/config.live.binance.private.json`, DB `user_data/tradesv3.binance.live.sqlite`.
- OKX: config gốc + `config-okx.json` + `user_data/config.live.okx.private.json`, DB `user_data/tradesv3.okx.live.sqlite`.
- `.env` trên VPS trỏ vào các tệp live và pin image digest; bind API tại `127.0.0.1`.
- Cấu hình private gốc trên máy cá nhân vẫn dry-run; Compose mặc định trên máy cá nhân không thay thế cấu hình live trên VPS.
- Tệp private live và thông tin đăng nhập dashboard có bản sao tại `E:\Project\trade_bot\freqtrade-bot\user_data`, bị Git ignore. Giữ bí mật, không commit hoặc chia sẻ.
- Mật khẩu điều khiển/JWT/WS mẫu đã được thay bằng giá trị ngẫu nhiên riêng cho từng bot.

Lịch cho phép xét mua 24/7, ưu tiên 03:00–04:00 giờ Việt Nam bằng hệ số vốn; ngoài giờ hệ số 0,75. Không dành riêng slot cho giờ ưu tiên. AI đang `advisory`, không bắt buộc đồng thuận; chưa có ứng viên kỹ thuật đủ điều kiện trong các snapshot đầu nên không khẳng định đã có lượt gọi AI thành công. Stoploss -3%, trailing bật; đây là cấu hình đã có, chưa được chứng minh tối ưu hoặc bảo đảm giới hạn lỗ thực tế.

## Mở dashboard trên Windows

Từ PowerShell tại gốc dự án:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\freqtrade-bot\open_live_dashboard.ps1
```

Script mở tunnel SSH 8080/8081/8090 tới VPS và mở `http://127.0.0.1:8090`. Nếu tunnel đang chạy, không mở thêm bản thứ hai; script sẽ báo cổng đã được sử dụng. PID tunnel được in ra lúc tạo; đóng tunnel bằng `Stop-Process -Id PID` không làm dừng bot trên VPS.

- API Binance trên dashboard: `http://127.0.0.1:8080`.
- API OKX trên dashboard: `http://127.0.0.1:8081`.
- Username/password nằm trong tệp riêng `freqtrade-bot/user_data/deployment-access.private.json`, mỗi sàn có mật khẩu riêng.
- Để xem snapshot nghiên cứu: SCP `latest.json` hoặc `latest-okx.json` từ VPS rồi dùng ô chọn JSON trên dashboard. Endpoint nghiên cứu của mock server không tồn tại trong Freqtrade thật.

## Kiểm tra và điều khiển

```powershell
ssh -i .\docs\bot_trade.pem ubuntu@54.66.15.21
```

Trên VPS:

```bash
cd ~/trade_bot/freqtrade-bot
sudo docker compose --profile okx ps -a
sudo docker compose --profile okx logs --tail 100 freqtrade freqtrade-okx research research-okx
sudo docker stats --no-stream
df -h /
```

Log có thể chứa thông tin riêng; không công khai toàn bộ log. Dùng StopBuy trên dashboard nếu muốn tạm dừng mua, giữ bot xử lý lệnh đã mở. Không dùng tắt VPS/`compose down` như thao tác tạm dừng mua. Với Binance stop-limit, lệnh có thể không khớp khi gap giá; ROI và cập nhật trailing cần bot đang hoạt động.

Sau khi chủ động Stop/Start EC2, kiểm tra public IP mới, cập nhật whitelist OKX/Binance nếu có và tham số `-Server` của helper SSH. Địa chỉ tự cấp hiện tại chưa phải Elastic IP. Không tự cấp thêm tài nguyên AWS trả phí hoặc nâng cấp Paid Plan trong phiên triển khai này.

Free Plan AWS đang dùng credit có thời hạn; VPS sẽ không chạy miễn phí vô hạn. Theo dõi credit và sao lưu trước khi hết hạn. Chưa thiết lập cảnh báo độc lập khi cả VPS mất kết nối hoặc backup ngoại vi định kỳ; không xem dashboard nội bộ là hệ thống cảnh báo sự cố toàn máy chủ.
