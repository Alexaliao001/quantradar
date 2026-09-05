"""Minimal Stripe Checkout + webhook (stdlib). Optional — only if secret key present."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.auth import public_base_url

CHECKOUT_PLANS = frozenset({"pro", "portfolio_pro"})


class StripeRequestError(RuntimeError):
    def __init__(self, status: int, error: dict):
        super().__init__(str(error.get("message") or "Stripe request failed"))
        self.coupon_rejected = status == 400 and error.get("type") == "invalid_request_error" and (
            error.get("code") == "coupon_expired" or
            (error.get("code") == "resource_missing" and str(error.get("param") or "").startswith("discounts")))


def stripe_secret() -> str:
    return (
        os.environ.get("QUANTRADAR_STRIPE_SECRET_KEY", "").strip()
        or os.environ.get("STRIPE_SECRET_KEY", "").strip()
    )


def stripe_configured() -> bool:
    return bool(stripe_secret())


def webhook_secret() -> str:
    return (
        os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
        or os.environ.get("QUANTRADAR_STRIPE_WEBHOOK_SECRET", "").strip()
    )


def normalize_checkout_plan(plan: str | None) -> str:
    plan_n = (plan or "pro").strip().lower().replace("-", "_")
    if plan_n in {"portfolio", "portfolio_pro"}:
        return "portfolio_pro"
    return "pro"


def stripe_product_slug(plan: str) -> str:
    return "quantradar_portfolio_pro" if plan == "portfolio_pro" else "quantradar_pro"


def plan_from_product(product: str | None) -> str:
    slug = str(product or "").strip().lower()
    if slug in {"quantradar_portfolio_pro", "portfolio_pro"}:
        return "portfolio_pro"
    return "pro"


def price_id_for_interval(interval: str | None) -> str:
    """Resolve Stripe Price ID for monthly|yearly. Falls back to STRIPE_PRICE_ID."""
    iv = (interval or "monthly").strip().lower()
    if iv in {"year", "yearly", "annual", "annually"}:
        return (
            os.environ.get("STRIPE_PRICE_ID_YEARLY", "").strip()
            or os.environ.get("QUANTRADAR_STRIPE_PRICE_ID_YEARLY", "").strip()
        )
    return (
        os.environ.get("STRIPE_PRICE_ID_MONTHLY", "").strip()
        or os.environ.get("QUANTRADAR_STRIPE_PRICE_ID_MONTHLY", "").strip()
        or os.environ.get("STRIPE_PRICE_ID", "").strip()
        or os.environ.get("QUANTRADAR_STRIPE_PRICE_ID", "").strip()
    )


def price_id_report() -> str:
    return (
        os.environ.get("STRIPE_PRICE_ID_REPORT", "").strip()
        or os.environ.get("QUANTRADAR_STRIPE_PRICE_ID_REPORT", "").strip()
    )


def price_id_bump() -> str:
    return (
        os.environ.get("STRIPE_PRICE_ID_BUMP", "").strip()
        or os.environ.get("QUANTRADAR_STRIPE_PRICE_ID_BUMP", "").strip()
    )

def price_id_for_plan(plan: str | None, interval: str | None = None) -> str:
    """Resolve Stripe Price ID for checkout plan + interval."""
    plan_n = normalize_checkout_plan(plan)
    if plan_n == "portfolio_pro":
        return (
            os.environ.get("STRIPE_PRICE_ID_PORTFOLIO_PRO_MONTHLY", "").strip()
            or os.environ.get("QUANTRADAR_STRIPE_PRICE_ID_PORTFOLIO_PRO_MONTHLY", "").strip()
        )
    return price_id_for_interval(interval)


def create_checkout_session(
    *,
    customer_email: str | None = None,
    price_id: str | None = None,
    interval: str | None = None,
    plan: str | None = "pro",
    mode: str = "subscription",
    coupon_id: str | None = None,
    customer_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Create a Stripe Checkout Session. Returns {id, url, plan}."""
    secret = stripe_secret()
    if not secret:
        raise RuntimeError("Stripe not configured")
    plan_n = normalize_checkout_plan(plan)
    if plan_n == "portfolio_pro":
        iv = "monthly"
    else:
        iv = (interval or "monthly").strip().lower()
        if iv in {"year", "yearly", "annual", "annually"}:
            iv = "yearly"
        else:
            iv = "monthly"
    price = (price_id or price_id_for_plan(plan_n, iv)).strip()
    if not price:
        if plan_n == "portfolio_pro":
            raise RuntimeError(
                "Stripe Price ID not configured — set STRIPE_PRICE_ID_PORTFOLIO_PRO_MONTHLY"
            )
        raise RuntimeError(
            "Stripe Price ID not configured — set STRIPE_PRICE_ID_MONTHLY / STRIPE_PRICE_ID_YEARLY"
        )
    product = stripe_product_slug(plan_n)
    base = public_base_url()
    data: dict[str, str] = {
        "mode": "subscription",
        "success_url": f"{base}/?checkout=success",
        "cancel_url": f"{base}/pricing?checkout=cancel",
        "allow_promotion_codes": "true",
        "line_items[0][price]": price,
        "line_items[0][quantity]": "1",
    }
    if customer_email:
        if customer_id:
            data["customer"] = customer_id
        else:
            data["customer_email"] = customer_email
        data["client_reference_id"] = customer_email
        data["metadata[email]"] = customer_email
        data["metadata[interval]"] = iv
        data["metadata[plan]"] = plan_n
        data["metadata[product]"] = product
        # Stripe does not copy session metadata onto the subscription — required for cancel→free.
        data["subscription_data[metadata][email]"] = customer_email
        data["subscription_data[metadata][interval]"] = iv
        data["subscription_data[metadata][plan]"] = plan_n
        data["subscription_data[metadata][product]"] = product
        if idempotency_key:
            data["metadata[checkout_attempt]"] = idempotency_key
            data["subscription_data[metadata][checkout_attempt]"] = idempotency_key

    if coupon_id and plan_n == "pro" and (idempotency_key or coupon_redeemable(coupon_id)):
        data.pop("allow_promotion_codes", None)
        data["discounts[0][coupon]"] = coupon_id

    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "QuantRadar-Stripe/0.5",
            **({"Idempotency-Key": idempotency_key} if idempotency_key else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        try:
            error = json.loads(detail).get("error") or {}
        except (ValueError, AttributeError):
            error = {}
        raise StripeRequestError(exc.code, error) from exc
    return {
        "id": obj.get("id"),
        "url": obj.get("url"),
        "raw_status": obj.get("status"),
        "interval": iv,
        "plan": plan_n,
    }


def create_report_checkout(*, customer_email: str, with_bump: bool = False, order: dict | None = None) -> dict[str, Any]:
    """One-time $9 deep report (+ optional $5 CSV/priority order bump).

    Payment mode, never subscription — no negative-option surface at all.
    """
    secret = stripe_secret()
    if not secret:
        raise RuntimeError("Stripe not configured")
    report_price = price_id_report()
    if not report_price:
        raise RuntimeError("STRIPE_PRICE_ID_REPORT not configured")
    if order is None or order["owner"] != customer_email or bool(order["bump"]) != with_bump:
        raise ValueError("A saved report order is required before checkout")
    if order.get("checkout_id"):
        return {"id": order["checkout_id"], "url": order["checkout_url"], "order_id": order["id"], "product": "report"}
    base = public_base_url()
    data: dict[str, str] = {
        "mode": "payment",
        "success_url": f"{base}/reports?order={order['id']}",
        "cancel_url": f"{base}/pricing?checkout=cancel",
        "line_items[0][price]": report_price,
        "line_items[0][quantity]": "1",
        "customer_email": customer_email,
        "client_reference_id": customer_email,
        "metadata[email]": customer_email,
        "metadata[product]": "quantradar_report",
        "metadata[order_id]": order["id"],
        "metadata[ticker]": order["ticker"],
        "metadata[as_of]": order["as_of"],
        "custom_text[submit][message]": f"{order['ticker']} report · snapshot as of {order['as_of']} · one-time payment.",
        "payment_intent_data[metadata][order_id]": order["id"],
        "payment_intent_data[metadata][product]": "quantradar_report",
    }
    bump_price = price_id_bump()
    if with_bump and not bump_price:
        raise ValueError("The CSV add-on price is not configured")
    if with_bump and bump_price:
        data["line_items[1][price]"] = bump_price
        data["line_items[1][quantity]"] = "1"
        data["metadata[bump]"] = "1"
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "QuantRadar-Stripe/0.5",
            "Idempotency-Key": "report-checkout-" + order["id"],
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:800]
        raise RuntimeError(f"stripe checkout failed: {exc.code} {detail}") from exc
    from app import paid_delivery
    paid_delivery.attach_checkout(order["id"], obj)
    return {"id": obj.get("id"), "url": obj.get("url"), "product": "report", "order_id": order["id"]}


