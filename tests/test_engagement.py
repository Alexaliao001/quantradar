"""Engagement layer: watchlist caps, real avoidance ledger, digest opt-in.

All avoidance math is tested against hand-computed numbers — no invented events.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app import engagement  # noqa: E402
from app.server import Handler  # noqa: E402


class AvoidanceLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        d = Path(self._td.name)
        self._orig_ledger = engagement.LEDGER_PATH
        self._orig_cache = engagement.PRICE_CACHE_PATH
        engagement.LEDGER_PATH = d / "ledger.json"
        engagement.PRICE_CACHE_PATH = d / "price_cache.json"

    def tearDown(self) -> None:
        engagement.LEDGER_PATH = self._orig_ledger
        engagement.PRICE_CACHE_PATH = self._orig_cache
        self._td.cleanup()

    def _seed(self, entries: list[dict], cache: dict) -> None:
        engagement.LEDGER_PATH.write_text(
            json.dumps({"version": 1, "entries": entries}), encoding="utf-8"
        )
        engagement.PRICE_CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")

    def test_no_event_fall_10pct_counts(self) -> None:
        self._seed(
            [
                {"ticker": "XYZ", "ts": time.time() - 86400, "action": "NO", "close": 100.0, "email": None},
            ],
            {"XYZ": {"ts": time.time(), "close": 90.0}},
        )
        events = engagement.avoidance_events(None)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["ticker"], "XYZ")
        self.assertEqual(events[0]["drop_pct"], 10.0)

    def test_put_action_counts(self) -> None:
        self._seed(
            [{"ticker": "ABC", "ts": time.time() - 100, "action": "PUT", "close": 50.0, "email": None}],
            {"ABC": {"ts": time.time(), "close": 46.0}},
        )
        events = engagement.avoidance_events(None)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["drop_pct"], 8.0)

    def test_small_fall_below_threshold_excluded(self) -> None:
        self._seed(
            [{"ticker": "XYZ", "ts": time.time() - 100, "action": "NO", "close": 100.0, "email": None}],
            {"XYZ": {"ts": time.time(), "close": 96.0}},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_setup_action_never_counts(self) -> None:
        self._seed(
            [{"ticker": "XYZ", "ts": time.time() - 100, "action": "SETUP", "close": 100.0, "email": None}],
            {"XYZ": {"ts": time.time(), "close": 80.0}},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_stale_cache_excluded(self) -> None:
        self._seed(
            [{"ticker": "XYZ", "ts": time.time() - 100, "action": "NO", "close": 100.0, "email": None}],
            {"XYZ": {"ts": time.time() - 24 * 3600, "close": 90.0}},
        )
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_email_scoping(self) -> None:
        self._seed(
            [
                {"ticker": "AAA", "ts": time.time() - 100, "action": "NO", "close": 10.0, "email": "a@x.com"},
                {"ticker": "BBB", "ts": time.time() - 100, "action": "NO", "close": 10.0, "email": "b@x.com"},
            ],
            {"AAA": {"ts": time.time(), "close": 9.0}, "BBB": {"ts": time.time(), "close": 9.0}},
        )
        self.assertEqual([e["ticker"] for e in engagement.avoidance_events("a@x.com")], ["AAA"])
        self.assertEqual(engagement.avoidance_events(None), [])

    def test_record_scan_background_write(self) -> None:
        orig = engagement._current_close
        engagement._current_close = lambda t: 42.0
        try:
            engagement.record_scan(
                "TESL",
                {"ok": True, "primary": {"action": "NO"}, "ticker": "TESL", "score": {"final": 30}},
                None,
            )
            deadline = time.time() + 5
            while time.time() < deadline:
                if engagement.LEDGER_PATH.is_file():
                    break
                time.sleep(0.05)
            data = json.loads(engagement.LEDGER_PATH.read_text(encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertEqual(data["entries"][0]["close"], 42.0)
        finally:
            engagement._current_close = orig

    def test_record_scan_ignores_failed_results(self) -> None:
        engagement.record_scan("TESL", {"ok": False}, None)
        time.sleep(0.2)
        self.assertFalse(engagement.LEDGER_PATH.is_file())


class HttpEngagementTests(unittest.TestCase):
    def setUp(self) -> None:
        import app.users as users

        self._td = tempfile.TemporaryDirectory()
        self._orig_users = users.USERS_PATH
        users.USERS_PATH = Path(self._td.name) / "users.json"

        d = Path(self._td.name) / "eng"
        d.mkdir()
        self._orig_ledger = engagement.LEDGER_PATH
        self._orig_cache = engagement.PRICE_CACHE_PATH
        self._orig_digest = engagement.DIGEST_DIR
        engagement.LEDGER_PATH = d / "ledger.json"
        engagement.PRICE_CACHE_PATH = d / "price_cache.json"
        engagement.DIGEST_DIR = d / "digest"

        os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1:0"
        os.environ["QUANTRADAR_DEV_LOGIN"] = "1"
        os.environ["SESSION_SECRET"] = "test-session-secret-for-unit"

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        import app.users as users

        users.USERS_PATH = self._orig_users
        engagement.LEDGER_PATH = self._orig_ledger
        engagement.PRICE_CACHE_PATH = self._orig_cache
        engagement.DIGEST_DIR = self._orig_digest
        self._td.cleanup()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _register(self, email: str, password: str = "hunter2secret") -> str:
        req = urllib.request.Request(
            self._url("/api/auth/register"),
            data=json.dumps({"email": email, "password": password}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read().decode())
        self.assertTrue(body.get("ok"), body)
        cookie = None
        for h, v in r.headers.items():
            if h.lower() == "set-cookie" and "qr_session=" in v:
                cookie = v.split(";")[0]
        assert cookie, "session cookie not set on register"
        return cookie

    def _post(self, path: str, payload: dict, cookie: str | None = None):
        req = urllib.request.Request(
            self._url(path),
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **({"Cookie": cookie} if cookie else {})},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def _get(self, path: str, cookie: str | None = None):
        req = urllib.request.Request(self._url(path), headers={"Cookie": cookie} if cookie else {})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def test_watchlist_free_limit_one_then_upgrade_unlocks(self) -> None:
        cookie = self._register("wl@test.local")
        code, body = self._post("/api/watchlist/add", {"ticker": "NVDA"}, cookie)
        self.assertEqual(code, 200, body)
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(body["watchlist"], ["NVDA"])
        self.assertEqual(body["limit"], 1)

        # Second ticker hits the free cap — honest limit message, not a fake gate.
        code, body = self._post("/api/watchlist/add", {"ticker": "AMD"}, cookie)
        self.assertEqual(code, 200, body)
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("error"), "watchlist_limit")
        self.assertIn("Pro", body.get("error_detail", ""))

        # Upgrade to pro in the store (SSOT) → ten slots.
        from app.users import set_plan

        set_plan("wl@test.local", "pro")
        cookie_pro = self._register("wl-pro@test.local")
        from app.users import set_plan as sp

        sp("wl-pro@test.local", "pro")
        code, body = self._post("/api/watchlist/add", {"ticker": "AMD"}, cookie_pro)
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(body["limit"], 10)

    def test_watchlist_requires_login(self) -> None:
        code, body = self._post("/api/watchlist/add", {"ticker": "NVDA"}, None)
        self.assertEqual(code, 401)
        self.assertEqual(body.get("error"), "login_required")

    def test_watchlist_remove(self) -> None:
        cookie = self._register("wl2@test.local")
        self._post("/api/watchlist/add", {"ticker": "MSFT"}, cookie)
        code, body = self._post("/api/watchlist/remove", {"ticker": "MSFT"}, cookie)
        self.assertEqual(code, 200)
        self.assertEqual(body["watchlist"], [])

    def test_auth_status_exposes_watchlist_and_caps(self) -> None:
        cookie = self._register("wl3@test.local")
        self._post("/api/watchlist/add", {"ticker": "AAPL"}, cookie)
        code, body = self._get("/api/auth/status", cookie)
        self.assertEqual(code, 200)
        self.assertTrue(body.get("authenticated"))
        self.assertEqual(body["user"]["watchlist"], ["AAPL"])
        self.assertEqual(body["user"]["watchlist_limit"], 1)
        self.assertFalse(body["user"]["daily_digest"])

    def test_digest_opt_in_honest_note(self) -> None:
        cookie = self._register("dg@test.local")
        code, body = self._post("/api/digest/opt", {"on": True}, cookie)
        self.assertEqual(code, 200, body)
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("on"))
        # No SMTP keys in tests → honest archive note.
        self.assertFalse(body.get("smtp"))
        self.assertIn("not enabled", body.get("note", ""))

    def test_guest_ledger_does_not_count_private_scans(self) -> None:
        engagement.LEDGER_PATH.write_text(
            json.dumps(
                {
                    "version": 1,
                    "entries": [
                        {"ticker": "XYZ", "ts": time.time() - 100, "action": "NO", "close": 100.0, "email": "a@x.com"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        engagement.PRICE_CACHE_PATH.write_text(
            json.dumps({"XYZ": {"ts": time.time(), "close": 90.0}}), encoding="utf-8"
        )
        code, body = self._get("/api/ledger", None)
        self.assertEqual(code, 200)
        self.assertEqual(body.get("avoided"), [])
        self.assertEqual(body.get("avoided_count"), 0)

    def test_today_page_served(self) -> None:
        req = urllib.request.Request(self._url("/today"))
        with urllib.request.urlopen(req, timeout=10) as r:
            self.assertEqual(r.status, 200)
            html = r.read().decode()
        self.assertIn("Today", html)
        self.assertIn("/api/today", html)

    def test_digest_cannot_read_another_accounts_watchlist(self) -> None:
        import types
        from app.users import set_plan

        cookie = self._register("owner@test.local")
        set_plan("owner@test.local", "pro")
        self._register("other@test.local")
        engagement.add_watch("owner@test.local", "MSFT")
        engagement.add_watch("other@test.local", "AAPL")
        engagement.set_digest_optin("other@test.local", True)
        source = types.ModuleType("free_sources")
        source.fetch_all_sources = mock.Mock(return_value=({"test": [("2026-09-04", 100, 1000)] * 60}, {}))
        with mock.patch.dict(sys.modules, {"free_sources": source}):
            code, body = self._post("/api/digest/build", {"email": "other@test.local"}, cookie)
        self.assertEqual(code, 200, body)
        self.assertEqual([u["email"] for u in body["digest"]["users"]], ["owner@test.local"])
        self.assertEqual([i["ticker"] for i in body["digest"]["users"][0]["items"]], ["MSFT"])
        self.assertNotIn("other@test.local", json.dumps(body))
        self.assertNotIn("AAPL", json.dumps(body))
        self.assertFalse(engagement.DIGEST_DIR.exists())

    def test_digest_missing_market_data_is_unknown(self) -> None:
        import types
        from app.users import set_plan

        cookie = self._register("unknown@test.local")
        set_plan("unknown@test.local", "pro")
        source = types.ModuleType("free_sources")
        source.fetch_all_sources = mock.Mock(return_value=({}, {"test": "offline"}))
        with mock.patch.dict(sys.modules, {"free_sources": source}):
            code, body = self._post("/api/digest/build", {}, cookie)
        self.assertEqual(code, 200, body)
        self.assertIsNone(body["digest"]["market"]["gate_open"])


if __name__ == "__main__":
    unittest.main()
