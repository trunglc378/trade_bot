#!/usr/bin/env bash
# ==============================================================================
# KỊCH BẢN CÀI ĐẶT TỰ ĐỘNG 24/7 TRÊN ORACLE CLOUD FREE TIER (UBUNTU 22.04/24.04)
# Dự án: Hệ thống Giao dịch Tự động & Cố vấn AI Đa nguồn (FreqBot VN Remote)
# Hỗ trợ ARM64 và AMD64; kiểm tra hạn mức Always Free hiện tại trên OCI Console.
# ==============================================================================
set -euo pipefail

echo "=============================================================================="
echo "🚀 BẮT ĐẦU CÀI ĐẶT HẠ TẦNG 24/7 TRÊN ORACLE CLOUD FREE TIER (FREQBOT VN REMOTE)"
echo "=============================================================================="

# 1. Cập nhật hệ thống & cài đặt đồng bộ thời gian thực NTP (Chrony)
echo "[1/6] Cài đặt các gói nền tảng và đồng bộ đồng hồ chuẩn sàn (Chrony NTP)..."
sudo apt-get update -y
sudo apt-get install -y chrony curl git ufw ca-certificates gnupg lsb-release python3 python3-pip
sudo systemctl enable --now chrony

# Đặt múi giờ máy chủ về chuẩn giờ Việt Nam (Asia/Ho_Chi_Minh) để dễ theo dõi nhật ký
sudo timedatectl set-timezone Asia/Ho_Chi_Minh || true

# 2. Tạo Swap 2GB để giảm nguy cơ hết RAM; vẫn cần theo dõi tài nguyên.
if ! sudo swapon --show | grep -q '/swapfile'; then
    echo "[2/6] Khởi tạo 2GB bộ nhớ đệm Swap..."
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
    fi
else
    echo "[2/6] Bộ nhớ Swap đã tồn tại, bỏ qua."
fi

# 3. Cài đặt Docker Engine & Docker Compose v2 (Hỗ trợ cả ARM64 và AMD64)
if ! command -v docker >/dev/null 2>&1; then
    echo "[3/6] Cài đặt Docker Engine và Docker Compose plugin..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER" || true
    sudo systemctl enable --now docker
else
    echo "[3/6] Docker đã được cài đặt sẵn."
fi

# 4. Cài đặt mạng riêng ảo Tailscale VPN (Truy cập từ App Android không cần mở Port công cộng)
if ! command -v tailscale >/dev/null 2>&1; then
    echo "[4/6] Cài đặt mạng riêng ảo Tailscale Mesh VPN..."
    curl -fsSL https://tailscale.com/install.sh | sh
else
    echo "[4/6] Tailscale VPN đã được cài đặt sẵn."
fi

# 5. Thiết lập tường lửa UFW (Khóa toàn bộ cổng công cộng, chỉ mở cổng 8080/8081 trên mạng riêng Tailscale)
echo "[5/6] Cấu hình tường lửa bảo mật UFW..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow in on tailscale0 to any port 8080 proto tcp comment 'FreqBot Binance API via Tailscale' || true
sudo ufw allow in on tailscale0 to any port 8081 proto tcp comment 'FreqBot OKX API via Tailscale' || true
sudo ufw --force enable

# 6. Khởi tạo tệp cấu hình bảo mật mặc định nếu chưa có
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo "[6/6] Khởi tạo tệp cấu hình mẫu (Dry-Run an toàn)..."
python3 setup_accounts.py --init-defaults

echo "=============================================================================="
echo "✅ HOÀN TẤT CÀI ĐẶT HẠ TẦNG ORACLE CLOUD 24/7!"
echo "=============================================================================="
echo "Các bước tiếp theo dành cho bạn:"
echo "  Bước 1: Kết nối VPS vào mạng Tailscale (nếu chưa đăng nhập):"
echo "          sudo tailscale up"
echo "          tailscale ip -4"
echo "  Bước 2: Nhập khóa API Binance, OKX, ChatGPT Pro và Gemini Pro:"
echo "          python3 setup_accounts.py"
echo "  Bước 3: Khởi chạy Bot 24/7 bằng Docker Compose:"
echo "          sudo docker compose up -d                 # Chỉ chạy sàn Binance (cổng 8080)"
echo "          sudo docker compose --profile okx up -d   # Chạy song song cả Binance (8080) & OKX (8081)"
echo "=============================================================================="
