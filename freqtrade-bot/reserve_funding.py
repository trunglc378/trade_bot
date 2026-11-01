"""One approved BTC-only limit sale per venue to reserve 100 net USDT.

Default is read-only. Execution uses a frozen, user-approved seven-day-high plan.
Never changes bot capital, sells bot positions, withdraws assets, or retries an
ambiguous financial request. Never enable a scheduler to re-run --execute.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import json
import os
from pathlib import Path
import sqlite3

D = lambda v: Decimal(str(v))

def quantity_for_target(target, price, fee, step):
    target, price, fee, step = map(D, (target, price, fee, step))
    if not (target == 100 and price > 0 and 0 <= fee <= D('.002') and step > 0):
        raise ValueError('Invalid reserve plan')
    return (target / (price * (1-fee)) / step).to_integral_value(rounding=ROUND_CEILING) * step

def bot_btc(root, name):
    con = sqlite3.connect(f'file:{root / ("tradesv3."+name+".live.sqlite")}?mode=ro', uri=True)
    try:
        return sum((D(r[0]) for r in con.execute("SELECT amount FROM trades WHERE is_open=1 AND pair='BTC/USDT'")), D(0))
    finally:
        con.close()

def non_bot_free(root, name, exchange, balance):
    """Exclude bot BTC, without subtracting an already locked bot stop twice."""
    protected = bot_btc(root, name)
    con = sqlite3.connect(f'file:{root / ("tradesv3."+name+".live.sqlite")}?mode=ro', uri=True)
    try:
        ids = {r[0] for r in con.execute("SELECT order_id FROM orders WHERE ft_pair='BTC/USDT' AND ft_is_open=1 AND side='sell'")}
    finally:
        con.close()
    locked = sum((D(o.get('remaining') or 0) for o in exchange.fetch_open_orders('BTC/USDT') if o['id'] in ids), D(0))
    coin = balance.get('BTC', {})
    return protected, usable_free(coin.get('free') or 0, protected, locked, coin.get('used') or 0)

def usable_free(free, protected, verified_bot_locked, used):
    free, protected, locked, used = map(D, (free, protected, verified_bot_locked, used))
    locked = min(locked, used, protected)
    return max(D(0), free-max(D(0), protected-locked))

def save(path, data):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.chmod(0o600)
    tmp.replace(path)

def claim_receipt(path, data):
    # Claim once before redemption/order submission, including concurrent calls.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exchange', choices=['binance', 'okx'], required=True)
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    import ccxt
    root = Path('/freqtrade/user_data')
    approved = json.loads((root / 'funding-plan-20261101.private.json').read_text(encoding='utf-8-sig'))
    name = args.exchange
    snapshot = approved['exchanges'][name]
    price = D(snapshot['btc_limit_reference'])
    fee = max(D(snapshot['btc_fee']['maker']), D(snapshot['btc_fee']['taker']))
    step = D(snapshot['btc_market_precision']['amount'])
    quantity = quantity_for_target(100, price, fee, step)
    cfg = json.loads((root / f'config.live.{name}.private.json').read_text())
    if D(cfg['available_capital']) != D('34.16'):
        raise ValueError('Bot capital changed; reconcile before reserving funds')
    keys = cfg['exchange']
    ex = getattr(ccxt, name)({'apiKey': keys['key'], 'secret': keys['secret'],
        'password': keys.get('password'), 'enableRateLimit': True, 'timeout': 20000,
        'options': {'defaultType': 'spot', 'fetchCurrencies': False}})
    ex.load_markets()
    if D(ex.amount_to_precision('BTC/USDT', float(quantity))) != quantity:
        raise ValueError('Precision changed')
    if D(ex.price_to_precision('BTC/USDT', float(price))) != price:
        raise ValueError('Price precision changed')
    client_id = 'vnreserve100' + ('b' if name == 'binance' else 'o') + '20261101'
    receipt = root / f'reserve100-{name}-20261101.private.json'
    if receipt.exists():
        raise ValueError('Journal exists; inspect order, never submit again')
    balance = ex.fetch_balance({'type': 'spot'})
    protected, safe_free = non_bot_free(root, name, ex, balance)
    redeem = max(D(0), quantity-safe_free)
    product = None
    if redeem:
        if name != 'binance':
            raise ValueError('Insufficient non-bot BTC')
        positions = ex.sapi_get_simple_earn_flexible_position({'asset': 'BTC', 'size': 100}).get('rows', [])
        product = next((r for r in positions if r.get('canRedeem') and D(r['totalAmount']) >= redeem), None)
        if not product:
            raise ValueError('Insufficient redeemable BTC outside bot')
    plan = {'exchange': name, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'purpose': 'additional_100_USDT_reserve_not_bot_capital', 'reference_snapshot': approved['captured_utc'],
        'pair': 'BTC/USDT', 'limit_price': str(price), 'quantity': str(quantity),
        'fee_bound': str(fee), 'expected_net_usdt': str(quantity*price*(1-fee)),
        'btc_redeem': str(redeem), 'protected_bot_btc': str(protected),
        'usdt_before': str(balance.get('USDT', {}).get('total') or 0),
        'client_order_id': client_id, 'post_only': True}
    print(json.dumps({'plan': plan, 'execute': args.execute}))
    if not args.execute:
        return
    if any(o.get('clientOrderId') == client_id for o in ex.fetch_open_orders('BTC/USDT')):
        raise ValueError('Order already exists; reconcile')
    def journal(stage, **extra):
        plan.update(stage=stage, updated_utc=datetime.now(timezone.utc).isoformat(), **extra)
        save(receipt, plan)
    plan.update(stage='prepared', updated_utc=datetime.now(timezone.utc).isoformat())
    claim_receipt(receipt, plan)
    if redeem:
        journal('redeem_submitting')
        response = ex.sapi_post_simple_earn_flexible_redeem({'productId': product['productId'],
            'redeemAll': 'false', 'amount': str(redeem), 'destAccount': 'SPOT'})
        if not response.get('success'):
            journal('redeem_not_confirmed')
            raise ValueError('Redemption not confirmed; do not retry')
        journal('redeemed', redemption_id=response.get('redeemId'))
    # Read again once; an unsettled redemption stops instead of re-redeeming.
    balance = ex.fetch_balance({'type': 'spot'})
    if non_bot_free(root, name, ex, balance)[1] < quantity:
        journal('waiting_for_spot_credit')
        raise ValueError('BTC not credited yet; reconcile, no automatic retries')
    journal('order_submitting')
    order = ex.create_order('BTC/USDT', 'limit', 'sell', float(quantity), float(price),
        {'postOnly': True, **({'newClientOrderId': client_id} if name == 'binance' else {'clOrdId': client_id, 'tdMode': 'cash'})})
    journal('order_acknowledged', order_id=order['id'], order_status=order.get('status'))
    check = ex.fetch_order(order['id'], 'BTC/USDT')
    journal('verified', order_status=check.get('status'), filled_btc=check.get('filled'),
        remaining_btc=check.get('remaining'), gross_filled_usdt=check.get('cost'))
    print(json.dumps({'stage': plan['stage'], 'exchange': name, 'order_id': order['id'],
        'status': check.get('status'), 'filled': check.get('filled'), 'price': str(price), 'amount': str(quantity)}))

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'error': type(error).__name__, 'action': 'stopped_reconcile_before_retry'}))
        raise SystemExit(1)
