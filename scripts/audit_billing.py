#!/usr/bin/env python3
"""Inspect real Stripe TEST Checkout amounts; never charge or load local .env.

Set a test secret, test Price IDs, and QR_STRIPE_TEST_ACCOUNT explicitly.
This verifies Checkout creation only. Payment, webhook, renewal, refund, and
portal acceptance still require separate Stripe sandbox end-to-end checks.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
import uuid
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from app import stripe_billing as stripe


def main() -> int:
    if not stripe.stripe_secret().startswith(("sk_test_", "rk_test_")):
        raise SystemExit("TEST key required in the environment; live mode is refused. No .env was loaded.")
    expected = os.environ.get("QR_STRIPE_TEST_ACCOUNT", "")
    if not expected.startswith("acct_") or stripe.stripe_get("account")["id"] != expected:
        raise SystemExit("Set QR_STRIPE_TEST_ACCOUNT to the intended sandbox account.")
    prices = [(stripe.price_id_report(), 900, None), (stripe.price_id_bump(), 500, None),
              (stripe.price_id_for_plan("pro", "monthly"), 2900, "month"),
              (stripe.price_id_for_plan("pro", "yearly"), 24900, "year"),
              (stripe.price_id_for_plan("portfolio_pro"), 9900, "month")]
    for price_id, amount, interval in prices:
        if not price_id.startswith("price_"):
            raise SystemExit("Configure all five test Price IDs before running this audit.")
        price = stripe.stripe_get("prices/" + price_id)
        assert price["livemode"] is False and price["active"] is True
        assert price["unit_amount"] == amount and price["currency"] == "usd"
        assert (price.get("recurring") or {}).get("interval") == interval
    os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1:8769"
    run_id = "qr-audit-" + uuid.uuid4().hex
    email = "billing-audit@example.com"
    sessions, coupons = [], []
    try:
        scenarios = []
        for bump in (False, True):
            order = {"id": run_id + str(int(bump)), "owner": email, "bump": bump,
                     "ticker": "TESTCO", "as_of": "2026-09-04"}
            # Synthetic test order; never touch production or local account storage.
            with mock.patch("app.paid_delivery.attach_checkout"):
                session = stripe.create_report_checkout(customer_email=email, with_bump=bump, order=order)
            sessions.append(session["id"])
            scenarios.append((session, 1400 if bump else 900, "payment", 2 if bump else 1))
        coupon = stripe.create_credit_coupon(email, order_id=run_id, paid_at=time.time())
        assert coupon, "Test coupon creation failed"
        coupons.append(coupon)
        for plan, interval, credit, amount in (("pro", "monthly", None, 2900),
                ("pro", "yearly", None, 24900), ("pro", "monthly", coupon, 2000),
                ("portfolio_pro", "monthly", None, 9900)):
            session = stripe.create_checkout_session(customer_email=email, plan=plan,
                interval=interval, coupon_id=credit, idempotency_key=run_id + str(len(sessions)))
            sessions.append(session["id"])
            scenarios.append((session, amount, "subscription", 1))
        for session, amount, mode, count in scenarios:
            full = stripe.stripe_get("checkout/sessions/" + session["id"] + "?expand[]=line_items")
            assert full["livemode"] is False
            assert full["amount_total"] == amount and full["currency"] == "usd"
            assert full["mode"] == mode and len(full["line_items"]["data"]) == count
            print(json.dumps({"session": full["id"], "test_mode": True, "amount_cents": amount, "mode": mode}))
    finally:
        failures = []
        for session_id in sessions:
            try:
                stripe.stripe_post("checkout/sessions/" + session_id + "/expire", {}, idempotency_key="expire-" + session_id)
            except Exception:
                failures.append(session_id)
        for coupon in coupons:
            if not stripe.revoke_credit_coupon(coupon):
                failures.append(coupon)
        if failures:
            raise RuntimeError("Test cleanup incomplete: " + ", ".join(failures))
    print("PASS: test Checkout amounts only; no payment or webhook lifecycle was exercised.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
