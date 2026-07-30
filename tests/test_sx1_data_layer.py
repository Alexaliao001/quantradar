"""SX1 — data-layer honesty: health fields, artifact options, path sanitization."""
from __future__ import annotations

import unittest

from app.charts_facade import analyze, find_analysis_artifact, load_charts_json
from app.contract import _public_path, map_charts_payload
from app.server import health_payload


class HealthDataLayer(unittest.TestCase):
    def test_health_has_sx1_fields(self) -> None:
        h = health_payload()
        self.assertTrue(h["ok"])
        self.assertEqual(h["service"], "quantradar-shell")
        self.assertFalse(h["manus_login"])
        self.assertIn(h["charts_status"], {"mounted", "artifact_only", "unavailable"})
        self.assertIn(h["data_path"], {"charts_engine", "artifact_fixtures", "none"})
        self.assertIsInstance(h["artifact_fixtures"], list)
        self.assertTrue(h.get("product_note"))
        self.assertIn("INTC", h["artifact_fixtures"])
        self.assertIn(h.get("pro_value"), {"supporter_until_mount", "live_ready"})
        self.assertIn("live_available", h)
        self.assertEqual(bool(h["live_available"]), h["charts_status"] == "mounted")
        self.assertTrue(h.get("pro_value_note"))
        if h["charts_status"] != "mounted":
            self.assertEqual(h["pro_value"], "supporter_until_mount")
            self.assertFalse(h["live_available"])


class ArtifactHonesty(unittest.TestCase):
    def test_intc_artifact_options_not_actionable(self) -> None:
        r = analyze("INTC", mode="artifact")
        self.assertTrue(r["ok"], r)
        self.assertFalse(r["data_quality"]["options_actionable"])
        self.assertEqual(r["data_quality"]["options"]["option_data_source"], "artifact_snapshot")
        self.assertTrue(r["data_quality"]["options"].get("options_from_artifact"))
        self.assertEqual(r["meta"]["mode"], "artifact")
        self.assertEqual(r["meta"]["data_path"], "artifact_fixtures")
        self.assertIn("disclaimer", r["meta"])

    def test_public_path_strips_home(self) -> None:
        self.assertEqual(_public_path("/Users/me/charts/foo.png"), "foo.png")
        self.assertEqual(
            _public_path("/opt/render/project/src/fixtures/x.json"),
            "x.json",
        )
        self.assertIsNone(_public_path(None))

    def test_mapped_charts_paths_no_home_leak(self) -> None:
        path = find_analysis_artifact("INTC")
        self.assertIsNotNone(path)
        payload = load_charts_json(path)
        ind = payload.setdefault("indicator_data", {})
        files = ind.setdefault("chart_files", {})
        files["daily"] = {
            "price": "/Users/rongjianliao/charts/reports/INTC_daily.png",
            "indicators": None,
        }
        mapped = map_charts_payload(payload, mode="artifact", analysis_json_path=str(path))
        dp = mapped["artifacts"]["charts"].get("daily_price")
        self.assertTrue(dp is None or not str(dp).startswith("/Users/"), dp)


if __name__ == "__main__":
    unittest.main()
