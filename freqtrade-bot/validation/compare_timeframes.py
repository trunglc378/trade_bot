"""Benchmark the 5m baseline, 5m + 1h, and 15m + 1h with public spot data."""
import json
from zipfile import ZipFile

import pandas as pd

from compare_entries import ROOT, STRATEGIES, WINDOWS, backtest
from compare_universe import EXTRA_PAIRS


PERIODS = {
    'recent': '20261113-20261117',
    'september_october': WINDOWS['september_october'],
    'november': WINDOWS['november'],
}
FEE = '0.0015'
CANDIDATE = 'VnTrend15mCandidate'


def check_candles(exchange, pairs, periods):
    ranges = [period.split('-') for period in periods]
    first = pd.Timestamp(min(start for start, end in ranges), tz='UTC')
    end = pd.Timestamp(max(end for start, end in ranges), tz='UTC')
    for pair in pairs:
        for timeframe in ('5m', '15m', '1h'):
            interval = pd.Timedelta(timeframe)
            start = first - 600 * interval
            path = ROOT / 'data' / exchange / f'{pair.replace("/", "_")}-{timeframe}.feather'
            dates = pd.to_datetime(pd.read_feather(path, columns=['date'])['date'], utc=True)
            dates = dates[(dates >= start) & (dates < end)]
            expected = pd.date_range(start, end, freq=interval, inclusive='left')
            if not pd.DatetimeIndex(dates).equals(expected):
                raise ValueError(f'Incomplete {exchange} {pair} {timeframe} candle history between {start} and {end}')


def results(archive, exchange, scope, period, timeframe):
    with ZipFile(archive) as bundle:
        entries = json.loads(bundle.read(archive.with_suffix('.json').name))['strategy']
    for strategy, stats in entries.items():
        if stats['timeframe'] != timeframe:
            raise ValueError(f'Unexpected candle interval for {strategy}: {stats["timeframe"]}')
        gross_gain = sum(max(0, trade['profit_abs']) for trade in stats['trades'])
        gross_loss = sum(max(0, -trade['profit_abs']) for trade in stats['trades'])
        yield {
            'exchange': exchange,
            'scope': scope,
            'period': period,
            'strategy': strategy,
            'trades': stats['total_trades'],
            'wins': stats['wins'],
            'pnl_usdt': stats['profit_total_abs'],
            'pnl_ratio': stats['profit_total'],
            'profit_factor': gross_gain / gross_loss if gross_loss else None,
            'drawdown_ratio': stats['max_drawdown_account'],
            'pairs_traded': sorted({trade['pair'] for trade in stats['trades']}),
            'archive': str(archive.relative_to(ROOT)),
        }


def main():
    settings_by_exchange = {}
    for exchange, extra in EXTRA_PAIRS.items():
        config = ROOT / f'config-{exchange}.json'
        settings = json.loads(config.read_text())
        market = settings['exchange']
        if (settings.get('dry_run') is not True or settings['trading_mode'] != 'spot'
                or any(market.get(key) for key in ('key', 'secret', 'password'))):
            raise ValueError('Public spot research config required')
        current = market['pair_whitelist']
        expanded = list(dict.fromkeys([*current, *extra]))
        check_candles(exchange, expanded, PERIODS.values())
        settings_by_exchange[exchange] = (config, current, expanded)

    report = ROOT / 'comparisons' / 'timeframes.jsonl'
    with report.open('w') as output:
        for period, days in PERIODS.items():
            for exchange, (config, current, expanded) in settings_by_exchange.items():
                for scope, pairs in [('current', current), ('expanded', expanded)]:
                    for timeframe, strategies, detail in [('5m', STRATEGIES[:2], None), ('15m', [CANDIDATE], '5m')]:
                        name = f'timeframes_{scope}_{period}_{timeframe}'
                        archive = backtest(config, exchange, name, days, strategies, FEE, pairs,
                                           timeframe=timeframe, detail=detail)
                        for row in results(archive, exchange, scope, period, timeframe):
                            print(json.dumps(row), file=output, flush=True)


if __name__ == '__main__':
    main()
