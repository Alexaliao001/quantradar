#!/usr/bin/env python3
"""Delete leftover audit coupons from Stripe.

Safety: only deletes coupons that are ALL of:
  - named "QuantRadar report credit" (our minted credits)
  - redeemed 0 times
  - past their redeem_by expiry

Never touches redeemed, still-valid, or non-QR coupons.
Usage: python3 scripts/cleanup_stripe_coupons.py [--dry-run]
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env if present (local dev)
_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env):
    for ln in open(_env):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SECRET = (
    os.environ.get("QUANTRADAR_STRIPE_SECRET_KEY", "").strip()
    or os.environ.get("STRIPE_SECRET_KEY", "").strip()
)
UA = {"Authorization": f"Bearer {SECRET}", "User-Agent": "QuantRadar-Stripe/0.5"}
TARGET_NAME = "QuantRadar report credit"


def api(path: str, data: bytes | None = None, method: str = "GET") -> dict:
    req = urllib.request.Request(
        f"https://api.stripe.com{path}", data=data, headers=UA, method=method
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    if not SECRET:
        print("no stripe secret key — nothing to do")
        return 0
    dry = "--dry-run" in sys.argv
    now = time.time()
    deleted = kept = 0
    starting_after = None
    while True:
        params = {"limit": "100"}
        if starting_after:
            params["starting_after"] = starting_after
        page = api("/v1/coupons?" + urllib.parse.urlencode(params))
        items = page.get("data", [])
        for c in items:
            starting_after = c.get("id")
            expired = isinstance(c.get("redeem_by"), int) and c["redeem_by"] < now
            unused = (c.get("times_redeemed") or 0) == 0
            ours = c.get("name") == TARGET_NAME
            if ours and expired and unused:
                print(f"DELETE {c['id']} (expired {int(now - c['redeem_by']) // 3600}h ago, never redeemed)")
                if not dry:
                    try:
                        api(f"/v1/coupons/{c['id']}", data=b"", method="DELETE")
                        deleted += 1
                    except urllib.error.HTTPError as e:
                        print(f"  ! failed: {e.code}")
            else:
                kept += 1
        if not page.get("has_more"):
            break
    print(f"done: {deleted} deleted, {kept} kept" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
