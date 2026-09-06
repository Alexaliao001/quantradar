#!/usr/bin/env python3
"""One command for the remaining launch work.

While Apple holds 1.0 / build 7: print status and exit 2.
After the version is editable: ship zh-Hans / zh-Hant and confirm the public listing.

  /tmp/asc-jwt2/bin/python ios/scripts/go_live.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ship_asc import api, load_token  # noqa: E402
from ship_locales_after_approval import LOCALES, latest_ios_version, main as ship_locales  # noqa: E402

APP_ID = "6800090745"
LOCKED = {"WAITING_FOR_REVIEW", "IN_REVIEW"}


def public_lookup() -> int:
    req = urllib.request.Request("https://itunes.apple.com/lookup?bundleId=one.quantradar.app")
    with urllib.request.urlopen(req, timeout=15) as response:
        body = json.loads(response.read().decode())
    count = int(body.get("resultCount") or 0)
    print("public listing", count)
    if count and body.get("results"):
        row = body["results"][0]
        print("  ", row.get("trackName"), row.get("version"), row.get("formattedPrice"), row.get("trackViewUrl"))
    return count


def main() -> int:
    token = load_token()
    version = latest_ios_version(token)
    attrs = version.get("attributes") or {}
    state = attrs.get("appVersionState") or attrs.get("appStoreState")
    print("version", version["id"], attrs.get("versionString"), state, attrs.get("releaseType"))

    st, iap = api(token, "GET", f"/v1/apps/{APP_ID}/inAppPurchasesV2?limit=10")
    if st == 200:
        for row in iap.get("data") or []:
            a = row.get("attributes") or {}
            print("iap", a.get("productId"), a.get("state"))

    public_lookup()

    if state in LOCKED:
        print("Apple still has the binary. Do not replace build 7. Re-run this script after approval.")
        return 2

    code = ship_locales()
    token = load_token()
    public_lookup()
    print("locales", "ok" if code == 0 else code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
