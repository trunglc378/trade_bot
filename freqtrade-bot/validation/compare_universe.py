"""Screen a reviewed universe on historical data before considering a dry-run."""
import json
import subprocess

from compare_entries import ROOT, STRATEGIES, WINDOWS, backtest


# Snapshot of liquid crypto assets screened on 2026-11-17.
EXTRA_PAIRS = {
    'binance': ['ZEC/USDT', 'NEAR/USDT', 'DOGE/USDT', 'UNI/USDT'],
    'okx': ['HYPE/USDT', 'LIT/USDT', 'ZEC/USDT', 'DOGE/USDT', 'NEAR/USDT', 'OKB/USDT'],
}


def main():
    for exchange, extra in EXTRA_PAIRS.items():
        config = ROOT / f'config-{exchange}.json'
        settings = json.loads(config.read_text())
        if not settings.get('dry_run') or settings['exchange'].get('key'):
            raise ValueError('Public research config required')
        current = settings['exchange']['pair_whitelist']
        expanded = list(dict.fromkeys([*current, *extra]))
        with (ROOT / f'download-expanded-{exchange}.log').open('w') as logfile:
            subprocess.run([
                'freqtrade', 'download-data', '-c', str(config),
                '--timeframes', '5m', '1h', '--timerange', '20260701-20261114',
                '--pairs', *extra, '--no-parallel-download', '--no-color',
            ], stdout=logfile, stderr=subprocess.STDOUT, check=True)
        for period in ('september_october', 'november'):
            for scope, pairs in [('current', current), ('expanded', expanded)]:
                backtest(config, exchange, f'universe_{scope}_{period}', WINDOWS[period],
                         STRATEGIES[:2], '0.0015', pairs)


if __name__ == '__main__':
    main()
