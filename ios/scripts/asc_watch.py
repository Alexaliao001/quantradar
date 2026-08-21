#!/usr/bin/env python3
"""Read-only App Store Connect watchdog for QuantRadar iOS.

Prints a JSON snapshot and writes ios/build/asc_watch_latest.json.
Does not mutate ASC. Exit codes:
  0 wait
  2 Apple sent a review problem (fix)
  3 1.0 approved/live as paid — run Free+IAP cutover
  4 done (live and no longer a paid-download shell)
  1 script/API error
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ship_asc import api, find_app, load_token  # noqa: E402

APP_ID = "6800090745"
OUT = ROOT / "build" / "asc_watch_latest.json"
LOG = ROOT / "build" / "asc_watch.jsonl"

WAIT = {
    "WAITING_FOR_REVIEW",
    "IN_REVIEW",
    "WAITING_FOR_EXPORT_COMPLIANCE",
}
FIX = {
    "REJECTED",
    "METADATA_REJECTED",
    "INVALID_BINARY",
    "DEVELOPER_REJECTED",
    "REMOVED_FROM_SALE",
}
CUTOVER = {
    "PENDING_DEVELOPER_RELEASE",
    "PROCESSING_FOR_APP_STORE",
    "READY_FOR_SALE",
    "READY_FOR_DISTRIBUTION",
    "ACCEPTED",
}


def _attr(node: dict) -> dict:
    return node.get("attributes") or {}


def snapshot() -> dict:
    token = load_token()
    app = find_app(token)
    if not app:
        return {"ok": False, "error": "app record missing", "action": "fix_review"}

    st, vers = api(token, "GET", f"/v1/apps/{APP_ID}/appStoreVersions?limit=10&include=build")
    if st != 200:
        return {"ok": False, "error": f"versions {st}", "action": "wait"}

    versions = []
    included = {(i.get("type"), i.get("id")): i for i in vers.get("included") or []}
    for v in vers.get("data") or []:
        a = _attr(v)
        build_rel = ((v.get("relationships") or {}).get("build") or {}).get("data") or {}
        build = included.get(("builds", build_rel.get("id")))
        ba = _attr(build) if build else {}
        versions.append(
            {
                "id": v["id"],
                "versionString": a.get("versionString"),
                "appStoreState": a.get("appStoreState"),
                "appVersionState": a.get("appVersionState"),
                "releaseType": a.get("releaseType"),
                "createdDate": a.get("createdDate"),
                "build": {
                    "id": build.get("id") if build else None,
                    "version": ba.get("version"),
                    "processingState": ba.get("processingState"),
                },
            }
        )

    st, revs = api(token, "GET", f"/v1/apps/{APP_ID}/reviewSubmissions?limit=5")
    submissions = []
    if st == 200:
        for r in revs.get("data") or []:
            submissions.append({"id": r["id"], **(_attr(r))})

    st, prices = api(
        token,
        "GET",
        f"/v1/appPriceSchedules/{APP_ID}/manualPrices?include=appPricePoint",
    )
    customer_price = None
    if st == 200:
        for inc in prices.get("included") or []:
            if inc.get("type") == "appPricePoints":
                customer_price = (_attr(inc) or {}).get("customerPrice")
                break

    st, iap = api(token, "GET", f"/v1/apps/{APP_ID}/inAppPurchasesV2?limit=10")
    iap_count = len((iap or {}).get("data") or []) if st == 200 else None

    import urllib.request

    on_store = False
    store_price = None
    try:
        with urllib.request.urlopen("https://itunes.apple.com/lookup?id=6800090745", timeout=15) as resp:
            lookup = json.loads(resp.read().decode())
        if lookup.get("resultCount"):
            on_store = True
            store_price = (lookup["results"][0] or {}).get("price")
    except Exception:
        pass

    current = versions[0] if versions else {}
    state = current.get("appVersionState") or current.get("appStoreState") or "UNKNOWN"
    submitted = None
    for s in submissions:
        if s.get("state") == "WAITING_FOR_REVIEW":
            submitted = s.get("submittedDate")
            break
    if not submitted and submissions:
        submitted = submissions[0].get("submittedDate")

    paid_shell = customer_price not in (None, "0", "0.00") and (iap_count or 0) == 0
    if on_store and (store_price == 0 or (customer_price in ("0", "0.00") and (iap_count or 0) > 0)):
        action = "done"
    elif state in FIX:
        action = "fix_review"
    elif state in CUTOVER or (on_store and paid_shell):
        action = "cutover"
    elif state in WAIT:
        action = "wait"
    else:
        action = "wait"

    return {
        "ok": True,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "state": state,
        "version": current.get("versionString"),
        "build": (current.get("build") or {}).get("version"),
        "price": customer_price,
        "iapCount": iap_count,
        "onStore": on_store,
        "storePrice": store_price,
        "submittedDate": submitted,
        "submissionState": (submissions[0].get("state") if submissions else None),
        "versions": versions,
        "submissions": submissions,
    }


def main() -> int:
    snap = snapshot()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap, indent=2) + "\n")
    with LOG.open("a") as f:
        f.write(json.dumps(snap) + "\n")
    print(json.dumps(snap, indent=2))
    action = snap.get("action")
    if not snap.get("ok"):
        return 1
    return {"wait": 0, "fix_review": 2, "cutover": 3, "done": 4}.get(action, 1)


if __name__ == "__main__":
    raise SystemExit(main())
