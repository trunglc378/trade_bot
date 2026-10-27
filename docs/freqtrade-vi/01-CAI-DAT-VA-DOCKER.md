# HƯỚNG DẪN CÀI ĐẶT FREQTRADE & TRIỂN KHAI BẰNG DOCKER (TÀI LIỆU VIỆT HÓA)
**Nguồn gốc tài liệu:** `docs/docker_quickstart.md` — Kho mã nguồn chính thức `freqtrade/freqtrade`  
**Bản dịch & Biên tập Tiếng Việt:** Dự án FreqBot VN Remote  

---

## 1. Tại Sao Nên Chạy Freqtrade Bằng Docker?

Triển khai Freqtrade thông qua **Docker & Docker Compose** là phương pháp được đội ngũ phát triển Freqtrade khuyến nghị hàng đầu vì:
1. **Không lo xung đột thư viện C/Python:** Các thư viện phân tích kỹ thuật như `TA-Lib`, `numpy`, `scipy`, `pandas` đã được biên dịch sẵn trong Docker Image chính thức (`freqtradeorg/freqtrade:stable`).
2. **Tự động khởi động lại 24/7 (`restart: unless-stopped`):** Nếu máy chủ VPS khởi động lại hoặc ứng dụng gặp sự cố, Docker tự động bật lại bot ngay lập tức.
3. **Nâng cấp phiên bản chỉ với 1 dòng lệnh:** Không ảnh hưởng tới dữ liệu lịch sử hay file chiến lược nằm trong thư mục `user_data/`.

---

## 2. Cấu Trúc File `docker-compose.yml` Chuẩn Cho Dự Án

File [`freqtrade-bot/docker-compose.yml`](file:///e:/Project/trade_bot/freqtrade-bot/docker-compose.yml) được cấu hình như sau:

```yaml
---
services:
  freqtrade:
    image: freqtradeorg/freqtrade:stable
    restart: unless-stopped
    container_name: freqtrade_vn_bot
    volumes:
      - "./user_data:/freqtrade/user_data"
    # Mở cổng 8080 cho Ứng dụng Android (FreqBot VN Remote) và Web Dashboard kết nối
    ports:
      - "8080:8080"
    # Lệnh khởi chạy Bot với cơ sở dữ liệu SQLite, cấu hình config.json và chiến lược VnSmartTrendStrategy
    command: >
      trade
      --logfile /freqtrade/user_data/logs/freqtrade.log
      --db-url sqlite:////freqtrade/user_data/tradesv3.sqlite
      --config /freqtrade/user_data/config.json
      --strategy VnSmartTrendStrategy
```

> [!IMPORTANT]
> Khi triển khai trên máy chủ VPS thực tế có cài đặt mạng riêng ảo **Tailscale** (ví dụ địa chỉ IP Tailscale của VPS là `100.88.10.25`), bạn nên sửa dòng `ports` thành `"100.88.10.25:8080:8080"` hoặc `"127.0.0.1:8080:8080"` để cổng điều khiển API không bị lộ ra ngoài Internet công cộng.

---

## 3. Các Lệnh Docker Compose Thường Dùng Nhất

### 3.1. Tạo cấu trúc thư mục `user_data/` (Nếu khởi tạo mới)
```bash
docker compose run --rm freqtrade create-userdir --userdir user_data
```

### 3.2. Tạo khung cấu hình tương tác (`new-config`)
```bash
docker compose run --rm freqtrade new-config --config user_data/config.json
```
*(Trong dự án này, file [`freqtrade-bot/user_data/config.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/config.json) đã được thiết lập sẵn đầy đủ).*

### 3.3. Khởi chạy Bot chạy ngầm 24/7
```bash
docker compose up -d
```

### 3.4. Theo dõi nhật ký hoạt động thời gian thực (Logs)
```bash
docker compose logs -f
```

### 3.5. Kiểm tra danh sách các cặp coin đang được lọc (`test-pairlist`)
```bash
docker compose run --rm freqtrade test-pairlist --config user_data/config.json
```

### 3.6. Cập nhật Freqtrade lên phiên bản mới nhất
```bash
# Tải Docker image mới nhất
docker compose pull

# Khởi động lại container với image mới
docker compose up -d
```

---

## 4. Đồng Bộ Thời Gian Hệ Thống Trên Máy Chủ Linux (`NTP / Chrony`)

Các sàn giao dịch tiền điện tử (như Binance, Bybit) yêu cầu mọi lệnh gọi API có chữ ký (`HMAC-SHA256`) phải đính kèm mốc thời gian (`timestamp`) không được lệch quá `1000ms` (`recvWindow`) so với đồng hồ máy chủ của sàn. Nếu đồng hồ VPS chạy nhanh hoặc chậm hơn vài giây, sàn sẽ từ chối đặt lệnh.

Cách cài đặt và kiểm tra đồng bộ giờ trên Ubuntu VPS:
```bash
sudo apt update && sudo apt install -y chrony
sudo systemctl enable --now chrony
chronyc tracking
```
Đảm bảo thông số `System time` lệch dưới `0.01 seconds`.
