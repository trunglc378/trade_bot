"""Read-only market research worker. Never creates exchange orders."""
import argparse
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "strategies"))
from vn_support import VN, aware, context_id, in_session, number, spread_ratio
from providers import advise

log = logging.getLogger("research")


def ema(values, period):
    result = values[0]
    for value in values[1:]:
        result += 2 / (period + 1) * (value - result)
    return result


def rsi(values, period=14):
    if len(values) <= period:
        return 50.0
    gains, losses = [], []
    for a, b in zip(values[:-1], values[1:]):
        diff = b - a
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
    if avg_loss == 0:
        return 100.0 if avg_gain else 50.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def analyze(pair, candles, ticker, book, now, settings):
    now_ms = aware(now).timestamp() * 1000
    # OHLCV timestamps are candle OPEN times. Discard the unfinished candle.
    closed = [row for row in candles if number(row[0]) + 300_000 <= now_ms]
    if len(closed) < 200:
        raise ValueError("Insufficient closed candles")
    if any(number(b[0]) - number(a[0]) != 300_000 for a, b in zip(closed, closed[1:])):
        raise ValueError("Duplicate/out-of-order/missing candle")
    age = (now_ms - number(closed[-1][0]) - 300_000) / 1000
    if not 0 <= age <= 600:
        raise ValueError("Stale candles")
    prices = [number(row[4]) for row in closed]
    volumes = [number(row[5]) for row in closed]
    if min(prices) <= 0 or min(volumes) < 0:
        raise ValueError("Invalid OHLCV")
    spread = spread_ratio(book["bids"][0][0], book["asks"][0][0])
    quote_volume = number(ticker["quoteVolume"])
    if quote_volume < 0:
        raise ValueError("Invalid volume")
    change = prices[-1] / prices[-13] - 1
    returns = [math.log(b / a) for a, b in zip(prices[-25:], prices[-24:])]
    avg = sum(returns) / len(returns)
    volatility = math.sqrt(sum((r - avg) ** 2 for r in returns) / len(returns))
    ema20_val = ema(prices, 20)
    ema50_val = ema(prices, 50)
    ema200_val = ema(prices, 200)
    rsi_val = rsi(prices, 14)
    trend = prices[-1] > ema200_val and ema20_val > ema50_val
    volume_ratio = volumes[-1] / (sum(volumes[-21:-1]) / 20) if sum(volumes[-21:-1]) else 0
    reasons = []
    if not trend:
        reasons.append("Xu hướng chưa tăng")
    if quote_volume < settings["min_quote_volume"]:
        reasons.append("Thanh khoản 24h thấp")
    if spread > settings["max_spread"]:
        reasons.append("Spread quá rộng")
    if volatility > settings["max_volatility"] or abs(change) > settings["max_hour_change"]:
        reasons.append("Biến động bất thường")
    if quote_volume < settings["min_quote_volume"] or spread > settings["max_spread"]:
        regime = "THANH_KHOẢN_THẤP"
    elif volatility > settings["max_volatility"] or abs(change) > settings["max_hour_change"]:
        regime = "BIẾN_ĐỘNG_CAO"
    elif trend and 45 <= rsi_val <= 68 and volume_ratio >= 1.15:
        regime = "TĂNG_MẠNH"
    elif trend:
        regime = "TĂNG_ỔN_ĐỊNH"
    else:
        regime = "XU_HƯỚNG_YẾU"
    score = round(max(0, min(100, 50 + (20 if trend else -20) + min(volume_ratio, 3) * 5
                                 + max(-10, min(10, change * 100)) - spread * 10000)), 2)
    return {"pair": pair, "close": prices[-1], "candle_closed_at": datetime.fromtimestamp(
                (number(closed[-1][0]) + 300_000) / 1000, timezone.utc).isoformat(),
            "quote_volume_24h": quote_volume, "spread": spread, "hour_change": change,
            "volatility_5m": volatility, "volume_ratio": volume_ratio,
            "rsi_14": rsi_val, "ema20": round(ema20_val, 6), "ema50": round(ema50_val, 6),
            "ema200": round(ema200_val, 6), "regime": regime, "score": score,
            "technical_eligible": not reasons, "reasons": reasons, "eligible": False, "ai_votes": {}}


