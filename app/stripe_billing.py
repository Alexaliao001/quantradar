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


def create_checkout_session(
    *,
    customer_email: str | None = None,
    price_id: str | None = None,
    interval: str | None = None,
    mode: str = "subscription",
) -> dict[str, Any]:
    """Create a Stripe Checkout Session. Returns {id, url}."""
    secret = stripe_secret()
    if not secret:
        raise RuntimeError("Stripe not configured")
    price = (price_id or price_id_for_interval(interval)).strip()
    if not price:
        raise RuntimeError(
            "Stripe Price ID not configured — set STRIPE_PRICE_ID_MONTHLY / STRIPE_PRICE_ID_YEARLY"
        )
    iv = (interval or "monthly").strip().lower()
    if iv in {"year", "yearly", "annual", "annually"}:
        iv = "yearly"
    else:
        iv = "monthly"
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
        data["customer_email"] = customer_email
        data["client_reference_id"] = customer_email
        data["metadata[email]"] = customer_email
        data["metadata[interval]"] = iv
        data["metadata[product]"] = "quantradar_pro"
        # Stripe does not copy session metadata onto the subscription — required for cancel→free.
        data["subscription_data[metadata][email]"] = customer_email
        data["subscription_data[metadata][interval]"] = iv
        data["subscription_data[metadata][product]"] = "quantradar_pro"

    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "QuantRadar-Stripe/0.5",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:800]
        raise RuntimeError(f"stripe checkout failed: {exc.code} {detail}") from exc
    return {
        "id": obj.get("id"),
        "url": obj.get("url"),
        "raw_status": obj.get("status"),
        "interval": iv,
    }


def create_report_checkout(*, customer_email: str, with_bump: bool = False) -> dict[str, Any]:
    """One-time $9 deep report (+ optional $5 CSV/priority order bump).

    Payment mode, never subscription — no negative-option surface at all.
    """
    secret = stripe_secret()
    if not secret:
        raise RuntimeError("Stripe not configured")
    report_price = price_id_report()
    if not report_price:
        raise RuntimeError("STRIPE_PRICE_ID_REPORT not configured")
    base = public_base_url()
    data: dict[str, str] = {
        "mode": "payment",
        "success_url": f"{base}/?checkout=report_success",
        "cancel_url": f"{base}/pricing?checkout=cancel",
        "line_items[0][price]": report_price,
        "line_items[0][quantity]": "1",
        "customer_email": customer_email,
        "client_reference_id": customer_email,
        "metadata[email]": customer_email,
        "metadata[product]": "quantradar_report",
    }
    bump_price = price_id_bump()
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
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:800]
        raise RuntimeError(f"stripe checkout failed: {exc.code} {detail}") from exc
    return {"id": obj.get("id"), "url": obj.get("url"), "product": "report"}


def create_credit_coupon(email: str, amount_cents: int = 900) -> str | None:
    """Once-only coupon crediting the $9 report toward Pro's first month.

    Expires in 7 days — the credit is a real, time-boxed incentive, and the
    countdown shown to the buyer is truthful.
    """
    secret = stripe_secret()
    if not secret:
        return None
    expires = int(time.time()) + 7 * 24 * 3600
    data = urllib.parse.urlencode(
        {
            "amount_off": str(amount_cents),
            "currency": "usd",
            "duration": "once",
            "max_redemptions": "1",
            "redeem_by": str(expires),
            "name": "QuantRadar report credit",
            "metadata[email]": email,
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/coupons",
        data=data,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "QuantRadar-Stripe/0.5",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
        return str(obj.get("id") or "") or None
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


def pro_checkout_with_credit(*, customer_email: str, interval: str, coupon_id: str | None) -> dict[str, Any]:
    secret = stripe_secret()
    if not secret:
        raise RuntimeError("Stripe not configured")
    price = price_id_for_interval(interval)
    if not price:
        raise RuntimeError("Stripe Price ID not configured")
    iv = "yearly" if (interval or "").lower().startswith("y") else "monthly"
    base = public_base_url()
    data: dict[str, str] = {
        "mode": "subscription",
        "success_url": f"{base}/?checkout=success",
        "cancel_url": f"{base}/pricing?checkout=cancel",
        "line_items[0][price]": price,
        "line_items[0][quantity]": "1",
        "customer_email": customer_email,
        "client_reference_id": customer_email,
        "metadata[email]": customer_email,
        "metadata[interval]": iv,
        "metadata[product]": "quantradar_pro",
        "subscription_data[metadata][email]": customer_email,
        "subscription_data[metadata][interval]": iv,
        "subscription_data[metadata][product]": "quantradar_pro",
    }
    if coupon_id and coupon_redeemable(coupon_id):
        data["discounts[0][coupon]"] = coupon_id
    else:
        # No valid server-side credit — allow buyer promo codes instead.
        data["allow_promotion_codes"] = "true"
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "QuantRadar-Stripe/0.5",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:800]
        raise RuntimeError(f"stripe checkout failed: {exc.code} {detail}") from exc
    return {"id": obj.get("id"), "url": obj.get("url"), "interval": iv}


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


def apply_webhook_event(event: dict[str, Any]) -> dict[str, Any]:
    """Apply plan changes from a verified Stripe event. Returns action summary."""
    from app.users import set_plan

    etype = str(event.get("type") or "")
    data_obj = (event.get("data") or {}).get("object") or {}
    if not isinstance(data_obj, dict):
        return {"ok": False, "error": "bad_event_object", "type": etype}

    if etype == "checkout.session.completed":
        email = _email_from_checkout_session(data_obj)
        if not email:
            return {"ok": False, "error": "no_email", "type": etype}
        payment_status = str(data_obj.get("payment_status") or "").strip().lower()
        if payment_status not in {"paid", "no_payment_required"}:
            return {
                "ok": False,
                "error": "not_paid",
                "type": etype,
                "status": payment_status or "missing",
            }
        meta = data_obj.get("metadata") if isinstance(data_obj.get("metadata"), dict) else {}
        product = str(meta.get("product") or "quantradar_pro")
        if product == "quantradar_report":
            # One-time $9 deep report: grant it and mint the $9→Pro credit.
            from app.users import grant_report

            grant_report(email, bump=bool(meta.get("bump")))
            coupon = create_credit_coupon(email)
            from app.users import set_report_coupon

            set_report_coupon(email, coupon)
            return {"ok": True, "action": "report_granted", "email": email, "type": etype}
        customer_id = data_obj.get("customer")
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("id")
        user = set_plan(
            email,
            "pro",
            stripe_customer_id=str(customer_id) if customer_id else None,
        )
        return {"ok": True, "action": "plan_pro", "email": email, "user": user, "type": etype}

    if etype in {
        "customer.subscription.deleted",
        "customer.subscription.paused",
    }:
        from app.users import find_email_by_stripe_customer

        email = None
        meta = data_obj.get("metadata") if isinstance(data_obj.get("metadata"), dict) else {}
        if meta.get("email"):
            email = str(meta["email"]).strip().lower()
        # Fallback: customer_email not always present on subscription objects
        if not email and data_obj.get("customer_email"):
            email = str(data_obj["customer_email"]).strip().lower()
        customer_id = data_obj.get("customer")
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("id")
        if not email and customer_id:
            email = find_email_by_stripe_customer(str(customer_id))
        if not email:
            return {"ok": False, "error": "no_email", "type": etype}
        user = set_plan(email, "free")
        return {"ok": True, "action": "plan_free", "email": email, "user": user, "type": etype}

    return {"ok": True, "action": "ignored", "type": etype}
