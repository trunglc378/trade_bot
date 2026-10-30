# AWS EC2 Free Plan: triển khai thử bot 24/7

Ngày kiểm tra: 29/10/2026. Hướng dẫn này thay phần chọn Oracle trong tài liệu 09 khi bạn dùng AWS.

## 1. Thông tin từ ảnh và phạm vi vốn

Ảnh AWS cho thấy Free Plan còn 100 USD credit và 184 ngày tại thời điểm chụp. Đây không phải cam kết VPS miễn phí vĩnh viễn: theo AWS, Free Plan kết thúc sau tối đa 6 tháng hoặc khi hết credit, tùy điều kiện nào đến trước. Kiểm tra ngày hết hạn thực tế trong Billing; không suy ra ngày hết hạn từ số ngày trong ảnh.

Ảnh Binance hiển thị tổng giá trị ước tính khoảng 418,2231 USDT; OKX khoảng 514,55 USD. Đây là giá trị danh mục, không phải số USDT có thể giải ngân. Ảnh không đủ để xác định USDT khả dụng trong ví Spot/Trading. Không bán hoặc chuyển toàn bộ tài sản để triển khai máy chủ.

Cấu hình hiện tại vẫn dry-run, ví mô phỏng 34,16 USDT/sàn. Bot chưa tự tiếp quản các coin đã có ngoài database giao dịch của nó. Không coi việc cài server là đã đặt chốt lời/cắt lỗ cho danh mục cá nhân.

Credit AWS không thanh toán phí giao dịch sàn hoặc chi phí API AI ngoài AWS.

## 2. Tạo EC2 trong console

Giữ Free Plan. Không chọn nút nâng cấp Paid Plan để làm theo hướng dẫn này.

1. Trên trang AWS trong ảnh, đóng menu tài khoản, tìm **EC2** ở ô tìm kiếm. Có thể đổi giao diện sang English bằng mục **Langue** để khớp tên nút dưới đây.
2. Chọn region **Asia Pacific (Singapore), ap-southeast-1** nếu Free Plan cho phép; sau khi tạo cần kiểm tra sàn chấp nhận kết nối từ vùng này. Không dùng máy chủ để vượt hạn chế địa lý của sàn.
3. Vào **Instances → Launch instances** (tiếng Pháp: **Lancer des instances**).
4. Name: `freqbot-vn-free`.
5. AMI: **Ubuntu Server 24.04 LTS**, kiến trúc **64-bit x86**, nhà phát hành Canonical; chọn AMI có nhãn Free tier eligible, không dùng AMI Marketplace có phí phần mềm.
6. Instance type: **t3.small**, 2 vCPU / 2 GiB RAM, nếu console xác nhận đủ điều kiện Free Plan. Đây là lựa chọn để chạy thử một bot + một worker; chưa xác minh đủ tài nguyên cho cả bốn service của hai sàn. `t3.micro` chỉ có 1 GiB nên không chọn cho cấu hình hai sàn. Nhãn Free tier eligible không có nghĩa máy chạy không tiêu credit.
7. Key pair: **Create new key pair**, tên `freqbot-vn`, RSA, định dạng `.pem`. Lưu private key trên máy cá nhân, không đưa lên Git hoặc gửi qua chat.
8. Network settings: dùng default VPC và subnet public có đường ra Internet; **Auto-assign public IP: Enable**. Tạo security group `freqbot-ssh`, inbound chỉ **SSH TCP 22 → My IP**. Không mở 8080, 8081 hoặc 8090 ra Internet. Giữ outbound mặc định để máy tải image và gọi sàn.
9. Storage: **20 GiB gp3**, bật mã hóa, không tăng IOPS/throughput hoặc thêm volume. Đây là mức khởi đầu cho dry-run, phải theo dõi dung lượng data/log.
10. Advanced details: nếu có **Credit specification**, chọn **Standard**. T3 mặc định Unlimited có thể tiêu thêm credit cho CPU vượt baseline; Standard có thể bị giới hạn CPU khi hết burst credit, cần theo dõi.
11. Dùng On-Demand thông thường; không bật Spot, không tạo load balancer, NAT Gateway hoặc RDS cho bot này. Xem phần Summary và dự toán, chỉ tạo **1 instance**.
12. Nhấn Launch instance. Chờ **Running** và các status checks đạt, ghi public IPv4.

