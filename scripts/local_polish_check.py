#!/usr/bin/env python3
"""Local polish gate before self-deploy (no Manus)."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"


def get(path: str) -> tuple[int, bytes, str]:
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=8) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b"", e.headers.get("Content-Type", "") if e.headers else ""


def main() -> int:
    print(f"== local_polish_check base={BASE} ==")
    fails = 0

    print("-- unittest --")
    u = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if u.returncode != 0:
        print(u.stderr[-2000:] or u.stdout[-2000:])
        print("FAIL unittest")
        fails += 1
    else:
        # last line usually OK
        tail = [ln for ln in (u.stderr + u.stdout).splitlines() if ln.strip()][-3:]
        print("\n".join(tail))
        print("PASS unittest")

    print("-- http --")
    checks = [
        ("/health", 200, b"quantradar-shell"),
        ("/", 200, b"Quant"),
        ("/pricing", 200, b"supporter"),
        ("/methodology", 200, b"Methodology"),
        ("/track", 200, b"track"),
        ("/r/INTC", 200, b"INTC"),
        ("/api/sample?ticker=INTC", 200, b"primary_score"),
        ("/api/track", 200, b"disclaimer"),
        (
            "/api/charts/INTC_daily_price_2026-03-21_01-43-21.png",
            200,
            b"\x89PNG",
        ),
    ]
    for path, want, needle in checks:
        code, body, ctype = get(path)
        ok = code == want and needle in body
        print(f"  {'PASS' if ok else 'FAIL'}  {path}  {code}  ctype={ctype[:40]}")
        if not ok:
            fails += 1

    code, body, _ = get("/health")
    if code == 200:
        try:
            h = json.loads(body.decode("utf-8"))
            if h.get("manus_login") is not False:
                print("FAIL  health.manus_login must be false")
                fails += 1
            else:
                print(f"PASS  health manus_login=false charts={h.get('charts_status')} pro={h.get('pro_value')}")
        except json.JSONDecodeError:
            print("FAIL  health JSON")
            fails += 1

    # p0 smoke
    print("-- p0_smoke --")
    s = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "p0_smoke.py"), "--base", BASE],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    print(s.stdout.strip().splitlines()[-1] if s.stdout else s.stderr[-500:])
    if s.returncode != 0:
        fails += 1

    print()
    if fails:
        print(f"RESULT: FAIL ({fails})")
        print("Fix issues, then re-run. Deploy only when PASS. See docs/LOCAL_POLISH.md")
        return 1
    print("RESULT: PASS — local polish gate green. Next: commit → push → docs/SELF_DEPLOY.md (Render, no Manus)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
