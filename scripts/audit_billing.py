"""Billing checkout-session audit: verify currency/amount/lines for every path.

Creates real Stripe Checkout Sessions in LIVE mode but NEVER charges
(sessions are inspect-only; they expire if abandoned). Each scenario asserts
the exact USD amounts and line counts that the buyer would see.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Load .env like the server does
from app.envload import load_dotenv  # noqa: E402

load_dotenv()

import urllib.request  # noqa: E402
from app import stripe_billing as sb  # noqa: E402

SECRET = sb.stripe_secret()
assert SECRET, "no stripe key"


def get_session(session_id: str) -> dict:
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/checkout/sessions/{session_id}?expand[]=line_items",
        headers={"Authorization": f"Bearer {SECRET}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def summarize(sess: dict) -> dict:
    items = (sess.get("line_items") or {}).get("data") or []
    lines = []
    for it in items:
        price = it.get("price") or {}
        lines.append(
            {
                "price_id": price.get("id"),
                "currency": (price.get("currency") or "").upper(),
                "amount": (price.get("unit_amount") or 0) / 100,
                "type": price.get("type"),
                "interval": (price.get("recurring") or {}).get("interval"),
                "qty": it.get("quantity"),
            }
        )
    return {
        "mode": sess.get("mode"),
        "currency": (sess.get("currency") or "").upper(),
        "amount_total": (sess.get("amount_total") or 0) / 100,
        "line_count": len(lines),
        "lines": lines,
        "has_discounts": bool(sess.get("discounts")),
        "allow_promo": sess.get("allow_promotion_codes"),
    }


def check(name: str, fn) -> bool:
    try:
        sess = fn()
        sid = sess["id"]
        full = get_session(sid)
        s = summarize(full)
        print(f"\n[{name}] session={sid}")
        print(json.dumps(s, indent=2))
        return s
    except Exception as exc:
        print(f"\n[{name}] ERROR: {exc}")
        FAILURES.append(f"{name}: {exc}")
        return None


FAILURES: list[str] = []


def main() -> None:
    email = "billing-audit@quantradar.one"
    results = {}

    results["report_no_bump"] = check(
        "Report $9 (no bump)",
        lambda: sb.create_report_checkout(customer_email=email, with_bump=False),
    )
    results["report_with_bump"] = check(
        "Report $9 + $5 bump",
        lambda: sb.create_report_checkout(customer_email=email, with_bump=True),
    )
    results["pro_monthly_no_coupon"] = check(
        "Pro monthly (no coupon)",
        lambda: sb.pro_checkout_with_credit(customer_email=email, interval="monthly", coupon_id=None),
    )
    results["pro_yearly_no_coupon"] = check(
        "Pro yearly (no coupon)",
        lambda: sb.pro_checkout_with_credit(customer_email=email, interval="yearly", coupon_id=None),
    )

    # coupon path — mint a real coupon then attach
    coupon = sb.create_credit_coupon(email)
    print(f"\nminted coupon: {coupon}")
    results["pro_monthly_with_coupon"] = check(
        "Pro monthly WITH $9 credit coupon",
        lambda: sb.pro_checkout_with_credit(customer_email=email, interval="monthly", coupon_id=coupon),
    )

    # Assertions
    failures = list(FAILURES)

    def expect(name, key, got, want):
        ok = got == want
        if not ok:
            failures.append(f"{name}.{key}: got {got!r} want {want!r}")

    # Sessions that failed to create are hard failures.
    for name, r in results.items():
        if r is None:
            failures.append(f"{name}: session creation failed")

    r = results["report_no_bump"]
    if r:
        expect("report", "currency", r["currency"], "USD")
        expect("report", "amount_total", r["amount_total"], 9.0)
        expect("report", "line_count", r["line_count"], 1)
        expect("report", "mode", r["mode"], "payment")

    r = results["report_with_bump"]
    if r:
        expect("report+bump", "currency", r["currency"], "USD")
        expect("report+bump", "amount_total", r["amount_total"], 14.0)
        expect("report+bump", "line_count", r["line_count"], 2)
        expect("report+bump", "mode", r["mode"], "payment")

    r = results["pro_monthly_no_coupon"]
    if r:
        expect("pro/mo", "currency", r["currency"], "USD")
        expect("pro/mo", "amount_total", r["amount_total"], 29.0)
        expect("pro/mo", "mode", r["mode"], "subscription")
        expect("pro/mo", "interval", r["lines"][0]["interval"], "month")

    r = results["pro_yearly_no_coupon"]
    if r:
        expect("pro/yr", "currency", r["currency"], "USD")
        expect("pro/yr", "amount_total", r["amount_total"], 249.0)
        expect("pro/yr", "interval", r["lines"][0]["interval"], "year")

    r = results["pro_monthly_with_coupon"]
    if r:
        expect("pro/mo+coupon", "currency", r["currency"], "USD")
        expect("pro/mo+coupon", "amount_total", r["amount_total"], 20.0)  # 29 - 9
        expect("pro/mo+coupon", "has_discounts", r["has_discounts"], True)

    print("\n" + "=" * 50)
    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("ALL BILLING CHECKOUT ASSERTIONS PASSED")


if __name__ == "__main__":
    main()
