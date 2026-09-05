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
    today = (ROOT / "QuantRadar/Views/TodayView.swift").read_text()
    onboarding = (ROOT / "QuantRadar/Views/OnboardingView.swift").read_text()
    settings = (ROOT / "QuantRadar/Views/SettingsView.swift").read_text()
    root_tab = (ROOT / "QuantRadar/App/RootTabView.swift").read_text()
    scorer = (ROOT / "QuantRadar/Services/FreeDataRadar.swift").read_text()
    radar = (ROOT / "QuantRadar/Services/RadarService.swift").read_text()
    launch = (ROOT / "docs/APP_STORE_LAUNCH.md").read_text()
    product = (ROOT / "docs/PRODUCT.md").read_text()
    verdict_card = (ROOT / "QuantRadar/Views/VerdictCardView.swift").read_text()
    locked = (ROOT / "QuantRadar/Views/LockedVerdictView.swift").read_text()
    depth = (ROOT / "QuantRadar/Services/PostureDepth.swift").read_text()
    briefing = (ROOT / "QuantRadar/Services/DailyBriefing.swift").read_text()
    ledger = (ROOT / "QuantRadar/Services/DisciplineLedger.swift").read_text()
    chase = (ROOT / "QuantRadar/Services/ChaseCheck.swift").read_text()
    journal = (ROOT / "QuantRadar/Services/DecisionJournal.swift").read_text()
    widget = (ROOT / "QuantRadarWidget/QuantRadarWidget.swift").read_text()
    privacy = (ROOT / "QuantRadar/PrivacyInfo.xcprivacy").read_text()

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
        ("SearchView", search, "isPreviewLocked"),
        ("SearchView", search, "LockedVerdictView"),
        ("RootTabView", root_tab, "WatchlistView()"),
        ("WatchlistView", watch, "Unlock Watch"),
        ("PaywallView", paywall, "Unlock any ticker"),
        ("PaywallView", paywall, "founderPriceLine"),
        ("OnboardingView", onboarding, "Open radar"),
        ("PurchaseStore", purchase, "purchaseUnlock"),
        ("TodayView", today, "Unlock any ticker"),
        ("TodayView", today, "todayVerdict"),
        ("TodayView", today, "DailyBriefing"),
        ("VerdictCardView", verdict_card, "ShareLink"),
        ("VerdictCardView", verdict_card, "PostureStripView"),
        ("SettingsView", settings, "privacyURL"),
        ("AppAccess", access, "privacy-ios"),
        ("AppAccess", access, "preview.personal_ticker"),
        ("AppAccess", access, "founderPriceLine"),
        ("FreeMechanicalScorer", scorer, 'action = "SETUP"'),
        ("FreeMechanicalScorer", scorer, "earningsForced"),
        ("WatchlistView", watch, "Remind if posture changes"),
        ("RadarService", radar, "Do not assign `latest`"),
        ("RadarService", radar, "refreshToday"),
        ("LockedVerdictView", locked, "Unlock to see"),
        ("PostureDepth", depth, "historyDays"),
        ("DailyBriefing", briefing, "Today's radar is ready"),
        ("DisciplineLedger", ledger, "qr.discipline.streak"),
        ("ChaseCheck", chase, "PROCESS CLEAR"),
        ("DecisionJournal", journal, "qr.decision.journal"),
        ("SearchView", search, "DecisionCommitView"),
        ("WatchlistView", watch, "Decision journal"),
        ("Privacy manifest", privacy, "NSPrivacyAccessedAPICategoryUserDefaults"),
        ("Privacy manifest", privacy, "CA92.1"),
        ("Widget", widget, "QuantRadarSPY"),
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
        ("PaywallView", paywall, "countdown"),
        ("SearchView", search, "forceDemo"),
        ("OnboardingView", onboarding, "You already paid"),
        ("OnboardingView", onboarding, "Try free"),
        ("SettingsView", settings, "Live+ Monthly"),
        ("FreeMechanicalScorer", scorer, 'action = "BUY"'),
        ("WatchlistView", watch, "Watch is locked"),
        ("DailyBriefing", briefing, "hurry"),
        ("LockedVerdictView", locked, "BUY"),
    ):
        if banned in blob:
            bad(f"{name} still contains banned `{banned}`")
        else:
            ok(f"{name} has no `{banned}`")

    builds = re.findall(r'CURRENT_PROJECT_VERSION: "([0-9]+)"', project)
    versions = re.findall(r'MARKETING_VERSION: "([0-9.]+)"', project)
    if len(builds) != 2 or len(set(builds)) != 1 or int(builds[0]) < 1 or len(versions) != 2 or len(set(versions)) != 1:
        bad("App and Widget must have matching marketing and positive build versions")
    else:
        ok(f"App/Widget {versions[0]} / build {builds[0]}")

    if "WAITING_FOR_REVIEW" not in launch or "IAP" not in launch:
        bad("APP_STORE_LAUNCH must distinguish pending review and IAP submission")
    else:
        ok("APP_STORE_LAUNCH records pending review and existing IAP")

    if "one lifetime personal ticker" not in product:
        bad("PRODUCT.md should describe one personal ticker preview")
    else:
        ok("PRODUCT.md free-download + one personal ticker")

    if "Stop chasing stock setups" not in launch:
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
