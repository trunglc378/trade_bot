# Điều tra lưu lượng AI và giới hạn worker

Ngày kiểm tra: 25/11/2026. Phạm vi: ảnh AI Studio/Antigravity người dùng cung cấp, mã nguồn hiện tại, tiến trình máy local và thử kết nối SSH tới AWS. Không gọi Gemini/OpenAI thật để thử quota.

## 1. Kết luận có bằng chứng

| Quan sát | Diễn giải |
| --- | --- |
| AI Studio báo “Prepay credits depleted” | Số dư trả trước của billing account trong ảnh đã cạn; đây là vấn đề billing, khác với tốc độ request |
| Flash Lite: RPD 509/500, RPM 2/15 | Đỉnh request/ngày vượt giới hạn; request/phút trong ảnh chưa vượt. Bảng là đỉnh trong 28 ngày, không chứng minh 509 request đều phát sinh hôm nay |
| Hydrogen: TPM 248,64K/250K, RPD 13/20 | Đỉnh input token/phút gần trần; một số request có thể mang context lớn dù số request thấp |
| Antigravity “Model unavailable… attempt 2/9” | Ứng dụng đang retry vì model không khả dụng; ảnh không đủ xác định chính xác do capacity, quota hay nguyên nhân khác |
| Local không có Python worker, config gốc providers rỗng, không có `.env` | Không có bằng chứng bản trên máy local đang tạo các request đó tại thời điểm kiểm tra |
| Người dùng xác nhận có bot trên VPS AWS | Cần đối chiếu log/cấu hình trên AWS để quy nguồn lưu lượng; chưa thu thập được |

