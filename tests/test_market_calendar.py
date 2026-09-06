import unittest
import tempfile
from pathlib import Path
from unittest import mock
from datetime import datetime, timedelta

from free_engine.market_calendar import completed_bars, completed_session, session_window


class MarketCalendarTests(unittest.TestCase):
    def test_completed_sessions_include_dst_holidays_and_early_closes(self):
        cases = {
            "2026-09-08T19:59:59+00:00": "2026-09-04",
            "2026-09-08T20:00:00+00:00": "2026-09-08",
            "2026-09-07T23:00:00+00:00": "2026-09-04",
            "2026-11-27T17:59:59+00:00": "2026-11-25",
            "2026-11-27T18:00:00+00:00": "2026-11-27",
            "2026-03-06T20:30:00+00:00": "2026-03-05",
            "2026-03-09T20:30:00+00:00": "2026-03-09",
            "2026-01-01T22:00:00+00:00": "2025-12-31",
            "2029-01-02T22:00:00+00:00": None,
        }
        for instant, expected in cases.items():
            with self.subTest(instant=instant):
                self.assertEqual(completed_session(datetime.fromisoformat(instant)), expected)

    def test_partial_bar_is_excluded_and_stale_data_rejected(self):
        now = datetime.fromisoformat("2026-09-08T18:00:00+00:00")
        end = datetime.fromisoformat("2026-09-04")
        bars = [((end - timedelta(days=59-i)).date().isoformat(), 100.0, 1000) for i in range(60)]
        self.assertEqual(completed_bars(bars + [("2026-09-08", 999.0, 1000)], now=now), bars)
        with self.assertRaises(ValueError):
            completed_bars(bars[:-1], now=now)
        with self.assertRaises(ValueError):
            completed_bars(bars[-20:], now=now)
        with self.assertRaises(ValueError):
            completed_bars(bars + [bars[-1]], now=now)
        with self.assertRaises(ValueError):
            completed_bars(bars[:-1] + [("2026-09-04", float("inf"), 1000)], now=now)

    def test_preclose_cache_must_refresh_after_close(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "free_engine"))
        import free_sources as sources
        now = datetime.fromisoformat("2026-09-08T20:01:00+00:00")
        rows = [(day, 100.0, 1000) for day in session_window("2026-09-08", 60)]
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            sources._cache_write(cache, "yahoo_q1:AAPL", rows, fetched_at=now.timestamp() - 120)
            with mock.patch.object(sources, "SOURCE_NAMES", ("yahoo_q1",)), mock.patch.object(sources.time, "time", return_value=now.timestamp()), mock.patch.object(sources, "_fetch_source", return_value=rows) as fetch:
                result, errors = sources.fetch_all_sources("AAPL", days=90, cache_dir=cache, as_of=now)
                fetch.assert_called_once()
                self.assertFalse(errors)
                self.assertEqual(result["yahoo_q1"], rows)
            with mock.patch.object(sources, "SOURCE_NAMES", ("yahoo_q1",)), mock.patch.object(sources.time, "time", return_value=now.timestamp()), mock.patch.object(sources, "_fetch_source") as fetch:
                sources.fetch_all_sources("AAPL", days=90, cache_dir=cache, as_of=now)
                fetch.assert_not_called()
