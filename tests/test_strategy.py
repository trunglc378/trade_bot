"""Exercise actual strategy hooks with pandas; exchange/Freqtrade runtime are test doubles."""
from datetime import timedelta
import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_research import config, NOW, Exchange, research

try:
    import pandas as pd
except ImportError:
    pd = None


@unittest.skipIf(pd is None, "Requires pandas: run with py -3.12")
class StrategyHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        modules = {}
        for name in ("freqtrade", "freqtrade.strategy", "freqtrade.persistence", "freqtrade.vendor",
                     "freqtrade.vendor.qtpylib", "freqtrade.vendor.qtpylib.indicators", "talib", "talib.abstract"):
            modules[name] = types.ModuleType(name)
        modules["freqtrade.strategy"].IStrategy = object
        modules["freqtrade.strategy"].IntParameter = lambda *a, **k: types.SimpleNamespace(value=k["default"])
        modules["freqtrade.strategy"].DecimalParameter = lambda *a, **k: None
        cls.trade = Mock()
        cls.trade.get_trades_proxy.return_value = []
        modules["freqtrade.persistence"].Trade = cls.trade
        cls.patch = patch.dict(sys.modules, modules)
        cls.patch.start()
        cls.strategy_type = importlib.import_module("VnSmartTrendStrategy").VnSmartTrendStrategy

    @classmethod
    def tearDownClass(cls):
        cls.patch.stop()

    def setUp(self):
        self.strategy = self.strategy_type()
        self.strategy.config = config()
        self.strategy.config["runmode"] = "dry_run"
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.strategy.config["user_data_dir"] = Path(self.temp.name)
        self.strategy.wallets = Mock()
        self.strategy.wallets.get_total_stake_amount.return_value = 1000
        self.trade.get_trades_proxy.return_value = []
        self.strategy.dp = Mock()
        self.strategy.dp.get_analyzed_dataframe.return_value = (pd.DataFrame([
            {"date": pd.Timestamp(NOW - timedelta(minutes=5)), "close": 102.59}]), None)
        self.strategy.dp.orderbook.return_value = Exchange().fetch_order_book()
        self.report = research.build_report(self.strategy.config, Exchange(), NOW)
        research.atomic_write(Path(self.temp.name) / "research/latest.json", self.report)

    def entry(self, now=NOW, amount=.5, rate=102.59):
        return self.strategy.confirm_trade_entry("BTC/USDT", "limit", amount, rate, "GTC", now, "test", "long")

    def test_entry_accepts_fresh_report_in_session(self):
        self.assertTrue(self.entry())
        self.strategy.dp.send_msg.assert_called_once()

    def test_entry_vetoes_outside_session_and_oversize(self):
        self.assertFalse(self.entry(NOW + timedelta(hours=1)))
        self.assertFalse(self.entry(amount=100))

    def test_entry_vetoes_stale_report_or_missing_file(self):
        research.atomic_write(Path(self.temp.name) / "research/latest.json", {})
        self.assertFalse(self.entry())
        (Path(self.temp.name) / "research/latest.json").unlink()
        self.assertFalse(self.entry())

    def test_entry_vetoes_wide_spread_deviation_and_stale_candle(self):
        self.strategy.dp.orderbook.return_value = {"bids": [[100, 1]], "asks": [[110, 1]]}
        self.assertFalse(self.entry())
        self.strategy.dp.orderbook.return_value = Exchange().fetch_order_book()
        self.assertFalse(self.entry(rate=105))
        self.strategy.dp.get_analyzed_dataframe.return_value = (pd.DataFrame([
            {"date": pd.Timestamp(NOW - timedelta(hours=1)), "close": 102.59}]), None)
        self.assertFalse(self.entry())

    def test_sizing_hook_rejects_exchange_minimum_and_api_failure(self):
        args = ("BTC/USDT", NOW, 102.59, 200, 150, 1000, 1, "test", "long")
        self.assertEqual(self.strategy.custom_stake_amount(*args), 0)
        self.strategy.wallets.get_total_stake_amount.side_effect = RuntimeError("offline")
        self.assertFalse(self.entry())

    def test_historical_does_not_read_research_or_orderbook(self):
        self.strategy.config["runmode"] = "backtest"
        self.assertTrue(self.entry())
        self.strategy.dp.orderbook.assert_not_called()
        self.strategy.config["vn_policy"]["research"]["mode"] = "required"
        with self.assertRaises(ValueError):
            self.strategy.bot_start()
        self.assertFalse(self.entry())

    def test_schedule_filters_candle_close_not_open_time(self):
        frame = pd.DataFrame([{"date": t, "close": 110, "open": 109, "ema200": 90,
                               "ema20": 105, "ema50": 100, "rsi": 55,
                               "volume": 200, "volume_mean_20": 100, "bb_lowerband": 95}
                              for t in pd.to_datetime(["2026-10-26T19:55:00Z", "2026-10-26T20:55:00Z"])])
        output = self.strategy.populate_entry_trend(frame, {})
        self.assertEqual(list(output["enter_long"]), [1, 0])

    def test_exits_not_blocked_by_schedule_or_broken_report(self):
        trade = Mock(open_rate=100)
        trade.calc_profit_ratio.return_value = -.04
        self.assertTrue(self.strategy.confirm_trade_exit("BTC/USDT", trade, "market", 1, 96,
            "GTC", "stop_loss", NOW + timedelta(hours=3)))

    def test_notification_failure_does_not_block_stoploss(self):
        self.strategy.dp.send_msg.side_effect = RuntimeError("notification unavailable")
        trade = Mock(open_rate=100)
        trade.calc_profit_ratio.return_value = -.04
        self.assertTrue(self.strategy.confirm_trade_exit("BTC/USDT", trade, "market", 1, 96,
            "GTC", "stop_loss", NOW + timedelta(hours=3)))


if __name__ == "__main__":
    unittest.main()
