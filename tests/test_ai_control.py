"""Quota/circuit regression tests; no network and no real keys."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
from email.message import Message
from pathlib import Path
import sqlite3
import subprocess
import sys
import json
import tempfile
import time
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError

from test_research import ROOT, config, NOW, Exchange, research, report_allows
from ai_control import AIController, AICallBlocked


class AIControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.c = config()
        self.c['vn_policy']['research']['ai_control'] = {
            'enabled': True, 'only_in_session': False}
        self.clock = Mock(return_value=NOW.timestamp())
        self.rows = [{'pair': 'BTC/USDT', 'score': 80}]
        def yes(provider, model, rows):
            return {row['pair']: {'action': 'consider', 'confidence': .9, 'reason': 'fixture'} for row in rows}
        self.advisor = Mock(side_effect=yes)

    def controller(self):
        return AIController(self.c, self.temp.name, self.advisor, self.clock)

    def expect_block(self, controller, reason, provider='gemini', rows=None):
        with self.assertRaises(AICallBlocked) as error:
            controller(provider, 'fixture-model', rows or self.rows)
        self.assertEqual(error.exception.reason, reason)

    def test_disabled_and_outside_session_never_call_advisor(self):
        p = self.c['vn_policy']['research']['ai_control']
        p['enabled'] = False
        self.expect_block(self.controller(), 'ai_disabled')
        p.update(enabled=True, only_in_session=True)
        self.clock.return_value = (NOW + timedelta(hours=2)).timestamp()
        self.expect_block(self.controller(), 'outside_ai_session')
        self.advisor.assert_not_called()

    def test_pause_survives_new_controller(self):
        (Path(self.temp.name) / 'AI_PAUSE').touch()
        self.expect_block(self.controller(), 'ai_paused')
        self.advisor.assert_not_called()

    def test_control_cli_pauses_and_resumes_without_api_or_database(self):
        script = ROOT / 'freqtrade-bot/user_data/research/ai_control.py'
        for action, expected in (('--pause', True), ('--resume', False)):
            proc = subprocess.run([sys.executable, str(script), '--directory', self.temp.name, action],
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['paused'], expected)
        self.advisor.assert_not_called()

    def test_cache_preserves_original_analysis_time_and_restart_interval(self):
        original = self.controller()('gemini', 'fixture-model', self.rows)
        self.clock.return_value += 300
        cached = self.controller()('gemini', 'fixture-model', self.rows)
        self.assertTrue(cached['BTC/USDT']['from_cache'])
        self.assertEqual(cached['BTC/USDT']['analysis_generated_at'], original['BTC/USDT']['analysis_generated_at'])
        self.advisor.assert_called_once()
        self.clock.return_value += 301
        self.expect_block(self.controller(), 'cooldown')

    def test_hourly_cap_is_shared_across_providers(self):
        self.controller()('gemini', 'fixture-model', self.rows)
        self.controller()('openai', 'fixture-model', self.rows)
        self.clock.return_value += 1801
        self.expect_block(self.controller(), 'hourly_limit')
        self.assertEqual(self.advisor.call_count, 2)

    def test_rolling_daily_cap_persists_across_restarts(self):
        self.c['vn_policy']['research']['ai_control']['max_requests_per_day'] = 2
        for shift in (0, 3601):
            self.clock.return_value = NOW.timestamp() + shift
            self.controller()('gemini', 'fixture-model', self.rows)
        self.clock.return_value = NOW.timestamp() + 7202
        self.expect_block(self.controller(), 'daily_limit')
        self.assertEqual(self.advisor.call_count, 2)

    def test_payment_auth_model_errors_latch_circuit(self):
        for code in (400, 401, 402, 403, 404):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                self.advisor.side_effect = HTTPError('https://fixture.invalid', code, 'fixture', Message(), None)
                controller = AIController(self.c, directory, self.advisor, self.clock)
                with self.assertRaises(HTTPError):
                    controller('gemini', 'fixture-model', self.rows)
                self.clock.return_value += 90000
                self.expect_block(AIController(self.c, directory, self.advisor, self.clock), 'circuit_open_' + str(code))

    def test_429_retry_after_stops_immediate_retries(self):
        headers = Message()
        headers['Retry-After'] = '3600'
        self.advisor.side_effect = HTTPError('https://fixture.invalid', 429, 'fixture', headers, None)
        with self.assertRaises(HTTPError):
            self.controller()('gemini', 'fixture-model', self.rows)
        self.expect_block(self.controller(), 'cooldown')
        with closing(sqlite3.connect(Path(self.temp.name) / 'ai-control.sqlite')) as db:
            self.assertGreaterEqual(db.execute('SELECT next_at FROM state').fetchone()[0], self.clock() + 3600)
            self.assertEqual(db.execute('SELECT count(*),code FROM attempts').fetchone(), (1, 429))

    def test_503_failure_backs_off_and_counts_failed_attempt(self):
        self.advisor.side_effect = HTTPError('https://fixture.invalid', 503, 'fixture', Message(), None)
        with self.assertRaises(HTTPError):
            self.controller()('gemini', 'fixture-model', self.rows)
        self.expect_block(self.controller(), 'cooldown')
        self.advisor.assert_called_once()
        with closing(sqlite3.connect(Path(self.temp.name) / 'ai-control.sqlite')) as db:
            self.assertEqual(db.execute('SELECT outcome,code FROM attempts').fetchone(), ('error', 503))

    def test_input_and_batch_caps(self):
        rows = [{'pair': f'COIN{i}/USDT', 'score': i} for i in range(8)]
        result = self.controller()('gemini', 'fixture-model', rows)
        self.assertEqual(len(result), 3)
        self.assertEqual(len(self.advisor.call_args.args[2]), 3)
        rows[0]['large'] = 'x' * 20000
        rows[0]['score'] = 999
        self.expect_block(self.controller(), 'input_limit', rows=rows)

    def test_concurrent_workers_reserve_only_one_request(self):
        def slow(*args):
            time.sleep(.1)
            return {'BTC/USDT': {'action': 'wait', 'confidence': .5, 'reason': 'fixture'}}
        self.advisor.side_effect = slow
        def call(_):
            try:
                return self.controller()('gemini', 'fixture-model', self.rows)
            except AICallBlocked:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(call, range(4)))
        self.advisor.assert_called_once()

    def test_required_snapshot_does_not_extend_cached_ai_freshness(self):
        self.c['vn_policy']['research'].update(mode='required', providers={'gemini': 'fixture-model'}, min_ai_votes=1)
        def cached(*args):
            return {'BTC/USDT': {'action': 'consider', 'confidence': .9, 'reason': 'fixture',
                    'analysis_generated_at': (NOW - timedelta(seconds=500)).isoformat(), 'from_cache': True}}
        report = research.build_report(self.c, Exchange(), NOW, advisor=cached)
        self.assertEqual(report['expires_at'], (NOW + timedelta(seconds=100)).isoformat())
        self.assertTrue(report_allows(report, self.c, 'BTC/USDT', NOW))
        self.assertFalse(report_allows(report, self.c, 'BTC/USDT', NOW + timedelta(seconds=100)))
