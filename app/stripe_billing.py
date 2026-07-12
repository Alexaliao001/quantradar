"""Minimal Stripe Checkout (stdlib). Optional — only if secret key present."""

from __future__ import annotations

import json
import os
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


def create_checkout_session(
    *,
    customer_email: str | None = None,
    price_id: str | None = None,
    mode: str = "subscription",
) -> dict[str, Any]:
    """Create a Stripe Checkout Session. Returns {id, url}."""
    secret = stripe_secret()
    if not secret:
        raise RuntimeError("Stripe not configured")
    price = (price_id or os.environ.get("STRIPE_PRICE_ID", "")).strip()
    base = public_base_url()
    data: dict[str, str] = {
        "mode": mode if price else "payment",
        "success_url": f"{base}/?checkout=success",
        "cancel_url": f"{base}/login?checkout=cancel",
        "allow_promotion_codes": "true",
    }
    if customer_email:
        data["customer_email"] = customer_email
    if price:
        data["line_items[0][price]"] = price
        data["line_items[0][quantity]"] = "1"
        data["mode"] = "subscription"
    else:
        # Fallback one-time $29 product description if no price id
        data["mode"] = "payment"
        data["line_items[0][price_data][currency]"] = "usd"
        data["line_items[0][price_data][unit_amount]"] = "2900"
        data["line_items[0][price_data][product_data][name]"] = "QuantRadar Pro (monthly-equivalent)"
        data["line_items[0][quantity]"] = "1"

    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "QuantRadar-Stripe/0.4",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            obj = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:800]
        raise RuntimeError(f"stripe checkout failed: {exc.code} {detail}") from exc
    return {"id": obj.get("id"), "url": obj.get("url"), "raw_status": obj.get("status")}
