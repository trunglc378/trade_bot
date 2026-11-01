"""Create a public-only research workspace; never read/copy private credentials."""
import copy
import json
from pathlib import Path
import shutil

source = Path(__file__).resolve().parents[1]
dest = source / 'user_data' / 'reports' / 'validation-20261101'
(dest / 'strategies').mkdir(parents=True, exist_ok=True)
for name in ['VnSmartTrendStrategy.py', 'vn_support.py']:
    shutil.copy2(source / 'user_data' / 'strategies' / name, dest / 'strategies' / name)
shutil.copy2(source / 'validation' / 'ValidationStrategies.py', dest / 'strategies' / 'ValidationStrategies.py')
base = json.loads((source / 'user_data' / 'config.json').read_text(encoding='utf-8-sig'))
for name in ['binance', 'okx']:
    cfg = copy.deepcopy(base)
    cfg.update(dry_run=True, dry_run_wallet=34.16, available_capital=34.16,
               max_open_trades=2, stake_amount=15.37, user_data_dir='/freqtrade/user_data')
    cfg.pop('api_server', None)
    cfg.pop('telegram', None)
    cfg['exchange'] = {'name': name, 'key': '', 'secret': '',
        'ccxt_config': {'enableRateLimit': True, 'options': {'fetchCurrencies': False}},
        'ccxt_async_config': {'enableRateLimit': True, 'options': {'fetchCurrencies': False}},
        'pair_whitelist': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'LINK/USDT'],
        'pair_blacklist': []}
    if name == 'binance':
        cfg['exchange']['pair_whitelist'] += ['ADA/USDT', 'AVAX/USDT']
    else:
        cfg['order_types']['stoploss'] = 'market'
    cfg['vn_policy']['schedule']['enabled'] = False
    cfg['vn_policy']['risk'].update(risk_per_trade=.016, max_position_fraction=.45,
        max_exposure_fraction=.9, off_peak_stake_multiplier=.75)
    # Historical technical baseline cannot reconstruct historical AI/orderbook.
    cfg['vn_policy']['research']['mode'] = 'off'
    cfg['vn_policy']['research']['providers'] = {}
    (dest / f'config-{name}.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
print(dest)
