"""User-authorized one-time BTC sell to fund 34.16 USDT on OKX Spot.

Read-only unless --execute. One FOK order; never retries a financial request.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import time

import ccxt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path("/deployment")
    config = json.loads((root / "user_data/config.live.okx.private.json").read_text())
    target = Decimal(str(config["available_capital"]))
    if target != Decimal("34.16"):
        raise ValueError("Authorization is limited to 34.16 USDT")
    keys = config["exchange"]
    exchange = ccxt.okx({"apiKey": keys["key"], "secret": keys["secret"], "password": keys["password"],
        "enableRateLimit": True, "timeout": 20000, "options": {"defaultType": "spot", "fetchCurrencies": False}})
    balance = exchange.fetch_balance({"type": "spot"})
    free = Decimal(str(balance.get("USDT", {}).get("free") or 0))
    if free >= target:
        print(json.dumps({"action": "none", "reason": "Already funded", "usdt_free": str(free)}))
        return
    receipt = root / "user_data/okx-initial-funding.private.json"
    if receipt.exists():
        raise ValueError("Receipt exists; reconcile instead of replaying")
    book = exchange.fetch_order_book("BTC/USDT", 5)
    bid, ask = Decimal(str(book["bids"][0][0])), Decimal(str(book["asks"][0][0]))
    if bid <= 0 or ask < bid or (ask - bid) / bid > Decimal("0.002"):
        raise ValueError("Invalid/wide orderbook")
    market = exchange.market("BTC/USDT")
    step = Decimal(str(market["precision"]["amount"]))
    floor = Decimal(exchange.price_to_precision("BTC/USDT", float(bid * Decimal("0.998"))))
    quantity = ((target - free) / Decimal("0.998") / floor / step).to_integral_value(rounding=ROUND_CEILING) * step
    if quantity * bid > target - free + Decimal("2"):
        raise ValueError("Exceeds funding buffer")
    if Decimal(str(balance.get("BTC", {}).get("free") or 0)) < quantity:
        raise ValueError("Insufficient free BTC; no other assets will be sold")
    plan = {"target_usdt": str(target), "usdt_before": str(free), "btc_to_sell": str(quantity),
        "limit_price_usdt": str(floor), "reference_bid_usdt": str(bid),
        "estimated_gross_usdt": str(quantity * bid), "time_in_force": "FOK",
        "client_order_id": "vnfundokx" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}
    print(json.dumps({"plan": plan, "execute": args.execute}))
    if not args.execute:
        return

    def save(stage, **values):
        plan.update(stage=stage, updated_at=datetime.now(timezone.utc).isoformat(), **values)
        receipt.write_text(json.dumps(plan, indent=2) + "\n")
        receipt.chmod(0o600)

    save("order_submitting")
    order = exchange.create_order("BTC/USDT", "limit", "sell", float(quantity), float(floor),
        {"tdMode": "cash", "timeInForce": "FOK", "clOrdId": plan["client_order_id"]})
    save("order_acknowledged", order_id=order.get("id"))
    for _ in range(10):
        order = exchange.fetch_order(order["id"], "BTC/USDT")
        if order.get("status") in ("closed", "canceled", "rejected", "expired"):
            break
        time.sleep(.5)
    after = exchange.fetch_balance({"type": "spot"})
    free_after = Decimal(str(after.get("USDT", {}).get("free") or 0))
    save("complete" if free_after >= target else "requires_reconciliation",
        order_status=order.get("status"), filled_btc=order.get("filled"),
        gross_usdt=order.get("cost"), fees=order.get("fees"), usdt_after=str(free_after))
    print(json.dumps({"stage": plan["stage"], "order_id": order.get("id"),
        "filled_btc": order.get("filled"), "usdt_free": str(free_after)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__, "action": "stopped_no_retry"}))
        raise SystemExit(1)
