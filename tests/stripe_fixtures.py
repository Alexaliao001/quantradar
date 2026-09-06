"""Stripe subscription response fixtures; never contact or charge a real account."""
import os
import time
from unittest import mock


def mock_subscription(case, email, *, status="active", plan="pro", customer="cus_test"):
    price = "price_portfolio_test" if plan == "portfolio_pro" else "price_monthly_test"
    sub = {"id": "sub_test", "customer": customer, "status": status,
           "metadata": {"email": email, "product": "quantradar_" + plan},
           "current_period_end": int(time.time()) + 86400,
           "items": {"data": [{"price": {"id": price}}]}}
    env = mock.patch.dict(os.environ, {"STRIPE_PRICE_ID_MONTHLY": "price_monthly_test",
                                      "STRIPE_PRICE_ID_PORTFOLIO_PRO_MONTHLY": "price_portfolio_test"})
    env.start(); case.addCleanup(env.stop)
    network = mock.patch("app.stripe_billing.stripe_get", return_value=sub)
    network.start(); case.addCleanup(network.stop)
    return sub