Nếu console yêu cầu chuyển Paid Plan hoặc không có t3.small đủ điều kiện, dừng tại màn hình đó để kiểm tra lựa chọn; không mặc định đổi sang instance khác đắt hơn.

## 3. Theo dõi credit

Vào Billing and Cost Management, xem Free Tier/Credits và thời hạn của credit. Kiểm tra lại sau 24–48 giờ chạy để đo mức tiêu thụ; ban đầu số liệu có thể cập nhật chậm. Tính thời gian còn chạy được bằng credit còn lại / mức tiêu trung bình mỗi ngày, đồng thời xét ngày hết hạn của plan.

EC2, EBS, public IPv4 và lưu lượng có thể tiêu credit riêng. Public IPv4 có giá niêm yết, không mặc định miễn phí chỉ vì instance đủ điều kiện. Stop instance không xóa EBS; không dựa vào Stop để coi mọi tài nguyên đều ngừng tiêu credit.

Giữ Free Plan giúp tránh tự chuyển thành hóa đơn sử dụng Paid Plan theo điều kiện AWS, nhưng khi hết hạn/credit dịch vụ có thể ngừng. Cần sao lưu và có kế hoạch trước khi tới hạn; không dựa vào Free Plan cho khả năng giám sát tiền thật vô thời hạn.

## 4. SSH và chuyển mã nguồn hiện có

Trong PowerShell trên Windows, thay đường dẫn `.pem` và `PUBLIC_IP`:

```powershell
ssh -i "C:\Users\Admin\Downloads\freqbot-vn.pem" ubuntu@PUBLIC_IP
```

Trên Ubuntu, tạo thư mục rồi thoát về Windows:

```bash
mkdir -p ~/trade_bot
exit
```

PowerShell tại `E:\Project\trade_bot`:

```powershell
scp -i "C:\Users\Admin\Downloads\freqbot-vn.pem" -r .\freqtrade-bot ubuntu@PUBLIC_IP:~/trade_bot/
ssh -i "C:\Users\Admin\Downloads\freqbot-vn.pem" ubuntu@PUBLIC_IP
```

Thư mục được copy chứa các cấu hình private và `.env`; SCP truyền qua SSH tới VPS của bạn. Copy bản workspace hiện tại để có cả sửa lỗi giữ nguyên khóa khi khởi tạo. Không cần nhập lại khóa hoặc dùng AWS access key cho bot. Không dùng cách copy đè database khi bot đã chạy và đang quản lý lệnh.

## 5. Cài hạ tầng và bảo mật

Trên EC2 Ubuntu mới:

```bash
cd ~/trade_bot/freqtrade-bot
sed -i 's/\r$//' deploy_oracle_cloud_24_7.sh
bash deploy_oracle_cloud_24_7.sh
chmod 600 .env user_data/config.private.binance.json user_data/config.private.okx.json
sudo systemctl enable --now docker
```

Tên script có Oracle nhưng các bước là cài gói Ubuntu/Docker/Chrony/swap/Tailscale/UFW, không gọi API Oracle. Chỉ dùng trên máy Ubuntu mới với SSH cổng 22 như cấu hình trên. Script có thể yêu cầu chạy `setup_accounts.py`; với cấu hình đã copy, bỏ qua bước nhập lại đó để giữ nguyên khóa và model.

Làm **mục 4 của tài liệu 09** để đổi mật khẩu API mẫu mà không thay các khóa đã nhập. Giữ `TAILSCALE_IP=127.0.0.1` trong `.env` cho lần khởi chạy này và dùng SSH tunnel. Giữ `dry_run: true` trong cả hai cấu hình private; không bật live trong bước cài máy chủ.

## 6. Chạy một sàn trước

Mặc định Compose chạy Binance và worker tương ứng:

```bash
sudo docker compose config --quiet
sudo docker compose pull
sudo docker compose up -d
sudo docker compose ps -a
sudo docker compose logs --tail 100 freqtrade research
sudo docker stats --no-stream
free -h
df -h
```

