import os
import tempfile
import unittest
import threading
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from app import paid_delivery as delivery
from app import users, auth
from app import stripe_billing
from test_paid_replay import report_payload


class PaidDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = mock.patch.dict(os.environ, {"QUANTRADAR_BILLING_DB": str(Path(self.tmp.name) / "billing.sqlite3")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.clock = mock.patch("free_engine.market_calendar.completed_session", return_value="2026-09-04")
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.accounts = mock.patch.object(users, "USERS_PATH", Path(self.tmp.name) / "users.json")
        self.accounts.start()
        self.addCleanup(self.accounts.stop)
        coupon = mock.patch("app.stripe_billing.create_credit_coupon", side_effect=lambda email, **kw: "coupon_" + kw["order_id"])
        coupon.start()
        self.addCleanup(coupon.stop)

    def order(self, owner="buyer@example.com", key="request_key_000001", bump=False):
        with mock.patch("app.charts_facade.run_fetch_all", return_value=report_payload()):
            return delivery.prepare_report_order(owner, "TESTCO", request_key=key, bump=bump)

    def pay(self, order):
        session = {"id": "cs_" + order["id"], "url": "https://checkout.stripe.com/test",
                   "mode": "payment", "payment_status": "paid", "amount_total": order["amount"], "currency": "usd",
                   "payment_intent": "pi_" + order["id"],
                   "metadata": {"order_id": order["id"], "email": order["owner"], "product": "quantradar_report"}}
        delivery.attach_checkout(order["id"], session)
        return delivery.event_once("evt_" + order["id"], "checkout.session.completed", lambda db: delivery.mark_report_paid(db, session))

    def test_two_orders_keep_owned_bundles_and_survive_restart(self):
        first = self.order()
        second = self.order("second@example.com", bump=True)
        self.pay(first)
        self.pay(second)
        self.assertIsNone(delivery.get_report("second@example.com", first["id"]))
        self.assertNotIn("bundle", delivery.get_report(first["owner"], first["id"]))
        self.assertTrue(delivery.fulfill_next())
        self.assertTrue(delivery.fulfill_next())
        self.assertFalse(delivery.fulfill_next())
        for order in (first, second):
            result = delivery.get_report(order["owner"], order["id"])
            self.assertEqual(result["delivery_state"], "ready")
            self.assertEqual(result["bundle"]["ticker"], "TESTCO")
            self.assertEqual("replay.csv" in result["bundle"]["assets"], bool(order["bump"]))
        self.assertEqual(len(delivery.list_reports(first["owner"])), 1)

    def test_expired_worker_cannot_hide_completed_download(self):
        order = self.order()
        self.pay(order)
        build = delivery.build_report_bundle
        calls = 0
        def resume(inputs, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                delivery.fulfill_next(now=1121)
                raise ValueError("Old worker failed after a recovered delivery completed")
            return build(inputs, **kwargs)
        with mock.patch.object(delivery, "build_report_bundle", side_effect=resume):
            delivery.fulfill_next(now=1000)
        report = delivery.get_report(order["owner"], order["id"])
        self.assertEqual(report["delivery_state"], "ready")
        self.assertIn("bundle", report)

    def test_request_and_event_idempotency_under_concurrency(self):
        first = self.order()
        self.assertEqual(first["id"], self.order()["id"])
        calls = []
        def apply(db):
            calls.append(True)
            return {"ok": True, "action": "applied"}
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: delivery.event_once("evt_repeated", "test", apply), range(10)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(sum(bool(r.get("duplicate")) for r in results), 9)
        self.pay(first)
        self.assertTrue(self.pay(first)["duplicate"])

    def test_conflicting_concurrent_request_keys_do_not_return_wrong_order(self):
        barrier = threading.Barrier(2)
        def payload(ticker, sector):
            barrier.wait(timeout=5)
            return report_payload()
        def prepare(ticker):
            try:
                return delivery.prepare_report_order("buyer@example.com", ticker, request_key="same_request_key_001")
            except ValueError:
                return None
        with mock.patch.object(delivery, "validated_report_payload", side_effect=payload), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(prepare, ["AAPL", "MSFT"]))
        self.assertEqual(sum(r is None for r in results), 1)
        self.assertEqual(len(delivery.list_reports("buyer@example.com")), 1)

    def test_refund_before_payment_and_stale_partial_never_restore_access(self):
        order = self.order()
        refund = {"id": "evt_refund_first", "type": "charge.refunded", "data": {"object": {
            "id": "ch_test", "payment_intent": "pi_" + order["id"], "refunded": True}}}
        stripe_billing.apply_webhook_event(refund)
        self.pay(order)
        self.assertEqual(delivery.get_report(order["owner"], order["id"])["payment_state"], "refunded")
        self.assertFalse(delivery.fulfill_next())
        refund["id"] = "evt_stale_partial"
        refund["data"]["object"]["refunded"] = False
        stripe_billing.apply_webhook_event(refund)
        report = delivery.get_report(order["owner"], order["id"])
        self.assertEqual(report["payment_state"], "refunded")
        self.assertNotIn("bundle", report)

    def test_refund_during_credit_issuance_revokes_credit_without_hiding_ready_bundle(self):
        order = self.order()
        self.pay(order)
        def issue(*args, **kwargs):
            stripe_billing.apply_webhook_event({"id": "evt_refund_during_credit", "type": "charge.refunded", "data": {"object": {
                "payment_intent": "pi_" + order["id"], "refunded": False}}})
            return "coupon_inflight"
        with mock.patch.object(stripe_billing, "create_credit_coupon", side_effect=issue):
            delivery.fulfill_next()
        report = delivery.get_report(order["owner"], order["id"])
        self.assertEqual(report["credit_state"], "revoking")
        self.assertIn("bundle", report)
        with mock.patch.object(stripe_billing, "revoke_credit_coupon", return_value=True) as revoke:
            delivery.fulfill_next(now=9999999999)
        revoke.assert_called_once_with("coupon_inflight")
        self.assertEqual(delivery.get_report(order["owner"], order["id"])["credit_state"], "revoked")

    def test_credit_failure_keeps_download_ready_and_older_unused_credit_is_selected(self):
        first = self.order()
        self.pay(first)
        delivery.fulfill_next()
        second = self.order(key="second_request_key_01")
        self.pay(second)
        with mock.patch.object(stripe_billing, "create_credit_coupon", side_effect=RuntimeError("temporary Stripe failure")):
            delivery.fulfill_next()
        self.assertIn("bundle", delivery.get_report(second["owner"], second["id"]))
        with delivery.database() as db:
            db.execute("UPDATE report_orders SET credit_state='ready',credit_code='coupon_spent' WHERE id=?", (second["id"],))
        with mock.patch.object(stripe_billing, "coupon_redeemable", side_effect=lambda code: code != "coupon_spent"):
            self.assertEqual(delivery.report_credit(first["owner"]), "coupon_" + first["id"])

    def test_legacy_paid_checkout_binds_existing_claim_once(self):
        owner = "legacy@example.com"
        users.set_plan(owner, "free")
        users.grant_report(owner, bump=False)
        users.set_report_coupon(owner, "coupon_legacy")
        claim = delivery.list_reports(owner)[0]
        session = {"id": "cs_legacy", "mode": "payment", "payment_status": "paid", "amount_total": 900,
                   "currency": "usd", "payment_intent": "pi_legacy", "metadata": {"product": "quantradar_report", "email": owner}}
        paid_at = int(time.time())
        event = {"id": "evt_legacy", "type": "checkout.session.completed", "created": paid_at, "data": {"object": session}}
        result = stripe_billing.apply_webhook_event(event)
        self.assertEqual(result["order_id"], claim["id"])
        self.assertTrue(stripe_billing.apply_webhook_event(event)["duplicate"])
        reports = delivery.list_reports(owner)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["paid_at"], paid_at)
        self.assertEqual(reports[0]["delivery_state"], "awaiting_ticker")
        with mock.patch.object(stripe_billing, "coupon_redeemable", return_value=True):
            self.assertEqual(delivery.report_credit(owner), "coupon_legacy")
            stripe_billing.apply_webhook_event({"id": "evt_legacy_refund", "type": "charge.refunded", "data": {"object": {"payment_intent": "pi_legacy", "refunded": True}}})
            self.assertIsNone(delivery.report_credit(owner))
        self.assertEqual(delivery.get_report(owner, claim["id"])["credit_state"], "revoking")

    def test_legacy_initialization_and_payment_are_atomic_on_disk(self):
        owner = "race@example.com"
        users.set_plan(owner, "free")
        users.grant_report(owner, bump=False)
        event = {"id": "evt_legacy_race", "type": "checkout.session.completed", "data": {"object": {
            "id": "cs_legacy_race", "mode": "payment", "payment_status": "paid", "amount_total": 900,
            "currency": "usd", "payment_intent": "pi_legacy_race", "metadata": {"product": "quantradar_report", "email": owner}}}}
        barrier = threading.Barrier(2)
        def initialize():
            barrier.wait(timeout=5)
            delivery.ensure_legacy_claim(owner)
        def webhook():
            barrier.wait(timeout=5)
            stripe_billing.apply_webhook_event(event)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(initialize), pool.submit(webhook)]
            for future in futures:
                future.result(timeout=10)
        self.assertEqual(len(delivery.list_reports(owner)), 1)

    def test_mismatched_payment_never_unlocks(self):
        order = self.order()
        delivery.attach_checkout(order["id"], {"id": "cs_bound", "url": "https://checkout.stripe.com/test"})
        for session in ({"id": "cs_wrong"}, {"id": "cs_bound", "payment_status": "paid", "amount_total": 1}):
            session["metadata"] = {"order_id": order["id"]}
            with self.assertRaises(ValueError):
                delivery.event_once("evt_wrong", "test", lambda db: delivery.mark_report_paid(db, session))
        self.assertEqual(delivery.get_report(order["owner"], order["id"])["payment_state"], "unpaid")

    def test_priority_and_abandoned_lease_recovery(self):
        normal = self.order(key="request_normal_001")
        priority = self.order(key="request_priority_01", bump=True)
        self.pay(normal)
        self.pay(priority)
        self.assertTrue(delivery.fulfill_next())
        self.assertEqual(delivery.get_report(priority["owner"], priority["id"])["delivery_state"], "ready")
        with delivery.database() as db:
            db.execute("UPDATE report_orders SET delivery_state='building',lease_until=0 WHERE id=?", (normal["id"],))
        self.assertTrue(delivery.fulfill_next())
        self.assertEqual(delivery.get_report(normal["owner"], normal["id"])["delivery_state"], "ready")

    def test_older_subscription_cancellation_cannot_remove_portfolio(self):
        with delivery.database() as db:
            db.executemany("INSERT INTO subscriptions VALUES(?,?,?,?,?,?,?,?)", [
                ("sub_old", "a@example.com", "cus_a", "pro", "price_pro", "canceled", 9999999999, 1),
                ("sub_new", "a@example.com", "cus_a", "portfolio_pro", "price_portfolio", "active", 9999999999, 2),
            ])
        self.assertEqual(delivery.subscription_plan("a@example.com"), "portfolio_pro")
        self.assertEqual(delivery.subscription_plan("a@example.com", now=99999999999), "free")
        self.assertIsNone(delivery.subscription_plan("other@example.com"))

    def test_legacy_claim_is_once_only_and_keeps_csv(self):
        users.set_plan("legacy@example.com", "free")
        users.grant_report("legacy@example.com", bump=False)
        first = delivery.list_reports("legacy@example.com")
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["delivery_state"], "awaiting_ticker")
        self.assertEqual(delivery.list_reports("legacy@example.com")[0]["id"], first[0]["id"])
        with mock.patch("app.charts_facade.run_fetch_all", return_value=report_payload()):
            delivery.claim_legacy_report("legacy@example.com", first[0]["id"], "TESTCO")
        self.assertTrue(delivery.fulfill_next())
        report = delivery.get_report("legacy@example.com", first[0]["id"])
        self.assertIn("replay.csv", report["bundle"]["assets"])
        with self.assertRaises(ValueError):
            delivery.claim_legacy_report("legacy@example.com", first[0]["id"], "AAPL")
        self.assertEqual(len(delivery.list_reports("legacy@example.com")), 1)

    def test_http_downloads_enforce_ownership_and_private_cache(self):
        from http.server import ThreadingHTTPServer
        from app.server import Handler
        order = self.order()
        self.pay(order)
        delivery.fulfill_next()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/reports/{order['id']}/assets/report.zip"
            for email, expected in ((None, 401), ("other@example.com", 404), (order["owner"], 200)):
                headers = {}
                if email:
                    headers["Cookie"] = auth.COOKIE_NAME + "=" + auth.mint_session(sub=email, email=email)
                request = urllib.request.Request(url, headers=headers)
                try:
                    response = urllib.request.urlopen(request)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    self.assertEqual(response.status, expected)
                    if expected == 200:
                        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
                        self.assertEqual(response.headers["Content-Type"], "application/zip")
                        self.assertTrue(response.read().startswith(b"PK"))
        finally:
            server.shutdown()
            server.server_close()
