# Triển khai VPS 24/7 theo cấu hình thực tế

Cập nhật ngày 29/10/2026. Đọc hướng dẫn này trước mục Oracle trong tài liệu 08.

## 1. Kết quả kiểm tra dự án

- Hai cấu hình riêng Binance và OKX đang là `dry_run: true`, ví thử và `available_capital` đều 34,16 USDT/sàn; tối đa 2 lệnh/sàn, stake đề xuất 15,37 USDT/lệnh.
- Có các trường khóa sàn và khóa AI trên máy hiện tại. Chỉ kiểm tra sự hiện diện, chưa xác minh khóa còn hiệu lực, quyền giao dịch hoặc kết nối sàn.
- Lịch riêng ghi đè cấu hình gốc: `schedule.enabled: false` cho phép xét mua cả ngày. `windows` 03:00–04:00 UTC+7 vẫn xác định giờ ưu tiên; ngoài giờ hệ số vốn là 0,75. Chốt lời/cắt lỗ không bị khóa theo lịch.
- Với vốn ban đầu 34,16 USDT, hạn mức tính toán khoảng 15,37 USDT trong giờ ưu tiên và 11,53 USDT ngoài giờ, còn phụ thuộc vốn khả dụng, exposure, phí và minimum stake của từng cặp. Không bảo đảm sẽ có lệnh lúc 03:00. Vị thế mở trước đó có thể chiếm hết số slot; hiện chưa dành riêng vốn/slot cho giờ ưu tiên.
- Hồ sơ vốn nhỏ dùng `risk_per_trade: 0.016` (1,6%), giới hạn một vị thế 45%, tổng stake 90%. Đây là cấu hình rủi ro cao hơn cấu hình gốc 0,5%/20%/60%; chưa có bằng chứng cho thấy hợp lý với tiền thật. Hai sàn có thể cùng lỗ trên các coin tương quan.
- AI đang ở `advisory`: chỉ bộ lọc kỹ thuật quyết định eligibility, AI `avoid` không phủ quyết ở chế độ này. Muốn bắt buộc cả hai AI đồng thuận, cần `required` và `min_ai_votes: 2`, rồi kiểm thử riêng. Chưa thay chế độ của bạn.
- Mật khẩu API hiện vẫn là mẫu; binding hiện là localhost. Cần đổi mật khẩu trước khi mở truy cập qua VPN.
- Docker CLI có nhưng Docker Engine ở máy hiện tại chưa chạy. Chưa có VPS và chưa triển khai tiến trình giao dịch.

## 2. Tạo máy chủ

Khuyến nghị kỹ thuật ban đầu: Ubuntu 24.04 LTS, 2 vCPU, ít nhất 4 GB RAM, SSD 40–60 GB cho hai bot và hai worker; đo lại CPU/RAM khi chạy. Không chạy hyperopt trên cùng VPS đang giao dịch. Chọn vùng được sàn cho phép truy cập, kiểm tra kết nối từ VPS trước khi dùng thật.

Nếu ưu tiên độ ổn định để giao dịch thật, chọn VPS trả phí có sao lưu và IP egress ổn định. Nếu muốn thử miễn phí, dùng Oracle Cloud:

1. Tạo tài khoản tại https://www.oracle.com/cloud/free/ và hoàn tất xác minh của nhà cung cấp.
2. Chọn home region có tài nguyên còn trống. Vào **Compute → Instances → Create instance**.
3. Chọn Ubuntu 24.04, shape `VM.Standard.A1.Flex` với nhãn **Always Free eligible**. Tài liệu Oracle được kiểm tra ngày 29/10/2026 công bố tổng hạn mức A1 tương đương **2 OCPU/12 GB RAM**, không phải 4 OCPU/24 GB như tài liệu cũ của dự án. Kiểm tra dự toán hiển thị trước khi tạo.
4. Dùng boot volume 50 GB, subnet có đường ra Internet và public IP để SSH. Lưu ý IP outbound dùng cho whitelist API sàn.
5. Tạo/tải SSH key về máy cá nhân, giữ private key tại máy. Security list/NSG chỉ mở TCP 22 từ IP của bạn; không mở công khai 8080/8081. Giữ outbound cần thiết cho sàn, DNS, NTP và Tailscale.
6. Ghi lại public IP và username (thường `ubuntu`). Thử SSH từ PowerShell; với key có sẵn: `ssh -i "C:\duong-dan\vps.key" ubuntu@PUBLIC_IP`.

