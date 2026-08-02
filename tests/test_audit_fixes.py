"""Regression tests for the 2026-08-02 security / honesty audit fixes."""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


class SessionSecretFailClosed(unittest.TestCase):
    def test_public_host_refuses_missing_secret(self) -> None:
        import app.auth as auth

        prev = {
            k: os.environ.get(k)
            for k in (
                "SESSION_SECRET",
                "_QUANTRADAR_DEV_SESSION_SECRET",
                "PUBLIC_BASE_URL",
                "RENDER",
                "RENDER_SERVICE_ID",
                "FLY_APP_NAME",
            )
        }
        try:
            for k in prev:
                os.environ.pop(k, None)
            auth._DEV_SESSION_SECRET = None  # type: ignore[attr-defined]
            os.environ["PUBLIC_BASE_URL"] = "https://quantradar.one"
            with self.assertRaises(RuntimeError):
                auth.session_secret()
        finally:
            auth._DEV_SESSION_SECRET = None  # type: ignore[attr-defined]
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_local_fallback_is_not_public_constant(self) -> None:
        import app.auth as auth

        prev = {
            k: os.environ.get(k)
            for k in (
                "SESSION_SECRET",
                "_QUANTRADAR_DEV_SESSION_SECRET",
                "PUBLIC_BASE_URL",
                "RENDER",
                "RENDER_SERVICE_ID",
                "FLY_APP_NAME",
            )
        }
        try:
            for k in prev:
                os.environ.pop(k, None)
            auth._DEV_SESSION_SECRET = None  # type: ignore[attr-defined]
            os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1:8765"
            secret = auth.session_secret()
            self.assertNotEqual(secret, "dev-insecure-session-secret")
            self.assertGreaterEqual(len(secret), 16)
        finally:
            auth._DEV_SESSION_SECRET = None  # type: ignore[attr-defined]
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class BootstrapDemoOptIn(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        import app.users as users

        self.users = users
        self._orig = users.USERS_PATH
        users.USERS_PATH = Path(self._td.name) / "users.json"
        self._env = {
            k: os.environ.get(k)
            for k in (
                "QUANTRADAR_BOOTSTRAP_DEMO",
                "QUANTRADAR_ADMIN_EMAIL",
                "QUANTRADAR_ADMIN_PASSWORD",
                "PUBLIC_BASE_URL",
                "RENDER",
            )
        }

    def tearDown(self) -> None:
        self.users.USERS_PATH = self._orig
        self._td.cleanup()
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_default_off_creates_nothing(self) -> None:
        os.environ.pop("QUANTRADAR_BOOTSTRAP_DEMO", None)
        os.environ.pop("QUANTRADAR_ADMIN_EMAIL", None)
        os.environ.pop("QUANTRADAR_ADMIN_PASSWORD", None)
        os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1:9"
        self.assertIsNone(self.users.ensure_bootstrap_admin())
        self.assertIsNone(self.users.get_user("admin@local.test"))

    def test_public_host_blocks_demo_even_when_enabled(self) -> None:
        os.environ["QUANTRADAR_BOOTSTRAP_DEMO"] = "1"
        os.environ["PUBLIC_BASE_URL"] = "https://quantradar.one"
        self.assertIsNone(self.users.ensure_bootstrap_admin())
        self.assertIsNone(self.users.get_user("admin@local.test"))


class PlanStoreSSOT(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        import app.users as users

        self.users = users
        self._orig = users.USERS_PATH
        users.USERS_PATH = Path(self._td.name) / "users.json"

    def tearDown(self) -> None:
        self.users.USERS_PATH = self._orig
        self._td.cleanup()

    def test_cookie_pro_without_store_row_is_free(self) -> None:
        self.assertEqual(
            self.users.resolve_plan("ghost@example.com", session_plan="pro"),
            "free",
        )

    def test_store_pro_wins(self) -> None:
        self.users.set_plan("paid@example.com", "pro")
        self.assertEqual(
            self.users.resolve_plan("paid@example.com", session_plan="free"),
            "pro",
        )


class ScoreHonesty(unittest.TestCase):
    def test_missing_score_withheld_not_zero(self) -> None:
        from app.contract import map_charts_payload

        payload = {
            "ticker": "TSLA",
            "mechanical_scores": {
                "signal_mechanical": "BUILD",
                "final_score": None,
                "base_score": {"total": 40},
                "state": {"code": 3, "name": "Uptrend", "reason": "trend intact"},
            },
            "data_quality": {"reliability": "high", "timeframes_ok": 3},
            "volumeAnalysis": {"avgVolume20": 1000, "currentVolume": 1200},
            "market_env": {"spy_change_pct": 0.4, "market_state": "open"},
        }
        mapped = map_charts_payload(payload, mode="live")
        self.assertTrue(mapped["score"]["withheld"])
        self.assertIsNone(mapped["score"]["final"])
        self.assertIn("withheld", mapped["summary"])

    def test_nan_and_out_of_range_withheld(self) -> None:
        from app.contract import map_charts_payload

        for bad in (float("nan"), 1e9, -50, True, "nope"):
            payload = {
                "ticker": "MSFT",
                "mechanical_scores": {
                    "signal_mechanical": "WAIT",
                    "final_score": bad,
                    "base_score": {"total": 10},
                    "state": {"code": 1, "name": "x", "reason": "y"},
                },
                "data_quality": {"reliability": "high", "timeframes_ok": 3},
                "volumeAnalysis": {"avgVolume20": 100, "currentVolume": 100},
                "market_env": {"spy_change_pct": 0.1},
            }
            mapped = map_charts_payload(payload, mode="live")
            self.assertTrue(mapped["score"]["withheld"], bad)
            self.assertIsNone(mapped["score"]["final"], bad)
            # Must serialize as strict JSON (no bare NaN)
            raw = json.dumps(mapped, allow_nan=False)
            self.assertNotIn("NaN", raw)

    def test_market_gate_not_pass_from_presence(self) -> None:
        from app.contract import map_charts_payload

        payload = {
            "ticker": "NVDA",
            "mechanical_scores": {
                "signal_mechanical": "FULL",
                "final_score": 88,
                "base_score": {"total": 70},
                "state": {"code": 5, "name": "Strong", "reason": "all clear"},
            },
            "data_quality": {"reliability": "high", "timeframes_ok": 3},
            "volumeAnalysis": {"avgVolume20": 1000, "currentVolume": 3000},
            "market_env": {
                "spy_change_pct": -6.5,
                "market_state": "open",
                "sector_etf": "XLK",
                "sector_change_pct": -8.1,
            },
        }
        mapped = map_charts_payload(payload, mode="live")
        self.assertEqual(mapped["gate"]["market_gate"]["status"], "unknown")
        self.assertEqual(mapped["gate"]["sector_gate"]["status"], "unknown")


class AuthRateLimits(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        import app.server as server_mod
        import app.users as users
        from app.server import Handler

        self._server_mod = server_mod
        self._orig = users.USERS_PATH
        users.USERS_PATH = Path(self._td.name) / "users.json"
        self._env = {
            k: os.environ.get(k)
            for k in (
                "QUANTRADAR_BOOTSTRAP_DEMO",
                "SESSION_SECRET",
                "PUBLIC_BASE_URL",
                "QUANTRADAR_RATE_LIMIT",
                "QUANTRADAR_RATE_WINDOW_SEC",
            )
        }
        os.environ["QUANTRADAR_BOOTSTRAP_DEMO"] = "0"
        os.environ["SESSION_SECRET"] = "audit-fix-test-secret"
        os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1:0"
        os.environ["QUANTRADAR_RATE_LIMIT"] = "3"
        os.environ["QUANTRADAR_RATE_WINDOW_SEC"] = "60"
        with server_mod._RATE_LOCK:
            server_mod._RATE_HITS.clear()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        os.environ["PUBLIC_BASE_URL"] = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        import app.users as users

        with self._server_mod._RATE_LOCK:
            self._server_mod._RATE_HITS.clear()
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        users.USERS_PATH = self._orig
        self._td.cleanup()

    def test_login_rate_limited(self) -> None:
        codes = []
        for _ in range(6):
            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/auth/login",
                data=json.dumps(
                    {"email": "nobody@example.com", "password": "wrongpass99"}
                ).encode(),
                headers={"content-type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    codes.append(r.status)
            except urllib.error.HTTPError as e:
                codes.append(e.code)
        self.assertIn(429, codes)


class StripeCustomerLookup(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        import app.users as users

        self.users = users
        self._orig = users.USERS_PATH
        users.USERS_PATH = Path(self._td.name) / "users.json"

    def tearDown(self) -> None:
        self.users.USERS_PATH = self._orig
        self._td.cleanup()

    def test_downgrade_via_customer_id(self) -> None:
        from app import stripe_billing

        self.users.set_plan("cust@test.local", "pro", stripe_customer_id="cus_abc")
        out = stripe_billing.apply_webhook_event(
            {
                "type": "customer.subscription.deleted",
                "data": {"object": {"customer": "cus_abc", "metadata": {}}},
            }
        )
        self.assertTrue(out.get("ok"), out)
        self.assertEqual(out.get("action"), "plan_free")
        self.assertEqual(self.users.resolve_plan("cust@test.local"), "free")


if __name__ == "__main__":
    unittest.main()
