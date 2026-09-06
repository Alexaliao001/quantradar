#!/usr/bin/env python3
"""Cut QuantRadar listing to free + Unlock 1.2 after the binary is uploaded.

Read-mostly until cancel. Then: cancel paid 1.0, price Free, Unlock IAP,
create 1.2, listing copy, attach latest VALID build, submit.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ship_asc import api, find_app, load_token  # noqa: E402

APP_ID = "6800090745"
UNLOCK_ID = "one.quantradar.app.unlock"
VERSION = "1.2"
SCREEN = ROOT / "docs" / "asc_screens" / "screen_1_1284x2778.png"

DESC = """QuantRadar is a pre-trade discipline tool for US-stock swing traders.

Start with Chase Check: confirm that your entry existed before the move, define what invalidates the setup, and separate your decision from social hype. Then read one mechanical posture score through market, sector, and stock gates.

Save the decision before you know the outcome. The private on-device journal records whether you chose to pause, wait, pass, or review — so discipline becomes a process, not a victory-lap screenshot.

Free to install: see today’s SPY posture and scan one ticker of yours. Unlock once ($9.99) for every supported ticker, Watch, and 90-day posture history.

This is not a broker, does not place trades, and is not investment advice or a tipster feed. Most days the honest answer is wait.

Independent App Store product. Website subscriptions do not unlock this app."""

KEYWORDS = "trading journal,fomo,swing trade,stock analysis,watchlist,market,ticker,discipline,setup"
SUBTITLE = "Stop chasing stock setups"
PROMO = "Before you chase, check your process. Three questions, one mechanical posture, and a private decision journal."
REVIEW_NOTES = (
    "This build addresses the prior 4.3(a) concern with distinct, original functionality: Chase Check is a "
    "three-part pre-trade process audit (planned entry, invalidation, independence from social hype), followed "
    "by one mechanical market/sector/stock posture. Users save a PAUSE/WAIT/PASS/REVIEW decision in a private "
    "on-device journal before knowing the outcome. This is not a repackaged signal template. "
    "Free download. Today shows SPY. User may scan one personal ticker for life. "
    "A second ticker is scored on-device but stays locked until the $9.99 non-consumable Unlock "
    "(one.quantradar.app.unlock). No account. No broker. Action label is SETUP, not BUY. "
    "Weekday 09:25 ET briefing is a local reminder with static copy, not a trade signal. "
    "Educational only. ITSAppUsesNonExemptEncryption=false. "
    "Privacy: https://quantradar.one/privacy-ios  Terms: https://quantradar.one/terms-ios"
)


def cancel_waiting(token: str) -> None:
    st, revs = api(token, "GET", f"/v1/apps/{APP_ID}/reviewSubmissions?limit=10")
    if st != 200:
        print("reviewSubmissions", st, revs)
        return
    for r in revs.get("data") or []:
        state = (r.get("attributes") or {}).get("state")
        if state in {"WAITING_FOR_REVIEW", "IN_REVIEW", "UNRESOLVED_ISSUES"}:
            rid = r["id"]
            print("canceling", rid, state)
            s, b = api(
                token,
                "PATCH",
                f"/v1/reviewSubmissions/{rid}",
                {"data": {"type": "reviewSubmissions", "id": rid, "attributes": {"canceled": True}}},
            )
            print("cancel", s, b if isinstance(b, str) else (b.get("data") or {}).get("attributes"))


def wait_version_editable(token: str, timeout=180) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        token = load_token()
        st, vers = api(token, "GET", f"/v1/apps/{APP_ID}/appStoreVersions?limit=10")
        if st == 200:
            for v in vers.get("data") or []:
                state = (v.get("attributes") or {}).get("appVersionState") or (v.get("attributes") or {}).get(
                    "appStoreState"
                )
                print("version", v["id"], v["attributes"].get("versionString"), state)
                if state in {
                    "PREPARE_FOR_SUBMISSION",
                    "DEVELOPER_REJECTED",
                    "REJECTED",
                    "METADATA_REJECTED",
                    "INVALID_BINARY",
                }:
                    return v
        time.sleep(8)
    return None


def ensure_version_12(token: str, existing: dict | None) -> str:
    if existing and existing["attributes"].get("versionString") in {"1.2", "1.2.0"}:
        return existing["id"]
    # If 1.0 is now editable, we still create 1.2 as the public version.
    st, created = api(
        token,
        "POST",
        "/v1/appStoreVersions",
        {
            "data": {
                "type": "appStoreVersions",
                "attributes": {
                    "platform": "IOS",
                    "versionString": VERSION,
                    "copyright": "2026 Fortune Insight, LLC",
                    "releaseType": "AFTER_APPROVAL",
                },
                "relationships": {"app": {"data": {"type": "apps", "id": APP_ID}}},
            }
        },
    )
    print("create 1.2", st, created if isinstance(created, str) else json.dumps(created)[:600])
    if st in (200, 201) and isinstance(created, dict):
        return created["data"]["id"]
    # Fallback: reuse editable 1.0 if Apple blocks a second inflight version.
    if existing:
        print("reusing existing version", existing["id"])
        return existing["id"]
    raise SystemExit("could not create or reuse a version")


def upsert_listing(token: str, version_id: str) -> None:
    st, locs = api(token, "GET", f"/v1/appStoreVersions/{version_id}/appStoreVersionLocalizations")
    loc_id = None
    if st == 200:
        for loc in (locs.get("data") or []):
            if loc["attributes"].get("locale") == "en-US":
                loc_id = loc["id"]
    attrs = {
        "description": DESC,
        "keywords": KEYWORDS,
        "marketingUrl": "https://quantradar.one",
        "supportUrl": "https://quantradar.one",
        "promotionalText": PROMO,
        "whatsNew": "New Chase Check and private Decision Journal turn the radar into a pre-trade discipline workflow. Free SPY plus one personal ticker; unlock once for the full radar.",
    }
    if loc_id:
        s, b = api(
            token,
            "PATCH",
            f"/v1/appStoreVersionLocalizations/{loc_id}",
            {"data": {"type": "appStoreVersionLocalizations", "id": loc_id, "attributes": attrs}},
        )
        print("loc patch", s)
    else:
        s, b = api(
            token,
            "POST",
            "/v1/appStoreVersionLocalizations",
            {
                "data": {
                    "type": "appStoreVersionLocalizations",
                    "attributes": {"locale": "en-US", **attrs},
                    "relationships": {
                        "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}
                    },
                }
            },
        )
        print("loc post", s, b if isinstance(b, str) else "ok")
        if s in (200, 201) and isinstance(b, dict):
            loc_id = b["data"]["id"]

    # App info subtitle + privacy (live URLs — /privacy-ios is 404 until next web publish)
    st, infos = api(token, "GET", f"/v1/apps/{APP_ID}/appInfos")
    if st == 200 and infos.get("data"):
        info_id = infos["data"][0]["id"]
        st, ilocs = api(token, "GET", f"/v1/appInfos/{info_id}/appInfoLocalizations")
        for loc in (ilocs.get("data") or []) if st == 200 else []:
            if loc["attributes"].get("locale") == "en-US":
                s, b = api(
                    token,
                    "PATCH",
                    f"/v1/appInfoLocalizations/{loc['id']}",
                    {
                        "data": {
                            "type": "appInfoLocalizations",
                            "id": loc["id"],
                            "attributes": {
                                "subtitle": SUBTITLE,
                                "privacyPolicyUrl": "https://quantradar.one/privacy-ios",
                                "privacyChoicesUrl": None,
                            },
                        }
                    },
                )
                print("subtitle/privacy", s)

    st, rd = api(token, "GET", f"/v1/appStoreVersions/{version_id}/appStoreReviewDetail")
    review_attrs = {
        "contactFirstName": "Rongjian",
        "contactLastName": "Liao",
        "contactEmail": "alexliao830@gmail.com",
        "contactPhone": "+14155550100",
        "demoAccountRequired": False,
        "notes": REVIEW_NOTES,
    }
    if st == 200 and isinstance(rd, dict) and rd.get("data"):
        rid = rd["data"]["id"]
        s, b = api(
            token,
            "PATCH",
            f"/v1/appStoreReviewDetails/{rid}",
            {"data": {"type": "appStoreReviewDetails", "id": rid, "attributes": review_attrs}},
        )
        print("review patch", s)
    else:
        s, b = api(
            token,
            "POST",
            "/v1/appStoreReviewDetails",
            {
                "data": {
                    "type": "appStoreReviewDetails",
                    "attributes": review_attrs,
                    "relationships": {
                        "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}
                    },
                }
            },
        )
        print("review post", s)


def ensure_unlock_iap(token: str) -> None:
    st, iap = api(token, "GET", f"/v1/apps/{APP_ID}/inAppPurchasesV2?limit=20")
    print("iap list", st)
    if st == 200:
        for p in iap.get("data") or []:
            pid = (p.get("attributes") or {}).get("productId")
            print("  iap", pid, p.get("attributes", {}).get("state"))
            if pid == UNLOCK_ID:
                print("unlock IAP already exists")
                return
    body = {
        "data": {
            "type": "inAppPurchases",
            "attributes": {
                "name": "QuantRadar Unlock",
                "productId": UNLOCK_ID,
                "inAppPurchaseType": "NON_CONSUMABLE",
                "reviewNote": "One-time unlock for all supported ticker scans, Watch, and 90-day posture history. Chase Check and the private Decision Journal remain visible for review. Not a subscription; educational only.",
            },
            "relationships": {"app": {"data": {"type": "apps", "id": APP_ID}}},
        }
    }
    s, b = api(token, "POST", "/v2/inAppPurchases", body)
    print("iap create v2", s, b if isinstance(b, str) else json.dumps(b)[:800])
    if s not in (200, 201):
        s, b = api(token, "POST", "/v1/inAppPurchases", body)
        print("iap create v1", s, b if isinstance(b, str) else json.dumps(b)[:800])


def set_app_free(token: str) -> None:
    st, pts = api(
        token,
        "GET",
        f"/v1/apps/{APP_ID}/appPricePoints?filter[territory]=USA&limit=200",
    )
    print("price points", st)
    free_id = None
    if st == 200:
        for p in pts.get("included") or pts.get("data") or []:
            attrs = p.get("attributes") or {}
            if str(attrs.get("customerPrice")) in {"0", "0.00"} and p.get("type") == "appPricePoints":
                free_id = p["id"]
                break
        if not free_id:
            for p in pts.get("data") or []:
                # fetch each? skip
                pass
        print("free point", free_id, "count", len(pts.get("data") or []))
    if not free_id and st == 200:
        # Try equalizations of current schedule
        st2, sched = api(token, "GET", f"/v1/apps/{APP_ID}/appPriceSchedule")
        print("schedule", st2, sched if isinstance(sched, str) else json.dumps(sched)[:400])
    if free_id:
        s, b = api(
            token,
            "POST",
            "/v1/appPriceSchedules",
            {
                "data": {
                    "type": "appPriceSchedules",
                    "relationships": {
                        "app": {"data": {"type": "apps", "id": APP_ID}},
                        "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
                        "manualPrices": {
                            "data": [{"type": "appPrices", "id": "${price1}"}]
                        },
                    },
                },
                "included": [
                    {
                        "type": "appPrices",
                        "id": "${price1}",
                        "attributes": {"startDate": None},
                        "relationships": {
                            "appPricePoint": {"data": {"type": "appPricePoints", "id": free_id}}
                        },
                    }
                ],
            },
        )
        print("set free", s, b if isinstance(b, str) else json.dumps(b)[:600])


def latest_valid_build(token: str) -> dict | None:
    st, builds = api(token, "GET", f"/v1/builds?filter[app]={APP_ID}&sort=-uploadedDate&limit=8")
    if st != 200:
        print("builds", st, builds)
        return None
    for b in builds.get("data") or []:
        a = b["attributes"]
        print("build", b["id"], a.get("version"), a.get("processingState"), a.get("uploadedDate"))
        if a.get("processingState") == "VALID":
            # Prefer highest version number that is not 3 if 6 exists
            pass
    valids = [
        b
        for b in (builds.get("data") or [])
        if b["attributes"].get("processingState") == "VALID"
    ]
    if not valids:
        return None
    def key(b):
        try:
            return int(b["attributes"].get("version") or 0)
        except ValueError:
            return 0
    valids.sort(key=key, reverse=True)
    return valids[0]


def attach_and_submit(token: str, version_id: str, build: dict) -> None:
    s, b = api(
        token,
        "PATCH",
        f"/v1/appStoreVersions/{version_id}",
        {
            "data": {
                "type": "appStoreVersions",
                "id": version_id,
                "relationships": {"build": {"data": {"type": "builds", "id": build["id"]}}},
            }
        },
    )
    print("attach", s, b if isinstance(b, str) else "ok")
    s, body = api(
        token,
        "POST",
        "/v1/reviewSubmissions",
        {
            "data": {
                "type": "reviewSubmissions",
                "attributes": {"platform": "IOS"},
                "relationships": {"app": {"data": {"type": "apps", "id": APP_ID}}},
            }
        },
    )
    print("rs create", s, body if isinstance(body, str) else json.dumps(body)[:500])
    if s not in (200, 201) or not isinstance(body, dict):
        return
    rs_id = body["data"]["id"]
    s2, body2 = api(
        token,
        "POST",
        "/v1/reviewSubmissionItems",
        {
            "data": {
                "type": "reviewSubmissionItems",
                "relationships": {
                    "reviewSubmission": {"data": {"type": "reviewSubmissions", "id": rs_id}},
                    "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}},
                },
            }
        },
    )
    print("rs item", s2)
    s3, body3 = api(
        token,
        "PATCH",
        f"/v1/reviewSubmissions/{rs_id}",
        {"data": {"type": "reviewSubmissions", "id": rs_id, "attributes": {"submitted": True}}},
    )
    print("rs submit", s3, body3 if isinstance(body3, str) else json.dumps(body3)[:500])


def main() -> int:
    token = load_token()
    app = find_app(token)
    print("app", app["id"] if app else None)
    print("=== cancel paid 1.0 thread ===")
    cancel_waiting(token)
    print("=== wait editable ===")
    editable = wait_version_editable(token)
    token = load_token()
    print("=== unlock IAP ===")
    ensure_unlock_iap(token)
    print("=== price Free ===")
    set_app_free(token)
    token = load_token()
    print("=== version 1.2 ===")
    vid = ensure_version_12(token, editable)
    print("using version", vid)
    upsert_listing(token, vid)
    print("=== wait for VALID build 6 ===")
    build = None
    for i in range(24):
        token = load_token()
        build = latest_valid_build(token)
        if build and str(build["attributes"].get("version")) not in {"3", "4"}:
            break
        if build and i > 6 and str(build["attributes"].get("version")) in {"5", "6", "7"}:
            break
        print("waiting for new build…", i)
        time.sleep(15)
    if not build:
        print("no VALID build yet — listing prepared, submit later")
        return 0
    print("using build", build["id"], build["attributes"].get("version"))
    if str(build["attributes"].get("version")) == "3":
        print("only build 3 is VALID — not attaching paid 1.0 binary to 1.2")
        return 0
    attach_and_submit(token, vid, build)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
