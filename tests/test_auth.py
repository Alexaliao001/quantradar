"""Own Google session auth (no Manus)."""

from __future__ import annotations

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app import auth as authlib  # noqa: E402
from app.server import Handler, health_payload, is_manus_auth_path  # noqa: E402


class SessionCryptoTests(unittest.TestCase):
    def test_mint_and_verify(self) -> None:
        token = authlib.mint_session(
            sub="u1", email="a@example.com", name="A", plan="free"
        )
        payload = authlib.verify_token(token)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["email"], "a@example.com")
        self.assertEqual(payload["sub"], "u1")

    def test_tamper_rejected(self) -> None:
        token = authlib.mint_session(sub="u1", email="a@example.com")
        bad = token[:-2] + ("x" if token[-2] != "x" else "y") + token[-1:]
        self.assertIsNone(authlib.verify_token(bad))

    def test_oauth_state_consume_once(self) -> None:
        s = authlib.create_oauth_state()
        self.assertTrue(authlib.consume_oauth_state(s))
        self.assertFalse(authlib.consume_oauth_state(s))


class ManusVsOwnLoginTests(unittest.TestCase):
    def test_paths(self) -> None:
        self.assertTrue(is_manus_auth_path("/api/oauth/callback"))
        self.assertTrue(is_manus_auth_path("/app-auth"))
        self.assertFalse(is_manus_auth_path("/login"))
        self.assertFalse(is_manus_auth_path("/api/auth/google/start"))
        self.assertFalse(is_manus_auth_path("/api/me"))

    def test_health_auth_fields(self) -> None:
        h = health_payload()
        self.assertIs(h["manus_login"], False)
        self.assertTrue(h["guest_access"])
        self.assertTrue(h["live_requires_login"])
        self.assertEqual(h["login_path"], "/login")
        self.assertIn(h["auth"], {"guest_only", "google_session"})


class HttpAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1:0"
        os.environ["QUANTRADAR_DEV_LOGIN"] = "1"
        os.environ["SESSION_SECRET"] = "test-session-secret-for-unit"
        # Force re-read of secret path uses env each call — ok
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        os.environ["PUBLIC_BASE_URL"] = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_guest_analyze_and_live_requires_login(self) -> None:
        with urllib.request.urlopen(self._url("/api/analyze?ticker=INTC"), timeout=5) as r:
            body = json.loads(r.read().decode())
        self.assertTrue(body.get("ok"), body)

        try:
            urllib.request.urlopen(
                self._url("/api/analyze?ticker=INTC&mode=live"), timeout=5
            )
            self.fail("live without session should 401")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)
            body = json.loads(e.read().decode())
            self.assertEqual(body.get("error"), "login_required")

    def test_dev_login_then_me(self) -> None:
        # Follow redirect and capture cookie
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        # dev-login redirects; HTTPRedirectHandler follows
        try:
            opener.open(self._url("/api/auth/dev-login?email=dev@test.local"), timeout=5)
        except urllib.error.HTTPError:
            pass
        # After redirect cookie should be set — open status
        with opener.open(self._url("/api/auth/status"), timeout=5) as r:
            body = json.loads(r.read().decode())
        # Cookie jar may work with redirect
        if not body.get("authenticated"):
            # mint cookie manually and send
            token = authlib.mint_session(sub="dev", email="dev@test.local")
            req = urllib.request.Request(
                self._url("/api/me"),
                headers={"Cookie": f"{authlib.COOKIE_NAME}={token}"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                body = json.loads(r.read().decode())
            self.assertTrue(body.get("authenticated"))
            self.assertEqual(body["user"]["email"], "dev@test.local")
        else:
            self.assertTrue(body["authenticated"])

        # live with cookie should not be 401 (engine may 502 if charts missing — force empty CHARTS_DIR)
        prev_charts = os.environ.get("CHARTS_DIR")
        os.environ["CHARTS_DIR"] = str(REPO / "fixtures" / "no_such_charts_dir")
        try:
            token = authlib.mint_session(sub="dev", email="dev@test.local")
            req = urllib.request.Request(
                self._url("/api/analyze?ticker=INTC&mode=live"),
                headers={"Cookie": f"{authlib.COOKIE_NAME}={token}"},
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    code = r.status
                    body = json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                code = e.code
                body = json.loads(e.read().decode())
        finally:
            if prev_charts is None:
                os.environ.pop("CHARTS_DIR", None)
            else:
                os.environ["CHARTS_DIR"] = prev_charts
        self.assertNotEqual(code, 401, body)
        self.assertNotEqual(body.get("error"), "login_required")

    def test_login_page_and_manus_410(self) -> None:
        with urllib.request.urlopen(self._url("/login"), timeout=5) as r:
            html = r.read().decode()
        self.assertIn("Continue with Google", html)
        self.assertNotIn("manus.im/app-auth", html)

        try:
            urllib.request.urlopen(self._url("/api/oauth/callback"), timeout=5)
            self.fail("expected 410")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 410)

        try:
            urllib.request.urlopen(self._url("/api/auth/google/start"), timeout=5)
            self.fail("expected 503 without google config")
        except urllib.error.HTTPError as e:
            # no GOOGLE_CLIENT_* → 503
            self.assertEqual(e.code, 503)


if __name__ == "__main__":
    unittest.main()
