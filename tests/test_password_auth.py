"""Local email+password auth."""

from __future__ import annotations

import json
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


class PasswordUserStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        import app.users as users

        self.users = users
        self._orig = users.USERS_PATH
        users.USERS_PATH = Path(self._td.name) / "users.json"

    def tearDown(self) -> None:
        self.users.USERS_PATH = self._orig
        self._td.cleanup()

    def test_register_and_login(self) -> None:
        u = self.users.register_user("Me@Example.com", "secretpass99", name="Me")
        self.assertEqual(u["email"], "me@example.com")
        a = self.users.authenticate("me@example.com", "secretpass99")
        self.assertEqual(a["email"], "me@example.com")
        with self.assertRaises(ValueError):
            self.users.authenticate("me@example.com", "wrongpass00")
        with self.assertRaises(ValueError):
            self.users.register_user("me@example.com", "anotherpass")


class PasswordHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        import app.users as users
        from app.server import Handler

        self._orig = users.USERS_PATH
        users.USERS_PATH = Path(self._td.name) / "users.json"
        os.environ["QUANTRADAR_BOOTSTRAP_DEMO"] = "0"
        os.environ["CHARTS_DIR"] = str(Path(self._td.name) / "no_charts")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        import app.users as users

        users.USERS_PATH = self._orig
        self._td.cleanup()

    def _post(self, path: str, body: dict) -> tuple[int, dict, str | None]:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(body).encode(),
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                cookie = r.headers.get("Set-Cookie")
                return r.status, json.loads(r.read().decode()), cookie
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode()), e.headers.get("Set-Cookie")

    def test_register_login_me(self) -> None:
        code, body, cookie = self._post(
            "/api/auth/register",
            {"email": "desk@test.local", "password": "password12", "name": "Desk"},
        )
        self.assertEqual(code, 200, body)
        self.assertTrue(body.get("ok"))
        self.assertIn("qr_session", cookie or "")

        code, body, cookie = self._post(
            "/api/auth/login",
            {"email": "desk@test.local", "password": "password12"},
        )
        self.assertEqual(code, 200, body)
        self.assertTrue(body["authenticated"])
        token = (cookie or "").split("qr_session=")[1].split(";")[0]
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/me",
            headers={"Cookie": f"qr_session={token}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            me = json.loads(r.read().decode())
        self.assertTrue(me.get("authenticated"))
        self.assertEqual(me["user"]["email"], "desk@test.local")

        # live allowed when cookie present (may 502 without charts live)
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/analyze?ticker=INTC&mode=live",
            headers={"Cookie": f"qr_session={token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                code = r.status
                j = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            code = e.code
            j = json.loads(e.read().decode())
        self.assertNotEqual(j.get("error"), "login_required")
        self.assertNotEqual(code, 401)


if __name__ == "__main__":
    unittest.main()
