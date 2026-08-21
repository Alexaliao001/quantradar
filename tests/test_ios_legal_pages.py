"""iOS-specific legal pages (no OAuth/Stripe copy)."""

from __future__ import annotations

import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from app.server import Handler

REPO = Path(__file__).resolve().parent.parent


class IosLegalFiles(unittest.TestCase):
    def test_files_exist_and_are_ios_specific(self) -> None:
        privacy = (REPO / "static" / "privacy-ios.html").read_text(encoding="utf-8")
        terms = (REPO / "static" / "terms-ios.html").read_text(encoding="utf-8")
        self.assertIn("We do not collect personal data from the iOS app", privacy)
        self.assertIn("weekday morning reminder", privacy)
        self.assertNotIn("Google OAuth", privacy)
        self.assertNotIn("Stripe", privacy)
        self.assertIn("not a broker", terms.lower())
        self.assertIn("In-App Purchase", terms)


class IosLegalHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return r.status, r.read().decode("utf-8")

    def test_privacy_and_terms_ios_routes(self) -> None:
        code, body = self._get("/privacy-ios")
        self.assertEqual(code, 200)
        self.assertIn("iOS app", body)
        code, body = self._get("/terms-ios")
        self.assertEqual(code, 200)
        self.assertIn("Educational only", body)
        code, sitemap = self._get("/sitemap.txt")
        self.assertEqual(code, 200)
        self.assertIn("/privacy-ios", sitemap)
        self.assertIn("/terms-ios", sitemap)