Nếu bot lỗi quyền đọc cấu hình/ghi database, làm bước kiểm tra UID trong tài liệu 09; không cấp `chmod 777`. Nếu sàn từ chối IP/vùng, xử lý theo chính sách sàn, không dùng thủ thuật vượt hạn chế.

Theo dõi 24–48 giờ và kiểm tra `CPUCreditBalance` trong EC2 Monitoring. Chỉ khi RAM, swap, CPU và tốc độ snapshot ổn định mới thử thêm OKX:

```bash
sudo docker compose --profile okx up -d
sudo docker compose --profile okx ps -a
sudo docker compose --profile okx logs --tail 100 freqtrade-okx research-okx
sudo docker stats --no-stream
```

Không bảo đảm t3.small đủ cho cả hai sàn. Nếu thiếu tài nguyên, giữ một sàn, không tự tăng kích thước instance và tiêu credit nhanh hơn. Không chạy backtest/hyperopt cùng lúc trên EC2 nhỏ đang theo dõi giao dịch.

Container có `restart: unless-stopped`. Thử reboot lúc dry-run và xác minh bot cùng worker tự chạy lại, snapshot mới, đồng hồ chuẩn. Sau đó ghi image digest/phiên bản đã kiểm thử như tài liệu 09. Docker `Up` chưa chứng minh bot đang xử lý đúng.

## 7. Dashboard và địa chỉ IP

Trên PowerShell, giữ SSH tunnel chạy:

```powershell
ssh -i "C:\Users\Admin\Downloads\freqbot-vn.pem" -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 ubuntu@PUBLIC_IP
```

Trong cửa sổ PowerShell khác, tại gốc dự án:

```powershell
py -3.12 -m http.server 8090 --bind 127.0.0.1 --directory web-dashboard
```

Mở `http://127.0.0.1:8090`; API Binance `http://127.0.0.1:8080`, OKX `http://127.0.0.1:8081` khi service OKX đã chạy. Dùng mật khẩu vừa đổi. Không dùng mock server để điều khiển EC2. Xem báo cáo AI bằng tải snapshot qua SCP theo tài liệu 09.

Public IPv4 tự cấp thường đổi sau stop/start. Nếu sau này bật live và whitelist IP API sàn, cần giải pháp IP egress ổn định cùng kiểm tra chi phí (ví dụ Elastic IP nếu plan cho phép). IP Tailscale không phải IP outbound Internet để whitelist ở sàn. Không bật live trước khi giải quyết việc này.

## 8. Tài sản và chốt lời/cắt lỗ

Giữ ví thử 34,16 USDT/sàn để kiểm tra vận hành. Không thay `available_capital` thành toàn bộ 418,2231 hoặc 514,55 chỉ dựa trên ảnh; cần biết USDT khả dụng và khoản bạn thực sự muốn phân bổ.

Việc tự động quản lý coin hiện có là phạm vi khác với mở lệnh mới bằng Freqtrade. Bot hiện dựa vào các trade trong database của nó, không tự gắn stoploss cho mọi coin trong ví. Cần thiết kế cách tiếp quản riêng và xác nhận mức vốn/tài sản trước khi thực hiện. Phương án cách ly rõ ràng là tài khoản phụ riêng cho bot khi sàn hỗ trợ.

Lịch hiện có vẫn xét mua cả ngày, tăng hạn mức mỗi lệnh trong 03:00–04:00 Việt Nam, chốt lời/cắt lỗ mọi giờ. Chưa có bằng chứng 03–04 là giờ có lợi thế hoặc bộ tham số hiện tại bảo đảm sinh lời. Xem tài liệu 09 về rủi ro stop-limit, giới hạn vốn và quy trình kiểm chứng trước live.

## Nguồn AWS đã đối chiếu

- [AWS Free Plan và credit](https://aws.amazon.com/free/free-tier-faqs/).
- [EC2 Free Tier: các loại instance và thời hạn](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html).
- [T3 Standard/Unlimited và CPU credit](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-unlimited-mode.html).
- [Giá public IPv4 và dịch vụ VPC](https://aws.amazon.com/vpc/pricing/).

Đây là hướng dẫn chuẩn bị; chưa tạo EC2, chưa tiêu credit AWS và chưa triển khai bot trên AWS trong phiên này.
