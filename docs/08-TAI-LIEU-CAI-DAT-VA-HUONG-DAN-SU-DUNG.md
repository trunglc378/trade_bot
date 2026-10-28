# TÀI LIỆU CÀI ĐẶT PHẦN MỀM & HƯỚNG DẪN SỬ DỤNG TOÀN DIỆN (INSTALLATION & USER MANUAL)
**Tên hệ thống:** Hệ thống Giao dịch Tiền điện tử Tự động, Phân tích AI Đa nguồn & Ứng dụng Điều khiển Từ xa Tiếng Việt (**FreqBot VN Remote**)<br>
**Phiên bản:** 2.0.0<br>
**Ngôn ngữ giao diện:** 100% Tiếng Việt chuẩn hóa<br>
**Ngày cập nhật:** 28/10/2026<br>

---

## MỤC LỤC
1. [Tổng Quan Kiến Trúc & Thành Phần Phần Mềm](#1-tổng-quan-kiến-trúc--thành-phần-phần-mềm)
2. [Yêu Cầu Hệ Thống (Phần Cứng, Phần Mềm & Mạng)](#2-yêu-cầu-hệ-thống-phần-cứng-phần-mềm--mạng)
3. [Hướng Dẫn Cài Đặt Chi Tiết Từng Phân Hệ](#3-hướng-dẫn-cài-đặt-chi-tiết-từng-phân-hệ)
   - [3.1. Cài đặt trên Máy cá nhân Windows (Chế độ Kiểm thử nhanh & Phát triển)](#31-cài-đặt-trên-máy-cá-nhân-windows-chế-độ-kiểm-thử-nhanh--phát-triển)
   - [3.2. Cài đặt Lõi Freqtrade & Dịch vụ AI Research bằng Docker Compose (24/7)](#32-cài-đặt-lõi-freqtrade--dịch-vụ-ai-research-bằng-docker-compose-247)
   - [3.3. Cài đặt & Triển khai trên Máy chủ VPS Ubuntu Linux + Mạng riêng Tailscale VPN](#33-cài-đặt--triển-khai-trên-máy-chủ-vps-ubuntu-linux--mạng-riêng-tailscale-vpn)
   - [3.4. Biên dịch & Cài đặt Ứng dụng Di động Android (`FreqBot VN Remote`)](#34-biên-dịch--cài-đặt-ứng-dụng-di-động-android-freqbot-vn-remote)
4. [Hướng Dẫn Cấu Hình Hệ Thống (`config.json`, `config-okx.json`, `.env`)](#4-hướng-dẫn-cấu-hình-hệ-thống-configjson-config-okxjson-env)
   - [4.1. Cấu hình Sàn giao dịch Binance & OKX](#41-cấu-hình-sàn-giao-dịch-binance--okx)
   - [4.2. Cấu hình Khung Giờ Giao Dịch Việt Nam (`vn_policy.schedule`)](#42-cấu-hình-khung-giờ-giao-dịch-việt-nam-vn_policyschedule)
   - [4.3. Cấu hình Quản Trị Vốn Động & Giáp Bảo Vệ Rủi Ro (`vn_policy.risk` & `protections`)](#43-cấu-hình-quản-trị-vốn-động--giáp-bảo-vệ-rủi-ro-vn_policyrisk--protections)
   - [4.4. Cấu hình Trợ Lý Phân Tích AI Đa Nguồn (`ChatGPT` + `Google Gemini`)](#44-cấu-hình-trợ-lý-phân-tích-ai-đa-nguồn-chatgpt--google-gemini)
5. [Hướng Dẫn Sử Dụng Giao Diện Web Dashboard Tiếng Việt](#5-hướng-dẫn-sử-dụng-giao-diện-web-dashboard-tiếng-việt)
6. [Hướng Dẫn Sử Dụng Ứng Dụng Android `FreqBot VN Remote`](#6-hướng-dẫn-sử-dụng-ứng-dụng-android-freqbot-vn-remote)
7. [Quy Trình Kiểm Chứng Chiến Lược & Thống Kê Khung Giờ (`hourly.py`)](#7-quy-trình-kiểm-chứng-chiến-lược--thống-kê-khung-giờ-hourlypy)
8. [Xử Lý Sự Cố Thường Gặp (Troubleshooting) & Quy Tắc An Toàn Vốn](#8-xử-lý-sự-cố-thường-gặp-troubleshooting--quy-tắc-an-toàn-vốn)

---

## 1. Tổng Quan Kiến Trúc & Thành Phần Phần Mềm

Hệ thống **FreqBot VN Remote** bao gồm 4 thành phần phần mềm phối hợp chặt chẽ:

| Thành phần | Đường dẫn mã nguồn | Chức năng chính |
| :--- | :--- | :--- |
| **1. Lõi Giao dịch Tự động Freqtrade & Chiến lược VN** | [`freqtrade-bot/user_data/strategies/VnSmartTrendStrategy.py`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/strategies/VnSmartTrendStrategy.py)<br>[`freqtrade-bot/user_data/strategies/vn_support.py`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/strategies/vn_support.py) | Kết nối sàn Binance/OKX, tính chỉ báo kỹ thuật (`EMA 20/50/200`, `RSI 14`, `Bollinger Bands`, `Volume`), lọc khung giờ giao dịch Việt Nam, tính khối lượng vốn động theo rủi ro (`stake_size`), kiểm tra báo cáo AI và vận hành 4 lớp giáp bảo vệ tự động 24/7. |
| **2. Dịch vụ Nghiên cứu Thị trường & Cố vấn AI (Sidecar)** | [`freqtrade-bot/user_data/research/run.py`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/research/run.py)<br>[`freqtrade-bot/user_data/research/providers.py`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/research/providers.py)<br>[`freqtrade-bot/user_data/research/hourly.py`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/research/hourly.py) | Quét các cặp coin trên sàn mỗi 5 phút, chấm điểm kỹ thuật (`0–100`), kiểm tra độ giãn `Bid-Ask Spread`, biến động 1h, tham vấn đồng thời **OpenAI ChatGPT** và **Google Gemini**, xuất bản chụp [`latest.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/research/latest.json) và tự động dọn dẹp lịch sử `history/`. |
| **3. Bảng Điều khiển Web Dashboard Tiếng Việt** | [`web-dashboard/index.html`](file:///e:/Project/trade_bot/web-dashboard/index.html)<br>[`web-dashboard/app.js`](file:///e:/Project/trade_bot/web-dashboard/app.js)<br>[`web-dashboard/styles.css`](file:///e:/Project/trade_bot/web-dashboard/styles.css) | Giao diện trình duyệt 100% Tiếng Việt giúp theo dõi số dư, lãi/lỗ (PnL), trạng thái chế độ chạy (`Dry-Run`/`Live`), bảng phân tích kỹ thuật & nhận định AI, danh sách lệnh đang mở và điều khiển khẩn cấp. |
| **4. Ứng dụng Di động Android (`FreqBot VN Remote`)** | [`android-app/`](file:///e:/Project/trade_bot/android-app) | Ứng dụng gốc Android (Kotlin) điều khiển Bot từ xa qua mạng riêng Tailscale VPN, chạy ngầm (`WorkManager`) phát cảnh báo Tiếng Việt khi có lệnh chốt lời/cắt lỗ hoặc chạm trần lỗ ngày, tích hợp nút **"Tạm dừng Mua"** và **"Cắt lỗ / Bán khẩn cấp toàn bộ"**. |

---

## 2. Yêu Cầu Hệ Thống (Phần Cứng, Phần Mềm & Mạng)

### 2.1. Đối với Máy chủ vận hành Bot 24/7 (VPS hoặc Máy cá nhân)
- **Hệ điều hành:** Ubuntu Server 22.04 / 24.04 LTS (khuyến nghị cho chạy 24/7) hoặc Windows 10/11 (64-bit).
- **CPU & RAM:** Tối thiểu 2 vCPU, 2 GB RAM (khuyến nghị 4 GB RAM nếu chạy kèm Backtest/Hyperopt).
- **Ổ cứng:** Tối thiểu 20 GB SSD trống.
- **Phần mềm cần cài đặt:**
  - **Python:** Phiên bản `3.11` hoặc `3.12` trở lên (để chạy kiểm thử, công cụ nghiên cứu hoặc Mock Server).
  - **Docker & Docker Compose:** Phiên bản Docker Engine `24.0+` và Docker Compose `v2+` (để đóng gói và chạy dịch vụ `freqtrade` + `research` 24/7).
  - **Node.js (Tùy chọn):** Phiên bản `18+` hoặc `20+` (để chạy kiểm thử giao diện tự động `node tests/test_dashboard.js`).
  - **Đồng bộ thời gian thực NTP (`Chrony` trên Linux):** Đảm bảo độ lệch đồng hồ hệ thống `< 100ms` so với máy chủ sàn Binance/OKX nhằm tránh lỗi `Timestamp for this request is outside of the recvWindow`.

### 2.2. Đối với Máy trạm Biên dịch Ứng dụng Android & Thiết bị Di động
- **Android Studio:** Phiên bản Iguana / Jellyfish / Koala trở lên, kèm **JDK 17** và **Android SDK API 34**.
- **Điện thoại Android:** Chạy hệ điều hành **Android 8.0 (API 26)** trở lên.
- **Mạng riêng ảo Tailscale VPN (Khuyến nghị bắt buộc khi điều khiển từ xa):** Cài đặt trên cả VPS và điện thoại Android để kết nối qua địa chỉ IP nội bộ `100.x.y.z` mà không cần mở cổng (Public Port) ra Internet.

---

## 3. Hướng Dẫn Cài Đặt Chi Tiết Từng Phân Hệ

### 3.1. Cài đặt trên Máy cá nhân Windows (Chế độ Kiểm thử nhanh & Phát triển)

Nếu bạn muốn kiểm tra toàn bộ tính năng giao diện Tiếng Việt (Web Dashboard + Ứng dụng Android) ngay lập tức mà chưa cần kết nối sàn thật hay cài Docker:

#### Bước 1: Tải mã nguồn dự án về máy
Mở **PowerShell** và thực hiện:
```powershell
git clone https://github.com/trunglc378/trade_bot.git e:\Project\trade_bot
cd e:\Project\trade_bot
```

#### Bước 2: Chạy bộ kiểm thử tự động để xác nhận môi trường sạch lỗi
```powershell
# Kiểm thử toàn bộ chính sách Khung giờ VN, Vốn động, AI Quorum, Mock API
py -3.12 -m unittest discover -s tests -v
py -3.12 -m unittest discover -s freqtrade-bot/tests -v

# Kiểm thử trình hiển thị Web Dashboard Tiếng Việt
node tests/test_dashboard.js
```

#### Bước 3: Khởi động Máy chủ Giả lập (`mock_api_server.py`)
Máy chủ giả lập đóng vai trò mô phỏng đầy đủ REST API của Freqtrade cùng dữ liệu báo cáo AI mẫu để bạn thao tác thử mọi nút bấm:
```powershell
py -3.12 freqtrade-bot/mock_api_server.py
```
Sau khi chạy lệnh trên, cửa sổ dòng lệnh sẽ hiển thị:
- **Địa chỉ API:** `http://127.0.0.1:8080`
- **Giao diện Web Dashboard Tiếng Việt:** Mở trình duyệt truy cập `http://127.0.0.1:8080/dashboard`
- **Tài khoản đăng nhập mặc định:**
  - Tài khoản (`Username`): `admin`
  - Mật khẩu (`Password`): `mat_khau_manh_cua_ban`

> **Lưu ý khi kết nối từ Máy ảo Android Emulator hoặc Điện thoại thật trong mạng LAN:**
> Mặc định `mock_api_server.py` chỉ lắng nghe trên `127.0.0.1` để bảo mật. Nếu muốn kết nối từ máy ảo Android hoặc điện thoại qua Wi-Fi nội bộ, hãy đặt biến môi trường `MOCK_HOST=0.0.0.0` trước khi chạy:
> ```powershell
> $env:MOCK_HOST="0.0.0.0"
> py -3.12 freqtrade-bot/mock_api_server.py
> ```

---

### 3.2. Kết Nối Tài Khoản Sàn Binance, OKX (Tiền Thật USDT) & AI Pro Bằng Trình Cài Đặt Tự Động (`setup_accounts.py`)

Dự án tích hợp sẵn công cụ [`freqtrade-bot/setup_accounts.py`](file:///e:/Project/trade_bot/freqtrade-bot/setup_accounts.py) giúp bạn đưa tài khoản sàn **Binance**, **OKX** cùng khóa API **ChatGPT Pro** và **Google Gemini Pro** vào hệ thống một cách an toàn tuyệt đối (tự động tách tệp cấu hình bí mật `config.private.binance.json`, `config.private.okx.json`, `.env`, khóa quyền đọc `chmod 600` và chặn hoàn toàn khỏi Git).

#### Bước 1: Tạo Khóa API An Toàn Trên Sàn Binance & Sàn OKX
1. **Trên Sàn Binance (Đã có sẵn USDT trong ví Spot / Giao ngay):**
   - Đăng nhập Binance -> Vào **Quản lý API (API Management)** -> Nhấn **Tạo API (Create API)** -> Chọn **Khóa API do hệ thống tạo (System generated)**.
   - Trong mục **Quyền hạn API (API Restrictions)**:
     - ✅ Bật **Cho phép Đọc (Enable Reading)**.
     - ✅ Bật **Bật Giao dịch Spot & Margin (Enable Spot & Margin Trading)**.
     - ❌ **TUYỆT ĐỐI KHÔNG BẬT** quyền **Rút tiền (Enable Withdrawals)**.
   - Trong mục **Giới hạn truy cập IP (IP Access Restrictions)**: Chọn **Chỉ giới hạn cho các IP đáng tin cậy (Restrict access to trusted IPs only)** và điền **Địa chỉ IP công cộng (Public IPv4)** của máy chủ Oracle Cloud của bạn.
   - Lưu lại **API Key** và **Secret Key**.
2. **Trên Sàn OKX (Đã có sẵn USDT trong tài khoản Giao dịch / Trading Account):**
   - Đăng nhập OKX -> Vào **Hồ sơ** -> **API** -> Nhấn **Tạo khóa API (Create V5 API Key)**.
   - Chọn mục đích **Giao dịch API (API Trading)**.
   - Đặt **Mật khẩu cụm từ (Passphrase)** — *Hãy ghi nhớ mật khẩu này vì OKX bắt buộc cả 3 thông tin: API Key + Secret Key + Passphrase*.
   - Điền **Địa chỉ IP công cộng của máy chủ Oracle Cloud** vào ô **Danh sách IP được phép (IP Whitelist)**.
   - Trong mục **Quyền (Permissions)**: Chọn **Đọc (Read)** và **Giao dịch (Trade)**; **TUYỆT ĐỐI KHÔNG CHỌN** **Rút tiền (Withdraw)**.
   - Lưu lại **API Key**, **Secret Key** và **Passphrase**.

#### Bước 2: Lấy Khóa API Cho ChatGPT Pro (`OPENAI_API_KEY`) & Google Gemini Pro (`GEMINI_API_KEY`)
- **OpenAI (ChatGPT):** Truy cập `https://platform.openai.com/api-keys`, tạo khóa `sk-proj-...` (mã model Pro khuyên dùng: `gpt-4.1`).
- **Google Gemini Pro:** Truy cập `https://aistudio.google.com/app/apikey`, tạo khóa `AIzaSy...` (mã model Pro khuyên dùng: `gemini-2.5-pro`).

#### Bước 3: Chạy Trình Kết Nối Tài Khoản Tự Động (`setup_accounts.py`)
Di chuyển vào thư mục [`freqtrade-bot/`](file:///e:/Project/trade_bot/freqtrade-bot) và chạy:
```powershell
cd e:\Project\trade_bot\freqtrade-bot
py -3.12 setup_accounts.py
```
Trình thuật sĩ Tiếng Việt sẽ lần lượt hỏi bạn:
1. Chế độ vận hành (`dry` = Giao dịch thử an toàn với 1000 USDT ảo, hoặc `live` = Giao dịch tiền thật USDT trên sàn với cơ sở dữ liệu `tradesv3.*.live.sqlite` tách biệt).
2. Tài khoản & mật khẩu điều khiển từ xa cho Ứng dụng Android / Web Dashboard (kèm tự động sinh khóa `jwt_secret_key` 64 ký tự và `ws_token`).
3. Khóa `OPENAI_API_KEY` (model `gpt-4.1`) và `GEMINI_API_KEY` (model `gemini-2.5-pro`).
4. Khóa `API Key` + `Secret Key` của **Binance** và `API Key` + `Secret Key` + `Passphrase` của **OKX**.

#### Bước 4: Khởi Chạy Hệ Thống 24/7 Bằng Docker Compose (Hỗ Trợ Chạy Đơn Sàn Hoặc Song Song Cả 2 Sàn)
Từ thư mục [`freqtrade-bot/`](file:///e:/Project/trade_bot/freqtrade-bot):
```powershell
# Trường hợp 1: Chỉ chạy sàn Binance (cổng 8080) + AI Research Binance
docker compose up -d

# Trường hợp 2: Chạy SONG SONG cả sàn Binance (cổng 8080) VÀ sàn OKX (cổng 8081) cùng lúc
docker compose --profile okx up -d
```
- **Sàn Binance:** Mở API tại cổng `8080`, đọc/ghi báo cáo nghiên cứu tại `user_data/research/latest.json`.
- **Sàn OKX:** Mở API tại cổng `8081`, đọc/ghi báo cáo nghiên cứu riêng biệt tại `user_data/research/latest-okx.json` và lịch sử tại `user_data/research/history-okx/`.

---

### 3.3. Triển Khai 24/24 Miễn Phí Trọn Đời (0 Đồng) Trên Oracle Cloud Free Tier (`deploy_oracle_cloud_24_7.sh`)

Dự án cung cấp sẵn kịch bản cài đặt tự động 1 chạm [`freqtrade-bot/deploy_oracle_cloud_24_7.sh`](file:///e:/Project/trade_bot/freqtrade-bot/deploy_oracle_cloud_24_7.sh) được thiết kế chuyên biệt cho máy ảo **Oracle Cloud Always Free (Ubuntu 22.04 / 24.04 LTS — hỗ trợ cả chip Ampere ARM64 4 OCPU / 24GB RAM và AMD64)**.

1. **Tạo máy ảo miễn phí trên Oracle Cloud (OCI):**
   - Chọn vùng máy chủ (**Region**): **Singapore (`ap-singapore-1`)** hoặc **Tokyo (`ap-tokyo-1`)** để có độ trễ thấp nhất tới máy chủ khớp lệnh của Binance & OKX.
   - Chọn hệ điều hành (**Image**): **Ubuntu 22.04 LTS** hoặc **Ubuntu 24.04 LTS**.
   - Chọn cấu hình (**Shape**): **Ampere `VM.Standard.A1.Flex` (Always Free — tối đa 4 OCPU, 24 GB RAM)**.
2. **Chạy kịch bản cài đặt tự động 24/7 trên máy chủ Oracle Cloud:**
   Kết nối SSH vào máy chủ Oracle Cloud và chạy đúng 3 dòng lệnh sau:
   ```bash
   git clone https://github.com/trunglc378/trade_bot.git ~/trade_bot
   cd ~/trade_bot/freqtrade-bot
   bash deploy_oracle_cloud_24_7.sh
   ```
   Kịch bản `deploy_oracle_cloud_24_7.sh` sẽ tự động thực hiện toàn bộ 6 bước:
   - `[1/6]` Cài đặt & kích hoạt đồng bộ thời gian thực chuẩn sàn **Chrony (NTP)** + đặt múi giờ `Asia/Ho_Chi_Minh`.
   - `[2/6]` Khởi tạo **2 GB bộ nhớ đệm Swap** chống tràn bộ nhớ tuyệt đối.
   - `[3/6]` Cài đặt **Docker Engine & Docker Compose v2** tự khởi động cùng hệ thống.
   - `[4/6]` Cài đặt mạng riêng ảo **Tailscale Mesh VPN**.
   - `[5/6]` Khóa toàn bộ cổng công cộng bằng tường lửa **`UFW`**, chỉ cho phép cổng `8080` (Binance) và `8081` (OKX) đi qua giao diện mạng riêng `tailscale0`.
   - `[6/6]` Khởi tạo sẵn các tệp cấu hình bảo mật mặc định.
3. **Kết nối Tailscale & Nhập tài khoản Binance / OKX / AI Pro:**
   ```bash
   # Đăng nhập Tailscale VPN và lấy địa chỉ IP 100.x.y.z của VPS
   sudo tailscale up
   tailscale ip -4

   # Chạy trình thuật sĩ nhập khóa Binance, OKX, ChatGPT Pro, Gemini Pro và IP Tailscale
   python3 setup_accounts.py

   # Khởi chạy 24/7 cả 2 sàn Binance (cổng 8080) & OKX (cổng 8081)
   sudo docker compose --profile okx up -d
   ```

---

### 3.4. Biên dịch & Cài đặt Ứng dụng Di động Android (`FreqBot VN Remote`)

1. Mở phần mềm **Android Studio** trên máy tính.
2. Chọn **Open** và trỏ tới thư mục [`e:\Project\trade_bot\android-app`](file:///e:/Project/trade_bot/android-app).
3. Chờ Android Studio đồng bộ cấu hình **Gradle** (tự động tải các thư viện `Retrofit2`, `OkHttp3`, `Kotlin Coroutines`, `WorkManager`, `EncryptedSharedPreferences`, `Material Design`).
4. Cắm cáp USB kết nối điện thoại Android (đã bật **Gỡ lỗi USB / USB Debugging**) hoặc khởi động máy ảo **Android Emulator**.
5. Nhấn nút **Run (`Shift + F10`)** trên thanh công cụ để cài đặt ứng dụng **FreqBot VN Remote** lên điện thoại, hoặc chọn **Build > Build Bundle(s) / APK(s) > Build APK(s)** để xuất tệp cài đặt `.apk`.

---

## 4. Hướng Dẫn Cấu Hình Hệ Thống (`config.json`, `config-okx.json`, `.env`)

Toàn bộ cấu hình vận hành của Bot nằm tại [`freqtrade-bot/user_data/config.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/config.json) (mặc định cho sàn **Binance**) và [`freqtrade-bot/user_data/config-okx.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/config-okx.json) (lớp phủ cấu hình cho sàn **OKX**).

### 4.1. Cấu hình Sàn giao dịch Binance & OKX
- **Sàn Binance (Mặc định):** Sử dụng trực tiếp `config.json`. Danh sách cặp giao dịch mặc định gồm `BTC/USDT`, `ETH/USDT`, `BNB/USDT`, `SOL/USDT`, `XRP/USDT`, `ADA/USDT`, `AVAX/USDT`, `LINK/USDT`.
- **Sàn OKX (Spot USDT):** Khi muốn chạy trên sàn OKX, truyền đồng thời cả `config.json` và `config-okx.json` cho **cả hai dịch vụ** (`freqtrade` và `research`) để mã băm ngữ cảnh `context_id` khớp tuyệt đối:
  ```bash
  # Chạy dịch vụ nghiên cứu AI trên sàn OKX
  py -3.12 freqtrade-bot/user_data/research/run.py \
      --config freqtrade-bot/user_data/config.json \
      --config freqtrade-bot/user_data/config-okx.json
  ```

### 4.2. Cấu hình Khung Giờ Giao Dịch Việt Nam (`vn_policy.schedule`)
Khối `vn_policy.schedule` trong [`config.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/config.json) kiểm soát thời điểm Bot được phép **Mua mới (`enter_long`)** theo múi giờ chuẩn Việt Nam (`Asia/Ho_Chi_Minh`, UTC+7):
```json
"schedule": {
    "enabled": true,
    "windows": [
        {
            "start": "03:00",
            "end": "04:00",
            "weekdays": [0, 1, 2, 3, 4, 5, 6]
        }
    ]
}
```
- **Giải thích thông số:**
  - `"enabled": true`: Bật bộ lọc khung giờ giao dịch. Nếu đặt `false`, Bot sẽ được phép mở lệnh mua mới 24/7 bất kỳ lúc nào có tín hiệu.
  - `"start"` và `"end"`: Giờ bắt đầu (bao gồm) và giờ kết thúc (không bao gồm) theo định dạng 24 giờ `HH:MM`. Ví dụ `"03:00"` đến `"04:00"` cho phép mở lệnh từ `03:00:00` đến `03:59:59` sáng giờ Việt Nam. Hỗ trợ cả khung giờ vắt qua nửa đêm (ví dụ `"start": "23:00"`, `"end": "02:00"`).
  - `"weekdays"`: Danh sách các ngày trong tuần được phép mua (`0` = Thứ Hai, `1` = Thứ Ba, ..., `6` = Chủ Nhật).
- **Quy tắc Bất đối xứng Bảo toàn Vốn:** Ngoài khung giờ trên, Bot chỉ khóa chiều **Mua vào**, nhưng vẫn thức **24/7** để canh chốt lời (`ROI` / `Trailing Stop`), giữ lệnh cắt lỗ cứng trên sàn (`Hard Stop-Loss`) và thực thi lệnh **Bán khẩn cấp (`Panic Sell`)** ngay lập tức khi người dùng bấm nút.

### 4.3. Cấu hình Quản Trị Vốn Động & Giáp Bảo Vệ Rủi Ro (`vn_policy.risk` & `protections`)
Khối `vn_policy.risk` tự động tính khối lượng vốn (`stake_amount`) cho từng lệnh dựa trên tổng tài sản hiện có:
```json
"risk": {
    "risk_per_trade": 0.005,
    "max_position_fraction": 0.2,
    "max_exposure_fraction": 0.6,
    "cost_buffer": 0.004,
    "max_entry_deviation": 0.005
}
```
- `risk_per_trade` (`0.005` = `0.5%`): Nếu lệnh chạm cắt lỗ (`-3.0%`) cộng đệm phí/trượt giá (`cost_buffer = 0.4%`), tổng số tiền thiệt hại tối đa của lệnh đó không vượt quá `0.5%` tổng vốn tài khoản.
- `max_position_fraction` (`0.2` = `20%`): Không bao giờ dồn quá `20%` tổng vốn vào một lệnh đơn lẻ.
- `max_exposure_fraction` (`0.6` = `60%`): Tổng giá trị tất cả các lệnh đang mở cùng lúc không vượt quá `60%` tổng vốn (luôn giữ tối thiểu `40%` tiền mặt USDT dự phòng).
- `max_entry_deviation` (`0.005` = `0.5%`): Từ chối đặt lệnh nếu giá khớp thực tế lệch quá `0.5%` so với giá đóng cửa của nến tín hiệu gần nhất.

### 4.4. Cấu hình Trợ Lý Phân Tích AI Đa Nguồn (`ChatGPT` + `Google Gemini`)
Khối `vn_policy.research` điều khiển cách Bot kết hợp phân tích định lượng với nhận định từ các mô hình ngôn ngữ lớn:
```json
"research": {
    "mode": "advisory",
    "ttl_seconds": 900,
    "min_quote_volume": 10000000,
    "max_spread": 0.002,
    "max_volatility": 0.02,
    "max_hour_change": 0.06,
    "max_history_files": 288,
    "providers": {},
    "min_ai_votes": 1,
    "min_ai_confidence": 0.65
}
```
- **3 Chế độ vận hành (`mode`):**
  1. `"off"`: Tắt kiểm tra tệp báo cáo nghiên cứu khi vào lệnh (phù hợp khi chạy Backtest lịch sử hoặc chỉ dùng chỉ báo kỹ thuật thuần túy).
  2. `"advisory"` (**Mặc định khuyên dùng**): Bắt buộc phải có tệp báo cáo `latest.json` còn hạn (`ttl_seconds = 900` giây = 15 phút) và cặp coin phải vượt qua các bộ lọc kỹ thuật định lượng (khối lượng 24h `>= 10 triệu USDT`, độ giãn Spread `<= 0.2%`, biến động nến `<= 2%`, biến động 1 giờ `<= 6%`). Nếu có cấu hình thêm `providers` AI, nhận định của AI sẽ được hiển thị để tham khảo; nếu bất kỳ AI nào bỏ phiếu **Né tránh (`avoid`)**, cặp coin đó sẽ bị loại khỏi danh sách mua.
  3. `"required"`: Chế độ **Bắt buộc Đồng thuận AI**. Ngoài việc đạt chuẩn kỹ thuật, cặp coin bắt buộc phải nhận đủ số phiếu **Đề xuất Mua (`consider`)** từ tối thiểu `min_ai_votes` nhà cung cấp AI (ví dụ cả `openai` và `gemini`) với độ tự tin `>= min_ai_confidence` (ví dụ `0.70`) và không có phiếu phủ quyết (`avoid`).

---

## 5. Hướng Dẫn Sử Dụng Giao Diện Web Dashboard Tiếng Việt

Mở trình duyệt truy cập `http://127.0.0.1:8080/dashboard` (khi chạy `mock_api_server.py`) hoặc mở tệp [`web-dashboard/index.html`](file:///e:/Project/trade_bot/web-dashboard/index.html):

1. **Thanh Kết Nối Máy Chủ (Phía trên cùng):**
   - Nhập **Địa chỉ API Freqtrade** (ví dụ `http://127.0.0.1:8080`), **Tài khoản** và **Mật khẩu**, sau đó nhấn nút **"Kết Nối & Đăng Nhập"**.
   - Sau khi đăng nhập thành công, Dashboard sẽ tự động làm mới dữ liệu mỗi **5 giây/lần**.
2. **4 Thẻ Thông Số Tổng Quan Tiếng Việt:**
   - **Tổng Vốn Tài Khoản (USDT):** Hiển thị tổng giá trị tài sản quy đổi ra USDT và số dư USDT khả dụng/đang đóng băng.
   - **Tổng Lợi Nhuận Đã Chốt:** Hiển thị lãi/lỗ ròng đã đóng lệnh (USDT và `%`) kèm tỷ lệ thắng (`Winrate`).
   - **Trạng Thái Giáp Rủi Ro & Chế Độ Bot:** Cho biết Bot đang chạy ở chế độ **Giao dịch thử (`Dry-Run`)** hay **Tiền thật (`Live`)**, trạng thái **Đang hoạt động** hay **Đang tạm dừng Mua mới (`PAUSED`)**, hoặc cảnh báo đỏ nếu lớp giáp `Protections` đang khóa Bot.
   - **Số Lệnh Đang Mở:** Hiển thị số lượng vị thế đang nắm giữ so với trần tối đa (`3 lệnh`).
3. **Bảng Phân Tích Thị Trường & Cố Vấn AI (`ChatGPT` + `Gemini`):**
   - **Chọn tệp báo cáo:** Nhấn nút chọn tệp và trỏ tới [`freqtrade-bot/user_data/research/latest.json`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/research/latest.json) để xem báo cáo nghiên cứu mới nhất từ ổ đĩa.
   - **Nút "Đồng Bộ Báo Cáo Máy Chủ Giả Lập":** Khi đang chạy `mock_api_server.py`, nhấn nút này để tải ngay báo cáo trực tiếp từ máy chủ mà không cần chọn tệp thủ công.
   - **Ý nghĩa các cột trong bảng:**
     - **Điểm KT:** Điểm sức mạnh kỹ thuật định lượng trên thang `0–100`.
     - **Trạng thái thị trường:** Được dịch rõ sang Tiếng Việt (`Xu hướng tăng`, `Đi ngang tích lũy`, `Quá mua ngắn hạn`, `Giảm dưới EMA200`).
     - **ChatGPT (OpenAI) & Google Gemini:** Hiển thị phiếu bầu (`Đề xuất Mua`, `Đứng ngoài chờ`, `Né tránh / Từ chối`), độ tự tin (`%`) và lý do chi tiết bằng Tiếng Việt.
     - **Kết luận duyệt lệnh:** Hiển thị `✅ Qua bộ lọc` (đủ điều kiện mua trong phiên) hoặc `⛔ Không qua bộ lọc` / `⏰ Báo cáo hết hạn` kèm nguyên nhân cụ thể.
4. **3 Nút Điều Khiển Khẩn Cấp:**
   - **⏸️ Tạm Dừng Mua Mới (`StopBuy`):** Khóa ngay chiều mở lệnh mua mới, giữ nguyên các lệnh đang mở để Bot tiếp tục canh chốt lời/cắt lỗ.
   - **▶️ Bật Lại Chế Độ Mua (`Reload`):** Khôi phục trạng thái cho phép mở lệnh mua mới.
   - **🚨 CẮT LỖ / BÁN KHẨN CẤP TOÀN BỘ (`PANIC SELL`):** Hiển thị hộp thoại xác nhận kép; khi đồng ý sẽ xả toàn bộ các lệnh đang mở về tiền mặt `USDT` ngay lập tức.

---

## 6. Hướng Dẫn Sử Dụng Ứng Dụng Android `FreqBot VN Remote`

Trên màn hình chính của ứng dụng di động **FreqBot VN Remote**:

1. **Thiết lập Kết nối Máy chủ (`⚙️ Máy chủ`):**
   - Nhấn nút **`⚙️ Máy chủ`** ở góc trên bên phải.
   - Nhập địa chỉ IP Tailscale VPN của VPS (ví dụ `http://100.88.99.101:8080/`) hoặc địa chỉ máy ảo (`http://10.0.2.2:8080/`), tài khoản và mật khẩu.
   - Nhấn **Lưu & Đăng nhập**. Thông tin xác thực và JWT Token sẽ được mã hóa phần cứng bằng `EncryptedSharedPreferences` (`Android Keystore AES-256`).
2. **Theo dõi Trạng thái Thời gian thực (100% Tiếng Việt):**
   - **Thanh trạng thái Giáp bảo vệ rủi ro:** Báo xanh khi hệ thống bình thường (kèm nhãn chế độ `Giao dịch thử (Dry-Run)` hoặc `Tiền thật (Live)`), chuyển sang vàng khi đang **Tạm dừng Mua mới**, hoặc đỏ rực khi chạm trần lỗ ngày.
   - **Thẻ Tổng quan Hiệu suất & Số dư USDT:** Cập nhật tự động mỗi 5 giây khi mở ứng dụng.
   - **Thẻ Phân tích Thị trường & Cố vấn AI:** Hiển thị trạng thái khung giờ giao dịch hiện tại (`Trong khung giờ giao dịch` / `Ngoài khung giờ Mua mới`), chế độ lọc AI (`Cố vấn tham khảo` / `Bắt buộc đồng thuận AI`) và danh sách các cặp coin tiềm năng kèm nhận định Tiếng Việt từ **ChatGPT** và **Gemini**.
3. **Thao tác Đóng lệnh đơn lẻ & Bán khẩn cấp (`Panic Sell`):**
   - Tại từng thẻ lệnh đang mở trong danh sách dưới cùng, bạn có thể nhấn nút **"Đóng lệnh này"** để thanh lý riêng cặp coin đó về USDT.
   - Trong trường hợp thị trường sập mạnh bất ngờ, nhấn nút đỏ lớn **"🚨 CẮT LỖ / BÁN KHẨN CẤP TOÀN BỘ (THU HỒI USDT)"** và xác nhận để thu hồi toàn bộ vốn về USDT.
4. **Cảnh báo Chạy ngầm Tự động (`WorkManager`):**
   - Ngay cả khi bạn đóng ứng dụng, tiến trình ngầm `BotMonitorWorker` vẫn kiểm tra trạng thái Bot định kỳ mỗi 15 phút và đẩy thông báo Tiếng Việt lên màn hình khóa điện thoại khi có lệnh vừa chốt lời/cắt lỗ hoặc khi lớp giáp rủi ro kích hoạt.

---

## 7. Quy Trình Kiểm Chứng Chiến Lược & Thống Kê Khung Giờ (`hourly.py`)

Trước khi quyết định sử dụng bất kỳ khung giờ giao dịch nào (như giả thuyết `03:00–04:00 sáng giờ Việt Nam`), bạn nên kiểm chứng định lượng trên dữ liệu lịch sử bằng công cụ [`freqtrade-bot/user_data/research/hourly.py`](file:///e:/Project/trade_bot/freqtrade-bot/user_data/research/hourly.py):

```powershell
# Phân tích kết quả Backtest của Freqtrade theo từng giờ Việt Nam (00h -> 23h)
py -3.12 freqtrade-bot/user_data/research/hourly.py duong_dan_ket_qua_backtest.json --min-trades 30
```
Công cụ sẽ xuất báo cáo JSON thống kê cho từng khung giờ từ `0` đến `23` (múi giờ `Asia/Ho_Chi_Minh`) gồm: tổng số lệnh (`trades`), tỷ lệ thắng (`win_rate`), lợi nhuận ròng (`net_profit`), hệ số lợi nhuận (`profit_factor`) và cờ đánh giá đủ kích thước mẫu (`enough_samples: true` khi đạt tối thiểu 30 lệnh).

---

## 8. Xử Lý Sự Cố Thường Gặp (Troubleshooting) & Quy Tắc An Toàn Vốn

| Triệu chứng / Thông báo lỗi | Nguyên nhân gốc rễ | Cách khắc phục nhanh |
| :--- | :--- | :--- |
| **Bot không mở lệnh mua mới dù có tín hiệu kỹ thuật tốt** | 1. Đang ở ngoài khung giờ `vn_policy.schedule` (`03:00–04:00 VN`).<br>2. Chế độ `research.mode` là `advisory`/`required` nhưng tệp `latest.json` chưa được tạo hoặc đã quá hạn 15 phút (`ttl_seconds`). | 1. Kiểm tra giờ hiện tại hoặc đặt `"enabled": false` trong `vn_policy.schedule` nếu muốn mua 24/7.<br>2. Đảm bảo dịch vụ `research/run.py` đang chạy định kỳ hoặc chuyển `research.mode` sang `"off"` khi test nhanh. |
| **Bảng AI báo `⏰ Báo cáo hết hạn` hoặc `⛔ Không qua bộ lọc`** | Bản chụp `latest.json` được tạo cách đây hơn `900 giây`, hoặc cấu hình sàn/whitelist giữa Bot và `run.py` không khớp (`context_id` khác nhau). | Chạy lại lệnh `py -3.12 freqtrade-bot/user_data/research/run.py --config freqtrade-bot/user_data/config.json` với cùng các tệp `--config` như lúc chạy Bot. |
| **Ứng dụng Android báo `Lỗi mạng hoặc VPS chưa bật`** | Sai địa chỉ IP/cổng trong mục `⚙️ Máy chủ`, hoặc `mock_api_server.py` đang chỉ lắng nghe trên `127.0.0.1`. | Nếu dùng máy ảo Android Emulator, nhập `http://10.0.2.2:8080/`. Nếu dùng điện thoại thật qua Tailscale VPN, nhập `http://100.x.y.z:8080/` và đảm bảo máy chủ đã bind đúng IP. |
| **Lỗi gọi API OpenAI / Google Gemini** | Chưa thiết lập `OPENAI_API_KEY` / `GEMINI_API_KEY` hoặc tên model trong `providers` không khớp với quyền truy cập tài khoản. | Kiểm tra tệp `.env` và cập nhật đúng mã model khả dụng trong `vn_policy.research.providers`. Ở chế độ `advisory`, lỗi mạng từ phía AI sẽ được ghi nhận an toàn mà không làm sập tiến trình quét kỹ thuật. |

> **⚠️ NGUYÊN TẮC KỶ LUẬT AN TOÀN VỐN BẮT BUỘC:**
> 1. Luôn vận hành ở chế độ **Giao dịch thử (`"dry_run": true`)** tối thiểu từ **2 đến 4 tuần** để kiểm chứng độ ổn định của kết nối sàn, mức trượt giá thực tế và hành vi của bộ lọc AI trước khi cân nhắc chạy tiền thật.
> 2. Khi tạo khóa API trên sàn Binance hoặc OKX, **CHỈ BẬT** quyền `Read Info` (Đọc dữ liệu) và `Spot Trading` (Giao dịch Giao ngay); **TUYỆT ĐỐI KHÔNG BẬT** quyền `Enable Withdrawals` (Rút tiền).
> 3. Khi chuyển sang chế độ tiền thật (`Live`), hãy cấu hình tệp cơ sở dữ liệu SQLite riêng (`tradesv3.live.sqlite`), tách biệt hoàn toàn với cơ sở dữ liệu thử nghiệm (`tradesv3.dryrun.sqlite`).
