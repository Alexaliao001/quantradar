"""Trust Gate TG-1…TG-10 smoke for path-C shell."""

from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.charts_facade import analyze  # noqa: E402
from app.server import Handler  # noqa: E402


class TrustGateContractTests(unittest.TestCase):
    def test_single_primary_score(self) -> None:
        r = analyze("INTC", mode="artifact")
        self.assertTrue(r.get("ok"), r)
        self.assertIn("primary_score", r)
        self.assertEqual(r["primary_score"]["value"], r["score"]["final"])
        self.assertIn("primary", r)
        self.assertEqual(r["primary"]["action"], r["gate"]["signal"])
        self.assertIn("summary", r)
        # summary must mention the same primary label path
        self.assertIn(str(int(r["score"]["final"])), r["summary"].replace(".0", ""))

    def test_no_fake_stats_on_homepage_bytes(self) -> None:
        html = (REPO / "static" / "index.html").read_text(encoding="utf-8")
        for bad in ("1247", "896", "M. Chen", "manuscdn", "Rodriguez", "Patel"):
            self.assertNotIn(bad, html)
        self.assertIn("primary_score", html)  # or Score only one
        self.assertIn("demo free", html.lower())
        # Gate tone helper must not invent pass from pct presence (display text may still show SPY %)
        start = html.find("function gateStatusFromResult")
        self.assertGreater(start, 0)
        end = html.find("\n    function ", start + 10)
        gate_fn = html[start:end] if end > start else html[start : start + 800]
        self.assertNotIn("spy_change_pct", gate_fn)
        self.assertNotIn("sector_change_pct", gate_fn)
        self.assertIn("Trust server statuses only", gate_fn)
        self.assertIn("Mechanical posture", html)
        self.assertIn("PUT ≠ sell", html)
        self.assertTrue((REPO / "docs" / "STOCK_AGENT_MAP.md").is_file())

    def test_pro_value_copy_not_selling_live_air(self) -> None:
        """QD1-0: pricing must not claim live desk is available now."""
        pricing = (REPO / "static" / "pricing.html").read_text(encoding="utf-8")
        self.assertNotIn("Pro for live desk", pricing)
        self.assertIn("supporter", pricing.lower())
        self.assertIn("when charts are mounted", pricing.lower())
        self.assertTrue((REPO / "docs" / "PRO_VALUE.md").is_file())
        body = (REPO / "docs" / "PRO_VALUE.md").read_text(encoding="utf-8")
        self.assertIn("Verdict: B", body)
        self.assertIn("supporter_until_mount", body)

    def test_legal_pages_exist(self) -> None:
        for name in (
            "methodology.html",
            "pricing.html",
            "terms.html",
            "privacy.html",
            "refund.html",
            "og-default.svg",
        ):
            self.assertTrue((REPO / "static" / name).is_file(), name)


class TrustGateHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _get(self, path: str) -> tuple[int, bytes]:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=5
            ) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_pages_and_sample(self) -> None:
        for path in (
            "/methodology",
            "/pricing",
            "/terms",
            "/privacy",
            "/refund",
            "/static/og-default.svg",
        ):
            code, body = self._get(path)
            self.assertEqual(code, 200, path)
            self.assertGreater(len(body), 50, path)

        code, body = self._get("/api/public_stats")
        self.assertEqual(code, 200)
        j = json.loads(body)
        self.assertIsNone(j.get("totalAnalyses"))
        self.assertIsNone(j.get("totalUsers"))

        code, body = self._get("/api/sample?ticker=INTC")
        self.assertEqual(code, 200)
        j = json.loads(body)
        self.assertTrue(j.get("sample") or j.get("demo"))
        self.assertEqual(j.get("meta", {}).get("credits_charged"), 0)
        if j.get("ok"):
            self.assertIn("primary_score", j)

        code, body = self._get("/")
        self.assertEqual(code, 200)
        text = body.decode()
        self.assertNotIn("1247", text)
        self.assertNotIn("manuscdn", text)


if __name__ == "__main__":
    unittest.main()
