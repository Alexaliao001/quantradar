#!/usr/bin/env python3
"""Ship QuantRadar iOS to App Store Connect end-to-end (after app record exists).

Usage:
  /tmp/asc-venv/bin/python ios/scripts/ship_asc.py           # full ship
  /tmp/asc-venv/bin/python ios/scripts/ship_asc.py --wait    # poll until app exists, then ship
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
ARCHIVE = ROOT / "build" / "QuantRadar.xcarchive"
EXPORT_PLIST = ROOT / "build" / "ExportOptions.plist"
ICON = ROOT / "QuantRadar/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png"
SCREENSHOTS = [
    ROOT / "docs" / "test-03-today-fixed.png",
    ROOT / "docs" / "test-01-onboarding.png",
]

BUNDLE_ID = "one.quantradar.app"
APP_NAME = "QuantRadar"
SKU = "quantradar-ios"
PRICE_TIER_HINT = "9.99"

DESC = """QuantRadar is a paid educational radar for US tickers. It shows a single mechanical posture score and a clear action — act, wait, or avoid — with market, sector, and stock gates.

This is not a broker, not investment advice, and not a tipster feed. Most days the honest answer is don't trade.

Independent App Store product. Website subscriptions do not apply."""

KEYWORDS = "stock radar,stock scanner,swing trade,trading,market posture,ticker,options setup"
SUBTITLE = "Mechanical stock posture radar"
PROMO = "One score. One action. Built for traders tired of tipster noise."
REVIEW_NOTES = (
    "Paid educational mechanical posture radar. Not a broker. "
    "Demo ticker INTC works offline with bundled sample. "
    "No account required for core use. No IAP in v1."
)


def load_token() -> str:
    import jwt

    cfg = json.loads(Path.home().joinpath(".appstoreconnect/api_key.json").read_text())
    key = Path(cfg["key_filepath"]).read_text()
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": cfg["issuer_id"],
            "iat": now,
            "exp": now + 20 * 60,
            "aud": "appstoreconnect-v1",
        },
        key,
        algorithm="ES256",
        headers={"kid": cfg["key_id"]},
    )
    return token.decode() if isinstance(token, bytes) else token


def api(token: str, method: str, path: str, body=None, content_type="application/json"):
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        if content_type == "application/json":
            data = json.dumps(body).encode()
            headers["Content-Type"] = content_type
        else:
            data = body
            headers["Content-Type"] = content_type
    req = urllib.request.Request(
        "https://api.appstoreconnect.apple.com" + path,
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def find_app(token: str):
    status, apps = api(token, "GET", "/v1/apps?limit=50")
    if status != 200:
        raise RuntimeError(f"list apps failed: {status} {apps}")
    for a in apps["data"]:
        if a["attributes"].get("bundleId") == BUNDLE_ID:
            return a
    return None


def wait_for_app(token: str, timeout_sec: int = 1800) -> dict:
    print("Waiting for App Store Connect app record one.quantradar.app …")
    print("Create it at: https://appstoreconnect.apple.com/apps (New App → bundle one.quantradar.app)")
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        app = find_app(token)
        if app:
            print("FOUND", app["id"], app["attributes"]["name"])
            return app
        time.sleep(15)
        token = load_token()  # refresh periodically
        print("… still waiting")
    raise TimeoutError("App record not found within timeout")


def ensure_version(token: str, app_id: str) -> str:
    status, vers = api(token, "GET", f"/v1/apps/{app_id}/appStoreVersions?limit=10")
    if status != 200:
        raise RuntimeError(vers)
    for v in vers.get("data", []):
        state = v["attributes"].get("appStoreState")
        if v["attributes"].get("versionString") == "1.0.0" and state in {
            "PREPARE_FOR_SUBMISSION",
            "READY_FOR_REVIEW",
            "WAITING_FOR_REVIEW",
            "DEVELOPER_REJECTED",
            "REJECTED",
            "METADATA_REJECTED",
            "INVALID_BINARY",
        }:
            return v["id"]
    # create
    status, created = api(
        token,
        "POST",
        "/v1/appStoreVersions",
        {
            "data": {
                "type": "appStoreVersions",
                "attributes": {
                    "platform": "IOS",
                    "versionString": "1.0.0",
                    "copyright": "2026 Fortune Insight, LLC / Rongjian Liao",
                    "releaseType": "AFTER_APPROVAL",
                },
                "relationships": {"app": {"data": {"type": "apps", "id": app_id}}},
            }
        },
    )
    if status not in (200, 201):
        raise RuntimeError(f"create version failed: {status} {created}")
    return created["data"]["id"]


def upsert_localization(token: str, version_id: str):
    status, locs = api(token, "GET", f"/v1/appStoreVersions/{version_id}/appStoreVersionLocalizations")
    loc_id = None
    if status == 200:
        for loc in locs.get("data", []):
            if loc["attributes"].get("locale") == "en-US":
                loc_id = loc["id"]
                break
    attrs = {
        "description": DESC,
        "keywords": KEYWORDS,
        "marketingUrl": "https://quantradar.one",
        "supportUrl": "https://quantradar.one",
        "promotionalText": PROMO,
        "whatsNew": "Initial App Store release. Paid educational mechanical posture radar.",
    }
    if loc_id:
        status, body = api(
            token,
            "PATCH",
            f"/v1/appStoreVersionLocalizations/{loc_id}",
            {"data": {"type": "appStoreVersionLocalizations", "id": loc_id, "attributes": attrs}},
        )
    else:
        status, body = api(
            token,
            "POST",
            "/v1/appStoreVersionLocalizations",
            {
                "data": {
                    "type": "appStoreVersionLocalizations",
                    "attributes": {"locale": "en-US", "name": APP_NAME, "subtitle": SUBTITLE, **attrs},
                    "relationships": {
                        "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}
                    },
                }
            },
        )
    if status not in (200, 201):
        print("localization warn", status, body[:500] if isinstance(body, str) else body)
    else:
        print("localization ok")
    return body["data"]["id"] if isinstance(body, dict) and "data" in body else loc_id


def set_review_details(token: str, version_id: str):
    status, body = api(
        token,
        "POST",
        "/v1/appStoreReviewDetails",
        {
            "data": {
                "type": "appStoreReviewDetails",
                "attributes": {
                    "contactFirstName": "Rongjian",
                    "contactLastName": "Liao",
                    "contactEmail": "alexliao830@gmail.com",
                    "contactPhone": "+1 0000000000",
                    "demoAccountRequired": False,
                    "notes": REVIEW_NOTES,
                },
                "relationships": {
                    "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}
                },
            }
        },
    )
    if status in (200, 201):
        print("review details ok")
    else:
        # may already exist — try related get
        print("review details", status, body[:400] if isinstance(body, str) else body)


def set_age_rating(token: str, app_id: str):
    status, infos = api(token, "GET", f"/v1/apps/{app_id}/appInfos")
    if status != 200 or not infos.get("data"):
        print("appInfos", status, infos)
        return
    info_id = infos["data"][0]["id"]
    # Age rating declaration via relationship
    status, decl = api(token, "GET", f"/v1/appInfos/{info_id}/ageRatingDeclaration")
    attrs = {
        "alcoholTobaccoOrDrugUseOrReferences": "NONE",
        "contests": "NONE",
        "gambling": False,
        "gamblingSimulated": "NONE",
        "horrorOrFearThemes": "NONE",
        "matureOrSuggestiveThemes": "NONE",
        "medicalOrTreatmentInformation": "NONE",
        "profanityOrCrudeHumor": "NONE",
        "sexualContentGraphicAndNudity": "NONE",
        "sexualContentOrNudity": "NONE",
        "violenceCartoonOrFantasy": "NONE",
        "violenceRealistic": "NONE",
        "violenceRealisticProlongedGraphicOrSadistic": "NONE",
        "gunsOrOtherWeapons": "NONE",
        "unrestrictedWebAccess": False,
        "gamblingAndContests": False,
        "seventeenPlus": False,
        "lootBox": False,
    }
    if status == 200 and decl.get("data"):
        did = decl["data"]["id"]
        s, b = api(
            token,
            "PATCH",
            f"/v1/ageRatingDeclarations/{did}",
            {"data": {"type": "ageRatingDeclarations", "id": did, "attributes": attrs}},
        )
        print("age rating patch", s)
    else:
        print("age rating get", status, decl if isinstance(decl, str) else "no declaration yet")


def set_category(token: str, app_id: str):
    status, infos = api(token, "GET", f"/v1/apps/{app_id}/appInfos")
    if status != 200 or not infos.get("data"):
        return
    info_id = infos["data"][0]["id"]
    # primaryCategory relationship — Finance
    # Categories are fixed IDs; Finance is typically queried
    status, cats = api(token, "GET", "/v1/appCategories?filter[platforms]=IOS&limit=50")
    finance = None
    if status == 200:
        for c in cats.get("data", []):
            if c["attributes"].get("name") or True:
                # attributes may only have platforms
                pass
        # Prefer known Finance id lookup via filter
    status, fin = api(token, "GET", "/v1/appCategories/FIANCE")  # typo guard
    status, fin = api(token, "GET", "/v1/appCategories?filter[platforms]=IOS")
    print("categories fetch", status)
    if status == 200:
        # Print ids for finance-like
        for c in fin.get("data", []):
            cid = c["id"]
            if "FINANCE" in cid.upper() or cid == "FINANCE":
                finance = cid
                break
        if not finance:
            # Apple uses ids like "FINANCE"
            finance = "FINANCE"
    s, b = api(
        token,
        "PATCH",
        f"/v1/appInfos/{info_id}",
        {
            "data": {
                "type": "appInfos",
                "id": info_id,
                "relationships": {
                    "primaryCategory": {"data": {"type": "appCategories", "id": finance or "FINANCE"}}
                },
            }
        },
    )
    print("category", s, b if isinstance(b, str) else "ok")


def set_privacy_policy(token: str, app_id: str):
    status, infos = api(token, "GET", f"/v1/apps/{app_id}/appInfos")
    if status != 200 or not infos.get("data"):
        return
    info_id = infos["data"][0]["id"]
    status, locs = api(token, "GET", f"/v1/appInfos/{info_id}/appInfoLocalizations")
    loc_id = None
    if status == 200:
        for loc in locs.get("data", []):
            if loc["attributes"].get("locale") == "en-US":
                loc_id = loc["id"]
    attrs = {
        "privacyPolicyUrl": "https://quantradar.one/privacy",
        "name": APP_NAME,
        "subtitle": SUBTITLE,
    }
    if loc_id:
        s, b = api(
            token,
            "PATCH",
            f"/v1/appInfoLocalizations/{loc_id}",
            {"data": {"type": "appInfoLocalizations", "id": loc_id, "attributes": attrs}},
        )
    else:
        s, b = api(
            token,
            "POST",
            "/v1/appInfoLocalizations",
            {
                "data": {
                    "type": "appInfoLocalizations",
                    "attributes": {"locale": "en-US", **attrs},
                    "relationships": {"appInfo": {"data": {"type": "appInfos", "id": info_id}}},
                }
            },
        )
    print("privacy/info loc", s)


def upload_binary(token: str):
    if not ARCHIVE.exists():
        raise SystemExit(f"Missing archive {ARCHIVE}. Build it first.")
    cfg = json.loads(Path.home().joinpath(".appstoreconnect/api_key.json").read_text())
    EXPORT_PLIST.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PLIST.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>method</key><string>app-store-connect</string>
  <key>destination</key><string>upload</string>
  <key>teamID</key><string>DZ9BFS26A5</string>
  <key>signingStyle</key><string>automatic</string>
  <key>uploadSymbols</key><true/>
  <key>manageAppVersionAndBuildNumber</key><true/>
</dict>
</plist>
"""
    )
    export_dir = ROOT / "build" / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "xcodebuild",
        "-exportArchive",
        "-archivePath",
        str(ARCHIVE),
        "-exportOptionsPlist",
        str(EXPORT_PLIST),
        "-exportPath",
        str(export_dir),
        "-allowProvisioningUpdates",
        "-authenticationKeyPath",
        str(Path(cfg["key_filepath"])),
        "-authenticationKeyID",
        cfg["key_id"],
        "-authenticationKeyIssuerID",
        cfg["issuer_id"],
    ]
    print("Uploading binary…")
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(proc.stdout[-2000:] if proc.stdout else "")
    print(proc.stderr[-2000:] if proc.stderr else "")
    if proc.returncode != 0:
        raise RuntimeError("export/upload failed")
    print("Upload command finished")


