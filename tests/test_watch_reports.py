import csv
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import urllib.request
import urllib.error
import unittest
from unittest import mock

from app import engagement, paid_delivery, users, watch_reports
from app import auth
from test_paid_replay import report_payload


class WatchReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for patcher in (mock.patch.object(users, "USERS_PATH", root / "users.json"),
                        mock.patch.dict(os.environ, {"QUANTRADAR_BILLING_DB": str(root / "billing.sqlite3")}),
                        mock.patch.object(watch_reports, "completed_session", return_value="2026-09-04")):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.owner = "portfolio@example.com"
        users.set_plan(self.owner, "portfolio_pro")
        engagement.add_watch(self.owner, "TESTCO")

    def test_free_cannot_create_and_automatic_optin_respects_current_entitlement(self):
        users.set_plan("free@example.com", "free")
        engagement.add_watch("free@example.com", "TESTCO")
        engagement.set_digest_optin("free@example.com", True)
        engagement.set_digest_optin(self.owner, True)
        with self.assertRaisesRegex(ValueError, "Pro is required"):
            watch_reports.request_report("free@example.com")
        watch_reports.schedule_optins()
        watch_reports.schedule_optins()
        self.assertEqual(len(watch_reports.list_reports(self.owner)), 1)
        self.assertEqual(watch_reports.list_reports("free@example.com"), [])

    def test_roster_freezes_once_and_owned_results_survive_downgrade(self):
        report_id = watch_reports.request_report(self.owner)
        engagement.add_watch(self.owner, "AAPL")
        self.assertEqual(watch_reports.request_report(self.owner), report_id)
        self.assertEqual(watch_reports.get_report(self.owner, report_id)["tickers"], ["TESTCO"])
        self.assertIsNone(watch_reports.get_report("other@example.com", report_id))
        with mock.patch("app.charts_facade.run_fetch_all", return_value=report_payload()):
            self.assertTrue(watch_reports.process_next())
        users.set_plan(self.owner, "free")
        report = watch_reports.get_report(self.owner, report_id)
        self.assertEqual(report["state"], "ready")
        self.assertTrue(report["csv_enabled"])
        exported = list(csv.DictReader(io.StringIO(watch_reports.csv_export(report))))
        self.assertEqual(exported[0]["ticker"], "TESTCO")
        self.assertEqual(float(exported[0]["close"]), report_payload()["daily_bars"][-1][1])
        self.assertNotIn(self.owner, json.dumps(report))
        self.assertFalse(watch_reports.process_next())

    def test_failed_ticker_does_not_block_remaining_roster_and_partial_is_explicit(self):
        engagement.add_watch(self.owner, "MISSING")
        report_id = watch_reports.request_report(self.owner)
        with mock.patch("app.charts_facade.run_fetch_all", side_effect=[report_payload(), ValueError("missing"), ValueError("missing"), ValueError("missing")]):
            for now in (1000, 1000, 1061, 1122):
                watch_reports.process_next(now=now)
        report = watch_reports.get_report(self.owner, report_id)
        self.assertEqual(report["state"], "partial")
        self.assertEqual(report["ready"], 1)
        self.assertEqual(report["rows"][1]["action"], "UNKNOWN")
        self.assertIsNone(report["rows"][1]["score"])

    def test_stale_session_rejected_and_expired_lease_recovers(self):
        report_id = watch_reports.request_report(self.owner)
        with paid_delivery.database() as db:
            db.execute("UPDATE watch_reports SET state='building',lease_until=1000 WHERE id=?", (report_id,))
        with mock.patch("app.charts_facade.run_fetch_all", return_value=report_payload()):
            self.assertFalse(watch_reports.process_next(now=999))
            self.assertTrue(watch_reports.process_next(now=1001))
        with mock.patch.object(watch_reports, "completed_session", return_value="2026-09-08"):
            next_id = watch_reports.request_report(self.owner)
        with mock.patch("app.charts_facade.run_fetch_all", return_value=report_payload()):
            watch_reports.process_next(now=2000)
        self.assertIsNone(watch_reports.get_report(self.owner, next_id)["rows"][0]["score"])

    def test_previous_action_is_only_from_prior_saved_session(self):
        previous_id = watch_reports.request_report(self.owner)
        with mock.patch("app.charts_facade.run_fetch_all", return_value=report_payload()):
            watch_reports.process_next()
        with mock.patch.object(watch_reports, "completed_session", return_value="2026-09-08"):
            current_id = watch_reports.request_report(self.owner)
        payload = report_payload()
        payload["data_quality"]["market_as_of"] = "2026-09-08"
        payload["daily_bars"][-1][0] = "2026-09-08"
        payload["mechanical_scores"]["signal_mechanical"] = "NO"
        with mock.patch("app.charts_facade.run_fetch_all", return_value=payload):
            watch_reports.process_next()
        current = watch_reports.get_report(self.owner, current_id)["rows"][0]
        self.assertEqual(current["previous_action"], "WAIT")
        self.assertTrue(current["changed"])
        self.assertEqual(watch_reports.get_report(self.owner, previous_id)["rows"][0]["action"], "WAIT")

    def test_reconstructed_and_saved_setup_aliases_do_not_signal_a_change(self):
        previous_id = watch_reports.request_report(self.owner)
        prior = {"TESTCO": {"ticker": "TESTCO", "status": "ready", "action": "SETUP", "attempts": 1}}
        with paid_delivery.database() as db:
            db.execute("UPDATE watch_reports SET results=?,state='ready' WHERE id=?", (json.dumps(prior), previous_id))
        with mock.patch.object(watch_reports, "completed_session", return_value="2026-09-08"):
            current_id = watch_reports.request_report(self.owner)
        historical = {"close": 100, "score": 80, "action": "SETUP", "market_gate": "PASS"}
        with mock.patch("app.charts_facade.run_fetch_all", return_value=report_payload()), mock.patch("free_engine.replay.build_replay", return_value=[historical]):
            watch_reports.process_next()
        row = watch_reports.get_report(self.owner, current_id)["rows"][0]
        self.assertEqual(row["action"], "PROBE")
        self.assertEqual(row["previous_action"], "PROBE")
        self.assertFalse(row["changed"])

    def test_http_exports_have_complete_bodies_and_enforce_ownership(self):
        from http.server import ThreadingHTTPServer
        from app.server import Handler
        report_id = watch_reports.request_report(self.owner)
        with mock.patch("app.charts_facade.run_fetch_all", return_value=report_payload()):
            watch_reports.process_next()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            for extension in ("json", "csv"):
                url = f"http://127.0.0.1:{server.server_port}/api/watch-reports/{report_id}/{extension}"
                for email, expected in ((None, 401), ("other@example.com", 404), (self.owner, 200)):
                    headers = {"Cookie": auth.COOKIE_NAME + "=" + auth.mint_session(sub=email, email=email)} if email else {}
                    try:
                        response = urllib.request.urlopen(urllib.request.Request(url, headers=headers))
                    except urllib.error.HTTPError as error:
                        response = error
                    with response:
                        self.assertEqual(response.status, expected)
                        data = response.read()
                        self.assertEqual(len(data), int(response.headers["Content-Length"]))
                        if expected == 200:
                            self.assertEqual(response.headers["Cache-Control"], "private, no-store")
                            self.assertGreater(len(data), 100)
                            if extension == "json":
                                self.assertEqual(json.loads(data)["rows"][0]["ticker"], "TESTCO")
                            else:
                                self.assertEqual(list(csv.DictReader(io.StringIO(data.decode())))[0]["ticker"], "TESTCO")
        finally:
            server.shutdown()
            server.server_close()

    def test_expired_worker_cannot_overwrite_recovered_results(self):
        report_id = watch_reports.request_report(self.owner)
        calls = 0
        def engine(ticker):
            nonlocal calls
            calls += 1
            if calls == 1:
                watch_reports.process_next(now=1121)
                raise ValueError("Old worker resumed after its lease expired")
            return report_payload()
        with mock.patch("app.charts_facade.run_fetch_all", side_effect=engine):
            watch_reports.process_next(now=1000)
        self.assertEqual(watch_reports.get_report(self.owner, report_id)["state"], "ready")

    def test_process_interruptions_count_toward_attempt_limit(self):
        report_id = watch_reports.request_report(self.owner)
        with mock.patch("app.charts_facade.run_fetch_all", side_effect=SystemExit("process stopped")) as fetch:
            for now in (1000, 1121, 1242):
                with self.assertRaises(SystemExit):
                    watch_reports.process_next(now=now)
            self.assertTrue(watch_reports.process_next(now=1363))
            self.assertEqual(fetch.call_count, 3)
        self.assertEqual(watch_reports.get_report(self.owner, report_id)["state"], "partial")

    def test_later_recovery_reconstructs_frozen_session_without_current_fundamentals(self):
        report_id = watch_reports.request_report(self.owner)
        payload = report_payload()
        payload["data_quality"]["market_as_of"] = "2026-09-08"
        payload["daily_bars"].append(["2026-09-08", 1, 1000000])
        payload["spy_daily_bars"].append(["2026-09-08", 1, 1000000])
        with mock.patch("app.charts_facade.run_fetch_all", return_value=payload):
            watch_reports.process_next()
        report = watch_reports.get_report(self.owner, report_id)
        self.assertEqual(report["state"], "ready")
        row = report["rows"][0]
        self.assertEqual(row["as_of"], "2026-09-04")
        self.assertTrue(row["reconstructed"])
        self.assertEqual(row["earnings_gate"], "UNKNOWN")
        self.assertGreater(row["close"], 100)