Oracle có thể thu hồi Always Free instance ít hoạt động; không xem đây là cam kết uptime 24/7 hoặc miễn phí vô điều kiện. Nguồn: [hạn mức và thu hồi Oracle](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

## 3. Chuyển phiên bản hiện tại lên VPS

Thực hiện trên PowerShell tại `E:\Project\trade_bot`, thay `PUBLIC_IP` và đường dẫn SSH key. Việc copy thư mục này truyền cả cấu hình bí mật qua SSH tới máy chủ của bạn; không đưa lên repository hoặc gửi qua chat.

```powershell
ssh -i "C:\duong-dan\vps.key" ubuntu@PUBLIC_IP "mkdir -p ~/trade_bot"
scp -i "C:\duong-dan\vps.key" -r .\freqtrade-bot ubuntu@PUBLIC_IP:~/trade_bot/
scp -i "C:\duong-dan\vps.key" -r .\web-dashboard ubuntu@PUBLIC_IP:~/trade_bot/
ssh -i "C:\duong-dan\vps.key" ubuntu@PUBLIC_IP
```

Copy trực tiếp giữ được cả sửa lỗi mới trong workspace và các tệp private vốn không có trên Git. Không cần nhập lại khóa qua `setup_accounts.py`. Chỉ thực hiện quy trình này cho lần triển khai đầu; khi đã giao dịch, không copy database từ máy khác đè lên database đang chạy.

Trên VPS Ubuntu mới, dùng SSH port 22 mặc định:

```bash
cd ~/trade_bot/freqtrade-bot
sed -i 's/\r$//' deploy_oracle_cloud_24_7.sh
bash deploy_oracle_cloud_24_7.sh
chmod 600 .env user_data/config.private.binance.json user_data/config.private.okx.json
sudo systemctl enable --now docker
sudo docker compose version
sudo tailscale up
tailscale ip -4
```

Script cài Docker, Chrony, swap, Tailscale và UFW; sửa lỗi lần này giúp `--init-defaults` giữ nguyên các tệp private đã có. Swap không loại trừ nguy cơ hết RAM. Script giả định SSH cổng 22; nếu VPS dùng cổng khác, sửa rule SSH trước khi bật UFW. Quy tắc UFW không thay thế binding Docker và firewall của nhà cung cấp.

## 4. Đổi mật khẩu mà không thay khóa sàn

Trên VPS, chạy đoạn sau trong thư mục `freqtrade-bot`. Đoạn này chỉ thay mật khẩu điều khiển trong hai cấu hình private:

```bash
python3 - <<'PY'
import getpass, json, os
from pathlib import Path
password = getpass.getpass('Mat khau API moi (toi thieu 16 ky tu): ')
if len(password) < 16 or password == 'mat_khau_manh_cua_ban':
    raise SystemExit('Mat khau chua dat yeu cau; chua ghi thay doi.')
for exchange in ('binance', 'okx'):
    path = Path('user_data') / f'config.private.{exchange}.json'
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    config['api_server']['password'] = password
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.chmod(path, 0o600)
print('Da doi mat khau cho hai bot.')
PY
```

Không cần đổi `TAILSCALE_IP` để khởi chạy lần đầu: giữ `127.0.0.1` an toàn và dùng SSH tunnel bên dưới. Cách này cũng tránh phụ thuộc thời điểm IP Tailscale sẵn sàng lúc máy chủ reboot.

Nếu dùng Android qua Tailscale, sau khi xác nhận mạng VPN hoạt động, sửa **duy nhất** `TAILSCALE_IP` trong `.env` thành IP `100.x.y.z` của VPS, rồi recreate container. Không dùng `0.0.0.0` hoặc public IP. Chỉ cho thiết bị của bạn truy cập bằng ACL Tailscale. Kiểm tra lại binding/container sau reboot.

## 5. Khởi chạy thử cả hai sàn

```bash
cd ~/trade_bot/freqtrade-bot
sudo docker compose --profile okx config --quiet
sudo docker compose --profile okx pull
sudo docker compose --profile okx up -d
sudo docker compose --profile okx ps -a
sudo docker compose --profile okx logs --tail 100 freqtrade research freqtrade-okx research-okx
```

Giữ `dry_run: true`. Có 4 service: hai bot và hai research worker. `restart: unless-stopped` giúp container tự chạy lại khi tiến trình chết hoặc host reboot nếu Docker khởi động và container không bị dừng thủ công. Nó không phát hiện mọi trường hợp tiến trình bị treo.

Nếu gặp permission denied, kiểm tra UID bằng `sudo docker compose run --rm --no-deps --entrypoint id freqtrade` và quyền thư mục `user_data`; cấp quyền cho đúng UID/container, không dùng `chmod 777`. Nếu không có snapshot mới, kiểm tra log research và quyền ghi.

Lưu phiên bản đã kiểm thử để tái lập; tag `stable` hiện có thể thay đổi khi pull:

```bash
sudo docker image inspect freqtradeorg/freqtrade:stable --format '{{index .RepoDigests 0}}'
sudo docker compose run --rm --no-deps freqtrade --version
```

Sau khi kiểm thử thành công, dùng digest vừa ghi thay cho tag `stable` ở cả bốn service và recreate trong một lần bảo trì. Không tự động pull bản mới mỗi ngày.

Kiểm tra snapshot không lộ khóa:

```bash
python3 - <<'PY'
import json
from pathlib import Path
for name in ('latest.json', 'latest-okx.json'):
    report = json.loads((Path('user_data/research') / name).read_text(encoding='utf-8'))
    print(name, report.get('exchange'), report.get('generated_at'), report.get('expires_at'))
PY
```

Chạy thử reboot một lần trong giai đoạn dry-run; SSH vào lại và kiểm tra 4 container, log, đồng hồ NTP và snapshot còn mới. Đây là bước kiểm chứng 24/7 cần làm trên VPS thật.

## 6. Xem dashboard từ Windows

Giữ binding localhost, mở PowerShell mới trên Windows và để cửa sổ tunnel chạy:

```powershell
ssh -i "C:\duong-dan\vps.key" -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 ubuntu@PUBLIC_IP
```

Trong cửa sổ PowerShell khác, từ gốc dự án:

```powershell
py -3.12 -m http.server 8090 --bind 127.0.0.1 --directory web-dashboard
```

Mở `http://127.0.0.1:8090`; API Binance là `http://127.0.0.1:8080`, API OKX là `http://127.0.0.1:8081`. Nhập username hiện có và mật khẩu vừa đổi. Freqtrade thật không phục vụ `/dashboard` hay endpoint mock `/api/v1/vn_research`.

Muốn xem AI trên dashboard thật: dùng SCP lấy snapshot từ VPS rồi chọn tệp JSON trên giao diện. Không chạy mock server để điều khiển tiền thật.

## 7. Chốt lời/cắt lỗ và điều kiện dùng tiền thật

Chiến lược hiện tại đặt stoploss -3% trên vị thế. ROI theo thời gian giữ lệnh: +6% lúc đầu, +3,5% sau 30 phút, +2% sau 60 phút, +1% sau 180 phút. Trailing kích hoạt từ +2,5%, bám cách đỉnh 1%. Tín hiệu bán kỹ thuật có thể thoát trước các mức ROI, kể cả khi lỗ. Đây là bộ tham số cần kiểm chứng, chưa phải mức đã tối ưu.

Binance Spot dùng stop-limit; khi giá nhảy qua mức limit có thể chưa bán được, lỗ có thể vượt -3%. OKX overlay dùng stop-market. Khi host ngừng, chỉ lệnh đã đặt thành công trên sàn mới có thể tiếp tục được sàn xử lý; ROI, tín hiệu bán và cập nhật trailing cần bot hoạt động. Nguồn: [Freqtrade stoploss](https://www.freqtrade.io/en/stable/stoploss/).

Trước live cần backtest có phí, lookahead/recursive analysis và theo dõi dry-run dài ngày, gồm cả ngoài giờ 03–04. So sánh với mua chỉ trong 03–04; chưa có bằng chứng giờ này sinh lời tốt hơn. `hourly.py` nhận CSV `open_date,profit_abs` với thời gian có timezone và PnL ròng, không nhận trực tiếp ZIP/JSON backtest Freqtrade.

Khi cân nhắc live: xác minh API chỉ có quyền đọc/Spot, tắt rút tiền, whitelist IP egress của VPS; dùng tài khoản phụ riêng để tách số coin cá nhân. `available_capital` là phân bổ vốn trong bot, không phải khóa tài sản tại sàn và lợi nhuận/lỗ sẽ làm vốn tính toán thay đổi. Không xem câu “không bao giờ đụng coin sẵn có” trong wizard là bảo đảm cách ly tài sản.

Giữ nguyên cấu hình hiện tại cho giai đoạn triển khai thử. Chỉ chuyển `dry_run` và database sang live sau khi hoàn tất kiểm chứng; không tự chuyển sau 3 ngày. Hai database live phải tách riêng và không dùng database dry-run.

## 8. Vận hành

- Theo dõi mỗi ngày trạng thái bot, lỗi API, snapshot hết hạn, dung lượng đĩa và NTP. Container `Up` chưa đủ chứng minh bot vẫn xử lý dữ liệu. Hiện chưa có giám sát độc lập cảnh báo khi cả VPS mất kết nối; bổ sung trước khi dựa vào hệ thống cho tiền thật.
- Sao lưu mã hóa cấu hình private, `.env` và database sang nơi khác. Sao lưu SQLite đang mở bằng SQLite backup API hoặc công cụ backup của volume có tính nhất quán, không chỉ copy file SQLite đang ghi. Thử khôi phục trước live.
- Tạm dừng mua bằng StopBuy khi cần; giữ bot chạy để xử lý lệnh đang mở. Không dùng `docker compose down` như một cách tạm dừng mua.
- Khi cập nhật code/config: sao lưu, kiểm tra diff, recreate trong lúc bảo trì, xác minh lại dry/live, database và lệnh đang mở. Không chạy hai instance cùng quản lý một database hoặc cùng danh mục trên một tài khoản.

Kiểm thử tại máy ngày 29/10/2026: 40 tests tại `tests` đạt (bao gồm callback với pandas và hai tests chống ghi đè); 6 tests tại `freqtrade-bot/tests` đạt; dashboard JavaScript đạt; Compose parse đạt. Chưa kiểm thử container, khớp lệnh, stoploss sàn hoặc reboot VPS. Các adapter sàn/Freqtrade/TA-Lib trong callback tests là test doubles.
