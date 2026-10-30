"""Offline policy, provider contract, market feed and snapshot integration tests."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "freqtrade-bot"),
                str(ROOT / "freqtrade-bot/user_data/strategies"),
                str(ROOT / "freqtrade-bot/user_data/research")]
import setup_accounts
from vn_support import (
    format_entry_tag_vi,
    format_exit_reason_vi,
    in_session,
    report_allows,
    spread_ratio,
    stake_size,
)
import providers
import run as research
from hourly import summarize

NOW = datetime(2026, 10, 26, 20, 30, tzinfo=timezone.utc)  # Tue 03:30 VN


def config():
    c = json.loads((ROOT / "freqtrade-bot/user_data/config.json").read_text(encoding="utf-8"))
    c["exchange"]["pair_whitelist"] = ["BTC/USDT"]
    return c


class Exchange:
    id = "binance"

    def load_markets(self):
        return {"BTC/USDT": {"spot": True, "active": True, "quote": "USDT"}}

    def fetch_ohlcv(self, *args, **kwargs):
        start = NOW.timestamp() * 1000 - 260 * 300000
        return [[start + i * 300000, 100, 110, 90, 100 + i * .01, 100 + i] for i in range(261)]

    def fetch_ticker(self, *args):
        return {"quoteVolume": 100000000}

    def fetch_order_book(self, *args, **kwargs):
        return {"bids": [[102.58, 100]], "asks": [[102.60, 100]]}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.c = config()

    def test_vn_session_boundaries(self):
        s = self.c["vn_policy"]["schedule"]
        self.assertTrue(in_session(NOW.replace(minute=0), s))
        self.assertTrue(in_session(NOW, s))
        self.assertFalse(in_session(NOW.replace(hour=21, minute=0), s))
        self.assertFalse(in_session(NOW.replace(hour=19, minute=59), s))

    def test_overnight_uses_start_day(self):
        s = {"enabled": True, "windows": [{"start": "23:00", "end": "02:00", "weekdays": [0]}]}
        self.assertTrue(in_session(NOW.replace(hour=18, minute=0), s))  # Tue 01 VN, Mon window
        self.assertFalse(in_session(NOW.replace(hour=20, minute=0), s))

    def test_multiple_windows_and_weekdays(self):
        s = {"enabled": True, "windows": [{"start": "03:00", "end": "04:00", "weekdays": [0]},
                                           {"start": "03:00", "end": "04:00", "weekdays": [1]}]}
        self.assertTrue(in_session(NOW, s))
        self.assertFalse(in_session(NOW + timedelta(days=1), s))

    def test_bad_timezone_and_schedule(self):
        with self.assertRaises(ValueError):
            in_session(NOW.replace(tzinfo=None), {"enabled": False})
        with self.assertRaises(ValueError):
            in_session(NOW, {"enabled": True, "windows": [{"start": "25:00", "end": "04:00", "weekdays": [1]}]})

    def test_risk_budget_position_and_exposure(self):
        r = self.c["vn_policy"]["risk"]
        self.assertAlmostEqual(stake_size(1000, 200, 1000, 10, 0, -.03, r), 5 / .034)
        self.assertEqual(stake_size(1000, 200, 1000, 10, 590, -.03, r), 10)
        self.assertEqual(stake_size(1000, 200, 1000, 11, 590, -.03, r), 0)
        self.assertEqual(stake_size(1000, 200, 1000, 10, 600, -.03, r), 0)
        self.assertEqual(stake_size(1000, 200, 30, 10, 0, -.03, r), 30)

    def test_non_finite_risk_and_invalid_book(self):
        for bad in (float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                stake_size(bad, 200, 1000, 10, 0, -.03, self.c["vn_policy"]["risk"])
        for bid, ask in ((0, 10), (10, 9), (float("nan"), 10)):
            with self.assertRaises(ValueError):
                spread_ratio(bid, ask)

    def test_hourly_timezone_and_net_profit(self):
        rows = [{"open_date": NOW.isoformat(), "profit_abs": p} for p in (3, -2, 0)]
        report = summarize(rows, 3)
        self.assertEqual(report[3]["net_profit"], 1)
        self.assertEqual(report[3]["profit_factor"], 1.5)
        self.assertTrue(report[3]["enough_samples"])
        self.assertFalse(report[4]["enough_samples"])

    def test_vietnamese_entry_tag_and_exit_reason_labels(self):
        self.assertIn("Xu hướng tăng", format_entry_tag_vi("XU_HUONG_TANG_EMA_RSI"))
        self.assertIn("Tín hiệu", format_entry_tag_vi(""))
        self.assertIn("Cắt lỗ", format_exit_reason_vi("stop_loss"))
        self.assertIn("khẩn cấp", format_exit_reason_vi("force_exit"))


class ResearchTests(unittest.TestCase):
    def test_okx_worker_does_not_overwrite_binance_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings = config()
            settings["exchange"]["name"] = "okx"
            settings["vn_policy"]["research"]["report_file"] = "latest-okx.json"
            config_file = root / "config.json"
            config_file.write_text(json.dumps(settings), encoding="utf-8")
            binance_path = root / "research/latest.json"
            research.atomic_write(binance_path, {"exchange": "binance"})
            original = binance_path.read_bytes()
            report = {"exchange": "okx", "candidates": [], "errors": []}
            with patch("sys.argv", ["run.py", "--config", str(config_file)]), \
                    patch.object(research, "_load_dotenv_if_present"), \
                    patch.object(research, "_create_exchange"), \
                    patch.object(research, "build_report", return_value=report):
                self.assertEqual(research.main(), 0)
            self.assertEqual(binance_path.read_bytes(), original)
            self.assertEqual(json.loads((root / "research/latest-okx.json").read_text()), report)
            self.assertEqual(len(list((root / "research/history-okx").glob("*.json"))), 1)

    def setUp(self):
        self.c = config()
        self.exchange = Exchange()

    def test_report_roundtrip_and_expiry(self):
        report = research.build_report(self.c, self.exchange, NOW)
        self.assertTrue(report_allows(report, self.c, "BTC/USDT", NOW))
        self.assertFalse(report_allows(report, self.c, "BTC/USDT", NOW + timedelta(seconds=900)))
        self.assertFalse(report_allows(report, self.c, "BTC/USDT", NOW - timedelta(seconds=1)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest.json"
            research.atomic_write(path, report)
            self.assertEqual(report, json.loads(path.read_text(encoding="utf-8")))

    def test_prune_history_keeps_most_recent_files(self):
        with tempfile.TemporaryDirectory() as directory:
            hist_dir = Path(directory) / "history"
            for idx in range(5):
                research.atomic_write(hist_dir / f"20261028T030{idx}00Z.json", {"seq": idx})
            research.prune_history(hist_dir, max_files=3)
            remaining = sorted(p.name for p in hist_dir.glob("*.json"))
            self.assertEqual(
                remaining,
                ["20261028T030200Z.json", "20261028T030300Z.json", "20261028T030400Z.json"],
            )

    def test_wrong_exchange_policy_and_pair(self):
        report = research.build_report(self.c, self.exchange, NOW)
        for key, value in (("name", "okx"), ("pair_whitelist", ["ETH/USDT"])):
            altered = copy.deepcopy(self.c)
            altered["exchange"][key] = value
            self.assertFalse(report_allows(report, altered, "BTC/USDT", NOW))
        self.assertFalse(report_allows({}, self.c, "BTC/USDT", NOW))
        report["is_mock"] = True
        self.assertFalse(report_allows(report, self.c, "BTC/USDT", NOW))

    def test_rsi_and_overlay_merge(self):
        self.assertEqual(research.rsi([100] * 200), 50)
        self.assertEqual(research.rsi(list(range(1, 201))), 100)
        self.assertEqual(research.rsi(list(range(200, 0, -1))), 0)
        overlay = json.loads((ROOT / "freqtrade-bot/user_data/config-okx.json").read_text())
        research.merge(self.c, overlay)
        self.assertEqual(self.c["exchange"]["name"], "okx")
        self.assertIn("vn_policy", self.c)
        self.assertEqual(self.c["order_types"]["stoploss"], "market")

    def test_unfinished_candle_not_used(self):
        candles = self.exchange.fetch_ohlcv()
        candles[-1][4] = 999999999
        row = research.analyze("BTC/USDT", candles, self.exchange.fetch_ticker(), self.exchange.fetch_order_book(), NOW, self.c["vn_policy"]["research"])
        self.assertAlmostEqual(row["close"], 102.59)

    def test_missing_stale_or_bad_candles_fail(self):
        settings = self.c["vn_policy"]["research"]
        original = self.exchange.fetch_ohlcv()
        bad = copy.deepcopy(original)
        bad[20][4] = float("nan")
        for candles in (original[:10], original[:-10], original[:20] + original[21:], bad):
            with self.assertRaises(ValueError):
                research.analyze("BTC/USDT", candles, self.exchange.fetch_ticker(), self.exchange.fetch_order_book(), NOW, settings)

    def required(self):
        self.c["vn_policy"]["research"].update(mode="required", providers={"openai": "model-a", "gemini": "model-b"})

    @staticmethod
    def yes(*args):
        return {"BTC/USDT": {"action": "consider", "confidence": .9, "reason": "Xu hướng tăng"}}

    def test_required_consensus(self):
        self.required()
        report = research.build_report(self.c, self.exchange, NOW, self.yes)
        self.assertTrue(report_allows(report, self.c, "BTC/USDT", NOW))

    def test_provider_failure_missing_vote_low_confidence_or_veto(self):
        self.required()
        def fail(*args):
            raise TimeoutError("secret never exposed")
        for advisor in (fail, lambda *a: {}, lambda *a: {"BTC/USDT": {"action": "consider", "confidence": .2, "reason": "weak"}},
                        lambda *a: {"BTC/USDT": {"action": "avoid", "confidence": .9, "reason": "risk"}}):
            report = research.build_report(self.c, self.exchange, NOW, advisor)
            self.assertFalse(report_allows(report, self.c, "BTC/USDT", NOW))
            self.assertNotIn("secret never exposed", json.dumps(report))

    def test_ai_cannot_override_market_veto(self):
        self.required()
        self.c["vn_policy"]["research"]["min_quote_volume"] = 1e12
        report = research.build_report(self.c, self.exchange, NOW, self.yes)
        self.assertFalse(report["candidates"][0]["eligible"])

    def test_advisory_failure_does_not_veto_technical(self):
        self.c["vn_policy"]["research"]["providers"] = {"openai": "test"}
        report = research.build_report(self.c, self.exchange, NOW, lambda *a: {})
        self.assertTrue(report["candidates"][0]["eligible"])

    def test_unavailable_market_and_blacklist(self):
        self.c["exchange"]["pair_blacklist"] = ["BTC/.*"]
        self.assertEqual(research.build_report(self.c, self.exchange, NOW)["candidates"], [])
        self.c["exchange"]["pair_blacklist"] = []
        with patch.object(self.exchange, "load_markets", return_value={}):
            self.assertEqual(research.build_report(self.c, self.exchange, NOW)["candidates"], [])

    def test_invalid_quorum_and_threshold(self):
        self.required()
        self.c["vn_policy"]["research"]["min_ai_votes"] = 3
        with self.assertRaises(ValueError):
            research.build_report(self.c, self.exchange, NOW)


class ProviderTests(unittest.TestCase):
    def test_reject_hallucinated_duplicate_and_invalid_confidence(self):
        row = {"pair": "BTC/USDT", "action": "consider", "confidence": .8, "reason": "test"}
        for rows in ([{**row, "pair": "SCAM/USDT"}], [row, row], [{**row, "confidence": float("nan")}],
                     [{**row, "confidence": 2}], [{**row, "confidence": True}]):
            with self.assertRaises(ValueError):
                providers.validate_votes({"recommendations": rows}, {"BTC/USDT"})

    def test_openai_request_and_parsing(self):
        payload = {"recommendations": [{"pair": "BTC/USDT", "action": "wait", "confidence": .5, "reason": "test"}]}
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake"}), patch.object(providers, "post", return_value={
            "status": "completed", "output": [{"content": [{"type": "output_text", "text": json.dumps(payload)}]}]}) as post:
            result = providers.advise("openai", "model-test", [{"pair": "BTC/USDT"}])
            self.assertEqual(result["BTC/USDT"]["action"], "wait")
            self.assertTrue(post.call_args.args[2]["text"]["format"]["strict"])

    def test_gemini_request_and_parsing(self):
        payload = {"recommendations": [{"pair": "BTC/USDT", "action": "consider", "confidence": .8, "reason": "test"}]}
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}), patch.object(providers, "post", return_value={
            "status": "completed", "steps": [{"type": "model_output", "content": [{"type": "text", "text": json.dumps(payload)}]}]}) as post:
            self.assertIn("BTC/USDT", providers.advise("gemini", "model-test", [{"pair": "BTC/USDT"}]))
            self.assertEqual(post.call_args.args[1], {"x-goog-api-key": "fake", "Api-Revision": "2026-05-20"})
            self.assertTrue(post.call_args.args[0].endswith("/interactions"))
            self.assertEqual(post.call_args.args[2]["generation_config"]["max_output_tokens"], 4000)

    def test_gemini_incomplete_text_is_never_a_vote(self):
        for response in ({"status": "incomplete", "output_text": "{}"},
                         {"status": "failed", "steps": []}, {"steps": []}):
            with self.assertRaises(ValueError):
                providers._extract_gemini_text(response)

    def test_refusal_and_truncation(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake"}), patch.object(providers, "post", return_value={"status": "incomplete"}):
            with self.assertRaises(ValueError):
                providers.advise("openai", "test", [{"pair": "BTC/USDT"}])

    def test_setup_accounts_binance_and_okx_builder(self):
        b_cfg = setup_accounts.build_private_config(
            exchange_name="binance",
            api_key="b_key",
            api_secret="b_sec",
            api_passphrase="",
            dry_run=False,
            admin_user="lo_admin",
            admin_password="secret_password",
            jwt_secret="jwt_64",
            ws_token="ws_tok",
            ai_mode="advisory",
            openai_model="gpt-4.1",
            gemini_model="gemini-2.5-pro",
        )
        self.assertFalse(b_cfg["dry_run"])
        self.assertEqual(b_cfg["exchange"]["name"], "binance")
        self.assertNotIn("password", b_cfg["exchange"])
        self.assertEqual(b_cfg["vn_policy"]["research"]["report_file"], "latest.json")
        self.assertEqual(b_cfg["vn_policy"]["research"]["min_ai_votes"], 2)

        o_cfg = setup_accounts.build_private_config(
            exchange_name="okx",
            api_key="o_key",
            api_secret="o_sec",
            api_passphrase="o_pass",
            dry_run=True,
            admin_user="lo_admin",
            admin_password="secret_password",
            jwt_secret="jwt_64",
            ws_token="ws_tok",
            ai_mode="required",
            openai_model="gpt-4.1",
            gemini_model="gemini-2.5-pro",
        )
        self.assertTrue(o_cfg["dry_run"])
        self.assertEqual(o_cfg["exchange"]["name"], "okx")
        self.assertEqual(o_cfg["exchange"]["password"], "o_pass")
        self.assertEqual(o_cfg["vn_policy"]["research"]["report_file"], "latest-okx.json")


if __name__ == "__main__":
    unittest.main()
