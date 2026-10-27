import base64
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class MockApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "freqtrade-bot/mock_api_server.py"
        spec = importlib.util.spec_from_file_location("mock_api", path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.server = HTTPServer(("127.0.0.1", 0), cls.module.FreqtradeMockHandler)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_login_read_and_stopbuy_over_http(self):
        auth = base64.b64encode(b"admin:mat_khau_manh_cua_ban").decode()
        req = Request(self.url + "/api/v1/token/login", data=b"", headers={"Authorization": "Basic " + auth})
        with urlopen(req, timeout=3) as response:
            token = json.load(response)["access_token"]
        headers = {"Authorization": "Bearer " + token}
        with urlopen(Request(self.url + "/api/v1/status", headers=headers), timeout=3) as response:
            self.assertIsInstance(json.load(response), list)
        with urlopen(Request(self.url + "/api/v1/stopbuy", data=b"", headers=headers), timeout=3) as response:
            self.assertEqual(response.status, 200)
        self.assertTrue(self.module.BOT_STATE["stopbuy_active"])
        with urlopen(Request(self.url + "/api/v1/vn_research", headers=headers), timeout=3) as response:
            report = json.load(response)
        self.assertEqual(report["schema_version"], 1)
        self.assertIn("schedule_enabled", report)

    def test_forged_bearer_rejected(self):
        req = Request(self.url + "/api/v1/status", headers={"Authorization": "Bearer forged-token-long-enough"})
        with self.assertRaises(HTTPError) as error:
            urlopen(req, timeout=3)
        self.assertEqual(error.exception.code, 401)

    def test_dashboard_is_served(self):
        with urlopen(self.url + "/dashboard", timeout=3) as response:
            self.assertIn(b"researchFile", response.read())