def create_credit_coupon(email: str, amount_cents: int = 900, *, order_id: str | None = None, paid_at: float | None = None) -> str | None:
    """Once-only coupon crediting the $9 report toward Pro's first month.

    Expires in 7 days — the credit is a real, time-boxed incentive, and the
    countdown shown to the buyer is truthful.
    """
    secret = stripe_secret()
    if not secret:
        return None
    if not order_id or paid_at is None:
        raise ValueError("A paid order is required to issue report credit")
    expires = int(paid_at) + 7 * 24 * 3600
    data = urllib.parse.urlencode(
        {
            "id": "qr-report-" + order_id,
            "amount_off": str(amount_cents),
            "currency": "usd",
            "duration": "once",
            "max_redemptions": "1",
            "redeem_by": str(expires),
            "name": "QuantRadar report credit",
            "metadata[email]": email,
            "metadata[order_id]": order_id,
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/coupons",
        data=data,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "QuantRadar-Stripe/0.5",
            "Idempotency-Key": "report-credit-" + order_id,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
        return str(obj.get("id") or "") or None
    except urllib.error.HTTPError as exc:
        if exc.code in {400, 409}:
            try:
                existing = stripe_get("coupons/" + urllib.parse.quote("qr-report-" + order_id, safe=""))
                if (existing.get("metadata") or {}).get("order_id") == order_id:
                    return str(existing["id"])
            except Exception:
                pass
        return None
    except Exception:
        return None


def coupon_redeemable(coupon_id: str | None) -> bool:
    """True only if the coupon exists and Stripe would still accept it
    (not expired by redeem_by, not exhausted max_redemptions)."""
    secret = stripe_secret()
    cid = (coupon_id or "").strip()
    if not secret or not cid:
        return False
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/coupons/{cid}",
        headers={"Authorization": f"Bearer {secret}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
    except Exception:
        return False
    if obj.get("valid") is False:
        return False
    redeem_by = obj.get("redeem_by")
    if isinstance(redeem_by, (int, float)) and time.time() > redeem_by:
        return False
    max_red = obj.get("max_redemptions")
    times = obj.get("times_redeemed") or 0
    if isinstance(max_red, int) and times >= max_red:
        return False
    return True


def revoke_credit_coupon(coupon_id: str | None) -> bool:
    if not coupon_id:
        return True
    if not stripe_secret():
        return False
    request = urllib.request.Request(
        "https://api.stripe.com/v1/coupons/" + urllib.parse.quote(coupon_id, safe=""),
        headers={"Authorization": "Bearer " + stripe_secret()}, method="DELETE")
    try:
        with urllib.request.urlopen(request, timeout=20):
            return True
    except urllib.error.HTTPError as exc:
        return exc.code == 404
    except Exception:
        return False


def pro_checkout_with_credit(
    *, customer_email: str, interval: str = "monthly", coupon_id: str | None = None,
    plan: str = "pro",
) -> dict[str, Any]:
    return create_checkout_session(
        customer_email=customer_email, interval=interval, plan=plan,
        coupon_id=coupon_id if plan == "pro" else None,
    )


def verify_webhook_signature(payload: bytes, sig_header: str | None, *, tolerance_sec: int = 300) -> bool:
    """Verify Stripe-Signature header (t=...,v1=...)."""
    secret = webhook_secret()
    if not secret or not sig_header:
        return False
    parts: dict[str, list[str]] = {}
    for item in sig_header.split(","):
        item = item.strip()
        if "=" not in item:
            continue
        k, _, v = item.partition("=")
        parts.setdefault(k.strip(), []).append(v.strip())
    try:
        timestamp = int((parts.get("t") or [""])[0])
    except ValueError:
        return False
    if abs(int(time.time()) - timestamp) > tolerance_sec:
        return False
    signed = f"{timestamp}.".encode() + payload
    expect = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    for got in parts.get("v1") or []:
        if hmac.compare_digest(expect, got):
            return True
    return False


def _email_from_checkout_session(session: dict[str, Any]) -> str | None:
    email = (
        session.get("customer_email")
        or session.get("client_reference_id")
        or (session.get("metadata") or {}).get("email")
        or (session.get("customer_details") or {}).get("email")
    )
    if isinstance(email, str) and "@" in email:
        return email.strip().lower()
    return None


def _plan_from_metadata(meta: dict[str, Any] | None) -> str:
    if not isinstance(meta, dict):
        return "pro"
    if meta.get("plan"):
        return normalize_checkout_plan(str(meta.get("plan")))
    return plan_from_product(str(meta.get("product") or ""))


def stripe_get(path: str) -> dict[str, Any]:
    secret = stripe_secret()
    if not secret:
        raise RuntimeError("Stripe is not configured")
    request = urllib.request.Request("https://api.stripe.com/v1/" + path,
                                     headers={"Authorization": f"Bearer {secret}"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def stripe_post(path: str, data: dict, *, idempotency_key: str) -> dict[str, Any]:
    request = urllib.request.Request("https://api.stripe.com/v1/" + path,
        data=urllib.parse.urlencode(data).encode(), method="POST",
        headers={"Authorization": "Bearer " + stripe_secret(), "Content-Type": "application/x-www-form-urlencoded",
                 "Idempotency-Key": idempotency_key})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def create_billing_portal(email: str, *, plan: str | None = None, interval: str | None = None) -> dict:
    from app import paid_delivery, users
    account = users.get_user(email) or {}
    with paid_delivery.database() as db:
        row = db.execute("SELECT * FROM subscriptions WHERE owner=? AND status NOT IN ('canceled','incomplete_expired') ORDER BY updated_at DESC LIMIT 1", (users.normalize_email(email),)).fetchone()
    customer = row["customer_id"] if row else account.get("stripe_customer_id")
    if not customer:
        raise ValueError("No Stripe subscription is linked to this account")
    data = {"customer": str(customer), "return_url": public_base_url() + "/pricing"}
    configuration = os.environ.get("STRIPE_PORTAL_CONFIGURATION_ID", "").strip()
    if configuration:
        data["configuration"] = configuration
    if plan and row:
        subscription = stripe_get("subscriptions/" + urllib.parse.quote(row["id"], safe=""))
        items = (subscription.get("items") or {}).get("data") or []
        price = price_id_for_plan(plan, interval)
        if not price:
            raise ValueError("Selected plan is not configured")
        if len(items) == 1 and items[0].get("id"):
            data.update({"flow_data[type]": "subscription_update_confirm",
                         "flow_data[subscription_update_confirm][subscription]": row["id"],
                         "flow_data[subscription_update_confirm][items][0][id]": items[0]["id"],
                         "flow_data[subscription_update_confirm][items][0][price]": price,
                         "flow_data[subscription_update_confirm][items][0][quantity]": "1"})
    request = urllib.request.Request("https://api.stripe.com/v1/billing_portal/sessions",
        data=urllib.parse.urlencode(data).encode(),
        headers={"Authorization": "Bearer " + stripe_secret(), "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        session = json.loads(response.read().decode())
    return {"id": session["id"], "url": session["url"], "billing_portal": True}


def _sync_subscription(db, subscription_id: str, *, expected_owner: str | None = None) -> dict[str, Any]:
    # Read current Stripe state while the event transaction serializes handlers.
    # Delivery order and event.created cannot reliably order subscription changes.
    if not subscription_id.startswith("sub_"):
        raise ValueError("subscription ID required")
    subscription = stripe_get("subscriptions/" + urllib.parse.quote(subscription_id, safe=""))
    metadata = subscription.get("metadata") or {}
    known_products = {"quantradar_pro", "quantradar_portfolio_pro"}
    items = (subscription.get("items") or {}).get("data") or []
    prices = {price_id_for_interval("monthly"): "pro", price_id_for_interval("yearly"): "pro",
              price_id_for_plan("portfolio_pro"): "portfolio_pro"}
    prices.pop("", None)
    if metadata.get("product") not in known_products and not any(
        (item.get("price", {}).get("id") if isinstance(item.get("price"), dict) else item.get("price")) in prices for item in items
    ):
        return {"ok": True, "action": "ignored", "reason": "unrelated_product"}
    if len(items) != 1:
        return {"ok": False, "error": "unsupported_subscription_items"}
    price = items[0].get("price") or {}
    price_id = price.get("id") if isinstance(price, dict) else price
    plan = prices.get(price_id)
    if plan is None:
        return {"ok": False, "error": "unrecognized_subscription_price"}
    from app.users import normalize_email, find_email_by_stripe_customer
    customer = subscription.get("customer")
    customer = customer.get("id") if isinstance(customer, dict) else customer
    prior = db.execute("SELECT owner FROM subscriptions WHERE id=?", (subscription_id,)).fetchone()
    email = metadata.get("email") or (prior["owner"] if prior else None) or find_email_by_stripe_customer(customer) or expected_owner
    if not email:
        return {"ok": False, "error": "no_email"}
    email = normalize_email(email)
    if expected_owner and email != normalize_email(expected_owner):
        raise ValueError("Subscription owner does not match the checkout account")
    previously_active = db.execute("SELECT 1 FROM subscriptions WHERE owner=? AND status IN ('active','trialing') AND paid_through>? LIMIT 1", (email, time.time())).fetchone() is not None
    paid_through = subscription.get("current_period_end") or items[0].get("current_period_end") or subscription.get("trial_end") or 0
    status = str(subscription.get("status") or "unknown")
    db.execute("""INSERT INTO subscriptions VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
        owner=excluded.owner,customer_id=excluded.customer_id,plan=excluded.plan,price_id=excluded.price_id,
        status=excluded.status,paid_through=excluded.paid_through,updated_at=excluded.updated_at""",
        (subscription_id, email, customer, plan, price_id, status, float(paid_through), time.time()))
    if metadata.get("checkout_attempt"):
        db.execute("UPDATE subscription_checkouts SET state='complete' WHERE owner=? AND id=?", (email, metadata["checkout_attempt"]))
    effective = {row[0] for row in db.execute("SELECT plan FROM subscriptions WHERE owner=? AND status IN ('active','trialing') AND paid_through>?", (email, time.time()))}
    plan = "portfolio_pro" if "portfolio_pro" in effective else "pro" if "pro" in effective else "free"
    return {"ok": True, "action": "plan_" + plan, "plan": plan, "email": email, "customer_id": customer,
            "activated": not previously_active and plan != "free"}


def apply_webhook_event(event: dict[str, Any]) -> dict[str, Any]:
    """Only verified events enter here; persist each effect once on durable storage."""
    from app import paid_delivery
    etype = str(event.get("type") or "")
    obj = (event.get("data") or {}).get("object") or {}
    if not isinstance(obj, dict):
        return {"ok": False, "error": "bad_event_object", "type": etype}

    def apply(db):
        if etype in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            metadata = obj.get("metadata") or {}
            product = metadata.get("product")
            if product not in {"quantradar_report", "quantradar_pro", "quantradar_portfolio_pro"}:
                return {"ok": True, "action": "ignored", "reason": "unrelated_product"}
            if obj.get("payment_status") not in {"paid", "no_payment_required"}:
                return {"ok": True, "action": "awaiting_payment"}
            if product == "quantradar_report":
                return paid_delivery.mark_report_paid(db, obj, paid_at=event.get("created"))
            if obj.get("mode") != "subscription":
                return {"ok": False, "error": "wrong_checkout_mode"}
            return _sync_subscription(db, str(obj.get("subscription") or ""))
        if etype.startswith("customer.subscription."):
            return _sync_subscription(db, str(obj.get("id") or ""))
        if etype in {"invoice.paid", "invoice.payment_failed", "invoice.payment_action_required"}:
            subscription_id = obj.get("subscription") or ((obj.get("parent") or {}).get("subscription_details") or {}).get("subscription")
            if subscription_id:
                return _sync_subscription(db, str(subscription_id))
        if etype == "charge.refunded":
            return paid_delivery.record_refund(db, obj)
        if etype in {"checkout.session.expired", "checkout.session.async_payment_failed"}:
            db.execute("UPDATE report_orders SET payment_state='expired' WHERE checkout_id=? AND payment_state='unpaid'", (obj.get("id"),))
        return {"ok": True, "action": "ignored", "type": etype}

    result = paid_delivery.event_once(str(event.get("id") or ""), etype, apply)
    if result.get("ok") and result.get("action", "").startswith("plan_") and not result.get("duplicate"):
        from app.users import set_plan
        set_plan(result["email"], result["plan"], stripe_customer_id=result.get("customer_id"))
    return result
