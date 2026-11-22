"""Compare entry signals on a fixed universe with the same 5m exits."""
import json

from compare_entries import ROOT, STRATEGIES, WINDOWS, backtest
from compare_timeframes import PERIODS, check_candles, results


FEES = {'standard': '0.0015', 'stress': '0.0025'}
ENTRY_CANDIDATES = [*STRATEGIES[:2], 'VnTrend15mEntryCandidate']


def main():
    periods = {**PERIODS, 'august': WINDOWS['august']}
    configs = {}
    for exchange in ('binance', 'okx'):
        config = ROOT / f'config-{exchange}.json'
        settings = json.loads(config.read_text())
        market = settings['exchange']
        if (settings.get('dry_run') is not True or settings['trading_mode'] != 'spot'
                or any(market.get(key) for key in ('key', 'secret', 'password'))):
            raise ValueError('Public spot research config required')
        check_candles(exchange, market['pair_whitelist'], periods.values())
        configs[exchange] = config

    with (ROOT / 'comparisons' / 'entry_cadence.jsonl').open('w') as report:
        for scenario, fee in FEES.items():
            for period, days in periods.items():
                for exchange, config in configs.items():
                    name = f'entry_cadence_{period}_{scenario}'
                    archive = backtest(config, exchange, name, days, ENTRY_CANDIDATES, fee,
                                       timeframe='5m')
                    for row in results(archive, exchange, 'current', period, '5m'):
                        print(json.dumps({**row, 'fee_per_side': float(fee)}), file=report, flush=True)


if __name__ == '__main__':
    main()
