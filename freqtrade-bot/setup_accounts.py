#!/usr/bin/env python3
"""
Trình cài đặt & kết nối tài khoản tự động bằng Tiếng Việt (FreqBot VN Remote)
Hỗ trợ:
1. Nhập khóa API Sàn Binance (API Key + Secret Key) và Sàn OKX (API Key + Secret Key + Passphrase).
2. Nhập khóa API ChatGPT Pro (OpenAI) & Google Gemini Pro, cấu hình model AI Pro.
3. Sinh tự động khóa bảo mật JWT Secret (64 ký tự) & WebSocket Token cho App Android / Web Dashboard.
4. Lựa chọn chế độ chạy an toàn (Giao dịch thử Dry-Run hoặc Tiền thật Live USDT với DB tách biệt).
5. Tự động tạo các tệp cấu hình riêng (được bảo vệ bởi .gitignore và chmod 600, không bao giờ lộ lên Git).
"""
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOT_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = BOT_DIR / "user_data"


def build_private_config(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    api_passphrase: str,
    dry_run: bool,
    admin_user: str,
    admin_password: str,
    jwt_secret: str,
    ws_token: str,
    ai_mode: str,
    openai_model: str,
    gemini_model: str,
) -> dict:
    """Tạo cấu trúc JSON cấu hình bí mật cho từng sàn (Binance hoặc OKX)."""
    if exchange_name not in ("binance", "okx"):
        raise ValueError(f"Sàn không hợp lệ: {exchange_name}")
    if ai_mode not in ("off", "advisory", "required"):
        raise ValueError(f"Chế độ AI không hợp lệ: {ai_mode}")

    providers = {}
    if openai_model.strip():
        providers["openai"] = openai_model.strip()
    if gemini_model.strip():
        providers["gemini"] = gemini_model.strip()

    min_votes = max(1, len(providers)) if providers else 1

    exchange_cfg = {
        "name": exchange_name,
        "key": api_key.strip(),
        "secret": api_secret.strip(),
    }
    if exchange_name == "okx":
        exchange_cfg["password"] = api_passphrase.strip()

    research_cfg = {
        "mode": ai_mode,
        "providers": providers,
        "min_ai_votes": min_votes,
        "min_ai_confidence": 0.70,
        "report_file": "latest-okx.json" if exchange_name == "okx" else "latest.json",
    }

    return {
        "dry_run": bool(dry_run),
        "exchange": exchange_cfg,
        "api_server": {
            "jwt_secret_key": jwt_secret,
            "ws_token": ws_token,
            "username": admin_user.strip() or "admin",
            "password": admin_password,
        },
        "vn_policy": {
            "research": research_cfg,
        },
    }


