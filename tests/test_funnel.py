"""Funnel event logging + engagement contract fields."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app import funnel  # noqa: E402
from app.charts_facade import analyze  # noqa: E402
from app.server import Handler  # noqa: E402


class FunnelUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "funnel.jsonl"
        self._patch = mock.patch.object(funnel, "FUNNEL_PATH", self.path)
        self._patch_data = mock.patch.object(funnel, "DATA", Path(self.tmp.name))
        self._patch.start()
        self._patch_data.start()

    def tearDown(self) -> None:
        self._patch.stop()
        self._patch_data.stop()
        self.tmp.cleanup()

    def test_track_and_summarize(self) -> None:
        self.assertIsNotNone(funnel.track("demo_run", ticker="INTC", ok=True, demo=True))
        self.assertIsNotNone(funnel.track("signup", plan="free", email="a@b.co"))
        self.assertIsNone(funnel.track("not_a_real_event"))
        s = funnel.summarize()
        self.assertEqual(s["counts"]["demo_run"], 1)
        self.assertEqual(s["counts"]["signup"], 1)
        self.assertEqual(s["rates"]["signup_per_demo"], 1.0)
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn("a@b.co", raw)
        self.assertIn("email_hash", raw)

    def test_engagement_fields_on_artifact(self) -> None:
        r = analyze("INTC", mode="artifact")
        self.assertTrue(r.get("ok"), r)
        self.assertIn("engagement", r)
        self.assertTrue(r["engagement"].get("avoided_line"))
        self.assertTrue(r["engagement"].get("freeze_label"))
        self.assertIn("breakdown", r["score"])
        self.assertGreaterEqual(len(r["score"]["breakdown"]), 1)
        self.assertIn("entry_timing", r.get("gate") or {})

    def test_funnel_max_bytes_refuses_write(self) -> None:
        self.path.write_text("x" * 2000, encoding="utf-8")
        # Cap below current file size → any append refused
        with mock.patch.dict("os.environ", {"QUANTRADAR_FUNNEL_MAX_BYTES": "1500"}):
            self.assertIsNone(funnel.track("demo_run", ticker="INTC", ok=True, demo=True))
        # Under the cap still works
        with mock.patch.dict("os.environ", {"QUANTRADAR_FUNNEL_MAX_BYTES": "100000"}):
            self.assertIsNotNone(funnel.track("demo_run", ticker="NVDA", ok=True, demo=True))


class FunnelHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "funnel.jsonl"
        self._patch = mock.patch.object(funnel, "FUNNEL_PATH", self.path)
        self._patch_data = mock.patch.object(funnel, "DATA", Path(self.tmp.name))
        self._patch.start()
        self._patch_data.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._patch.stop()
        self._patch_data.stop()
        self.tmp.cleanup()

    def test_sample_logs_demo_run(self) -> None:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/api/sample?ticker=INTC", timeout=5
        ) as r:
            body = json.loads(r.read().decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("engagement", {}).get("freeze_label"))
        rows = [json.loads(x) for x in self.path.read_text(encoding="utf-8").splitlines() if x.strip()]
        self.assertTrue(any(x.get("event") == "demo_run" for x in rows))

    def test_sample_and_notify_rate_limited(self) -> None:
        import app.server as server_mod

        with mock.patch.object(server_mod, "check_rate_limit", return_value=False):
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{self.port}/api/sample?ticker=INTC", timeout=5
                )
                self.fail("expected 429")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 429)
                body = json.loads(e.read().decode("utf-8"))
                self.assertEqual(body.get("error"), "rate_limited")

            req = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/notify",
                data=json.dumps({"email": "rate@test.local", "ticker": "INTC"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req, timeout=5)
                self.fail("expected 429")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 429)

            req2 = urllib.request.Request(
                f"http://127.0.0.1:{self.port}/api/auth/register",
                data=json.dumps(
                    {"email": "ratelim@test.local", "password": "long-enough-pass"}
                ).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req2, timeout=5)
                self.fail("expected 429")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 429)

    def test_share_card_intc_html(self) -> None:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/r/INTC", timeout=5) as r:
            body = r.read().decode("utf-8")
            self.assertEqual(r.status, 200)
            self.assertIn("text/html", r.headers.get("Content-Type", ""))
        self.assertIn("INTC", body)
        self.assertIn("og:title", body)
        self.assertIn("/?demo=INTC", body)
        self.assertIn("Educational only", body)
        self.assertIn('href="/track"', body)
        self.assertIn('href="/methodology"', body)
        self.assertNotIn("1247", body)

    def test_share_card_unknown_ticker_404(self) -> None:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/r/NOTADEMO", timeout=5)
            self.fail("expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            body = e.read().decode("utf-8")
            self.assertIn("not a published demo", body)


if __name__ == "__main__":
    unittest.main()
