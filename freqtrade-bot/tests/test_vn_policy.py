import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "user_data" / "strategies"))
sys.path.insert(0, str(ROOT / "user_data" / "research"))
sys.path.insert(0, str(ROOT))

from vn_support import VN, context_id, in_session, report_allows, spread_ratio, stake_size
from providers import _extract_gemini_text, validate_votes
from run import analyze, build_report, rsi
import mock_api_server


class FakeExchange:
    id = "binance"

    def __init__(self, now_ms):
        self.now_ms = now_ms

    def load_markets(self):
        return {
            "BTC/USDT": {"spot": True, "active": True, "quote": "USDT"},
            "SOL/USDT": {"spot": True, "active": True, "quote": "USDT"},
        }

    def fetch_ohlcv(self, pair, timeframe="5m", limit=260):
        # 210 closed 5m candles with steady uptrend
        start_ms = self.now_ms - 210 * 300_000
        candles = []
        price = 60000.0 if pair == "BTC/USDT" else 150.0
        for i in range(210):
            ts = start_ms + i * 300_000
            close = price * (1.0 + 0.0004 * i)
            vol = 100.0 if i < 209 else 160.0
            candles.append([ts, close * 0.999, close * 1.001, close * 0.998, close, vol])
        return candles

    def fetch_ticker(self, pair):
        return {"quoteVolume": 250_000_000.0}

    def fetch_order_book(self, pair, limit=5):
        return {"bids": [[68000.0, 1.5]], "asks": [[68010.0, 1.5]]}


class TestVnPolicyAndAiAdvisor(unittest.TestCase):

    def setUp(self):
        config_path = ROOT / "user_data" / "config.json"
        self.config = json.loads(config_path.read_text(encoding="utf-8-sig"))

    def test_golden_trading_session_03_to_04_vn(self):
        schedule = self.config["vn_policy"]["schedule"]
        # 03:30 giờ Việt Nam (UTC+7) -> Cho phép mua mới
        t_inside = datetime(2026, 10, 27, 3, 30, tzinfo=VN)
        self.assertTrue(in_session(t_inside, schedule))

        # 04:00 giờ Việt Nam -> Đã hết khung [03:00, 04:00)
        t_boundary = datetime(2026, 10, 27, 4, 0, tzinfo=VN)
        self.assertFalse(in_session(t_boundary, schedule))

        # 15:00 chiều giờ Việt Nam -> Ngoài khung giờ mua mới
        t_outside = datetime(2026, 10, 27, 15, 0, tzinfo=VN)
        self.assertFalse(in_session(t_outside, schedule))

    def test_overnight_trading_session(self):
        overnight = {
            "enabled": True,
            "windows": [{"start": "23:00", "end": "04:00", "weekdays": [0, 1, 2, 3, 4, 5, 6]}],
        }
        self.assertTrue(in_session(datetime(2026, 10, 27, 23, 30, tzinfo=VN), overnight))
        self.assertTrue(in_session(datetime(2026, 10, 28, 3, 15, tzinfo=VN), overnight))
        self.assertFalse(in_session(datetime(2026, 10, 28, 12, 0, tzinfo=VN), overnight))

    def test_dynamic_stake_size_risk_limits(self):
        risk = self.config["vn_policy"]["risk"]
        # Với equity = 1000 USDT, risk_per_trade = 0.5% (5 USDT), stoploss = -3%, cost_buffer = 0.4%
        # Stake tối đa theo rủi ro = 5 / 0.034 = 147.0588 USDT (< 20% equity = 200 USDT)
        stake = stake_size(
            equity=1000.0,
            proposed=200.0,
            maximum=500.0,
            minimum=10.0,
            used=0.0,
            stoploss=-0.03,
            risk=risk,
        )
        self.assertAlmostEqual(stake, 1000.0 * 0.005 / (0.03 + 0.004), places=4)

        # Khi vốn đang mở (used) đã đạt trần 60% (600 USDT), không mở thêm lệnh mới
        zero_stake = stake_size(1000.0, 200.0, 500.0, 10.0, 600.0, -0.03, risk)
        self.assertEqual(zero_stake, 0.0)

    def test_multi_ai_consensus_and_veto(self):
        now = datetime(2026, 10, 27, 20, 30, tzinfo=timezone.utc)  # 03:30 sáng giờ VN
        exchange = FakeExchange(now.timestamp() * 1000)

        cfg = json.loads(json.dumps(self.config))
        cfg["exchange"]["pair_whitelist"] = ["BTC/USDT", "SOL/USDT"]
        cfg["vn_policy"]["research"]["mode"] = "required"
        cfg["vn_policy"]["research"]["providers"] = {
            "openai": "gpt-4.1-mini",
            "gemini": "gemini-3.8-flash",
        }
        cfg["vn_policy"]["research"]["min_ai_votes"] = 2
        cfg["vn_policy"]["research"]["min_ai_confidence"] = 0.75

        def fake_advisor(provider, model, candidates):
            if provider == "openai":
                return {
                    "BTC/USDT": {"action": "consider", "confidence": 0.88, "reason": "Xu hướng tăng mạnh"},
                    "SOL/USDT": {"action": "consider", "confidence": 0.82, "reason": "Dòng tiền tốt"},
                }
            # Gemini đồng thuận BTC/USDT nhưng phủ quyết (avoid) SOL/USDT
            return {
                "BTC/USDT": {"action": "consider", "confidence": 0.85, "reason": "Đồng thuận xu hướng tăng"},
                "SOL/USDT": {"action": "avoid", "confidence": 0.80, "reason": "Cảnh báo kháng cự gần"},
            }

        report = build_report(cfg, exchange, now=now, advisor=fake_advisor)
        self.assertTrue(report["in_trading_session"])
        self.assertTrue(report_allows(report, cfg, "BTC/USDT", now + timedelta(seconds=60)))
        self.assertFalse(report_allows(report, cfg, "SOL/USDT", now + timedelta(seconds=60)))
        # Báo cáo hết hạn sau TTL -> từ chối
        self.assertFalse(report_allows(report, cfg, "BTC/USDT", now + timedelta(seconds=1000)))

    def test_gemini_interactions_and_legacy_parser(self):
        payload_json = '{"recommendations":[{"pair":"BTC/USDT","action":"consider","confidence":0.9,"reason":"Tốt"}]}'
        interactions_res = {
            "status": "completed",
            "steps": [
                {"type": "thought", "signature": "sig123"},
                {"type": "model_output", "content": [{"type": "text", "text": payload_json}]},
            ],
        }
        parsed = validate_votes(json.loads(_extract_gemini_text(interactions_res)), {"BTC/USDT"})
        self.assertEqual(parsed["BTC/USDT"]["action"], "consider")

    def test_mock_server_research_report(self):
        with patch.object(mock_api_server.Path, "is_file", return_value=False):
            report = mock_api_server.get_research_report()
        self.assertEqual(report["schema_version"], 1)
        self.assertTrue(report["is_mock"])
        self.assertTrue(len(report["candidates"]) >= 3)
        self.assertIn("openai", report["candidates"][0]["ai_votes"])
        self.assertIn("gemini", report["candidates"][0]["ai_votes"])


if __name__ == "__main__":
    unittest.main()
