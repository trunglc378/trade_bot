"""Pure, offline-testable entry policies. No exchange or AI credentials here."""
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7), "Asia/Ho_Chi_Minh")


def number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Non-finite number")
    return value


def aware(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return value


def minute(text):
    hour, minutes = map(int, text.split(":"))
    if not (0 <= hour < 24 and 0 <= minutes < 60):
        raise ValueError("Invalid HH:MM")
    return hour * 60 + minutes


def in_session(now, schedule):
    """[start, end); overnight windows use weekday of the starting date."""
    local = aware(now).astimezone(VN)
    if not schedule.get("enabled", False):
        return True
    for window in schedule["windows"]:
        start, end = minute(window["start"]), minute(window["end"])
        days = window["weekdays"]  # Monday = 0
        if start == end or not days or any(type(d) is not int or d not in range(7) for d in days):
            raise ValueError("Empty/invalid trading window")
        m = local.hour * 60 + local.minute
        if start < end and local.weekday() in days and start <= m < end:
            return True
        if start > end:
            if m >= start and local.weekday() in days:
                return True
            if m < end and (local.weekday() - 1) % 7 in days:
                return True
    return False


def stake_size(equity, proposed, maximum, minimum, used, stoploss, risk):
    equity, proposed, maximum, used, stoploss = map(number, (equity, proposed, maximum, used, stoploss))
    per_trade = number(risk["risk_per_trade"])
    per_position = number(risk["max_position_fraction"])
    exposure = number(risk["max_exposure_fraction"])
    costs = number(risk["cost_buffer"])
    if not (0 < per_trade <= .02 and 0 < per_position <= exposure <= 1 and costs >= 0 and -1 < stoploss < 0):
        raise ValueError("Invalid risk limits")
    if min(equity, proposed, maximum) <= 0 or used < 0:
        return 0.0
    size = min(proposed, maximum, equity * per_position,
               equity * per_trade / (abs(stoploss) + costs),
               max(0, equity * exposure - used))
    return size if size >= number(minimum or 0) else 0.0


def spread_ratio(bid, ask):
    bid, ask = number(bid), number(ask)
    if bid <= 0 or ask < bid:
        raise ValueError("Invalid orderbook")
    return (ask - bid) / ((ask + bid) / 2)


def context_id(config):
    context = {"research": config["vn_policy"]["research"],
               "exchange": config["exchange"]["name"],
               "pairs": config["exchange"]["pair_whitelist"],
               "blacklist": config["exchange"].get("pair_blacklist", [])}
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


def report_allows(report, config, pair, now):
    """Missing, mismatched, stale or future snapshots always veto new entries."""
    try:
        settings = config["vn_policy"]["research"]
        now = aware(now)
        created, expires = aware(report["generated_at"]), aware(report["expires_at"])
        if report.get("is_mock") or report["schema_version"] != 1 or report["context_id"] != context_id(config):
            return False
        if not created <= now < expires or (expires - created).total_seconds() > settings["ttl_seconds"]:
            return False
        return any(row["pair"] == pair and row["eligible"] is True for row in report["candidates"])
    except (KeyError, TypeError, ValueError):
        return False
