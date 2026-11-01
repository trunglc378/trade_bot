"""Extra offline checks for the 1h candidate, not an auto-deployment command."""
import json
from pathlib import Path
import subprocess

root = Path('/freqtrade/user_data')
def run(args, name):
    with (root / name).open('w') as log:
        p = subprocess.run(['freqtrade', *args, '--no-color'], stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f'{name} failed: {p.returncode}')

for exchange in ['binance', 'okx']:
    cfg = ['-c', str(root / f'config-{exchange}.json'), '--strategy-path', str(root / 'strategies'), '-s', 'VnTrend1hCandidate']
    dest = root / 'results' / exchange / 'stress'
    dest.mkdir(parents=True, exist_ok=True)
    run(['backtesting', *cfg, '--timerange', '20260915-20261029', '--fee', '.0015',
         '--enable-protections', '--cache', 'none', '--backtest-directory', str(dest)], f'stress-{exchange}.log')
# This tool forces a huge stake/wallet. Remove the 34.16 capital allocation
# ONLY for indicator-bias analysis, otherwise no orders can pass sizing.
bias_cfg = json.loads((root / 'config-binance.json').read_text())
bias_cfg.pop('available_capital', None)
(root / 'config-bias.json').write_text(json.dumps(bias_cfg))
# A scoped bias check, not a claim that all markets or settings are bias-free.
run(['lookahead-analysis', '-c', str(root / 'config-bias.json'),
     '--strategy-path', str(root / 'strategies'), '-s', 'VnTrend1hCandidate',
     '--timerange', '20260915-20261029', '--minimum-trade-amount', '10',
     '--targeted-trade-amount', '20', '--lookahead-analysis-exportfilename',
     str(root / 'lookahead-binance.csv')], 'lookahead-binance.log')
run(['recursive-analysis', '-c', str(root / 'config-binance.json'),
     '--strategy-path', str(root / 'strategies'), '-s', 'VnTrend1hCandidate',
     '--timerange', '20260901-20261029', '-p', 'BTC/USDT',
     '--startup-candle', '600', '1200', '2400'], 'recursive-binance.log')
(root / 'checks-completed.txt').write_text('completed\n')
