#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Máy chủ giả lập Freqtrade REST API (Mock API Server)
Thuộc Dự án: Hệ thống Giao dịch Tự động & Ứng dụng Điều khiển Từ xa Tiếng Việt (FreqBot VN Remote)

Mục đích:
- Mô phỏng chính xác 100% các Endpoint của Freqtrade (/api/v1/token/login, /profit, /balance, /status, /locks, /stopbuy, /reload_config, /forceexit, /show_config, /ping).
- Tự động biến động giá nhẹ theo thời gian thực để kiểm thử giao diện Android (FreqBot VN Remote) và Web Dashboard Tiếng Việt ngay lập tức mà không cần đợi Docker hay sàn giao dịch.
"""

import base64
import json
import os
import random
import secrets
import sys
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HOST = "0.0.0.0"
PORT = 8080

# Tài khoản mặc định khớp với config.json
VALID_USERNAME = "admin"
VALID_PASSWORD = "mat_khau_manh_cua_ban"

# Trạng thái giả lập trong bộ nhớ
BOT_STATE = {
    "state": "running",          # "running" hoặc "stopped"
    "stopbuy_active": False,     # True khi bấm "Tạm dừng Mua mới"
    "closed_profit_usdt": 68.45,
    "closed_trades": 22,
    "winning_trades": 17,
    "losing_trades": 5,
    "max_drawdown": 0.0185,      # 1.85%
    "initial_wallet": 1000.0,
    "active_tokens": set(),
    "locks": [],
    "open_trades": [
        {
            "trade_id": 101,
            "pair": "BTC/USDT",
            "is_open": True,
            "stake_amount": 250.0,
            "amount": 0.003676,
            "open_rate": 68000.0,
            "current_rate": 69420.0,
            "stop_loss_abs": 65960.0,
            "open_date": (datetime.now() - timedelta(hours=3, minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "enter_tag": "XU_HUONG_TANG_EMA_RSI"
        },
        {
            "trade_id": 102,
            "pair": "SOL/USDT",
            "is_open": True,
            "stake_amount": 200.0,
            "amount": 1.142857,
            "open_rate": 175.0,
            "current_rate": 179.55,
            "stop_loss_abs": 169.75,
            "open_date": (datetime.now() - timedelta(hours=1, minutes=40)).strftime("%Y-%m-%d %H:%M:%S"),
            "enter_tag": "XU_HUONG_TANG_EMA_RSI"
        },
        {
            "trade_id": 103,
            "pair": "ETH/USDT",
            "is_open": True,
            "stake_amount": 200.0,
            "amount": 0.078431,
            "open_rate": 2550.0,
            "current_rate": 2528.30,
            "stop_loss_abs": 2473.50,
            "open_date": (datetime.now() - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
            "enter_tag": "BAT_NHIP_HOI_BOLLINGER_RSI"
        }
    ]
}


def update_live_prices():
    """Mô phỏng dao động giá nhẹ thời gian thực cho các lệnh đang mở"""
    for trade in BOT_STATE["open_trades"]:
        delta_pct = random.uniform(-0.0025, 0.0030)
        new_rate = max(trade["open_rate"] * 0.90, trade["current_rate"] * (1.0 + delta_pct))
        trade["current_rate"] = round(new_rate, 4)
        profit_ratio = (trade["current_rate"] - trade["open_rate"]) / trade["open_rate"]
        trade["profit_ratio"] = round(profit_ratio, 4)
        trade["profit_pct"] = round(profit_ratio * 100, 2)
        trade["profit_abs"] = round(trade["stake_amount"] * profit_ratio, 2)
        dist_ratio = (trade["stop_loss_abs"] - trade["current_rate"]) / trade["current_rate"]
        trade["stoploss_current_dist_ratio"] = round(dist_ratio, 4)


class FreqtradeMockHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _check_bearer_auth(self) -> bool:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
            if token in BOT_STATE["active_tokens"] or len(token) > 8:
                return True
        self._send_json({"detail": "Chưa xác thực hoặc JWT Token không hợp lệ"}, status_code=401)
        return False

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/v1/ping":
            return self._send_json({"status": "pong"})

        # Phục vụ trực tiếp Web Dashboard Tiếng Việt nếu truy cập "/" hoặc "/dashboard"
        if path in ("/", "/dashboard", "/index.html", "/styles.css", "/app.js"):
            web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web-dashboard"))
            filename = "index.html" if path in ("/", "/dashboard") else path.lstrip("/")
            filepath = os.path.join(web_dir, filename)
            if os.path.isfile(filepath):
                content_type = "text/html; charset=utf-8"
                if filename.endswith(".css"):
                    content_type = "text/css; charset=utf-8"
                elif filename.endswith(".js"):
                    content_type = "application/javascript; charset=utf-8"
                with open(filepath, "rb") as f:
                    raw = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(raw)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(raw)
                return

        if not self._check_bearer_auth():
            return

        update_live_prices()

        if path == "/api/v1/status":
            return self._send_json(BOT_STATE["open_trades"])

        elif path == "/api/v1/profit":
            open_profit = sum(t.get("profit_abs", 0.0) for t in BOT_STATE["open_trades"])
            total_profit = round(BOT_STATE["closed_profit_usdt"] + open_profit, 2)
            total_pct = round((total_profit / BOT_STATE["initial_wallet"]) * 100, 2)
            return self._send_json({
                "profit_closed_coin": BOT_STATE["closed_profit_usdt"],
                "profit_closed_percent": round((BOT_STATE["closed_profit_usdt"] / BOT_STATE["initial_wallet"]) * 100, 2),
                "profit_all_coin": total_profit,
                "profit_all_percent": total_pct,
                "trade_count": BOT_STATE["closed_trades"] + len(BOT_STATE["open_trades"]),
                "closed_trade_count": BOT_STATE["closed_trades"],
                "winning_trades": BOT_STATE["winning_trades"],
                "losing_trades": BOT_STATE["losing_trades"],
                "max_drawdown": BOT_STATE["max_drawdown"],
                "max_drawdown_abs": round(BOT_STATE["initial_wallet"] * BOT_STATE["max_drawdown"], 2)
            })

        elif path == "/api/v1/balance":
            used_usdt = round(sum(t["stake_amount"] for t in BOT_STATE["open_trades"]), 2)
            total_wallet = round(BOT_STATE["initial_wallet"] + BOT_STATE["closed_profit_usdt"], 2)
            free_usdt = round(max(0.0, total_wallet - used_usdt), 2)
            return self._send_json({
                "currencies": [
                    {
                        "currency": "USDT",
                        "free": free_usdt,
                        "used": used_usdt,
                        "balance": total_wallet,
                        "est_stake": total_wallet,
                        "stake": "USDT"
                    }
                ],
                "total": total_wallet,
                "free": free_usdt,
                "used": used_usdt,
                "symbol": "USDT",
                "value": total_wallet
            })

        elif path == "/api/v1/locks":
            return self._send_json({
                "lock_count": len(BOT_STATE["locks"]),
                "locks": BOT_STATE["locks"]
            })

        elif path == "/api/v1/show_config":
            return self._send_json({
                "bot_name": "FreqBot_VN_Remote",
                "state": BOT_STATE["state"],
                "dry_run": True,
                "strategy": "VnSmartTrendStrategy",
                "timeframe": "5m",
                "stake_currency": "USDT",
                "max_open_trades": 0 if BOT_STATE["stopbuy_active"] else 4,
                "stopbuy_active": BOT_STATE["stopbuy_active"]
            })

        self._send_json({"detail": f"Không tìm thấy đường dẫn {path}"}, status_code=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Xử lý đăng nhập Basic Auth (/api/v1/token/login)
        if path == "/api/v1/token/login":
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Basic "):
                try:
                    decoded = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
                    username, password = decoded.split(":", 1)
                    if username == VALID_USERNAME and password == VALID_PASSWORD:
                        token = f"vn_jwt_{secrets.token_urlsafe(24)}"
                        BOT_STATE["active_tokens"].add(token)
                        return self._send_json({
                            "access_token": token,
                            "refresh_token": f"vn_refresh_{secrets.token_urlsafe(24)}"
                        })
                except Exception:
                    pass
            return self._send_json({"detail": "Sai tài khoản hoặc mật khẩu điều khiển Bot!"}, status_code=401)

        if not self._check_bearer_auth():
            return

        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except Exception:
            payload = {}

        # 2. Tạm dừng mua mới (/api/v1/stopbuy)
        if path == "/api/v1/stopbuy":
            BOT_STATE["stopbuy_active"] = True
            return self._send_json({
                "status": "Đã bật chế độ NGỪNG MUA MỚI (max_open_trades = 0). Chỉ canh chốt lời/cắt lỗ các lệnh đang giữ."
            })

        # 3. Khởi động lại cấu hình mua bán (/api/v1/reload_config hoặc /api/v1/start)
        elif path in ("/api/v1/reload_config", "/api/v1/start"):
            BOT_STATE["stopbuy_active"] = False
            BOT_STATE["state"] = "running"
            BOT_STATE["locks"] = []
            # Khôi phục lệnh mẫu nếu đã bán hết trước đó để dễ thử nghiệm lại
            if not BOT_STATE["open_trades"]:
                BOT_STATE["open_trades"] = [
                    {
                        "trade_id": int(time.time()) % 10000,
                        "pair": "BTC/USDT",
                        "is_open": True,
                        "stake_amount": 250.0,
                        "amount": 0.003676,
                        "open_rate": 68000.0,
                        "current_rate": 69150.0,
                        "stop_loss_abs": 65960.0,
                        "open_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "enter_tag": "XU_HUONG_TANG_EMA_RSI"
                    },
                    {
                        "trade_id": (int(time.time()) % 10000) + 1,
                        "pair": "SOL/USDT",
                        "is_open": True,
                        "stake_amount": 200.0,
                        "amount": 1.142857,
                        "open_rate": 175.0,
                        "current_rate": 178.40,
                        "stop_loss_abs": 169.75,
                        "open_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "enter_tag": "XU_HUONG_TANG_EMA_RSI"
                    }
                ]
            return self._send_json({
                "status": "Đã nạp lại cấu hình và bật chế độ giao dịch bình thường!"
            })

        # 4. Bán khẩn cấp - Panic Sell (/api/v1/forceexit)
        elif path == "/api/v1/forceexit":
            trade_id = str(payload.get("tradeid", "all"))
            update_live_prices()
            if trade_id.lower() == "all":
                closed_count = len(BOT_STATE["open_trades"])
                for t in BOT_STATE["open_trades"]:
                    pnl = t.get("profit_abs", 0.0)
                    BOT_STATE["closed_profit_usdt"] = round(BOT_STATE["closed_profit_usdt"] + pnl, 2)
                    BOT_STATE["closed_trades"] += 1
                    if pnl >= 0:
                        BOT_STATE["winning_trades"] += 1
                    else:
                        BOT_STATE["losing_trades"] += 1
                BOT_STATE["open_trades"] = []
                return self._send_json({
                    "status": f"Đã thực thi BÁN KHẨN CẤP toàn bộ {closed_count} lệnh theo giá thị trường và thu hồi về USDT!"
                })
            else:
                remaining = []
                closed_pair = None
                for t in BOT_STATE["open_trades"]:
                    if str(t["trade_id"]) == trade_id:
                        closed_pair = t["pair"]
                        pnl = t.get("profit_abs", 0.0)
                        BOT_STATE["closed_profit_usdt"] = round(BOT_STATE["closed_profit_usdt"] + pnl, 2)
                        BOT_STATE["closed_trades"] += 1
                        if pnl >= 0:
                            BOT_STATE["winning_trades"] += 1
                        else:
                            BOT_STATE["losing_trades"] += 1
                    else:
                        remaining.append(t)
                BOT_STATE["open_trades"] = remaining
                return self._send_json({
                    "status": f"Đã đóng lệnh #{trade_id} ({closed_pair or 'N/A'}) theo giá thị trường!"
                })

        # 5. Endpoint hỗ trợ giả lập kích hoạt Giáp bảo vệ rủi ro (để test giao diện cảnh báo)
        elif path == "/api/v1/mock/toggle_lock":
            if BOT_STATE["locks"]:
                BOT_STATE["locks"] = []
                return self._send_json({"status": "Đã tắt khóa giả lập, trạng thái an toàn."})
            else:
                BOT_STATE["locks"] = [
                    {
                        "id": 1,
                        "pair": "*",
                        "reason": "MaxDrawdown",
                        "lock_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "lock_end_time": (datetime.now() + timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S"),
                        "active": True
                    }
                ]
                return self._send_json({"status": "Đã kích hoạt thử nghiệm Giáp bảo vệ MaxDrawdown!"})

        self._send_json({"detail": f"Không hỗ trợ POST {path}"}, status_code=404)


if __name__ == "__main__":
    update_live_prices()
    server = HTTPServer((HOST, PORT), FreqtradeMockHandler)
    print("=" * 72)
    print(f"🚀 MÁY CHỦ GIẢ LẬP FREQTRADE API ĐANG CHẠY TẠI: http://127.0.0.1:{PORT}")
    print(f"🌐 Giao diện Web Dashboard Tiếng Việt:         http://127.0.0.1:{PORT}/dashboard")
    print(f"📱 Địa chỉ cho Android Emulator:               http://10.0.2.2:{PORT}/")
    print(f"🔑 Tài khoản: {VALID_USERNAME} | Mật khẩu: {VALID_PASSWORD}")
    print("=" * 72)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng máy chủ giả lập Freqtrade API.")
