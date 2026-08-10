"""知势单元与契约测试。"""
from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engine.score import analyze, fail_closed, posture_for  # noqa: E402
from app.engine.data import load_fixture  # noqa: E402
from app.server import Handler, do_analyze, health  # noqa: E402
from http.server import ThreadingHTTPServer


class ScoreTests(unittest.TestCase):
    def test_posture_bands(self):
        self.assertEqual(posture_for(70), "偏强学习态")
        self.assertEqual(posture_for(40), "中性观察态")
        self.assertEqual(posture_for(10), "偏弱学习态")
        self.assertEqual(posture_for(None), "数据不足")

    def test_fail_closed_no_score(self):
        r = fail_closed("999999")
        self.assertFalse(r["ok"])
        self.assertIsNone(r["primary_score"])
        self.assertEqual(r["posture"], "数据不足")
        self.assertIn("不构成", r["disclaimer"])

    def test_analyze_single_primary_score(self):
        payload = load_fixture("600519")
        self.assertIsNotNone(payload)
        r = analyze(payload)
        self.assertTrue(r["ok"])
        self.assertIn("primary_score", r)
        self.assertIsInstance(r["primary_score"], int)
        self.assertIn(r["posture"], {"偏强学习态", "中性观察态", "偏弱学习态"})
        # 姿态与对外动作词禁止；教学释义亦避免买卖指令用语
        self.assertNotIn(r["posture"], {"买入", "卖出", "加仓", "减仓", "Buy", "Sell"})
        blob = json.dumps({"posture": r["posture"], "primary_score": r["primary_score"]}, ensure_ascii=False)
        for b in ("买入", "卖出", "Buy", "Sell", "加仓", "减仓"):
            self.assertNotIn(b, blob)
        full = json.dumps(r, ensure_ascii=False)
        for b in ("建议买入", "建议卖出", "目标价", "稳赚", "必涨"):
            self.assertNotIn(b, full)

    def test_hkconnect_gates(self):
        payload = dict(load_fixture("600519"))
        payload["market"] = "HKCONNECT"
        r = analyze(payload)
        self.assertTrue(r["ok"])
        ids = {g["id"] for g in r["gates"]}
        self.assertIn("hkconnect_quota", ids)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def _get(self, path: str):
        with urllib.request.urlopen(self.base + path, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status

    def _post(self, path: str, data: dict, session: str | None = None):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json", **({"X-Session": session} if session else {})},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status

    def test_health(self):
        body, status = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["service"], "zhishi")
        self.assertIn("live_eligible", body)

    def test_sample_and_legal_pages(self):
        body, _ = self._get("/api/sample")
        self.assertTrue(body["ok"])
        self.assertEqual(body["symbol"], "600519")
        for path in ("/terms", "/privacy", "/disclaimer", "/methodology", "/pricing"):
            with urllib.request.urlopen(self.base + path, timeout=5) as resp:
                html = resp.read().decode("utf-8")
                self.assertIn("知势", html)
                self.assertIn("投资教育", html)

    def test_invalid_symbol_fail_closed(self):
        try:
            self._get("/api/analyze?symbol=ABC")
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8"))
            self.assertFalse(body["ok"])
            self.assertIsNone(body["primary_score"])

    def test_unknown_symbol(self):
        try:
            self._get("/api/analyze?symbol=999999")
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode("utf-8"))
            self.assertEqual(body["error"], "symbol_not_found")

    def test_cases_and_lessons(self):
        cases, _ = self._get("/api/cases")
        self.assertGreaterEqual(len(cases["cases"]), 20)
        lessons, _ = self._get("/api/lessons")
        ids = {l["id"] for l in lessons["lessons"]}
        self.assertIn("01-t1-liquidity", ids)
        self.assertIn("hk-01-session-quota", ids)

    def test_review_reminder_drill_pay(self):
        sess, _ = self._post("/api/session", {})
        sid = sess["session"]
        analysis = do_analyze("000001")
        rev, _ = self._post(
            "/api/reviews",
            {
                "symbol": analysis["symbol"],
                "name": analysis["name"],
                "primary_score": analysis["primary_score"],
                "posture": analysis["posture"],
                "hypothesis": "量能常态则继续观察",
                "invalidation": "收盘跌破教学均线",
            },
            session=sid,
        )
        self.assertTrue(rev["ok"])
        rem, _ = self._get("/api/me/reminders")
        # need session header — use request helper
        req = urllib.request.Request(self.base + "/api/me/reminders", headers={"X-Session": sid})
        with urllib.request.urlopen(req, timeout=5) as resp:
            rem = json.loads(resp.read().decode("utf-8"))
        self.assertGreaterEqual(len(rem["reminders"]), 1)
        drill, _ = self._post(
            "/api/drills",
            {"prompt": "T+1?", "user_answer": "a", "correct": False, "explanation": "T+1"},
            session=sid,
        )
        self.assertTrue(drill["ok"])
        pay, _ = self._post("/api/pay/mock_checkout", {"sku": "monthly"})
        self.assertTrue(pay["ok"])
        self.assertTrue(pay["mock"])
        skus, _ = self._get("/api/skus")
        self.assertEqual(skus["skus"]["monthly"]["price_fen"], 6800)

    def test_no_banned_marketing_on_home(self):
        with urllib.request.urlopen(self.base + "/", timeout=5) as resp:
            html = resp.read().decode("utf-8")
        for ban in ("稳赚", "必涨", "建议买入", "投资顾问"):
            self.assertNotIn(ban, html)


class ContentTests(unittest.TestCase):
    def test_twenty_cases(self):
        idx = ROOT / "content" / "cases" / "index.json"
        cases = json.loads(idx.read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 20)
        free = [c for c in cases if c.get("free_demo")]
        self.assertEqual(len(free), 3)

    def test_health_helper(self):
        h = health()
        self.assertEqual(h["mode_default"], "artifact")


if __name__ == "__main__":
    unittest.main()
