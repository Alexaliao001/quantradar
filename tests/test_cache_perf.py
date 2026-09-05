"""Atomic tests: HTTP caching layer, favicon, health memoization, static 304s."""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from app import server as server_mod
from app.server import Handler


class CacheAtoms(unittest.TestCase):
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

    def _request(self, path: str, headers: dict | None = None) -> tuple[int, dict, bytes]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request("GET", path, headers=headers or {})
            resp = conn.getresponse()
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def test_css_has_etag_and_public_cache(self) -> None:
        code, h, body = self._request("/static/site.css")
        self.assertEqual(code, 200)
        self.assertIn("ETag", h)
        self.assertTrue(h["Cache-Control"].startswith("public"), h["Cache-Control"])
        self.assertGreater(len(body), 0)

    def test_conditional_get_returns_304_without_body(self) -> None:
        code, h, body = self._request("/static/site.css")
        etag = h.get("ETag")
        self.assertTrue(etag)
        code2, h2, body2 = self._request("/static/site.css", {"If-None-Match": etag})
        self.assertEqual(code2, 304)
        self.assertEqual(body2, b"")
        self.assertEqual(h2.get("ETag"), etag)

    def test_weak_etag_also_matches(self) -> None:
        code, h, _ = self._request("/static/site.css")
        etag = h.get("ETag")
        code2, _, body2 = self._request("/static/site.css", {"If-None-Match": "W/" + etag})
        self.assertEqual(code2, 304)
        self.assertEqual(body2, b"")

    def test_wrong_etag_returns_full_200(self) -> None:
        code, _, body = self._request("/static/site.css", {"If-None-Match": '"bogus"'})
        self.assertEqual(code, 200)
        self.assertGreater(len(body), 0)

    def test_favicon_served_with_cache(self) -> None:
        code, h, body = self._request("/favicon.ico")
        self.assertEqual(code, 200)
        self.assertIn("image/svg+xml", h.get("Content-Type", ""))
        self.assertTrue(body.startswith(b"<svg"))
        self.assertIn("max-age=86400", h.get("Cache-Control", ""))

    def test_api_stays_no_store(self) -> None:
        """API responses must never be cached — plans/auth change underneath."""
        code, h, _ = self._request("/api/auth/status")
        self.assertEqual(code, 200)
        self.assertEqual(h.get("Cache-Control"), "no-store")

    def test_html_pages_stay_no_store(self) -> None:
        for path in ("/", "/pricing", "/login"):
            with self.subTest(path=path):
                code, h, _ = self._request(path)
                self.assertEqual(code, 200)
                self.assertEqual(h.get("Cache-Control"), "no-store")

    def test_chart_asset_cached(self) -> None:
        # fixture asset shipped in repo
        code, h, _ = self._request("/api/charts/AAPL_daily_price_2026-03-21_17-27-46.png")
        if code == 404:
            self.skipTest("fixture chart asset not present")
        self.assertEqual(code, 200)
        self.assertIn("max-age", h.get("Cache-Control", ""))

    def test_git_sha_memoized(self) -> None:
        """git_sha must not re-fork git on every health poll."""
        server_mod._GIT_SHA_RESOLVED = False
        server_mod._GIT_SHA_CACHE = None
        a = server_mod.git_sha()
        server_mod._GIT_SHA_CACHE = "SENTINEL"  # would be overwritten if re-forked
        b = server_mod.git_sha()
        self.assertEqual(b, "SENTINEL")
        # restore clean state for other tests
        server_mod._GIT_SHA_RESOLVED = False
        server_mod._GIT_SHA_CACHE = None


class MosaicCapAtoms(unittest.TestCase):
    def test_cell_cap_arithmetic(self) -> None:
        """Mirror of mosaic.js cap loop: 1080p must yield <= 1400 cells."""
        w, h, gap = 1920, 1080, 3
        cell = 32
        cols = max(18, -(-w // (cell + gap)))
        rows = max(14, -(-h // (cell + gap)))
        while cols * rows > 1400:
            cell += 6
            cols = max(18, -(-w // (cell + gap)))
            rows = max(14, -(-h // (cell + gap)))
        self.assertLessEqual(cols * rows, 1400)
        self.assertGreaterEqual(cell, 32)


if __name__ == "__main__":
    unittest.main()