def write_secure_json(path: Path, payload: dict) -> None:
    """Ghi tệp JSON cấu hình bí mật và giới hạn quyền đọc (chmod 600 trên Linux)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def write_env_file(
    env_path: Path,
    openai_key: str,
    gemini_key: str,
    tailscale_ip: str,
    dry_run: bool,
    research_interval: int = 300,
) -> None:
    """Ghi tệp .env cho Docker Compose (tự động chọn tệp SQLite tách biệt giữa Dry-Run và Live)."""
    binance_db = "tradesv3.binance.dryrun.sqlite" if dry_run else "tradesv3.binance.live.sqlite"
    okx_db = "tradesv3.okx.dryrun.sqlite" if dry_run else "tradesv3.okx.live.sqlite"
    lines = [
        "# Tệp môi trường tự động tạo bởi setup_accounts.py (Tuyệt đối không commit lên Git)",
        f"OPENAI_API_KEY={openai_key.strip()}",
        f"GEMINI_API_KEY={gemini_key.strip()}",
        f"RESEARCH_INTERVAL_SECONDS={max(60, int(research_interval))}",
        f"TAILSCALE_IP={tailscale_ip.strip() or '127.0.0.1'}",
        "BINANCE_PRIVATE_CONFIG=config.private.binance.json",
        f"BINANCE_DB_FILE={binance_db}",
        "OKX_PRIVATE_CONFIG=config.private.okx.json",
        f"OKX_DB_FILE={okx_db}",
        "",
    ]
    env_path.write_text("\n".join(lines), encoding="utf-8")
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass


def prompt_text(label: str, default: str = "", secret: bool = False) -> str:
    suffix = f" [{default}]" if default and not secret else (" [Đã ẩn]" if default and secret else "")
    prompt_str = f"{label}{suffix}: "
    val = getpass.getpass(prompt_str) if secret else input(prompt_str)
    return val.strip() if val.strip() else default


def run_interactive() -> int:
    print("=" * 76)
    print("🤖 TRÌNH CÀI ĐẶT TÀI KHOẢN BINANCE / OKX & AI PRO (FREQBOT VN REMOTE)")
    print("=" * 76)
    print("Lưu ý Bảo mật An toàn Vốn:")
    print("  1. Khi tạo API Key trên Binance & OKX, CHỈ BẬT quyền 'Read' (Đọc) và")
    print("     'Spot Trading' (Giao dịch Giao ngay). TUYỆT ĐỐI KHÔNG BẬT quyền Rút tiền!")
    print("  2. Mọi khóa bạn nhập dưới đây chỉ lưu cục bộ trong tệp .private.json & .env")
    print("     (đã khóa quyền đọc 600 và chặn hoàn toàn khỏi Git).\n")

    mode_choice = prompt_text(
        "Chọn chế độ vận hành ('dry' = Giao dịch thử an toàn, 'live' = Giao dịch tiền thật USDT)",
        default="dry",
    ).lower()
    dry_run = mode_choice != "live"
    if not dry_run:
        confirm = prompt_text(
            "⚠️ CẢNH BÁO: Bạn đang chọn chạy TIỀN THẬT (LIVE USDT). Gõ 'DONG_Y' để xác nhận",
            default="HUY",
        )
        if confirm != "DONG_Y":
            print("-> Đã tự động chuyển về chế độ Giao dịch thử (Dry-Run) để bảo vệ vốn.")
            dry_run = True

    print("\n--- 1. CẤU HÌNH TÀI KHOẢN ĐIỀU KHIỂN TỪ XA (APP ANDROID & WEB DASHBOARD) ---")
    admin_user = prompt_text("Tên đăng nhập điều khiển Bot", default="admin")
    admin_password = prompt_text(
        "Mật khẩu điều khiển Bot (để trống sẽ tự sinh mật khẩu mạnh)",
        default="",
        secret=True,
    )
    generated_pwd = False
    if not admin_password:
        admin_password = secrets.token_urlsafe(16)
        generated_pwd = True
    tailscale_ip = prompt_text(
        "Địa chỉ IP Tailscale của VPS Oracle Cloud (để 127.0.0.1 nếu chạy trên máy này)",
        default="127.0.0.1",
    )

    print("\n--- 2. KẾT NỐI TRÍ TUỆ NHÂN TẠO BẢN PRO (CHATGPT PRO & GEMINI PRO) ---")
    openai_key = prompt_text("Nhập OPENAI_API_KEY (Platform OpenAI, nhấn Enter nếu bỏ qua)", secret=True)
    openai_model = (
        prompt_text("Mã model OpenAI Pro sử dụng", default="gpt-4.1")
        if openai_key
        else ""
    )
    gemini_key = prompt_text("Nhập GEMINI_API_KEY (Google AI Studio / Vertex Pro, nhấn Enter nếu bỏ qua)", secret=True)
    gemini_model = (
        prompt_text("Mã model Google Gemini Pro sử dụng", default="gemini-2.5-pro")
        if gemini_key
        else ""
    )
    default_ai_mode = "advisory"
    ai_mode = prompt_text(
        "Chế độ lọc AI ('advisory' = Cố vấn & chặn khi AI báo tránh, 'required' = Bắt buộc đủ phiếu AI, 'off' = Tắt)",
        default=default_ai_mode,
    ).lower()
    if ai_mode not in ("off", "advisory", "required"):
        ai_mode = "advisory"

    print("\n--- 3. KẾT NỐI TÀI KHOẢN SÀN BINANCE (SPOT USDT) ---")
    binance_key = prompt_text("Nhập Binance API Key (nhấn Enter nếu chưa dùng Binance)", secret=False)
    binance_secret = (
        prompt_text("Nhập Binance Secret Key", secret=True) if binance_key else ""
    )

    print("\n--- 4. KẾT NỐI TÀI KHOẢN SÀN OKX (SPOT USDT) ---")
    okx_key = prompt_text("Nhập OKX API Key (nhấn Enter nếu chưa dùng OKX)", secret=False)
    okx_secret = prompt_text("Nhập OKX Secret Key", secret=True) if okx_key else ""
    okx_passphrase = (
        prompt_text("Nhập OKX API Passphrase (Mật khẩu tạo API trên OKX)", secret=True)
        if okx_key
        else ""
    )

    jwt_secret = secrets.token_hex(32)
    ws_token = secrets.token_urlsafe(24)

    binance_cfg = build_private_config(
        exchange_name="binance",
        api_key=binance_key,
        api_secret=binance_secret,
        api_passphrase="",
        dry_run=dry_run,
        admin_user=admin_user,
        admin_password=admin_password,
        jwt_secret=jwt_secret,
        ws_token=ws_token,
        ai_mode=ai_mode,
        openai_model=openai_model,
        gemini_model=gemini_model,
    )
    okx_cfg = build_private_config(
        exchange_name="okx",
        api_key=okx_key,
        api_secret=okx_secret,
        api_passphrase=okx_passphrase,
        dry_run=dry_run,
        admin_user=admin_user,
        admin_password=admin_password,
        jwt_secret=jwt_secret,
        ws_token=ws_token,
        ai_mode=ai_mode,
        openai_model=openai_model,
        gemini_model=gemini_model,
    )

    binance_path = USER_DATA_DIR / "config.private.binance.json"
    okx_path = USER_DATA_DIR / "config.private.okx.json"
    env_path = BOT_DIR / ".env"

    write_secure_json(binance_path, binance_cfg)
    write_secure_json(okx_path, okx_cfg)
    write_env_file(env_path, openai_key, gemini_key, tailscale_ip, dry_run)

    print("\n" + "=" * 76)
    print("✅ ĐÃ KHỞI TẠO THÀNH CÔNG CẤU HÌNH BẢO MẬT CHO FREQBOT VN REMOTE!")
    print("=" * 76)
    print(f"• Chế độ vận hành       : {'🟢 GIAO DỊCH THỬ (DRY-RUN)' if dry_run else '🔴 TIỀN THẬT (LIVE USDT)'}")
    print(f"• Tệp cấu hình Binance  : {binance_path}")
    print(f"• Tệp cấu hình OKX      : {okx_path}")
    print(f"• Tệp biến môi trường   : {env_path}")
    print(f"• Tài khoản điều khiển  : {admin_user}")
    if generated_pwd:
        print(f"• Mật khẩu tự sinh      : {admin_password}  <-- Hãy lưu lại để nhập vào App Android / Web!")
    print("\nCách khởi chạy 24/7 bằng Docker Compose:")
    print("  - Chạy sàn Binance (Cổng 8080): docker compose up -d")
    print("  - Chạy cả Binance (8080) & OKX (8081): docker compose --profile okx up -d")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Thiết lập tài khoản Binance, OKX và AI Pro cho FreqBot VN Remote.")
    parser.add_argument("--init-defaults", action="store_true", help="Tạo nhanh các tệp cấu hình mặc định (Dry-Run) không cần hỏi")
    args = parser.parse_args()

    if args.init_defaults:
        jwt_secret = secrets.token_hex(32)
        ws_token = secrets.token_urlsafe(24)
        for ex_name in ("binance", "okx"):
            out_path = USER_DATA_DIR / f"config.private.{ex_name}.json"
            if not out_path.exists():
                cfg = build_private_config(
                    exchange_name=ex_name,
                    api_key="",
                    api_secret="",
                    api_passphrase="",
                    dry_run=True,
                    admin_user="admin",
                    admin_password="mat_khau_manh_cua_ban",
                    jwt_secret=jwt_secret,
                    ws_token=ws_token,
                    ai_mode="advisory",
                    openai_model="gpt-4.1",
                    gemini_model="gemini-2.5-pro",
                )
                write_secure_json(out_path, cfg)
        env_path = BOT_DIR / ".env"
        if not env_path.exists():
            write_env_file(env_path, "", "", "127.0.0.1", dry_run=True)
        print("Đã tạo sẵn config.private.binance.json, config.private.okx.json và .env ở chế độ Dry-Run an toàn.")
        return 0

    return run_interactive()


if __name__ == "__main__":
    sys.exit(main())
