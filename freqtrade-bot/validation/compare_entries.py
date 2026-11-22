"""Compare a fixed set of entry rules, using only public market data."""
import json
from pathlib import Path
import subprocess

ROOT = Path('/freqtrade/user_data')
STRATEGIES = [
    'VnSmartTrendStrategy', 'VnTrend1hCandidate', 'VnTrendPullbackCandidate',
    'VnTrendQualityCandidate', 'VnTrendMarketCandidate',
]
WINDOWS = {
    'august': '20260801-20260915',
    'september_october': '20260915-20261029',
    'november': '20261101-20261113',
}


def backtest(config, exchange, name, days, strategies, fee, pairs=(), *, timeframe=None, detail=None):
    dest = ROOT / 'comparisons' / exchange / name
    dest.mkdir(parents=True, exist_ok=True)
    command = [
        'freqtrade', 'backtesting', '-c', str(config),
        '--strategy-path', str(ROOT / 'strategies'), '--strategy-list', *strategies,
        '--timerange', days, '--enable-protections', '--fee', fee, '--cache', 'none',
        '--export', 'trades', '--backtest-directory', str(dest), '--no-color',
    ]
    if pairs:
        command.extend(['--pairs', *pairs])
    if timeframe:
        command.extend(['--timeframe', timeframe])
    if detail:
        command.extend(['--timeframe-detail', detail])
    latest = dest / '.last_result.json'
    latest.unlink(missing_ok=True)
    with (dest / 'run.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    archive = dest / json.loads(latest.read_text())['latest_backtest']
    if not archive.is_file():
        raise RuntimeError(f'Missing backtest archive {archive}')
    return archive


def main():
    for name, days in WINDOWS.items():
        for exchange in ('binance', 'okx'):
            config = ROOT / f'config-{exchange}.json'
            settings = json.loads(config.read_text())
            if not settings.get('dry_run') or settings['exchange'].get('key'):
                raise ValueError('Public research config required')
            backtest(config, exchange, name, days, STRATEGIES, '0.001')
            backtest(config, exchange, f'{name}_stress', days, STRATEGIES, '0.0015')
            pairs = [p for p in settings['exchange']['pair_whitelist'] if p not in ('SOL/USDT', 'XRP/USDT')]
            backtest(config, exchange, f'{name}_without_sol_xrp', days, STRATEGIES[:2], '0.001', pairs)


if __name__ == '__main__':
    main()
