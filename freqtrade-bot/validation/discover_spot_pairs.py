"""Shortlist liquid Spot/USDT instruments using public exchange data.

Review instrument type before including results in a crypto-only backtest.
Some exchanges also expose tokenized equities as spot instruments.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'user_data' / 'strategies'))
from vn_support import number, spread_ratio


STABLE_OR_FIAT = frozenset({
    'BRL', 'DAI', 'EUR', 'EURC', 'EURI', 'FDUSD', 'GBP', 'GUSD', 'JPY',
    'PYUSD', 'RLUSD', 'TUSD', 'TRY', 'UAH', 'USDC', 'USD1', 'USDE', 'USDP',
    'USDS', 'USDT', 'USDD', 'USDG', 'USDF', 'XUSD',
})


def ranked_pairs(markets, tickers, config, excluded=()):
    current = set(config['exchange']['pair_whitelist']) | set(excluded)
    blacklist = [re.compile(pattern) for pattern in config['exchange'].get('pair_blacklist', ())]
    settings = config['vn_policy']['research']
    rows = []
    for pair, market in markets.items():
        if pair in current or not re.fullmatch(r'[A-Z0-9]+/USDT', pair):
            continue
        if market.get('active') is not True or market.get('spot') is not True:
            continue
        if market.get('base') in STABLE_OR_FIAT or any(pattern.fullmatch(pair) for pattern in blacklist):
            continue
        ticker = tickers.get(pair)
        if not ticker:
            continue
        try:
            volume = number(ticker['quoteVolume'])
            spread = spread_ratio(ticker['bid'], ticker['ask'])
        except (KeyError, TypeError, ValueError):
            continue
        if volume >= settings['min_quote_volume'] and spread <= settings['max_spread']:
            rows.append({'pair': pair, 'quote_volume': volume, 'spread': spread})
    return sorted(rows, key=lambda row: (-row['quote_volume'], row['pair']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path, help='Public research configuration')
    parser.add_argument('--limit', type=int, default=8)
    parser.add_argument('--history-start', help='Required earliest daily candle, UTC, YYYY-MM-DD')
    parser.add_argument('--exclude', nargs='*', default=(), metavar='PAIR')
    args = parser.parse_args()
    if not 1 <= args.limit <= 20:
        parser.error('--limit must be between 1 and 20')
    import ccxt

    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    name = config['exchange']['name']
    if name not in ('binance', 'okx'):
        parser.error('Only Binance and OKX are supported')
    exchange = getattr(ccxt, name)({'enableRateLimit': True, 'timeout': 12000,
                                   'options': {'defaultType': 'spot', 'fetchCurrencies': False}})
    ranked = ranked_pairs(exchange.load_markets(), exchange.fetch_tickers(), config, args.exclude)
    if args.history_start:
        since = int(datetime.fromisoformat(args.history_start).replace(tzinfo=timezone.utc).timestamp() * 1000)
        selected = []
        for row in ranked[:30]:
            candles = exchange.fetch_ohlcv(row['pair'], '1d', since=since, limit=2)
            if candles and candles[0][0] == since:
                selected.append(row)
            if len(selected) == args.limit:
                break
    else:
        selected = ranked[:args.limit]
    print(json.dumps({'exchange': name, 'timestamp': datetime.now(timezone.utc).isoformat(),
                      'passed_liquidity': len(ranked), 'candidates': selected}, indent=2))


if __name__ == '__main__':
    main()
