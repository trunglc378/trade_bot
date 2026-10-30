"""Deployment initialization must preserve configured credentials and trading state."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "deployment_setup_accounts", Path(__file__).resolve().parents[1] / "freqtrade-bot/setup_accounts.py")
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class InitializationTests(unittest.TestCase):
    def test_repeated_initialization_preserves_existing_files_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "user_data"
            data.mkdir()
            originals = {
                data / "config.private.binance.json": b'{"dry_run": false, "exchange": {"key": "keep"}}\n',
                data / "config.private.okx.json": b'{"available_capital": 42}\n',
                root / ".env": b'BINANCE_DB_FILE=tradesv3.binance.live.sqlite\n',
            }
            for path, content in originals.items():
                path.write_bytes(content)
            with patch.object(setup, "BOT_DIR", root), patch.object(setup, "USER_DATA_DIR", data), \
                    patch("sys.argv", ["setup_accounts.py", "--init-defaults"]):
                self.assertEqual(setup.main(), 0)
            for path, content in originals.items():
                self.assertEqual(path.read_bytes(), content)

    def test_missing_files_created_without_replacing_existing_exchange(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "user_data"
            data.mkdir()
            existing = data / "config.private.binance.json"
            existing.write_text('{"keep": true}', encoding="utf-8")
            with patch.object(setup, "BOT_DIR", root), patch.object(setup, "USER_DATA_DIR", data), \
                    patch("sys.argv", ["setup_accounts.py", "--init-defaults"]):
                self.assertEqual(setup.main(), 0)
            self.assertEqual(json.loads(existing.read_text()), {"keep": True})
            created = json.loads((data / "config.private.okx.json").read_text(encoding="utf-8"))
            self.assertTrue(created["dry_run"])
            self.assertFalse(created["exchange"]["key"])
            self.assertGreaterEqual(len(created["api_server"]["password"]), 24)
            self.assertNotEqual(created["api_server"]["password"], "mat_khau_manh_cua_ban")
            self.assertIn("dryrun.sqlite", (root / ".env").read_text(encoding="utf-8"))
