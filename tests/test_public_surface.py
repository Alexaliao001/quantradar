"""Public surface hardening + track notes (clone-defense, Trust Gate honest)."""

from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from app.charts_facade import analyze
from app.contract import _public_path
from app.public_surface import harden_public_analyze, is_pro_live_audience
from app.server import Handler, health_payload
from app.track_record import load_track_record


class PublicPath(unittest.TestCase):
    def test_basename_only(self) -> None:
        self.assertEqual(_public_path("/Users/me/charts/foo.png"), "foo.png")
        self.assertEqual(
            _public_path("/opt/render/project/src/fixtures/x.json"),
            "x.json",
        )
        self.assertIsNone(_public_path(None))


class HardenSurface(unittest.TestCase):
    def test_desk_strips_analysis_json_and_volume_raw(self) -> None:
        raw = analyze("INTC", mode="artifact")
        self.assertTrue(raw["ok"], raw)
        # Internal map may still carry volume avg fields before harden
        hard = harden_public_analyze(raw, user=None)
        self.assertIsNone(hard["artifacts"]["analysis_json"])
        self.assertEqual(hard["meta"].get("public_surface"), "desk")
        vol = hard["data_quality"]["volume"]
        self.assertNotIn("avg_volume_20", vol)
        self.assertNotIn("current_volume", vol)
        self.assertIn("volume_zero_flag", vol)
        self.assertTrue(hard["engagement"].get("freeze_label"))
        self.assertIsNotNone(hard["score"].get("final"))

    def test_pro_live_keeps_fuller_volume(self) -> None:
        raw = analyze("INTC", mode="artifact")
        # Force pro+live meta for audience check only
        raw = dict(raw)
        raw["meta"] = {**(raw.get("meta") or {}), "mode": "live"}
        user = {"email": "pro@example.com", "plan": "pro"}
        self.assertTrue(is_pro_live_audience(user, raw))
        hard = harden_public_analyze(raw, user=user)
        self.assertEqual(hard["meta"].get("public_surface"), "pro_live")
        self.assertIn("avg_volume_20", hard["data_quality"]["volume"])


class HealthRedaction(unittest.TestCase):
    def test_charts_dir_null(self) -> None:
        h = health_payload()
        self.assertIsNone(h.get("charts_dir"))
        self.assertIn("charts_dir_configured", h)


class TrackRecord(unittest.TestCase):
    def test_load_has_disclaimer_no_fake_stats(self) -> None:
        t = load_track_record()
        self.assertTrue(t.get("ok"))
        self.assertTrue(t.get("disclaimer"))
        self.assertIsNone(t.get("stats"))
        self.assertIsInstance(t.get("entries"), list)


class HttpSurface(unittest.TestCase):
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

    def _get(self, path: str) -> tuple[int, dict | str]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=8) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "")
            if "json" in ctype:
                return r.status, json.loads(body.decode("utf-8"))
            return r.status, body.decode("utf-8", errors="replace")

    def test_sample_hardened(self) -> None:
        code, body = self._get("/api/sample?ticker=INTC")
        self.assertEqual(code, 200)
        assert isinstance(body, dict)
        self.assertIsNone(body["artifacts"]["analysis_json"])
        self.assertEqual(body["meta"].get("public_surface"), "desk")
        self.assertNotIn("avg_volume_20", body["data_quality"].get("volume") or {})

    def test_track_api_and_page(self) -> None:
        code, body = self._get("/api/track")
        self.assertEqual(code, 200)
        assert isinstance(body, dict)
        self.assertIsNone(body.get("stats"))
        code2, html = self._get("/track")
        self.assertEqual(code2, 200)
        self.assertIn("track", html.lower())

    def test_robots_disallow_api(self) -> None:
        code, body = self._get("/robots.txt")
        self.assertEqual(code, 200)
        self.assertIn("Disallow: /api/", body)
        self.assertIn("Disallow: /btn-demos", body)


if __name__ == "__main__":
    unittest.main()
