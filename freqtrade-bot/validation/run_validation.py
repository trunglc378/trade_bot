"""Bounded, credential-free research runner. Never runs `trade` or alters live DBs."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path('/freqtrade/user_data')
STRATEGIES = ['VnSmartTrendStrategy', 'VnTrend1hCandidate', 'VnEarlierTrailCandidate', 'VnTrendTrailCandidate']
WINDOWS = {'development': '20260801-20260915', 'holdout': '20260915-20261029'}

def run(args, logfile):
    with (ROOT / logfile).open('w') as log:
        p = subprocess.run(['freqtrade', *args, '--no-color'], stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f'Command failed: see {logfile}, exit {p.returncode}')

def main():
    for exchange in ['binance', 'okx']:
        config = ROOT / f'config-{exchange}.json'
        cfg = json.loads(config.read_text())
        assert cfg['dry_run'] and not cfg['exchange'].get('key') and not cfg.get('api_server', {}).get('enabled')
        run(['download-data', '-c', str(config), '--timerange', '20260701-20261101',
             '--timeframes', '5m', '1h', '--no-parallel-download'], f'download-{exchange}.log')
        for pair in cfg['exchange']['pair_whitelist']:
            for timeframe in ['5m', '1h']:
                expected = ROOT / 'data' / exchange / f'{pair.replace("/", "_")}-{timeframe}.feather'
                if not expected.exists():
                    raise RuntimeError(f'Missing data: {expected}')
        for window, timerange in WINDOWS.items():
            dest = ROOT / 'results' / exchange / window
            dest.mkdir(parents=True, exist_ok=True)
            run(['backtesting', '-c', str(config), '--strategy-path', str(ROOT / 'strategies'),
                 '--strategy-list', *STRATEGIES, '--timerange', timerange, '--enable-protections',
                 '--fee', '0.001', '--cache', 'none', '--export', 'trades',
                 '--backtest-directory', str(dest)], f'backtest-{exchange}-{window}.log')
            if not list(dest.glob('*.zip')):
                raise RuntimeError(f'No backtest result: {dest}')
    (ROOT / 'completed.json').write_text(json.dumps({'status': 'completed', 'windows': WINDOWS, 'strategies': STRATEGIES}))

if __name__ == '__main__':
    main()