def rebuild_archive():
    print("Rebuilding Release archive…")
    subprocess.check_call(["xcodegen", "generate"], cwd=ROOT)
    subprocess.check_call(
        [
            "xcodebuild",
            "-project",
            "QuantRadar.xcodeproj",
            "-scheme",
            "QuantRadar",
            "-configuration",
            "Release",
            "-destination",
            "generic/platform=iOS",
            "-archivePath",
            str(ARCHIVE),
            "DEVELOPMENT_TEAM=DZ9BFS26A5",
            "CODE_SIGN_STYLE=Automatic",
            "archive",
        ],
        cwd=ROOT,
    )


def submit_review(token: str, version_id: str):
    status, body = api(
        token,
        "POST",
        "/v1/reviewSubmissions",
        {
            "data": {
                "type": "reviewSubmissions",
                "attributes": {"platform": "IOS"},
                "relationships": {
                    "app": {
                        "data": {
                            "type": "apps",
                            "id": find_app(token)["id"],
                        }
                    }
                },
            }
        },
    )
    print("reviewSubmissions", status, body if isinstance(body, str) else json.dumps(body)[:800])
    if status not in (200, 201):
        # Fallback older endpoint
        status2, body2 = api(
            token,
            "POST",
            "/v1/appStoreVersionSubmissions",
            {
                "data": {
                    "type": "appStoreVersionSubmissions",
                    "relationships": {
                        "appStoreVersion": {"data": {"type": "appStoreVersions", "id": version_id}}
                    },
                }
            },
        )
        print("legacy submit", status2, body2 if isinstance(body2, str) else json.dumps(body2)[:800])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    token = load_token()
    app = find_app(token)
    if not app and args.wait:
        app = wait_for_app(token)
    if not app:
        print("ERROR: App record missing for", BUNDLE_ID)
        print("Create New App in App Store Connect, then re-run with --wait")
        sys.exit(2)

    app_id = app["id"]
    print("App", app_id)

    if args.rebuild or not ARCHIVE.exists():
        rebuild_archive()

    version_id = ensure_version(token, app_id)
    print("Version", version_id)
    upsert_localization(token, version_id)
    set_privacy_policy(token, app_id)
    set_category(token, app_id)
    set_age_rating(token, app_id)
    set_review_details(token, version_id)

    if not args.skip_upload:
        upload_binary(token)

    # Give ASC a moment to process build
    print("Waiting 60s for build processing before submit…")
    time.sleep(60)
    token = load_token()
    submit_review(token, version_id)
    print("DONE — check App Store Connect for review state / screenshot requirements.")


if __name__ == "__main__":
    main()
