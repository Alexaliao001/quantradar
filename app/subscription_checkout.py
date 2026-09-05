"""One recoverable subscription checkout per account, across clicks and restarts."""

from __future__ import annotations

import time
import uuid
import urllib.parse

from app import paid_delivery, stripe_billing as stripe, users


class CouponRejected(Exception):
    pass


def _reconcile_existing(owner: str, customer: str):
    """Legacy customers may have paid before the local subscription ledger existed."""
    prices = {stripe.price_id_for_plan("pro", "monthly"), stripe.price_id_for_plan("pro", "yearly"), stripe.price_id_for_plan("portfolio_pro")}
    prices.discard("")
    path = "subscriptions?customer=" + urllib.parse.quote(customer, safe="") + "&status=all&limit=100"
    for _ in range(20):
        page = stripe.stripe_get(path)
        for subscription in page["data"]:
            related = (subscription.get("metadata") or {}).get("product") in {"quantradar_pro", "quantradar_portfolio_pro"}
            related = related or any((item.get("price") or {}).get("id") in prices for item in (subscription.get("items") or {}).get("data", []))
            if related and subscription.get("status") not in {"canceled", "incomplete_expired"}:
                with paid_delivery.database() as db:
                    db.execute("BEGIN IMMEDIATE")
                    result = stripe._sync_subscription(db, subscription["id"], expected_owner=owner)
                    if not result.get("ok") or result.get("email") != owner:
                        raise RuntimeError("Existing subscription reconciliation is incomplete")
        if not page.get("has_more"):
            return
        path = path.split("&starting_after=")[0] + "&starting_after=" + urllib.parse.quote(page["data"][-1]["id"], safe="")
    raise RuntimeError("Existing subscriptions could not be fully reconciled")


def _customer(owner: str) -> str:
    existing = (users.get_user(owner) or {}).get("stripe_customer_id")
    with paid_delivery.database() as db:
        db.execute("INSERT OR IGNORE INTO stripe_customers VALUES(?,?,?)", (owner, uuid.uuid4().hex, existing))
        row = db.execute("SELECT * FROM stripe_customers WHERE owner=?", (owner,)).fetchone()
    if row["customer_id"]:
        return row["customer_id"]
    customer = stripe.stripe_post("customers", {"email": owner, "metadata[product]": "quantradar"},
                                  idempotency_key="qr-customer-" + row["request_id"])
    if not str(customer.get("id", "")).startswith("cus_"):
        raise RuntimeError("Stripe customer creation is incomplete")
    with paid_delivery.database() as db:
        db.execute("UPDATE stripe_customers SET customer_id=? WHERE owner=? AND customer_id IS NULL", (customer["id"], owner))
        return db.execute("SELECT customer_id FROM stripe_customers WHERE owner=?", (owner,)).fetchone()[0]


def _current_attempt(owner: str, plan: str, interval: str, price: str, coupon: str | None, customer: str):
    with paid_delivery.database() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM subscriptions WHERE owner=? AND status NOT IN ('canceled','incomplete_expired') LIMIT 1", (owner,)).fetchone():
            return None
        row = db.execute("SELECT * FROM subscription_checkouts WHERE owner=?", (owner,)).fetchone()
        if row is None or row["state"] == "closed":
            db.execute("""INSERT INTO subscription_checkouts(owner,id,plan,interval,price_id,coupon_id,customer_id,created_at)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(owner) DO UPDATE SET
                id=excluded.id,plan=excluded.plan,interval=excluded.interval,price_id=excluded.price_id,
                coupon_id=excluded.coupon_id,customer_id=excluded.customer_id,checkout_id=NULL,checkout_url=NULL,
                state='creating',created_at=excluded.created_at""",
                (owner, "qr-sub-" + uuid.uuid4().hex, plan, interval, price, coupon, customer, time.time()))
            row = db.execute("SELECT * FROM subscription_checkouts WHERE owner=?", (owner,)).fetchone()
        return dict(row)


