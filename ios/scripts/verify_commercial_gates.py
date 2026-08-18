#!/usr/bin/env python3
"""Offline commercial-loop invariants for QuantRadar iOS (no Xcode required)."""

from __future__ import annotations

import json
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
    today = (ROOT / "QuantRadar/Views/TodayView.swift").read_text()
    onboarding = (ROOT / "QuantRadar/Views/OnboardingView.swift").read_text()
    settings = (ROOT / "QuantRadar/Views/SettingsView.swift").read_text()
    root_tab = (ROOT / "QuantRadar/App/RootTabView.swift").read_text()
    scorer = (ROOT / "QuantRadar/Services/FreeDataRadar.swift").read_text()
    radar = (ROOT / "QuantRadar/Services/RadarService.swift").read_text()
    launch = (ROOT / "docs/APP_STORE_LAUNCH.md").read_text()
    product = (ROOT / "docs/PRODUCT.md").read_text()
    verdict_card = (ROOT / "QuantRadar/Views/VerdictCardView.swift").read_text()

    for pid in (
        "one.quantradar.app.unlock",
        "one.quantradar.app.live.monthly",
        "one.quantradar.app.live.yearly",
    ):
        if pid not in access:
            bad(f"missing product id in AppAccess: {pid}")
        else:
            ok(f"AppAccess has {pid}")

    unlock_products = [
        p for p in storekit.get("products", []) if p.get("productID") == "one.quantradar.app.unlock"
    ]
    if not unlock_products or unlock_products[0].get("type") != "NonConsumable":
        bad("storekit unlock must be NonConsumable $9.99 product")
    else:
        ok("storekit unlock NonConsumable present")
        if unlock_products[0].get("displayPrice") != "9.99":
            bad(f"unlock price expected 9.99 got {unlock_products[0].get('displayPrice')}")
        else:
            ok("unlock displayPrice 9.99")

    class Preview:
        def __init__(self) -> None:
            self.claimed: str | None = None

        def can_scan(self, ticker: str, unlocked: bool) -> bool:
            t = ticker.strip().upper()
            if unlocked:
                return True
            if t == "SPY":
                return True
            if self.claimed:
                return self.claimed == t
            return bool(t)

        def claim(self, ticker: str, withheld: bool = False) -> None:
            t = ticker.strip().upper()
            if withheld or t == "SPY" or not t:
                return
            if self.claimed is None:
                self.claimed = t

    p = Preview()
    if not (
        p.can_scan("SPY", False)
        and p.can_scan("AAPL", False)
        and not (p.claim("AAPL") or p.can_scan("NVDA", False))
        and p.can_scan("AAPL", False)
        and p.can_scan("NVDA", True)
    ):
        bad("canScan mirror failed (SPY + one personal ticker)")
    else:
        ok("canScan free=SPY + one personal ticker / unlocked=any")

    for name, blob, needle in (
        ("SearchView", search, "showPaywall"),
        ("SearchView", search, "claimPreviewTickerIfNeeded"),
        ("RootTabView", root_tab, "effectiveUnlocked"),
        ("PaywallView", paywall, "Unlock any ticker"),
        ("OnboardingView", onboarding, "Open radar"),
        ("PurchaseStore", purchase, "purchaseUnlock"),
        ("TodayView", today, "Unlock any ticker"),
        ("VerdictCardView", verdict_card, "ShareLink"),
        ("SettingsView", settings, "privacyURL"),
        ("AppAccess", access, "privacy-ios"),
        ("AppAccess", access, "preview.personal_ticker"),
        ("FreeMechanicalScorer", scorer, 'action = "SETUP"'),
        ("WatchlistView", watch, "Remind if posture changes"),
        ("RadarService", radar, "Do not assign `latest`"),
    ):
        if needle not in blob:
            bad(f"{name} missing `{needle}`")
        else:
            ok(f"{name} contains `{needle}`")

    for name, blob, banned in (
        ("TodayView", today, "Massive"),
        ("TodayView", today, "$0 API"),
        ("PaywallView", paywall, "Live+"),
        ("PaywallView", paywall, "Massive"),
        ("PaywallView", paywall, "Stripe"),
        ("SearchView", search, "forceDemo"),
        ("OnboardingView", onboarding, "You already paid"),
        ("OnboardingView", onboarding, "Try free"),
        ("SettingsView", settings, "Live+ Monthly"),
        ("FreeMechanicalScorer", scorer, 'action = "BUY"'),
        ("WatchlistView", watch, "Watch is locked"),
    ):
        if banned in blob:
            bad(f"{name} still contains banned `{banned}`")
        else:
            ok(f"{name} has no `{banned}`")

    if 'MARKETING_VERSION: "1.1.0"' not in project or 'CURRENT_PROJECT_VERSION: "5"' not in project:
        bad("project.yml should be 1.1.0 / build 5")
    else:
        ok("project.yml 1.1.0 / 5")

    if "Do not touch ASC 1.0" not in launch:
        bad("APP_STORE_LAUNCH missing ASC 1.0 leave-alone note")
    else:
        ok("APP_STORE_LAUNCH protects ASC 1.0")

    if "one lifetime personal ticker" not in product:
        bad("PRODUCT.md should describe one personal ticker preview")
    else:
        ok("PRODUCT.md free-download + one personal ticker")

    if "Stock scanner: wait or act" not in launch:
        bad("APP_STORE_LAUNCH missing ASO subtitle")
    else:
        ok("APP_STORE_LAUNCH ASO subtitle")

    if FAIL:
        print(f"\n{FAIL} failure(s)")
        return 1
    print("\nAll commercial gate checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
