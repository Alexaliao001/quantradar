import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from app import charts_facade as facade
from app.public_surface import harden_public_analyze
from app.server import Handler, check_rate_limit, _RATE_HITS


class ScanRuntimeTests(unittest.TestCase):
    def setUp(self):
        facade._SCAN_CACHE.clear()
        _RATE_HITS.clear()

    def test_two_engine_slots_allow_shared_requests_and_reject_new_work(self):
        started = {ticker: threading.Event() for ticker in ("AAPL", "MSFT")}
        release = threading.Event()
        calls = []
        def engine(ticker, sector, timeout):
            calls.append(ticker)
            started[ticker].set()
            release.wait(timeout=5)
            return {"ticker": ticker, "rows": [1]}
        with mock.patch.object(facade, "_run_fetch_all", side_effect=engine), ThreadPoolExecutor(max_workers=6) as pool:
            first = pool.submit(facade.run_fetch_all, "AAPL")
            second = pool.submit(facade.run_fetch_all, "MSFT")
            try:
                self.assertTrue(started["AAPL"].wait(timeout=2))
                self.assertTrue(started["MSFT"].wait(timeout=2))
                copies = [pool.submit(facade.run_fetch_all, "AAPL") for _ in range(3)]
                with self.assertRaisesRegex(RuntimeError, "capacity"):
                    facade.run_fetch_all("NVDA")
            finally:
                release.set()
            a, b = first.result(), second.result()
            for future in copies:
                self.assertEqual(future.result(), a)
            a["rows"].append(2)
            self.assertEqual(facade.run_fetch_all("AAPL")["rows"], [1])
        self.assertCountEqual(calls, ["AAPL", "MSFT"])

    def test_cache_expiry_session_switch_and_failure_release(self):
        with mock.patch("free_engine.market_calendar.completed_session", return_value="2026-09-04") as session, mock.patch.object(facade.time, "monotonic", return_value=100) as clock, mock.patch.object(facade, "_run_fetch_all", return_value={"ok": True}) as engine:
            facade.run_fetch_all("AAPL")
            clock.return_value = 159
            facade.run_fetch_all("AAPL")
            self.assertEqual(engine.call_count, 1)
            clock.return_value = 160
            facade.run_fetch_all("AAPL")
            session.return_value = "2026-09-08"
            facade.run_fetch_all("AAPL")
            self.assertEqual(engine.call_count, 3)
            engine.side_effect = RuntimeError("upstream unavailable")
            with self.assertRaisesRegex(RuntimeError, "upstream"):
                facade.run_fetch_all("MSFT")
            engine.side_effect = None
            self.assertTrue(facade.run_fetch_all("MSFT")["ok"])

    def test_replay_restricts_again_when_audience_changes(self):
        raw = {"meta": {"mode": "live"}, "_replay": [{"date": str(i), "close": i, "score": 50} for i in range(100)]}
        pro = harden_public_analyze(raw, user={"plan": "pro"})
        self.assertEqual(len(pro["engagement_replay"]["rows"]), 90)
        free = harden_public_analyze(pro)
        self.assertEqual(len(free["engagement_replay"]["rows"]), 5)
        self.assertFalse(free["engagement_replay"]["unlocked"])
        self.assertNotIn("_replay", free)
        self.assertEqual(len(raw["_replay"]), 100)

    def test_paid_scan_limit_exceeds_free_but_untrusted_plan_does_not(self):
        with mock.patch.dict(os.environ, {"QUANTRADAR_RATE_LIMIT": "1", "QUANTRADAR_RATE_LIMIT_AUTH": "2", "QUANTRADAR_RATE_LIMIT_PRO": "3"}):
            self.assertTrue(check_rate_limit("owner", authenticated=True))
            self.assertTrue(check_rate_limit("owner", authenticated=True))
            self.assertFalse(check_rate_limit("owner", authenticated=True, plan="unknown"))
            self.assertTrue(check_rate_limit("owner", authenticated=True, plan="portfolio_pro"))
            self.assertFalse(check_rate_limit("owner", authenticated=True, plan="pro"))

    def test_only_loopback_proxy_can_supply_client_ip(self):
        handler = object.__new__(Handler)
        handler.headers = {"X-Forwarded-For": "198.51.100.1, 203.0.113.2"}
        handler.client_address = ("198.51.100.3", 1234)
        self.assertEqual(handler._client_id(), "198.51.100.3")
        handler.client_address = ("127.0.0.1", 1234)
        self.assertEqual(handler._client_id(), "203.0.113.2")
