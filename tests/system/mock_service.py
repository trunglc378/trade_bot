"""Isolated test-only server: ephemeral port and reset; never binds outside localhost."""
import copy
import importlib.util
import json
from pathlib import Path
from http.server import HTTPServer
from datetime import datetime, timedelta, timezone

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("system_mock", root / "freqtrade-bot/mock_api_server.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
initial = copy.deepcopy(module.BOT_STATE)


def report():
    now = datetime.now(timezone.utc)
    return {"schema_version": 1, "is_mock": True, "exchange": "binance", "mode": "advisory",
            "generated_at": now.isoformat(), "expires_at": (now + timedelta(minutes=15)).isoformat(),
            "schedule_enabled": False, "schedule_windows": [], "errors": [],
            "candidates": [{"pair": "BTC/USDT", "score": 80, "rsi_14": 55, "regime": "TĂNG_ỔN_ĐỊNH",
                "spread": .001, "hour_change": .01, "eligible": True, "reasons": [], "ai_votes": {
                    "gemini": {"action": "consider", "confidence": .8, "reason": "Dữ liệu thử nghiệm",
                        "sources": [{"url": "https://reuters.com/markets", "title": "Fixture source"}]}}}]}


module.get_research_report = report


class Handler(module.FreqtradeMockHandler):
    def log_message(self, *args):
        pass
    def do_POST(self):
        if self.path == "/__test__/reset":
            module.BOT_STATE = copy.deepcopy(initial)
            return self._send_json({"status": "reset"})
        return super().do_POST()


server = HTTPServer(("127.0.0.1", 0), Handler)
print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}"}), flush=True)
server.serve_forever()
