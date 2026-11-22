"""Exercise persisted quotas and caches without sending paid or free API requests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'freqtrade-bot/user_data/research'))
from ai_budget import AIBudgetUnavailable, advise_with_budget


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.now = datetime(2026, 11, 22, 10, tzinfo=timezone.utc).timestamp()
        self.calls = []

    def request(self, provider, model, rows):
        self.calls.append(rows)
        return {r['pair']: {'action': 'consider', 'confidence': .8, 'reason': 'test'} for r in rows}

    def call(self, *, scope='binance', now=None, settings=None, request=None, pair='BTC/USDT'):
        return advise_with_budget('gemini', 'gemini-3.1-flash-lite', [{'pair': pair}],
                                  request or self.request, directory=self.directory, scope=scope,
                                  now=self.now if now is None else now, settings=settings)

    def state(self):
        return json.loads((self.directory / 'gemini.json').read_text())

    def test_cache_survives_restart_and_is_exchange_scoped(self):
        self.call()
        self.call(now=self.now + 600)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.call(scope='okx', now=self.now + 600)['BTC/USDT']['action'], 'consider')
        self.call(now=self.now + 900)
        self.assertEqual(len(self.calls), 3)

    def test_daily_attempts_shared_and_counted_before_network_failure(self):
        def fail(*args):
            self.assertEqual(self.state()['requests'], 1)
            raise HTTPError('redacted', 429, 'quota', {'Retry-After': '3600'}, None)
        self.assertEqual(self.call(request=fail), {})
        self.assertEqual(self.call(now=self.now + 1801), {})
        self.assertEqual(self.state()['requests'], 1)
        self.assertEqual(self.state()['last_error']['http_status'], 429)
        self.call(now=self.now + 3601, settings={'daily_requests': 1})
        self.assertEqual(len(self.calls), 0)

    def test_service_error_does_not_retry_and_expired_cache_is_neutral(self):
        self.call()
        def fail(*args):
            raise HTTPError('redacted', 503, 'unavailable', {}, None)
        self.assertEqual(self.call(now=self.now + 901, request=fail), {})
        self.assertEqual(self.call(now=self.now + 1000), {})
        self.assertEqual(self.state()['requests'], 2)

    def test_pacific_midnight_resets_daily_not_at_utc_midnight(self):
        start = datetime(2026, 11, 22, 7, 50, tzinfo=timezone.utc).timestamp()
        self.call(now=start, settings={'daily_requests': 1})
        self.assertEqual(self.call(now=start + 301, scope='okx', settings={'daily_requests': 1}), {})
        self.call(now=start + 901, scope='okx', settings={'daily_requests': 1})
        self.assertEqual(self.state()['day'], '2026-11-22')
        self.assertEqual(self.state()['requests'], 1)
        self.assertEqual(len(self.calls), 2)
        with self.assertRaises(AIBudgetUnavailable):
            self.call(now=start)

    def test_rate_and_token_window_are_rolling_and_persistent(self):
        self.call()
        state = self.state()
        state['next_call'] = 0
        state['minute'] = [{'at': self.now, 'tokens': 199999}]
        (self.directory / 'gemini.json').write_text(json.dumps(state))
        self.assertEqual(self.call(scope='okx', now=self.now + 1), {})
        self.call(scope='okx', now=self.now + 61)
        self.assertEqual(len(self.calls), 2)
        state = self.state()
        state['next_call'] = 0
        state['minute'] = [{'at': self.now + 61, 'tokens': 1}] * 8
        (self.directory / 'gemini.json').write_text(json.dumps(state))
        self.assertEqual(self.call(scope='another', now=self.now + 62), {})

    def test_concurrent_workers_share_one_reservation(self):
        def worker(index):
            try:
                return self.call(scope=str(index))
            except OSError:
                return {}  # Busy lock makes the caller wait until its next scan.
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(worker, range(8)))
        self.assertEqual(self.state()['requests'], 1)
        self.assertEqual(len(self.calls), 1)

    def test_corrupt_state_never_resets_quota(self):
        (self.directory / 'gemini.json').write_text('{broken')
        with self.assertRaises(ValueError):
            self.call()
        self.assertEqual(self.calls, [])

    def test_openai_quota_error_records_code_without_secrets(self):
        def fail(*args):
            body = BytesIO(json.dumps({'error': {'code': 'insufficient_quota',
                                                 'message': 'private upstream message'}}).encode())
            raise HTTPError('https://redacted', 429, 'quota', {}, body)
        result = advise_with_budget('openai', 'gpt-4.1-mini', [{'pair': 'BTC/USDT'}], fail,
                                    directory=self.directory, scope='binance', now=self.now)
        self.assertEqual(result, {})
        text = (self.directory / 'openai.json').read_text()
        self.assertEqual(json.loads(text)['last_error']['code'], 'insufficient_quota')
        self.assertNotIn('private upstream message', text)

    def test_global_interval_bounds_a_busy_two_exchange_day(self):
        for minutes in range(24 * 60):
            self.call(now=self.now + minutes * 60, scope='binance')
            self.call(now=self.now + minutes * 60, scope='okx')
        # Per-pair cache reduces calls further, regardless of worker restarts.
        self.assertLessEqual(len(self.calls), 288)

    def test_other_gemini_models_use_smaller_daily_budget(self):
        for index in range(20):
            advise_with_budget('gemini', 'gemini-3.8-flash', [{'pair': 'BTC/USDT'}], self.request,
                               directory=self.directory, scope=str(index), now=self.now + index * 300)
        self.assertEqual(len(self.calls), 18)

    def test_prompt_batches_are_bounded_and_missing_votes_wait(self):
        rows = [{'pair': f'COIN{i}/USDT', 'regime': 'x' * 100} for i in range(200)]
        def missing(provider, model, batch):
            self.assertLessEqual(len(json.dumps(batch).encode()), 12000)
            self.assertLess(len(batch), len(rows))
            return {}
        result = advise_with_budget('gemini', 'gemini-3.1-flash-lite', rows, missing,
                                    directory=self.directory, scope='binance', now=self.now)
        self.assertTrue(result)
        self.assertTrue(all(r['action'] == 'wait' for r in result.values()))


if __name__ == '__main__':
    unittest.main()
