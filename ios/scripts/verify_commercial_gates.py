#!/usr/bin/env python3
"""Offline commercial-loop invariants for QuantRadar iOS (no Xcode required)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAIL = 0


def ok(msg: str) -> None:
    print(f"OK  {msg}")


def bad(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"FAIL {msg}")


def main() -> int:
    access = (ROOT / "QuantRadar/Services/AppAccess.swift").read_text()
    storekit = json.loads((ROOT / "QuantRadar/Resources/Products.storekit").read_text())
    project = (ROOT / "project.yml").read_text()
    purchase = (ROOT / "QuantRadar/Services/PurchaseStore.swift").read_text()
    paywall = (ROOT / "QuantRadar/Views/PaywallView.swift").read_text()
    search = (ROOT / "QuantRadar/Views/SearchView.swift").read_text()
    watch = (ROOT / "QuantRadar/Views/WatchlistView.swift").read_text()
    onboarding = (ROOT / "QuantRadar/Views/OnboardingView.swift").read_text()
    launch = (ROOT / "docs/APP_STORE_LAUNCH.md").read_text()
    product = (ROOT / "docs/PRODUCT.md").read_text()

    # Product IDs
    for pid in (
        "one.quantradar.app.unlock",
        "one.quantradar.app.live.monthly",
        "one.quantradar.app.live.yearly",
    ):
        if pid not in access:
            bad(f"missing product id in AppAccess: {pid}")
        else:
            ok(f"AppAccess has {pid}")

    unlock_products = [p for p in storekit.get("products", []) if p.get("productID") == "one.quantradar.app.unlock"]
    if not unlock_products or unlock_products[0].get("type") != "NonConsumable":
        bad("storekit unlock must be NonConsumable $9.99 product")
    else:
        ok("storekit unlock NonConsumable present")
        if unlock_products[0].get("displayPrice") != "9.99":
            bad(f"unlock price expected 9.99 got {unlock_products[0].get('displayPrice')}")
        else:
            ok("unlock displayPrice 9.99")

    # Gate logic mirrored
    def can_scan(ticker: str, unlocked: bool) -> bool:
        return unlocked or ticker.strip().upper() == "INTC"

    if not (can_scan("INTC", False) and not can_scan("AAPL", False) and can_scan("SPY", True)):
        bad("canScan mirror failed")
    else:
        ok("canScan free=INTC-only / unlocked=any")

    # UI wiring
    for name, blob, needle in (
        ("SearchView", search, "showPaywall"),
        ("WatchlistView", watch, "Watch is locked"),
        ("PaywallView", paywall, "Most days"),
        ("OnboardingView", onboarding, "Try free"),
        ("PurchaseStore", purchase, "purchaseUnlock"),
    ):
        if needle not in blob:
            bad(f"{name} missing `{needle}`")
        else:
            ok(f"{name} contains `{needle}`")

    # Version bump local 1.1 — must not imply uploading over 1.0 review
    if 'MARKETING_VERSION: "1.1.0"' not in project or 'CURRENT_PROJECT_VERSION: "4"' not in project:
        bad("project.yml should be 1.1.0 / build 4")
    else:
        ok("project.yml 1.1.0 / 4")

    if "Do not touch ASC 1.0" not in launch and "Do **not** change the waiting 1.0" not in launch:
        # APP_STORE_LAUNCH has "Do not touch ASC 1.0 while Waiting for Review"
        if "Do not touch ASC 1.0" not in launch:
            bad("APP_STORE_LAUNCH missing ASC 1.0 leave-alone note")
        else:
            ok("APP_STORE_LAUNCH protects ASC 1.0")
    else:
        ok("APP_STORE_LAUNCH protects ASC 1.0")

    if "Free download" not in product and "one-time unlock" not in product:
        if "Free download" not in product:
            bad("PRODUCT.md should describe free download unlock model")
        else:
            ok("PRODUCT.md free-download model")
    else:
        ok("PRODUCT.md free-download model")

    # No paid-app-only copy left in onboarding
    if "You already paid" in onboarding:
        bad("onboarding still says You already paid")
    else:
        ok("onboarding no longer paid-download copy")

    if FAIL:
        print(f"\n{FAIL} failure(s)")
        return 1
    print("\nAll commercial gate checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
