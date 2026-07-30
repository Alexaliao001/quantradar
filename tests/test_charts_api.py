"""QD2-0: chart image serving by basename."""

from __future__ import annotations

import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.charts_facade import resolve_chart_asset  # noqa: E402
from app.server import Handler  # noqa: E402


class ResolveChartTests(unittest.TestCase):
    def test_fixture_daily_price(self) -> None:
        name = "INTC_daily_price_2026-03-21_01-43-21.png"
        path = resolve_chart_asset(name)
        self.assertIsNotNone(path)
        assert path is not None
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, name)

    def test_path_traversal_rejected(self) -> None:
        self.assertIsNone(resolve_chart_asset("../etc/passwd"))
        self.assertIsNone(resolve_chart_asset("foo/bar.png"))
        self.assertIsNone(resolve_chart_asset("not-an-image.txt"))


class ChartsHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def test_serves_png(self) -> None:
        name = "INTC_daily_price_2026-03-21_01-43-21.png"
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/charts/{name}", timeout=5
        ) as r:
            self.assertEqual(r.status, 200)
            ctype = r.headers.get("Content-Type", "")
            self.assertIn("image/png", ctype)
            body = r.read()
            self.assertGreater(len(body), 1000)
            self.assertTrue(body.startswith(b"\x89PNG"))

    def test_missing_404(self) -> None:
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/api/charts/no_such_chart.png",
                timeout=5,
            )
            self.fail("expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()
