"""Integration: real CLI/files/HTTP; exchange and paid provider are controlled fixtures."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from test_research import ROOT, NOW, Exchange, config, research, providers, report_allows
import test_gemini_grounding as grounding_fixtures


class PipelineIntegrationTests(unittest.TestCase):
    def test_grounded_provider_to_snapshot_to_entry_policy(self):
        fixture = grounding_fixtures.GroundingTests()
        fixture.setUp()
        c = config()
        c["vn_policy"]["research"].update(mode="required", providers={"gemini": fixture.options}, min_ai_votes=1)
        for native, expected in ((None, True), ([], False)):
            with self.subTest(native=native):
                with patch.dict(os.environ, {"GEMINI_API_KEY": "fixture-key"}), patch.object(providers, "post", return_value=fixture.response(native=native)):
                    report = research.build_report(c, Exchange(), NOW)
                with tempfile.TemporaryDirectory() as directory:
                    target = Path(directory) / "latest.json"
                    research.atomic_write(target, report)
                    readback = json.loads(target.read_text(encoding="utf-8"))
                    self.assertEqual(report_allows(readback, c, "BTC/USDT", NOW), expected)
                    self.assertEqual(readback["candidates"][0]["ai_votes"]["gemini"]["action"], "consider" if expected else "wait")

    def test_worker_cli_merges_overlay_and_writes_history(self):
        fixture_code = '''
import time
class okx:
    id = "okx"
    def __init__(self, options):
        assert not any(k in options for k in ("apiKey", "secret", "password"))
    def load_markets(self):
        return {"BTC/USDT": {"spot": True, "active": True, "quote": "USDT"}}
    def fetch_ohlcv(self, *args, **kwargs):
        end = int(time.time() // 300) * 300000
        return [[end - (260-i)*300000, 100, 110, 90, 100+i*.01, 100+i] for i in range(261)]
    def fetch_ticker(self, *args):
        return {"quoteVolume": 100000000}
    def fetch_order_book(self, *args, **kwargs):
        return {"bids": [[102.58, 100]], "asks": [[102.60, 100]]}
'''
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "ccxt.py").write_text(fixture_code, encoding="utf-8")
            c = config()
            c["exchange"]["key"] = "EXCHANGE_SECRET_MUST_NOT_APPEAR"
            c["vn_policy"]["research"]["mode"] = "off"
            (base / "config.json").write_text(json.dumps(c), encoding="utf-8")
            (base / "overlay.json").write_text(json.dumps({"exchange": {"name": "okx"}}))
            env = {**os.environ, "PYTHONPATH": str(base), "PYTHONIOENCODING": "utf-8"}
            proc = subprocess.run([sys.executable, str(ROOT / "freqtrade-bot/user_data/research/run.py"),
                "--config", str(base / "config.json"), "--config", str(base / "overlay.json")],
                env=env, capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads((base / "research/latest.json").read_text(encoding="utf-8"))
            self.assertEqual(report["exchange"], "okx")
            self.assertEqual(len(report["candidates"]), 1)
            self.assertEqual(report["errors"], [])
            self.assertEqual(len(list((base / "research/history").glob("*.json"))), 1)
            self.assertNotIn(c["exchange"]["key"], json.dumps(report) + proc.stdout + proc.stderr)

    def test_worker_cli_invalid_loop_exits_before_importing_ccxt(self):
        proc = subprocess.run([sys.executable, str(ROOT / "freqtrade-bot/user_data/research/run.py"), "--loop", "1"],
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--loop must be >= 60", proc.stderr)


class TransportIntegrationTests(unittest.TestCase):
    def test_provider_transport_serializes_json_and_rejects_oversized_reply(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received.append((self.headers.get("Content-Type"), payload))
                body = b"x" * 1000001 if self.path == "/oversized" else b'{"status":"completed"}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            self.assertEqual(providers.post(base + "/json", {}, {"prompt": "thị trường"}), {"status": "completed"})
            self.assertEqual(received[0], ("application/json", {"prompt": "thị trường"}))
            with self.assertRaises(ValueError):
                providers.post(base + "/oversized", {}, {})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
