"""Publish aggregate Freqtrade PnL from read-only SQLite and localhost status."""
import argparse
import base64
import datetime as dt
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request


def open_pnl(settings, port, open_ids):
    if not open_ids:
        return 0
    try:
        authorization = base64.b64encode(
            (settings['username'] + ':' + settings['password']).encode()
        ).decode()
        request = urllib.request.Request(f'http://127.0.0.1:{port}/api/v1/status',
                                         headers={'Authorization': 'Basic ' + authorization})
        with urllib.request.urlopen(request, timeout=8) as response:
            trades = json.load(response)
        if {trade['trade_id'] for trade in trades} != open_ids:
            return None
        value = sum(trade['profit_abs'] for trade in trades)
        return round(value, 8) if math.isfinite(value) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def collect_exchange(root, name, port):
    config = json.loads((root / 'config.json').read_text())
    private = json.loads((root / f'config.live.{name.lower()}.private.json').read_text())
    api_settings = config['api_server'] | private.get('api_server', {})
    database = root / f'tradesv3.{name.lower()}.live.sqlite'
    conn = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('BEGIN')
        open_ids = {row['id'] for row in conn.execute('SELECT id FROM trades WHERE is_open=1')}
        daily = [dict(row) for row in conn.execute("""
            SELECT date(close_date,'+7 hours') AS date, pair,
                   round(sum(close_profit_abs),8) AS pnl,
                   sum(close_profit_abs > 0) AS wins, sum(close_profit_abs < 0) AS losses,
                   sum(close_profit_abs = 0) AS flat,
                   round(sum(max(close_profit_abs,0)),8) AS gains,
                   round(sum(max(-close_profit_abs,0)),8) AS lossAbs
            FROM trades WHERE is_open=0 AND close_profit_abs IS NOT NULL AND close_date IS NOT NULL
            GROUP BY 1,2 ORDER BY 1,2
        """)]
        recent = []
        for row in conn.execute("""
            SELECT close_date, pair, close_profit_abs, exit_reason FROM trades
            WHERE is_open=0 AND close_profit_abs IS NOT NULL AND close_date IS NOT NULL
            ORDER BY close_date DESC LIMIT 35
        """):
            closed = dt.datetime.fromisoformat(row['close_date']).replace(tzinfo=dt.timezone.utc)
            reason = re.sub(r'[^a-zA-Z0-9_]', '_', row['exit_reason'] or '')[:80]
            recent.append({'closedAt': closed.isoformat(), 'pair': row['pair'],
                           'pnl': row['close_profit_abs'], 'reason': reason})
    finally:
        conn.close()
    return {'name': name, 'capital': private['available_capital'], 'openCount': len(open_ids),
            'unrealized': open_pnl(api_settings, port, open_ids), 'daily': daily, 'recent': recent}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bot-data', type=Path, required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    root = args.bot_data.resolve()
    exchanges = [collect_exchange(root, 'Binance', 8080), collect_exchange(root, 'OKX', 8081)]
    snapshot = {'version': 1, 'capturedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
                'exchanges': exchanges}
    if not args.publish:
        print(json.dumps(snapshot, allow_nan=False))
        return
    url = os.environ['SNAPSHOT_ENDPOINT']
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.vercel.app') or parsed.path != '/api/snapshot' or parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port:
        raise ValueError('Invalid snapshot endpoint')
    request = urllib.request.Request(url, data=json.dumps(snapshot, allow_nan=False).encode(),
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': 'Bearer ' + os.environ['SNAPSHOT_PUBLISH_TOKEN']})
    # Avoid forwarding the publish token to redirects.
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=30) as response:
        result = json.load(response)
    if result.get('capturedAt') != snapshot['capturedAt']:
        raise ValueError('Snapshot acknowledgement mismatch')
    print('Snapshot published at', result['capturedAt'])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as error:
        raise SystemExit(f'Snapshot publishing returned HTTP {error.code}') from None
