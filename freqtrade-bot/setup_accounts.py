#!/usr/bin/env python3
"""
Trình cài đặt & kết nối tài khoản tự động bằng Tiếng Việt (FreqBot VN Remote)
Đã tối ưu riêng cho hồ sơ vốn của LO:
1. Vốn thử nghiệm 34.16 USDT/sàn (hoặc mở rộng lên toàn bộ vốn 423.77 USDT Binance / 521 USDT OKX chỉ bằng 1 tham số).
2. Săn lệnh 24/24 bất cứ khi nào Kỹ thuật + AI Pro đồng thuận, đồng thời ƯU TIÊN tối đa (100% hạn mức lệnh) cho khung giờ vàng 03:00 - 04:00 sáng giờ Việt Nam (ngoài giờ ưu tiên giải ngân 75% hạn mức lệnh để bảo vệ vốn).
3. Kết nối API thật của Binance & OKX + ChatGPT Pro (gpt-4.1) & Gemini Pro (gemini-2.5-pro) ở chế độ Lựa chọn A ("dry_run": true) trong 3 ngày đầu.
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
    wallet_usdt: float = 34.16,
    hunt_24_7_with_priority_03_04: bool = True,
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

    # Tối ưu thông số chia vốn theo quy mô tài khoản (mặc định 34.16 USDT hoặc khi nâng lên 423.77 / 521 USDT)
    wallet_usdt = max(15.0, float(wallet_usdt))
    if wallet_usdt <= 60.0:
        # Với vốn 34.16 USDT: Mở tối đa 2 lệnh cùng lúc, mỗi lệnh chuẩn ~15 USDT (trên mức minNotional 5-10 USDT của Binance/OKX)
        max_open_trades = 2
        stake_amount = round(wallet_usdt * 0.45, 2)  # ~15.37 USDT trong khung giờ ưu tiên 03:00-04:00, ~11.53 USDT ngoài giờ
        risk_cfg = {
            "risk_per_trade": 0.016,          # Cho phép mức rủi ro cắt lỗ ~0.54 USDT/lệnh để đủ minNotional trên vốn 34.16 USDT
            "max_position_fraction": 0.45,    # Tối đa 45% vốn (~15.37 USDT) cho 1 vị thế
            "max_exposure_fraction": 0.90,    # Tối đa 90% vốn cho 2 vị thế mở cùng lúc
            "cost_buffer": 0.004,
            "max_entry_deviation": 0.005,
            "off_peak_stake_multiplier": 0.75 if hunt_24_7_with_priority_03_04 else 1.0,
        }
    else:
        # Khi LO nâng lên toàn bộ vốn (423.77 USDT trên Binance hoặc 521 USDT trên OKX)
        max_open_trades = 3
        stake_amount = round(wallet_usdt * 0.20, 2)
        risk_cfg = {
            "risk_per_trade": 0.005,
            "max_position_fraction": 0.20,
            "max_exposure_fraction": 0.60,
            "cost_buffer": 0.004,
            "max_entry_deviation": 0.005,
            "off_peak_stake_multiplier": 0.75 if hunt_24_7_with_priority_03_04 else 1.0,
        }

    # Chế độ săn lệnh 24/24 nhưng ưu tiên khung giờ 03:00 - 04:00 sáng giờ Việt Nam
    schedule_cfg = {
        "enabled": not hunt_24_7_with_priority_03_04,
        "windows": [
            {
                "start": "03:00",
                "end": "04:00",
                "weekdays": [0, 1, 2, 3, 4, 5, 6],
            }
        ],
    }

    research_cfg = {
        "mode": ai_mode,
        "providers": providers,
        "min_ai_votes": min_votes,
        "min_ai_confidence": 0.70,
        "report_file": "latest-okx.json" if exchange_name == "okx" else "latest.json",
    }

    return {
        "max_open_trades": max_open_trades,
        "stake_amount": stake_amount,
        "dry_run": bool(dry_run),
        "dry_run_wallet": round(wallet_usdt, 2),
        "available_capital": round(wallet_usdt, 2),
        "exchange": exchange_cfg,
        "api_server": {
            "jwt_secret_key": jwt_secret,
            "ws_token": ws_token,
            "username": admin_user.strip() or "admin",
            "password": admin_password,
        },
        "vn_policy": {
            "schedule": schedule_cfg,
            "risk": risk_cfg,
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
    print("=" * 78)
    print("🤖 TRÌNH CÀI ĐẶT TÀI KHOẢN BINANCE / OKX & AI PRO (FREQBOT VN REMOTE)")
    print("=" * 78)
    print("Hồ sơ mặc định đã được căn chỉnh sẵn cho bạn:")
    print("  • Vốn phân bổ mỗi sàn : 34.16 USDT (Chỉ dùng 34.16 USDT ngay cả khi ví OKX có 521 USDT)")
    print("  • Lịch săn lệnh       : Mở mua 24/24 khi Kỹ thuật + AI Pro đồng thuận,")
    print("                          ƯU TIÊN 100% hạn mức (~15.37 USDT/lệnh) vào khung 03:00-04:00 VN,")
    print("                          ngoài khung giờ vàng vào lệnh thận trọng (~11.53 USDT/lệnh).")
    print("  • Bảo vệ Coin sẵn có  : Không bao giờ đụng vào TRX, SOL, ADA, BTC, Pi đang có sẵn của bạn!\n")

    mode_choice = prompt_text(
        "Chọn chế độ ('dry' = Lựa chọn A: Kết nối API thật + AI thật nhưng dùng ví thử 34.16 USDT, 'live' = Tiền thật)",
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

    binance_capital_str = prompt_text("Hạn mức vốn USDT cấp cho Bot trên sàn BINANCE", default="34.16")
    okx_capital_str = prompt_text("Hạn mức vốn USDT cấp cho Bot trên sàn OKX", default="34.16")
    try:
        binance_capital = float(binance_capital_str.replace(",", "."))
    except ValueError:
        binance_capital = 34.16
    try:
        okx_capital = float(okx_capital_str.replace(",", "."))
    except ValueError:
        okx_capital = 34.16

    print("\n--- 1. CẤU HÌNH TÀI KHOẢN ĐIỀU KHIỂN TỪ XA (APP ANDROID & WEB DASHBOARD) ---")
    admin_user = prompt_text("Tên đăng nhập điều khiển Bot", default="admin")
    admin_password = prompt_text(
        "Mật khẩu điều khiển Bot (nhấn Enter để giữ 'mat_khau_manh_cua_ban')",
        default="mat_khau_manh_cua_ban",
        secret=True,
    )
    tailscale_ip = prompt_text(
        "Địa chỉ IP Tailscale của VPS Oracle Cloud (để 127.0.0.1 nếu đang chạy trên máy Windows này)",
        default="127.0.0.1",
    )

    print("\n--- 2. KẾT NỐI TRÍ TUỆ NHÂN TẠO BẢN PRO (CHATGPT PRO & GEMINI PRO) ---")
    openai_key = prompt_text("Nhập OPENAI_API_KEY (Platform OpenAI, nhấn Enter nếu bỏ qua)", secret=True)
    openai_model = (
        prompt_text("Mã model OpenAI Pro sử dụng", default="gpt-4.1")
        if openai_key
        else "gpt-4.1"
    )
    gemini_key = prompt_text("Nhập GEMINI_API_KEY (Google AI Studio Pro, nhấn Enter nếu bỏ qua)", secret=True)
    gemini_model = (
        prompt_text("Mã model Google Gemini Pro sử dụng", default="gemini-2.5-pro")
        if gemini_key
        else "gemini-2.5-pro"
    )
    ai_mode = prompt_text(
        "Chế độ lọc AI ('advisory' = Cố vấn & chặn khi AI báo tránh, 'required' = Bắt buộc đủ phiếu AI, 'off' = Tắt)",
        default="advisory",
    ).lower()
    if ai_mode not in ("off", "advisory", "required"):
        ai_mode = "advisory"

    print("\n--- 3. KẾT NỐI TÀI KHOẢN SÀN BINANCE (SPOT USDT) ---")
    binance_key = prompt_text("Nhập Binance API Key (nhấn Enter nếu chưa nhập ngay)", secret=False)
    binance_secret = (
        prompt_text("Nhập Binance Secret Key", secret=True) if binance_key else ""
    )

    print("\n--- 4. KẾT NỐI TÀI KHOẢN SÀN OKX (SPOT USDT) ---")
    okx_key = prompt_text("Nhập OKX API Key (nhấn Enter nếu chưa nhập ngay)", secret=False)
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
        wallet_usdt=binance_capital,
        hunt_24_7_with_priority_03_04=True,
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
        wallet_usdt=okx_capital,
        hunt_24_7_with_priority_03_04=True,
    )

    binance_path = USER_DATA_DIR / "config.private.binance.json"
    okx_path = USER_DATA_DIR / "config.private.okx.json"
    env_path = BOT_DIR / ".env"

    write_secure_json(binance_path, binance_cfg)
    write_secure_json(okx_path, okx_cfg)
    write_env_file(env_path, openai_key, gemini_key, tailscale_ip, dry_run)

    print("\n" + "=" * 78)
    print("✅ ĐÃ CÀI ĐẶT XONG CẤU HÌNH CHO BINANCE (34.16 USDT) & OKX (34.16 USDT)!")
    print("=" * 78)
    print(f"• Chế độ vận hành       : {'🟢 GIAO DỊCH THỬ (DRY-RUN - LỰA CHỌN A)' if dry_run else '🔴 TIỀN THẬT (LIVE USDT)'}")
    print(f"• Hạn mức vốn Binance   : {binance_capital:.2f} USDT (Tối đa {binance_cfg['max_open_trades']} lệnh mở)")
    print(f"• Hạn mức vốn OKX       : {okx_capital:.2f} USDT (Tối đa {okx_cfg['max_open_trades']} lệnh mở, khóa bảo vệ phần dư trong 521 USDT)")
    print("• Chế độ săn lệnh       : Săn 24/24 (Ưu tiên 100% vốn lúc 03:00-04:00 VN, 75% vốn ngoài giờ)")
    print(f"• Tệp cấu hình Binance  : {binance_path}")
    print(f"• Tệp cấu hình OKX      : {okx_path}")
    print(f"• Tệp biến môi trường   : {env_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Thiết lập tài khoản Binance, OKX và AI Pro cho FreqBot VN Remote.")
    parser.add_argument("--init-defaults", action="store_true", help="Tạo nhanh các tệp cấu hình mặc định (34.16 USDT, Dry-Run, Săn 24/7 ưu tiên 03-04h)")
    parser.add_argument("--binance-usdt", type=float, default=34.16, help="Vốn USDT cấp cho Bot trên Binance (mặc định 34.16)")
    parser.add_argument("--okx-usdt", type=float, default=34.16, help="Vốn USDT cấp cho Bot trên OKX (mặc định 34.16)")
    args = parser.parse_args()

    if args.init_defaults:
        jwt_secret = secrets.token_hex(32)
        ws_token = secrets.token_urlsafe(24)
        for ex_name, cap in (("binance", args.binance_usdt), ("okx", args.okx_usdt)):
            out_path = USER_DATA_DIR / f"config.private.{ex_name}.json"
            if out_path.exists():
                print(f"Giữ nguyên cấu hình đã có: {out_path.name}")
                continue
            cfg = build_private_config(
                exchange_name=ex_name,
                api_key="",
                api_secret="",
                api_passphrase="",
                dry_run=True,
                admin_user="admin",
                admin_password=secrets.token_urlsafe(24),
                jwt_secret=jwt_secret,
                ws_token=ws_token,
                ai_mode="advisory",
                openai_model="gpt-4.1",
                gemini_model="gemini-2.5-pro",
                wallet_usdt=cap,
                hunt_24_7_with_priority_03_04=True,
            )
            write_secure_json(out_path, cfg)
        env_path = BOT_DIR / ".env"
        if not env_path.exists():
            write_env_file(env_path, "", "", "127.0.0.1", dry_run=True)
        print(
            "Đã tạo các tệp mặc định còn thiếu; giữ nguyên các tệp đã có. "
            "Tệp mới dùng Dry-Run và mật khẩu ngẫu nhiên; cấu hình tài khoản trước khi truy cập từ xa."
        )
        return 0

    return run_interactive()


if __name__ == "__main__":
    sys.exit(main())
