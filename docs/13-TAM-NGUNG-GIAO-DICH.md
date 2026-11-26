# Tạm ngừng giao dịch và AI — 26/11/2026

## Trạng thái thực tế

Đã tạm ngừng cả bản local và AWS ngày 26/11/2026, khoảng 14:37–14:38 giờ Việt Nam. Thao tác AWS thực hiện qua EC2 Instance Connect với user ubuntu sau khi người dùng đăng nhập AWS Console. Instance `i-053cea1c286785e60` (`freqbot-vn-live`), Sydney, IP `54.66.15.21`.

Kết quả thực tế trên AWS:

- Dừng `freqtrade_vn_research_binance` và `freqtrade_vn_research_okx`; trạng thái Exited (137) sau thời gian chờ dừng container.
- Gọi `/api/v1/stopbuy` trên từng bot; cả hai phản hồi `paused, no more entries will occur from now`. Phiên bản đang chạy giữ `max_open_trades = 2` trong show_config nhưng chuyển state sang `paused` (khác với việc chỉnh max_open_trades trong file).
- `/api/v1/status` trả 0 vị thế mở trên cả hai bot; danh sách lệnh mở trong dữ liệu bot rỗng. Chưa đối soát độc lập mọi lệnh thủ công ngoài bot trên sàn.
- Sau xác nhận trên, dừng `freqtrade_vn_binance` và `freqtrade_vn_okx`; trạng thái Exited (130).
- Tắt tự khởi động lại cho cả bốn container: Docker restart policy `no`.
- Lưu vào bốn file cấu hình hiệu lực `config.json`, `config-okx.json`, `config.live.binance.private.json`, `config.live.okx.private.json`: max_open_trades 0, initial_state stopped, force_entry và position_adjustment disabled, trading_paused true, research mode off, providers rỗng, ai_control disabled. Thêm marker `user_data/research/AI_PAUSE`.
- Sao lưu cấu hình trước thay đổi tại `/home/ubuntu/.local/state/freqbot-suspension/20261126T143710`, ngoài Git, thư mục quyền 0700 và file quyền 0600. Không sao chép các bản private về máy local.
- Kiểm tra độc lập lại bốn container và bốn file cấu hình bằng assert, kết quả `VERIFICATION_OK`. Không bán tài sản, không đổi database, không thu hồi API key toàn tài khoản. Các lệnh đã gửi tới nhà cung cấp trước khi dừng không thể được thu hồi bằng thao tác này.

Không tự bật lại. Lệnh `docker compose up` có thể khôi phục restart policy trong Compose; khi cần chạy lại phải rà soát toàn bộ cấu hình và chỉ thực hiện theo yêu cầu mới.

## Thay đổi local

- `config.json`: `max_open_trades = 0`, `force_entry_enable = false`, `position_adjustment_enable = false`, `vn_policy.trading_paused = true`, research `mode = off`; AI control tiếp tục disabled.
- Overlay Gemini đặt research `mode = off`.
- Strategy từ chối vào lệnh và cấp thêm vốn khi `trading_paused = true`; hook thoát lệnh tiếp tục hoạt động.
- Đã tạo marker local `user_data/research/AI_PAUSE`, được bỏ qua bởi Git.
- Không đổi dry-run, database, API key hay bán toàn bộ tài sản.

Các cấu hình private, biến môi trường và overlay được áp dụng sau có thể ghi đè cấu hình gốc. Khi triển khai phải kiểm tra cấu hình hiệu lực của từng bot.

## Quy trình tham khảo trên AWS (đã thực hiện)

Mở EC2 tại Sydney (`ap-southeast-2`), chọn instance đang thực sự chạy bot và mở Instance Connect hoặc Session Manager. Instance đã được ghi nhận trong tài liệu là `i-053cea1c286785e60`; kiểm tra lại trước khi thao tác.

Trong terminal Linux của EC2, dừng riêng worker AI:

```bash
cd /home/ubuntu/trade_bot/freqtrade-bot
sudo docker compose --profile okx stop research research-okx
sudo docker compose --profile okx ps -a
```

Xác minh cả hai worker research có trạng thái Exited. Không chạy lại `compose up` cho research trong giai đoạn tạm ngừng.

Với mỗi bot Binance và OKX, dùng dashboard/API đang đăng nhập để gọi `POST /api/v1/stopbuy` (Pause/Stop buying). Xác minh `GET /api/v1/show_config` cho thấy state `paused` trên phiên bản đang chạy; không chỉ dựa vào max_open_trades vì giá trị này có thể vẫn giữ nguyên. Xem `GET /api/v1/status` để kiểm tra vị thế đang mở. Theo [tài liệu Freqtrade REST API](https://www.freqtrade.io/en/stable/rest-api/), stopbuy chặn mở vị thế mới và giữ xử lý thoát các vị thế hiện có.

Ghi cấu hình tạm ngừng vào các file cấu hình đang được container sử dụng, bao gồm file private cuối cùng nếu có ghi đè: `max_open_trades: 0`, `force_entry_enable: false`, `position_adjustment_enable: false`, research `mode: off`, `ai_control.enabled: false`. Giữ nguyên exchange, thông tin tài khoản, dry_run và database. Nếu đang có DCA hoặc lệnh mua chờ, kiểm tra riêng: stopbuy không phải bằng chứng rằng lệnh chờ đã bị hủy hoặc DCA đã bị vô hiệu hóa. Chỉ hủy lệnh vào, giữ các lệnh thoát và stoploss.

Không dùng `compose down`, `/stop` hay tắt EC2 khi còn cần bot quản lý các vị thế mở. Không dùng forceexit nếu chưa có yêu cầu bán tài sản.

## Kiểm thử

Kiểm tra offline bằng `py -3.12 -m unittest discover -s tests -p 'test_*.py'`. Bộ kiểm thử không gọi AI thật hay đặt lệnh thật. Kết quả local không chứng minh trạng thái AWS hoặc trạng thái lệnh trên sàn.

Chỉ bật lại giao dịch và AI khi có yêu cầu mới; không tự động gỡ chế độ tạm ngừng.
