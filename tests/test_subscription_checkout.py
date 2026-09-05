import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from app import paid_delivery, stripe_billing, subscription_checkout, users


class SubscriptionCheckoutTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.owner = "subscriber@example.com"
        self.sessions = {}
        self.keys = {}
        self.customer_keys = {}
        self.lock = threading.Lock()
        self.lose_response = False
        self.subscription_status = "active"
        self.legacy_subscription = None
        patches = [
            mock.patch.object(users, "USERS_PATH", Path(temporary.name) / "users.json"),
            mock.patch.dict(os.environ, {"QUANTRADAR_BILLING_DB": str(Path(temporary.name) / "billing.sqlite3"),
                "STRIPE_PRICE_ID_MONTHLY": "price_monthly", "STRIPE_PRICE_ID_YEARLY": "price_yearly",
                "STRIPE_PRICE_ID_PORTFOLIO_PRO_MONTHLY": "price_portfolio"}),
            mock.patch.object(stripe_billing, "stripe_post", side_effect=self.post),
            mock.patch.object(stripe_billing, "stripe_get", side_effect=self.get),
            mock.patch.object(stripe_billing, "create_checkout_session", side_effect=self.create),
            mock.patch.object(stripe_billing, "create_billing_portal", return_value={"url":"https://billing.stripe.com/portal", "billing_portal":True}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        users.set_plan(self.owner, "free")

    def post(self, path, data, *, idempotency_key):
        with self.lock:
            if path == "customers":
                return self.customer_keys.setdefault(idempotency_key, {"id":"cus_" + str(len(self.customer_keys))})
            session = self.sessions[path.split("/")[2]]
            self.assertEqual(session["status"], "open")
            session["status"] = "expired"
            return copy.deepcopy(session)

    def create(self, **params):
        with self.lock:
            key = params["idempotency_key"]
            if key not in self.keys:
                self.keys[key] = copy.deepcopy(params)
                session_id = "cs_" + str(len(self.keys))
                self.sessions[session_id] = {"id":session_id, "url":"https://checkout.stripe.com/"+session_id,
                    "status":"open", "mode":"subscription", "customer":params["customer_id"],
                    "metadata":{"checkout_attempt":key}, "subscription":None}
            else:
                self.assertEqual(self.keys[key], params)
            session = next(s for s in self.sessions.values() if s["metadata"]["checkout_attempt"] == key)
            if self.lose_response:
                self.lose_response = False
                raise TimeoutError("Stripe created the session but response was lost")
            return copy.deepcopy(session)

    def get(self, path):
        with self.lock:
            if path.startswith("subscriptions?"):
                return {"data":[copy.deepcopy(self.legacy_subscription)] if self.legacy_subscription else [], "has_more":False}
            if path.startswith("checkout/sessions?"):
                return {"data":copy.deepcopy(list(self.sessions.values())), "has_more":False}
            if path.startswith("checkout/sessions/"):
                return copy.deepcopy(self.sessions[path.rsplit("/",1)[-1]])
            if path.startswith("subscriptions/"):
                if self.legacy_subscription and path.endswith(self.legacy_subscription["id"]):
                    return copy.deepcopy(self.legacy_subscription)
                session = next(s for s in self.sessions.values() if s["subscription"] == path.rsplit("/",1)[-1])
                return {"id":session["subscription"], "customer":session["customer"], "status":self.subscription_status,
                    "current_period_end":time.time()+86400, "metadata":{"email":self.owner,"product":"quantradar_pro",
                    "checkout_attempt":session["metadata"]["checkout_attempt"]},
                    "items":{"data":[{"id":"si_one", "price":{"id":"price_monthly"}}]}}
            raise AssertionError(path)

    def start(self, interval="monthly"):
        return subscription_checkout.start(self.owner, plan="pro", interval=interval)

    def test_concurrent_clicks_share_customer_and_only_payable_session(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.start(), range(6)))
        self.assertEqual(len({r["id"] for r in results}), 1)
        self.assertEqual(len(self.sessions), 1)
        self.assertEqual(len(self.customer_keys), 1)

    def test_response_loss_recovers_same_attempt_after_new_connection(self):
        self.lose_response = True
        with self.assertRaises(TimeoutError):
            self.start()
        result = self.start()
        self.assertEqual(result["id"], "cs_1")
        self.assertEqual(len(self.sessions), 1)

    def test_changing_interval_expires_old_link_before_new_one(self):
        first = self.start()
        second = self.start("yearly")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(self.sessions[first["id"]]["status"], "expired")
        self.assertEqual(sum(s["status"] == "open" for s in self.sessions.values()), 1)

    def test_completed_payment_without_webhook_opens_portal(self):
        first = self.start()
        self.sessions[first["id"]].update(status="complete", subscription="sub_first")
        result = self.start("yearly")
        self.assertTrue(result["billing_portal"])
        self.assertEqual(users.resolve_plan(self.owner), "pro")
        self.assertEqual(len(self.sessions), 1)

    def test_unknown_expiration_never_starts_replacement(self):
        first = self.start()
        with mock.patch.object(stripe_billing, "stripe_post", side_effect=TimeoutError("expiration result unknown")):
            with self.assertRaises(TimeoutError):
                self.start("yearly")
        self.assertEqual(len(self.sessions), 1)
        self.assertEqual(self.sessions[first["id"]]["status"], "open")

    def test_uncertain_old_attempt_recovers_by_metadata_without_recreating(self):
        self.lose_response = True
        with self.assertRaises(TimeoutError):
            self.start()
        with paid_delivery.database() as db:
            db.execute("UPDATE subscription_checkouts SET created_at=1")
        result = self.start()
        self.assertEqual(result["id"], "cs_1")
        self.assertEqual(len(self.sessions), 1)

    def test_current_cancellation_allows_a_new_subscription(self):
        first = self.start()
        self.sessions[first["id"]].update(status="complete", subscription="sub_first")
        self.subscription_status = "canceled"
        second = self.start()
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(self.customer_keys), 1)

    def test_legacy_remote_subscription_is_reconciled_before_new_checkout(self):
        self.legacy_subscription = {"id":"sub_legacy", "customer":"cus_0", "status":"active",
            "current_period_end":time.time()+86400, "metadata":{},
            "items":{"data":[{"id":"si_legacy", "price":{"id":"price_monthly"}}]}}
        result = self.start()
        self.assertTrue(result["billing_portal"])
        self.assertEqual(len(self.sessions), 0)
        self.assertEqual(users.resolve_plan(self.owner), "pro")

    def test_definitively_rejected_coupon_can_retry_without_discount(self):
        def create(**params):
            if params["coupon_id"]:
                raise stripe_billing.StripeRequestError(400, {"type":"invalid_request_error", "code":"resource_missing", "param":"discounts[0][coupon]"})
            return self.create(**params)
        with mock.patch.object(stripe_billing, "create_checkout_session", side_effect=create), mock.patch.object(paid_delivery, "report_credit", return_value=None):
            result = subscription_checkout.start(self.owner, plan="pro", interval="monthly", coupon_id="revoked_coupon")
        self.assertEqual(result["id"], "cs_1")
        self.assertEqual(len(self.sessions), 1)
        self.assertIsNone(next(iter(self.keys.values()))["coupon_id"])


class StripeCheckoutErrorTests(unittest.TestCase):
    def test_real_http_helper_preserves_definitive_coupon_validation_error(self):
        error = urllib.error.HTTPError("https://api.stripe.com/v1/checkout/sessions", 400, "Bad Request", {},
            io.BytesIO(json.dumps({"error":{"type":"invalid_request_error", "code":"resource_missing", "param":"discounts[0][coupon]"}}).encode()))
        with mock.patch.dict(os.environ, {"STRIPE_SECRET_KEY":"sk_test_fixture", "STRIPE_PRICE_ID_MONTHLY":"price_fixture"}), mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(stripe_billing.StripeRequestError) as caught:
                stripe_billing.create_checkout_session(customer_email="test@example.com", coupon_id="missing", idempotency_key="test-key")
        self.assertTrue(caught.exception.coupon_rejected)
