"""Read-only funding inventory and seven-day BTC reference prices. No mutations."""
import datetime as dt
import json
from pathlib import Path
import sqlite3
import time
import ccxt

root = Path('/freqtrade/user_data')
now = int(time.time() * 1000)
start = (now // 60000) * 60000 - 7 * 86400000
hour = 3600000
first_full_hour = ((start + hour - 1) // hour) * hour
out = {'captured_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
       'weekly_window_start_ms': start, 'additional_net_usdt_per_exchange': 100, 'exchanges': {}}
for name in ['binance', 'okx']:
    cfg = json.loads((root / f'config.live.{name}.private.json').read_text())
    keys = cfg['exchange']
    ex = getattr(ccxt, name)({'apiKey': keys['key'], 'secret': keys['secret'],
        'password': keys.get('password'), 'enableRateLimit': True, 'timeout': 20000,
        'options': {'defaultType': 'spot', 'fetchCurrencies': False}})
    ex.load_markets()
    bal = ex.fetch_balance({'type': 'spot'})
    con = sqlite3.connect(f'file:{root / ("tradesv3." + name + ".live.sqlite")}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    protected = {}
    for t in con.execute('SELECT pair, amount FROM trades WHERE is_open=1'):
        asset = t['pair'].split('/')[0]
        protected[asset] = protected.get(asset, 0) + t['amount']
    con.close()
    rows = ex.fetch_ohlcv('BTC/USDT', '1h', (start // hour) * hour, 200)
    peaks = [r[2] for r in rows if first_full_hour <= r[0] <= now]
    if start < first_full_hour:
        partial = ex.fetch_ohlcv('BTC/USDT', '1m', start, 60)
        peaks += [r[2] for r in partial if start <= r[0] < first_full_hour]
    if not peaks:
        raise ValueError('Missing weekly BTC candles')
    high = max(peaks)
    book = ex.fetch_order_book('BTC/USDT', 5)
    spot = {c: {'free': bal['free'].get(c, 0), 'used': bal['used'].get(c, 0), 'total': q}
            for c, q in bal['total'].items() if q and q > 0}
    e = {'available_capital': cfg['available_capital'], 'stake_amount': cfg['stake_amount'],
         'spot': spot, 'protected_bot_amount': protected, 'btc_7d_high': high,
         'btc_limit_reference': ex.price_to_precision('BTC/USDT', high),
         'btc_bid': book['bids'][0][0], 'btc_ask': book['asks'][0][0],
         'btc_market_precision': ex.market('BTC/USDT')['precision'],
         'btc_limits': ex.market('BTC/USDT')['limits'], 'earn': [], 'errors': []}
    try:
        e['btc_fee'] = ex.fetch_trading_fee('BTC/USDT')
    except Exception as error:
        e['btc_fee'] = {'error': type(error).__name__}
    if name == 'binance':
        try:
            earned = ex.sapi_get_simple_earn_flexible_position({'size': 100})
            e['earn'] = [{k: row.get(k) for k in ['asset', 'totalAmount', 'canRedeem', 'productId']}
                         for row in earned.get('rows', [])]
            e['earn_reported_total'] = earned.get('total')
        except Exception as error:
            e['errors'].append({'stage': 'earn', 'error': type(error).__name__})
    # Standardized open orders omit raw exchange/account metadata.
    try:
        orders = ex.fetch_open_orders('BTC/USDT')
        e['open_btc_orders'] = [{k: o.get(k) for k in ['id', 'symbol', 'type', 'side', 'price', 'amount', 'filled', 'status']} for o in orders]
    except Exception as error:
        e['errors'].append({'stage': 'orders', 'error': type(error).__name__})
    out['exchanges'][name] = e
    ex.close()
print(json.dumps(out, ensure_ascii=False, default=str))
