"""HEAD support: monitors/crawlers must not see 501, nor trip state changes."""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from app import auth, funnel
from app.server import Handler


class HeadMethod(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QUANTRADAR_MODE", "artifact")
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()

    def _request(self, method: str, path: str) -> tuple[int, dict[str, str], bytes]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path)
            resp = conn.getresponse()
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def test_head_home_matches_get_headers_without_body(self) -> None:
        gcode, gheaders, gbody = self._request("GET", "/")
        hcode, hheaders, hbody = self._request("HEAD", "/")
        self.assertEqual(gcode, 200)
        self.assertEqual(hcode, 200)
        self.assertEqual(hbody, b"")
        self.assertGreater(len(gbody), 0)
        # RFC 9110: HEAD advertises the length the GET body would have had
        self.assertEqual(hheaders.get("Content-Length"), str(len(gbody)))
        self.assertEqual(hheaders.get("Content-Type"), gheaders.get("Content-Type"))

    def test_head_public_surfaces_reachable(self) -> None:
        for path in (
            "/health",
            "/pricing",
            "/methodology",
            "/track",
            "/login",
            "/robots.txt",
            "/sitemap.txt",
            "/r/INTC",
        ):
            with self.subTest(path=path):
                code, _headers, body = self._request("HEAD", path)
                self.assertEqual(code, 200, f"{path} should be reachable via HEAD")
                self.assertEqual(body, b"")

    def test_head_unknown_path_still_404(self) -> None:
        code, _headers, body = self._request("HEAD", "/no-such-page")
        self.assertEqual(code, 404)
        self.assertEqual(body, b"")

    def test_head_rejects_state_changing_auth_routes(self) -> None:
        for path in (
            "/api/auth/logout",
            "/api/auth/dev-login",
            "/api/auth/magic/consume",
            "/api/auth/google/callback",
        ):
            with self.subTest(path=path):
                code, headers, body = self._request("HEAD", path)
                self.assertEqual(code, 405, f"{path} must not run via HEAD")
                self.assertEqual(headers.get("Allow"), "GET")
                self.assertEqual(body, b"")

    def test_head_does_not_burn_magic_link(self) -> None:
        issued = auth.issue_magic_link("head-probe@example.com")
        login_url = issued.get("login_url")
        self.assertTrue(login_url, "console delivery should echo the login URL")
        token = str(login_url).split("token=")[-1]

        code, _headers, _body = self._request(
            "HEAD", f"/api/auth/magic/consume?token={token}"
        )
        self.assertEqual(code, 405)

        # The one-time token must still be usable by the human who got the email
        profile = auth.consume_magic_token(token)
        self.assertEqual(profile["email"], "head-probe@example.com")

    def test_head_does_not_write_funnel_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            probe_log = Path(tmp) / "funnel.jsonl"
            original = funnel.FUNNEL_PATH
            funnel.FUNNEL_PATH = probe_log
            try:
                head_code, _h, head_body = self._request("HEAD", "/api/sample?ticker=INTC")
                self.assertEqual(head_code, 200)
                self.assertEqual(head_body, b"")
                self.assertFalse(
                    probe_log.exists() and probe_log.read_text().strip(),
                    "HEAD probe must not count as a demo_run",
                )

                get_code, _h2, _b2 = self._request("GET", "/api/sample?ticker=INTC")
                self.assertEqual(get_code, 200)
                self.assertIn("demo_run", probe_log.read_text())
            finally:
                funnel.FUNNEL_PATH = original


if __name__ == "__main__":
    unittest.main()