[Gemini API rate limits](https://aistudio.google.com/docs/rate-limits) áp dụng theo project và có RPM/TPM/RPD; đổi key trong cùng project không tạo quota riêng. [Billing](https://aistudio.google.com/docs/billing#prepay) nêu khi prepay về 0 thì các API key của các project gắn với billing account đó bị dừng, hiện trả HTTP 402.

[Antigravity Plans](https://antigravity.google/docs/plans) mô tả baseline quota theo gói và lượng công việc của agent, có cơ chế AI credit overages riêng. Không thể kết luận chỉ từ AI Studio rằng API worker đã dùng hết baseline quota Antigravity. Cần xem Settings/quota và lỗi cụ thể của Antigravity; nhiều request không tự động đồng nghĩa cùng một quota.

## 2. Thiếu sót tìm thấy trong worker trước sửa

Worker Compose chạy `--loop 300`. Khi provider bật và có ứng viên đạt kỹ thuật, mỗi vòng gọi một batch cho mỗi provider, kể cả ngoài khung giờ mua. Trước sửa chưa có bộ đếm ngày/giờ, cache hoặc khóa lâu dài khi billing/quota lỗi.

Một worker gọi mỗi 5 phút có thể tạo xấp xỉ **288 lượt/ngày/provider**, thực tế còn trừ thời gian xử lý và các vòng không đủ ứng viên. Hai instance, một lịch cron khác hoặc client khác có thể làm tổng cao hơn. Đây là khả năng từ mã nguồn, không phải kết luận hai instance đang chạy trên AWS. Số liệu trong ảnh chưa được đối chiếu log nhà cung cấp hoặc log VPS.

Dashboard polling 5 giây chỉ gọi REST API bot và đọc snapshot. Mock không gọi model thật. Những request localhost đó không phải request Gemini API. Trong bộ tests, provider/market data dùng fixture và browser bị chặn request ra ngoài test origin.

## 3. Bản sửa cục bộ

CLI worker hiện bắt buộc đi qua `research/ai_control.py` trước khi gọi provider. Cấu hình `vn_policy.research.ai_control` trong config gốc và overlay Gemini mặc định:

```json
{
  "enabled": false,
  "only_in_session": true,
  "min_interval_seconds": 1800,
  "max_requests_per_hour": 2,
  "max_requests_per_day": 20,
  "cache_ttl_seconds": 600,
  "max_candidates": 3,
  "max_input_chars": 12000,
  "backoff_seconds": 900,
  "max_backoff_seconds": 21600
}
```

- Mặc định tắt gọi AI mạng, để người vận hành kiểm tra usage/billing trước khi bật lại. Phân tích kỹ thuật công khai vẫn chạy theo chu kỳ worker.
- Khi bật: chỉ gọi trong khung mua cấu hình, tối thiểu 30 phút/lượt/provider; cap dùng chung **2 lần/giờ và 20 lần/24 giờ trượt** cho tổng các provider trên cùng database.
- Batch tối đa 3 coin, dữ liệu ứng viên tối đa 12.000 ký tự; prompt/schema còn có phần cố định ngoài giới hạn này. Cả OpenAI và Gemini giảm output cap từ 4.000 xuống 1.000 token. Output bị cắt/JSON lỗi vẫn không được chấp nhận.
- Cache tối đa 10 phút cho cùng danh sách cặp và cấu hình provider; dùng lại cache không gọi API và không đổi `analysis_generated_at`. Trong required, expiry snapshot bị giới hạn bởi độ mới của nhận định, không kéo dài thời hạn AI qua mỗi lần xuất file.
- Sau lỗi HTTP 429/503 hoặc lỗi khác: không retry ngay trong vòng đó; lưu cooldown/backoff tăng dần và jitter, có xét Retry-After dạng số giây. Thời gian tối thiểu giữa hai lần gọi vẫn được áp dụng.
- HTTP 400/401/402/403/404: mở circuit lưu trên đĩa, cần người vận hành xử lý rồi reset; không cứ 5 phút thử lại model/khóa/billing lỗi.
- Bộ đếm tăng trước khi gọi và tính cả lượt thất bại. SQLite transaction chặn nhiều worker đồng thời cấp cùng một lượt. Restart không xóa lịch sử quota/circuit.
- Lưu trạng thái vào `user_data/research/ai-control.sqlite`, chỉ chứa provider/thời gian/kết quả/status code và votes nghiên cứu; không lưu API key hoặc prompt. Lỗi JSON có trường http_status/reason an toàn thay vì nội dung exception có thể chứa key.

Các cap trên chỉ bao phủ CLI worker của bản sửa và các tiến trình dùng **cùng file database trên cùng volume**. Chúng không đếm được Antigravity, client khác, VPS khác hoặc deployment có data directory riêng. Đây là hạn mức số lượt do ứng dụng cấp, không phải ngân sách USD/token/search-query ở cấp tài khoản Google. Search có thể phát sinh nhiều truy vấn trong một lượt model.

Nếu `research.mode` là advisory, tắt AI không đồng nghĩa dừng giao dịch kỹ thuật. Nếu cần dừng mua mới nhưng tiếp tục quản lý thoát lệnh, dùng nút “Tạm dừng mua mới”. Required không đủ phiếu sẽ từ chối mua; không tự hạ xuống advisory khi quota lỗi.

## 4. Dừng tiêu thụ trên AWS ngay

Kiểm tra thực hiện trên máy AWS đang chạy bot, trong thư mục chứa Compose:

```bash
docker compose config --services
docker compose stop research
docker compose ps
docker compose logs --since 24h --tail 200 research
```

Chỉ dừng service nghiên cứu, không dùng `docker compose down` nếu muốn giữ engine xử lý các vị thế đang mở. Nếu worker được chạy qua cron/systemd hoặc deployment khác, lệnh Compose không dừng các bản đó; cần xác định và tạm dừng đúng lịch/service. Không chia sẻ log chưa che API key, token, mật khẩu hoặc dữ liệu tài khoản.

Khi đã triển khai bản sửa, có thêm nút dừng bằng tệp dùng chung, không gọi AI:

```bash
docker compose exec research python /freqtrade/user_data/research/ai_control.py --pause
docker compose exec research python /freqtrade/user_data/research/ai_control.py
```

Lệnh pause tạo `AI_PAUSE`, chặn lượt gọi tiếp theo và tồn tại qua restart; một request đang ở trên mạng không được hủy ngược. Status hiển thị số attempts 24 giờ trượt và circuit. Dùng `--resume` để bỏ tệp pause; config enabled=false, cooldown và cap vẫn có hiệu lực.

Sau khi sửa billing/key/model và kiểm tra usage, mới cân nhắc đặt `enabled: true`, bỏ pause và reset circuit cần thiết:

```bash
docker compose exec research python /freqtrade/user_data/research/ai_control.py --reset-circuit gemini
```

Reset circuit không xóa bộ đếm hoặc thời gian chờ. Không xóa database để “làm mới quota”; quota thật của Google vẫn tồn tại. Áp dụng cùng overlay cấu hình cho cả Freqtrade và worker vì context hash phải khớp. Kiểm tra các bản chạy trùng và quota tại AI Studio theo từng project/key/model/ngày trước khi mở lại vòng lặp.

## 5. Trạng thái truy cập và triển khai

Đã thử SSH key được người dùng bổ sung vào AWS tại địa chỉ đã cung cấp với user `ubuntu`; server chấp nhận kết nối nhưng từ chối xác thực với các key đã thử. Vì vậy **chưa đọc log/cấu hình, chưa dừng worker và chưa triển khai bản sửa trên AWS**. Cần xác nhận đúng EC2 instance public IP, AMI user và key pair; có thể dùng AWS EC2 Instance Connect/Session Manager nếu đã được cấu hình để chạy các lệnh kiểm tra trên.

Các credential người dùng đã gửi trong chat không được sử dụng để thử Gemini/OpenAI hoặc đặt lệnh sàn. Cần thu hồi các key đã lộ, tạo lại khóa với quyền/IP phù hợp và đổi các mật khẩu liên quan. Đã thêm ignore cho `.pem`, `.key` và file ghi chú truy cập để tránh commit chúng; ignore không thay thế thu hồi khóa đã lộ.

## 6. Kiểm thử sau sửa

Nguồn bằng chứng: [results cuối ngày 25/11/2026](../test-results/20261125-ai-control-final/results.json).

- 65 ca Python PASS (22 unit, 43 integration theo runner hiện tại), 8 ca browser PASS; không gọi API thật.
- 12 ca mới cho disable/session/pause, CLI pause/resume độc lập, cache, cap chia sẻ theo giờ/ngày, restart, reserve đồng thời, khóa lỗi 400/401/402/403/404, backoff 429/503, giới hạn input/batch và hạn dùng AI cached.
- Test đồng thời xác nhận bốn controller cùng data directory chỉ cấp một lượt gọi; test circuit xác nhận restart/qua ngày không tự mở lại lỗi terminal.
- Docker Engine/Android build vẫn bị chặn trên máy local; truy cập AWS bị chặn xác thực. Không tuyên bố đã khôi phục Antigravity hoặc đã giảm lưu lượng trên deployment từ xa.

## 7. Hướng xử lý Antigravity

Tạm dừng tác vụ đang tự retry trước khi tiếp tục gửi nhiều yêu cầu “kiểm tra kết nối”. Kiểm tra quota trong Settings của Antigravity và gói/account đang đăng nhập; lỗi availability không được sửa chỉ bằng cách đổi Gemini API key. AI Studio cần xử lý riêng số dư prepay và RPD/TPM của project. Không cần nạp thêm tiền để kiểm tra bản sửa offline, và chưa có bằng chứng rằng chỉ nạp tiền sẽ khắc phục lỗi Antigravity đang thấy.
