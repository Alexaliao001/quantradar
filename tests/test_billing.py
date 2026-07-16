"""Stripe checkout interval + webhook plan upgrades."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app import auth as authlib  # noqa: E402
from app import stripe_billing  # noqa: E402
from app.server import Handler  # noqa: E402
from app import users as users_mod  # noqa: E402


class PriceIntervalTests(unittest.TestCase):
    def test_price_id_for_interval(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "STRIPE_PRICE_ID_MONTHLY": "price_m",
                "STRIPE_PRICE_ID_YEARLY": "price_y",
                "STRIPE_PRICE_ID": "price_legacy",
            },
            clear=False,
        ):
            self.assertEqual(stripe_billing.price_id_for_interval("monthly"), "price_m")
            self.assertEqual(stripe_billing.price_id_for_interval("yearly"), "price_y")
            self.assertEqual(stripe_billing.price_id_for_interval(None), "price_m")


class WebhookSigTests(unittest.TestCase):
    def test_verify_signature(self) -> None:
        secret = "whsec_test_secret"
        payload = b'{"type":"checkout.session.completed"}'
        ts = str(int(time.time()))
        signed = f"{ts}.".encode() + payload
        sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        header = f"t={ts},v1={sig}"
        with mock.patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": secret}, clear=False):
            self.assertTrue(stripe_billing.verify_webhook_signature(payload, header))
            self.assertFalse(stripe_billing.verify_webhook_signature(payload, "t=1,v1=bad"))


class BillingHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        users_mod.USERS_PATH = Path(self._tmpdir.name) / "users.json"
        os.environ["SESSION_SECRET"] = "test-session-secret-for-billing"
        os.environ["QUANTRADAR_STRIPE_WEBHOOK_TEST"] = "1"
        os.environ.pop("QUANTRADAR_STRIPE_SECRET_KEY", None)
        os.environ.pop("STRIPE_SECRET_KEY", None)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        os.environ["PUBLIC_BASE_URL"] = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        os.environ.pop("QUANTRADAR_STRIPE_WEBHOOK_TEST", None)
        self._tmpdir.cleanup()

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _post(self, path: str, body: dict, *, cookie: str | None = None) -> tuple[int, dict]:
        headers = {"content-type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        req = urllib.request.Request(
            self._url(path),
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def test_checkout_requires_login_and_stripe(self) -> None:
        code, body = self._post("/api/billing/checkout", {"interval": "monthly"})
        self.assertEqual(code, 401)
        self.assertEqual(body.get("error"), "login_required")

        token = authlib.mint_session(sub="u", email="pay@test.local", plan="free")
        cookie = f"{authlib.COOKIE_NAME}={token}"
        code, body = self._post("/api/billing/checkout", {"interval": "yearly"}, cookie=cookie)
        self.assertEqual(code, 503)
        self.assertEqual(body.get("error"), "stripe_not_configured")

    def test_webhook_sets_pro(self) -> None:
        users_mod.register_user("buyer@test.local", "password12", name="Buyer")
        self.assertEqual(users_mod.resolve_plan("buyer@test.local"), "free")
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer_email": "buyer@test.local",
                    "payment_status": "paid",
                    "status": "complete",
                    "metadata": {"email": "buyer@test.local", "product": "quantradar_pro"},
                }
            },
        }
        code, body = self._post("/api/billing/webhook", event)
        self.assertEqual(code, 200, body)
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(body.get("action"), "plan_pro")
        self.assertEqual(users_mod.resolve_plan("buyer@test.local"), "pro")

        # status exposes pro when session email matches
        token = authlib.mint_session(sub="b", email="buyer@test.local", plan="free")
        req = urllib.request.Request(
            self._url("/api/auth/status"),
            headers={"Cookie": f"{authlib.COOKIE_NAME}={token}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            status = json.loads(r.read().decode())
        self.assertEqual(status["user"]["plan"], "pro")

    def test_webhook_unpaid_rejected(self) -> None:
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer_email": "unpaid@test.local",
                    "payment_status": "unpaid",
                    "status": "complete",
                    "metadata": {"email": "unpaid@test.local"},
                }
            },
        }
        code, body = self._post("/api/billing/webhook", event)
        self.assertEqual(code, 422, body)
        self.assertEqual(body.get("error"), "not_paid")
        self.assertEqual(users_mod.resolve_plan("unpaid@test.local"), "free")

    def test_billing_status_shape(self) -> None:
        with urllib.request.urlopen(self._url("/api/billing/status"), timeout=5) as r:
            body = json.loads(r.read().decode())
        self.assertTrue(body.get("ok"))
        self.assertIn("monthly", body.get("intervals") or [])
        self.assertEqual(body["prices"]["yearly"], "$249")
        self.assertIn(body.get("pro_value"), {"supporter_until_mount", "live_ready"})
        self.assertIn("live_available", body)
        self.assertTrue(body.get("pro_value_note"))


class ApplyEventUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        users_mod.USERS_PATH = Path(self._tmpdir.name) / "users.json"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_subscription_deleted_downgrades(self) -> None:
        users_mod.set_plan("gone@test.local", "pro")
        out = stripe_billing.apply_webhook_event(
            {
                "type": "customer.subscription.deleted",
                "data": {"object": {"metadata": {"email": "gone@test.local"}}},
            }
        )
        self.assertEqual(out.get("action"), "plan_free")
        self.assertEqual(users_mod.resolve_plan("gone@test.local"), "free")

    def test_subscription_deleted_without_email_fails(self) -> None:
        users_mod.set_plan("stuck@test.local", "pro")
        out = stripe_billing.apply_webhook_event(
            {
                "type": "customer.subscription.deleted",
                "data": {"object": {"metadata": {}}},
            }
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "no_email")
        self.assertEqual(users_mod.resolve_plan("stuck@test.local"), "pro")


class StripeStubClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        users_mod.USERS_PATH = Path(self._tmpdir.name) / "users.json"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_register_claims_stripe_stub_keeps_pro(self) -> None:
        users_mod.set_plan("stub@test.local", "pro")
        pub = users_mod.register_user("stub@test.local", "password12", name="Stub")
        self.assertEqual(pub["plan"], "pro")
        authed = users_mod.authenticate("stub@test.local", "password12")
        self.assertEqual(authed["email"], "stub@test.local")
        self.assertEqual(authed["plan"], "pro")


class CheckoutPayloadTests(unittest.TestCase):
    def test_subscription_metadata_includes_email(self) -> None:
        captured: dict[str, Any] = {}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self) -> bytes:
                return json.dumps(
                    {"id": "cs_test", "url": "https://checkout.stripe.com/test", "status": "open"}
                ).encode()

        def fake_urlopen(req, timeout=30):  # noqa: ANN001
            captured["body"] = req.data.decode() if isinstance(req.data, bytes) else str(req.data)
            return FakeResp()

        with mock.patch.dict(
            os.environ,
            {
                "QUANTRADAR_STRIPE_SECRET_KEY": "sk_test_x",
                "STRIPE_PRICE_ID_MONTHLY": "price_m",
                "PUBLIC_BASE_URL": "https://quantradar.one",
            },
            clear=False,
        ):
            with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                out = stripe_billing.create_checkout_session(
                    customer_email="buyer@test.local",
                    interval="monthly",
                )
        self.assertEqual(out.get("id"), "cs_test")
        body = urllib.parse.parse_qs(captured["body"])
        self.assertEqual(body.get("metadata[email]"), ["buyer@test.local"])
        self.assertEqual(body.get("subscription_data[metadata][email]"), ["buyer@test.local"])
        self.assertEqual(body.get("mode"), ["subscription"])


if __name__ == "__main__":
    unittest.main()
