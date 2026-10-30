"""Read-only live deployment check. Never creates, cancels or modifies orders.

Run inside the pinned Freqtrade image. Credentials stay in private config files;
only selected balances, permissions and sanitized error codes are printed.
"""
import argparse
import json
from pathlib import Path
import re

import ccxt


def merge(target, source):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge(target[key], value)
        else:
            target[key] = value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", action="append", required=True, type=Path)
    args = parser.parse_args()
    config = {}
    for path in args.config:
        merge(config, json.loads(path.read_text(encoding="utf-8-sig")))
    settings = config["exchange"]
    name = settings["name"]
    if name not in ("binance", "okx"):
        raise ValueError("Only Binance and OKX spot are supported")
    result = {"exchange": name, "read_only": True}
    try:
        exchange = getattr(ccxt, name)({
            "apiKey": settings["key"], "secret": settings["secret"],
            "password": settings.get("password", ""),
            "enableRateLimit": True, "timeout": 20000,
            "options": {"defaultType": "spot", "fetchCurrencies": False},
        })
        balance = exchange.fetch_balance({"type": "spot"})
        result["authenticated"] = True
        result["usdt_free"] = balance.get("USDT", {}).get("free", 0)
        result["usdt_total"] = balance.get("USDT", {}).get("total", 0)
        result["configured_capital"] = config.get("available_capital")
        result["enough_free_usdt"] = float(result["usdt_free"] or 0) >= float(config["available_capital"])
        if name == "binance":
            permissions = exchange.sapi_get_account_apirestrictions()
            result["permissions"] = {key: permissions.get(key) for key in (
                "ipRestrict", "enableReading", "enableSpotAndMarginTrading", "enableWithdrawals")}
        else:
            rows = exchange.private_get_account_config().get("data", [])
            result["permissions"] = {"perm": rows[0].get("perm") if rows else None}
        result["ok"] = True
    except Exception as exc:
        result["ok"] = False
        result["error_type"] = type(exc).__name__
        match = re.search(r'"code"\s*:\s*"?(-?\d+)', str(exc))
        if match:
            result["error_code"] = match.group(1)
        # Return only the provider's message after removing all credential values.
        raw = str(exc)
        try:
            payload = json.loads(raw[raw.index("{"):])
            message = str(payload.get("msg", ""))
            for field in ("key", "secret", "password"):
                if settings.get(field):
                    message = message.replace(settings[field], "[REDACTED]")
            result["error_message"] = message[:300]
        except (ValueError, TypeError):
            pass
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