def _session(attempt: dict) -> dict:
    if attempt["checkout_id"]:
        return stripe.stripe_get("checkout/sessions/" + urllib.parse.quote(attempt["checkout_id"], safe=""))
    # Stripe may prune idempotency keys after 24h. Recover an old uncertain result
    # by metadata; never blindly create a second payable session after that window.
    if time.time() - attempt["created_at"] >= 23 * 3600:
        path = "checkout/sessions?customer=" + urllib.parse.quote(attempt["customer_id"], safe="") + "&limit=100"
        for _ in range(20):
            page = stripe.stripe_get(path)
            for session in page["data"]:
                if (session.get("metadata") or {}).get("checkout_attempt") == attempt["id"]:
                    return session
            if not page.get("has_more"):
                break
            path = path.split("&starting_after=")[0] + "&starting_after=" + urllib.parse.quote(page["data"][-1]["id"], safe="")
        raise ValueError("A previous checkout needs reconciliation. Please contact support; no new payment was started.")
    try:
        session = stripe.create_checkout_session(customer_email=attempt["owner"], customer_id=attempt["customer_id"],
            price_id=attempt["price_id"], plan=attempt["plan"], interval=attempt["interval"],
            coupon_id=attempt["coupon_id"], idempotency_key=attempt["id"])
    except stripe.StripeRequestError as error:
        if not error.coupon_rejected or not attempt["coupon_id"]:
            raise
        with paid_delivery.database() as db:
            db.execute("UPDATE subscription_checkouts SET state='closed' WHERE owner=? AND id=? AND checkout_id IS NULL", (attempt["owner"], attempt["id"]))
        raise CouponRejected from error
    if not session.get("id") or not session.get("url"):
        raise RuntimeError("Checkout creation is incomplete. Retry to recover the same checkout.")
    with paid_delivery.database() as db:
        updated = db.execute("UPDATE subscription_checkouts SET checkout_id=?,checkout_url=?,state=CASE WHEN state='complete' THEN state ELSE 'open' END WHERE owner=? AND id=?",
                             (session["id"], session["url"], attempt["owner"], attempt["id"]))
        if updated.rowcount != 1:
            raise ValueError("Checkout changed in another window. Please retry.")
    # Fetch authoritative state: a lost response can hide a completed payment.
    return stripe.stripe_get("checkout/sessions/" + urllib.parse.quote(session["id"], safe=""))


def start(owner: str, *, plan: str, interval: str, coupon_id: str | None = None) -> dict:
    owner = users.normalize_email(owner)
    plan = stripe.normalize_checkout_plan(plan)
    interval = "yearly" if plan == "pro" and interval.lower() in {"year", "yearly", "annual", "annually"} else "monthly"
    price = stripe.price_id_for_plan(plan, interval)
    if not price:
        raise ValueError("This plan is temporarily unavailable")
    customer = _customer(owner)
    with paid_delivery.database() as db:
        prior = db.execute("SELECT state FROM subscription_checkouts WHERE owner=?", (owner,)).fetchone()
    if prior is None or prior["state"] == "closed":
        _reconcile_existing(owner, customer)
    for _ in range(3):
        attempt = _current_attempt(owner, plan, interval, price, coupon_id if plan == "pro" else None, customer)
        if attempt is None:
            return stripe.create_billing_portal(owner, plan=plan, interval=interval)
        try:
            session = _session(attempt)
        except CouponRejected:
            coupon_id = paid_delivery.report_credit(owner)
            continue
        status = session.get("status")
        if status == "complete":
            subscription = session.get("subscription")
            if not subscription:
                raise ValueError("Your payment is being confirmed. Please retry shortly; no second subscription was started.")
            with paid_delivery.database() as db:
                db.execute("BEGIN IMMEDIATE")
                result = stripe._sync_subscription(db, str(subscription), expected_owner=owner)
                if not result.get("ok") or result.get("email") != owner or not result.get("action", "").startswith("plan_"):
                    raise RuntimeError("Subscription confirmation is pending")
            if paid_delivery.has_open_subscription(owner):
                return stripe.create_billing_portal(owner, plan=plan, interval=interval)
            status = "expired"  # A completed checkout is not payable again after cancellation.
        if status == "open" and (attempt["plan"], attempt["interval"]) == (plan, interval):
            if not session.get("url"):
                raise RuntimeError("Checkout URL is unavailable")
            return {"id": session["id"], "url": session["url"], "plan": plan, "interval": interval}
        if status == "open":
            expired = stripe.stripe_post("checkout/sessions/" + urllib.parse.quote(session["id"], safe="") + "/expire", {},
                                         idempotency_key="expire-" + attempt["id"])
            status = expired.get("status")
        if status != "expired":
            raise ValueError("Previous checkout status is unresolved. Please retry; no new payment was started.")
        with paid_delivery.database() as db:
            db.execute("UPDATE subscription_checkouts SET state='closed' WHERE owner=? AND id=?", (owner, attempt["id"]))
    raise ValueError("Checkout changed in another window. Please retry.")
