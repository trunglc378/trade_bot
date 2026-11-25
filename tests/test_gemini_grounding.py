import json
import unittest
from unittest.mock import patch
from pathlib import Path

from test_research import providers, research, config, Exchange, NOW


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.options = {"model": "gemini-pro-latest", "google_search": True,
                        "source_domains": ["binance.com", "reuters.com"], "min_source_domains": 2}
        self.rows = [{"pair": "BTC/USDT", "action": "consider", "confidence": .9, "reason": "Có bằng chứng",
                      "sources": [{"url": "https://binance.com/announcement/1", "title": "Exchange update"},
                                  {"url": "https://reuters.com/markets/1", "title": "Market report"}]}]

    def response(self, rows=None, native=None):
        rows = self.rows if rows is None else rows
        native = [s["url"] for s in self.rows[0]["sources"]] if native is None else native
        return {"status": "completed", "steps": [{"type": "model_output", "content": [{
            "type": "text", "text": json.dumps({"recommendations": rows}),
            "annotations": [{"type": "url_citation", "url": u} for u in native]}]}]}

    def call(self, result):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}), patch.object(providers, "post", return_value=result) as post:
            votes = providers.advise("gemini", self.options, [{"pair": "BTC/USDT"}])
        return votes["BTC/USDT"], post.call_args.args[2]

    def test_grounding_request_and_native_evidence(self):
        vote, payload = self.call(self.response())
        self.assertEqual(vote["action"], "consider")
        self.assertEqual(len(vote["sources"]), 2)
        self.assertEqual(payload["tools"], [{"type": "google_search"}])
        self.assertIn("sources", payload["response_format"]["schema"]["properties"]["recommendations"]["items"]["required"])

    def test_model_urls_without_native_citations_do_not_count(self):
        vote, _ = self.call(self.response(native=[]))
        self.assertEqual(vote["action"], "wait")
        self.assertEqual(vote["sources"], [])

    def test_two_subdomains_count_as_one_configured_source(self):
        rows = [{**self.rows[0], "sources": [{"url": "https://a.binance.com/1", "title": "A"},
                                            {"url": "https://b.binance.com/2", "title": "B"}]}]
        vote, _ = self.call(self.response(rows, [s["url"] for s in rows[0]["sources"]]))
        self.assertEqual(vote["action"], "wait")

    def test_untrusted_and_unsafe_urls_are_excluded(self):
        for bad in ("https://binance.com.evil.example/1", "http://binance.com/1",
                    "https://user@reuters.com/1", "javascript:alert(1)"):
            rows = [{**self.rows[0], "sources": [self.rows[0]["sources"][0], {"url": bad, "title": "Untrusted"}]}]
            vote, _ = self.call(self.response(rows, [rows[0]["sources"][0]["url"], bad]))
            self.assertEqual(vote["action"], "wait")

    def test_avoid_remains_a_veto_without_enough_sources(self):
        rows = [{**self.rows[0], "action": "avoid"}]
        vote, _ = self.call(self.response(rows, []))
        self.assertEqual(vote["action"], "avoid")

    def test_options_reject_misconfiguration(self):
        for options in ({**self.options, "google_search": "yes"}, {**self.options, "min_source_domains": 1},
                        {**self.options, "source_domains": ["binance.com", "news.binance.com"]}):
            with self.assertRaises(ValueError):
                providers.provider_options("gemini", options)
        with self.assertRaises(ValueError):
            providers.provider_options("openai", self.options)

    def test_gemini_only_overlay_and_worker(self):
        c = config()
        overlay = Path(__file__).resolve().parents[1] / "freqtrade-bot/user_data/config-gemini-research.json"
        research.merge(c, json.loads(overlay.read_text(encoding="utf-8")))
        c["vn_policy"]["research"]["mode"] = "required"
        def advisor(provider, specification, candidates):
            self.assertEqual(provider, "gemini")
            self.assertEqual(specification["model"], "gemini-pro-latest")
            return {"BTC/USDT": {"action": "consider", "confidence": .9, "reason": "test"}}
        report = research.build_report(c, Exchange(), NOW, advisor)
        self.assertTrue(report["candidates"][0]["eligible"])
        self.assertEqual(len(report["candidates"][0]["ai_votes"]), 1)


if __name__ == "__main__":
    unittest.main()