def build_report(config, exchange, now=None, advisor=advise):
    now = now or datetime.now(timezone.utc)
    settings = config["vn_policy"]["research"]
    for key in ("min_quote_volume", "max_spread", "max_volatility", "max_hour_change"):
        if number(settings[key]) <= 0:
            raise ValueError("Invalid market threshold")
    if settings["mode"] not in ("off", "advisory", "required"):
        raise ValueError("Invalid research mode")
    if not 30 <= settings["ttl_seconds"] <= 3600:
        raise ValueError("Invalid report TTL")
    providers = settings["providers"]
    if any(p not in ("openai", "gemini") for p in providers):
        raise ValueError("Unsupported provider")
    quorum = settings["min_ai_votes"]
    if type(quorum) is not int or quorum < 1:
        raise ValueError("Invalid AI quorum")
    if not 0 <= number(settings["min_ai_confidence"]) <= 1:
        raise ValueError("Invalid confidence threshold")
    if settings["mode"] == "required" and quorum > len(providers):
        raise ValueError("AI quorum exceeds configured providers")
    markets = exchange.load_markets()
    candidates, errors = [], []
    for pair in config["exchange"]["pair_whitelist"]:
        if any(re.fullmatch(pattern, pair) for pattern in config["exchange"].get("pair_blacklist", [])):
            continue
        market = markets.get(pair, {})
        if market.get("spot") is not True or market.get("active") is not True or market.get("quote") != "USDT":
            errors.append({"pair": pair, "error": "inactive_or_non_spot_usdt"})
            continue
        try:
            candles = exchange.fetch_ohlcv(pair, "5m", limit=260)
            ticker = exchange.fetch_ticker(pair)
            book = exchange.fetch_order_book(pair, limit=5)
            candidates.append(analyze(pair, candles, ticker, book, now, settings))
        except Exception as exc:
            errors.append({"pair": pair, "error": type(exc).__name__})
    eligible = [r for r in candidates if r["technical_eligible"]]
    if eligible and settings["mode"] != "off":
        for provider, model in providers.items():
            try:
                votes = advisor(provider, model, eligible)
                for row in eligible:
                    if row["pair"] in votes:
                        row["ai_votes"][provider] = votes[row["pair"]]
            except Exception as exc:
                # Never log exception messages: upstream errors may contain credentials.
                errors.append({"provider": provider, "error": type(exc).__name__})
    for row in candidates:
        votes = list(row["ai_votes"].values())
        agreement = sum(v["action"] == "consider" and v["confidence"] >= settings["min_ai_confidence"] for v in votes)
        veto = any(v["action"] == "avoid" for v in votes)
        row["eligible"] = row["technical_eligible"] and (
            settings["mode"] != "required" or (agreement >= quorum and not veto))
        if row["technical_eligible"] and settings["mode"] == "required":
            if veto:
                row["reasons"].append("Có AI đề xuất tránh giao dịch")
            if agreement < quorum:
                row["reasons"].append("Chưa đủ phiếu AI đạt ngưỡng đồng thuận")
    schedule = config["vn_policy"].get("schedule", {"enabled": False, "windows": []})
    session_open = in_session(now, schedule)
    return {"schema_version": 1, "context_id": context_id(config), "exchange": exchange.id,
            "generated_at": now.isoformat(), "expires_at": (now + timedelta(seconds=settings["ttl_seconds"])).isoformat(),
            "vn_time": aware(now).astimezone(VN).strftime("%Y-%m-%d %H:%M:%S GMT+7"),
            "in_trading_session": session_open, "schedule_enabled": schedule.get("enabled", False),
            "schedule_windows": schedule.get("windows", []),
            "mode": settings["mode"], "candidates": sorted(candidates, key=lambda r: r["score"], reverse=True),
            "errors": errors}


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
            name = f.name
            json.dump(data, f, ensure_ascii=False, allow_nan=False, indent=2)
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, action="append", help="Later JSON files override earlier configs")
    parser.add_argument("--loop", type=int, default=0, help="Refresh seconds, >=60; 0 = once")
    args = parser.parse_args()
    configs = args.config or [Path(__file__).resolve().parents[1] / "config.json"]
    if args.loop and args.loop < 60:
        parser.error("--loop must be >= 60")
    import ccxt
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            config = {}
            for path in configs:
                merge(config, json.loads(path.read_text(encoding="utf-8-sig")))
            name = config["exchange"]["name"]
            if name not in ("binance", "okx"):
                raise ValueError("Only Binance / OKX spot research supported")
            # Intentionally do not pass private exchange keys or arbitrary CCXT config.
            exchange = getattr(ccxt, name)({"enableRateLimit": True, "timeout": 15000,
                                           "options": {"defaultType": "spot"}})
            report = build_report(config, exchange)
            atomic_write(configs[0].parent / "research" / "latest.json", report)
            atomic_write(configs[0].parent / "research" / "history" /
                         (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json"), report)
            log.info("Snapshot saved: %s candidates, %s errors", len(report["candidates"]), len(report["errors"]))
        except Exception as exc:
            log.error("Research failed: %s", type(exc).__name__)
            if not args.loop:
                return 1
        if not args.loop:
            return 0
        time.sleep(args.loop)


def merge(target, source):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge(target[key], value)
        else:
            target[key] = value


if __name__ == "__main__":
    sys.exit(main())
