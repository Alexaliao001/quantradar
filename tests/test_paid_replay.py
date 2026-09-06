import csv
import io
import json
import unittest
import zipfile

from free_engine.market_calendar import session_window
from free_engine.replay import build_replay, build_report_bundle, zip_bundle


def report_payload():
    dates = session_window("2026-09-04", 150)
    bars = [[day, 100 + i * 0.1, 1000000] for i, day in enumerate(dates)]
    return {
        "ticker": "TESTCO", "fetch_time": "2026-09-04T21:00:00+00:00",
        "data_quality": {"market_as_of": "2026-09-04", "reliability": "medium", "timeframes_ok": 1},
        "daily_bars": bars, "spy_daily_bars": [[day, 500, 1000000] for day in dates],
        "mechanical_scores": {"final_score": 58, "signal_mechanical": "WAIT", "base_score": {"total": 58},
                              "state": {"code": "B", "name": "wait_watch", "reason": "Wait"}},
        "market_env": {"spy_change_pct": 0}, "fundamentals": {}, "indicator_data": {},
    }


class PaidReplayTests(unittest.TestCase):
    def test_future_prices_cannot_change_past_replay(self):
        payload = report_payload()
        cutoff = payload["daily_bars"][-10][0]
        original = build_replay(payload, sessions=50, cutoff=cutoff)
        for row in payload["daily_bars"] + payload["spy_daily_bars"]:
            if row[0] > cutoff:
                row[1] = 0.001
        self.assertEqual(build_replay(payload, sessions=50, cutoff=cutoff), original)

    def test_missing_market_and_stock_sessions_remain_explicit(self):
        payload = report_payload()
        payload["spy_daily_bars"].pop()
        row = build_replay(payload)[-1]
        self.assertEqual(row["market_gate"], "UNKNOWN")
        self.assertNotEqual(row["action"], "SETUP")
        payload["daily_bars"].pop(-10)
        row = build_replay(payload)[-1]
        self.assertEqual(row["action"], "UNKNOWN")
        self.assertIsNone(row["score"])
        with self.assertRaisesRegex(ValueError, "139 consecutive"):
            build_report_bundle(payload)

    def test_bundle_json_csv_charts_and_zip_are_consistent(self):
        bundle = build_report_bundle(report_payload(), include_csv=True)
        self.assertEqual(bundle["sessions"], 90)
        report = json.loads(bundle["assets"]["report.json"])
        csv_rows = list(csv.DictReader(io.StringIO(bundle["assets"]["replay.csv"])))
        self.assertEqual([r["date"] for r in csv_rows], [r["date"] for r in report["replay"]])
        self.assertEqual(float(csv_rows[-1]["close"]), report["replay"][-1]["close"])
        self.assertIn(report["as_of"], bundle["assets"]["price.svg"])
        archive = zip_bundle(bundle)
        self.assertEqual(archive, zip_bundle(bundle))
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            self.assertEqual(set(zipped.namelist()), set(bundle["assets"]))
            self.assertEqual(zipped.read("report.json").decode(), bundle["assets"]["report.json"])
        self.assertNotIn("replay.csv", build_report_bundle(report_payload())["assets"])
