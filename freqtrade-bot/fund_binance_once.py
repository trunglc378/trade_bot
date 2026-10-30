"""One-time, user-authorized funding of the 34.16 USDT Binance live allocation.

Default is a read-only plan. --execute redeems only the required BTC from Flexible
Earn and submits one FOK limit sell with a 0.2% price bound. A durable receipt
prevents accidental replay; ambiguous requests are never retried automatically.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import time

import ccxt

D = lambda value: Decimal(str(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path("/deployment")
    config = json.loads((root / "user_data/config.live.binance.private.json").read_text())
    target = D(config["available_capital"])
    if target != D("34.16"):
        raise ValueError("This authorization is limited to 34.16 USDT")
    settings = config["exchange"]
    exchange = ccxt.binance({
        "apiKey": settings["key"], "secret": settings["secret"],
        "timeout": 20000, "enableRateLimit": True,
        "options": {"defaultType": "spot", "fetchCurrencies": False},
    })
    balance = exchange.fetch_balance({"type": "spot"})
    usdt = D(balance.get("USDT", {}).get("free") or 0)
    if usdt >= target:
        print(json.dumps({"action": "none", "reason": "Already funded", "usdt_free": str(usdt)}))
        return
    receipt = root / "user_data/binance-initial-funding.private.json"
    if receipt.exists():
        raise ValueError("Funding receipt already exists; reconcile it before any further action")
    book = exchange.fetch_order_book("BTC/USDT", 5)
    bid, ask = D(book["bids"][0][0]), D(book["asks"][0][0])
    if bid <= 0 or ask < bid or (ask - bid) / bid > D("0.002"):
        raise ValueError("Invalid/wide orderbook")
    market = exchange.market("BTC/USDT")
    step = D(market["precision"]["amount"])
    floor = D(exchange.price_to_precision("BTC/USDT", float(bid * D("0.998"))))
    minimum = D(market["limits"]["cost"]["min"])
    gross_required = max((target - usdt) / D("0.998"), minimum * D("1.01"))
    quantity = (gross_required / floor / step).to_integral_value(rounding=ROUND_CEILING) * step
    if quantity * bid > target - usdt + D("2"):
        raise ValueError("Rounding would exceed the authorized funding buffer")
    spot_btc = D(balance.get("BTC", {}).get("free") or 0)
    redeem = max(D(0), quantity - spot_btc)
    product = None
    if redeem:
        rows = exchange.sapi_get_simple_earn_flexible_position({"asset": "BTC", "size": 100}).get("rows", [])
        product = next((row for row in rows if row.get("canRedeem") and D(row["totalAmount"]) >= redeem), None)
        if product is None:
            raise ValueError("Insufficient redeemable BTC in Flexible Earn")
    plan = {
        "target_usdt": str(target), "usdt_before": str(usdt),
        "btc_redeem": str(redeem), "btc_to_sell": str(quantity),
        "limit_price_usdt": str(floor), "reference_bid_usdt": str(bid),
        "estimated_gross_usdt": str(quantity * bid), "time_in_force": "FOK",
        "client_order_id": "vnfund" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    }
    print(json.dumps({"plan": plan, "execute": args.execute}))
    if not args.execute:
        return

    def save(stage, **values):
        plan.update(stage=stage, updated_at=datetime.now(timezone.utc).isoformat(), **values)
        receipt.write_text(json.dumps(plan, indent=2) + "\n")
        receipt.chmod(0o600)

    save("prepared")
    if redeem:
        save("redeem_submitting")
        result = exchange.sapi_post_simple_earn_flexible_redeem({
            "productId": product["productId"], "redeemAll": "false",
            "amount": str(redeem), "destAccount": "SPOT",
        })
        if not result.get("success"):
            save("redeem_rejected")
            raise ValueError("Redemption was not accepted")
        save("redeemed", redemption_id=result.get("redeemId"))
    for _ in range(10):
        balance = exchange.fetch_balance({"type": "spot"})
        if D(balance.get("BTC", {}).get("free") or 0) >= quantity:
            break
        time.sleep(1)
    else:
        save("waiting_for_spot_credit")
        raise ValueError("Redeemed BTC not yet credited; do not retry redemption")
    # A single FOK order fills entirely at this price or better, or expires.
    save("order_submitting")
    order = exchange.create_order("BTC/USDT", "limit", "sell", float(quantity), float(floor), {
        "timeInForce": "FOK", "newClientOrderId": plan["client_order_id"], "newOrderRespType": "FULL",
    })
    save("order_returned", order_id=order.get("id"), order_status=order.get("status"),
         filled_btc=order.get("filled"), gross_usdt=order.get("cost"), fees=order.get("fees"))
    after = exchange.fetch_balance({"type": "spot"})
    usdt_after = D(after.get("USDT", {}).get("free") or 0)
    save("complete" if usdt_after >= target else "requires_reconciliation", usdt_after=str(usdt_after))
    print(json.dumps({"stage": plan["stage"], "order_id": order.get("id"),
                      "filled_btc": order.get("filled"), "usdt_free": str(usdt_after)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never print authenticated URLs, headers or raw provider exceptions.
        print(json.dumps({"error_type": type(exc).__name__, "action": "stopped_no_retry"}))
        raise SystemExit(1)
