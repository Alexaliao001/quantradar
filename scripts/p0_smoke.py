#!/usr/bin/env python3
"""P0 acceptance smoke — local shell (required) + optional live domain.

Usage:
  python3 scripts/p0_smoke.py              # local in-process + optional server
  python3 scripts/p0_smoke.py --live       # also probe https://quantradar.one
  python3 scripts/p0_smoke.py --base http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app.charts_facade import analyze  # noqa: E402
from app.contract import validate_response  # noqa: E402
from app.quality import canonicalize_ticker  # noqa: E402


def _ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL  {msg}")


def local_inprocess() -> list[str]:
    failures: list[str] = []
    print("== local in-process ==")

    # 1) placeholder rejected at normalize / analyze path
    try:
        analyze("XXXX", mode="artifact")
        failures.append("XXXX should raise ValueError")
        _fail("XXXX raises")
    except ValueError:
        _ok("XXXX rejected (ValueError)")

    # 2) unknown ticker no fake score
    r = analyze("NOREALTK", mode="artifact")
    if r.get("ok"):
        failures.append("unknown ticker returned ok=true")
        _fail("unknown ticker fails closed")
    elif (r.get("score") or {}).get("final") not in (None, 0) and not (
        r.get("score") or {}
    ).get("withheld"):
        # withheld None is required; final 0 without withheld is weak but we require withheld
        failures.append("unknown ticker exposed score")
        _fail("unknown ticker score withheld")
    else:
        errs = validate_response(r)
        if errs:
            failures.append(f"unknown response contract: {errs}")
            _fail(f"contract {errs}")
        else:
            _ok("unknown ticker ok=false + score withheld")

    # 3) INTC sample works
    r = analyze("INTC", mode="artifact")
    if not r.get("ok"):
        failures.append(f"INTC failed: {r.get('error')}")
        _fail("INTC artifact analyze")
    else:
        errs = validate_response(r)
        if errs:
            failures.append(f"INTC contract: {errs}")
            _fail(f"INTC contract {errs}")
        elif r["primary"]["action"] != r["gate"]["signal"]:
            failures.append("primary != gate.signal")
            _fail("single primary equals gate")
        else:
            _ok(f"INTC ok score={r['score']['final']} primary={r['primary']['action']}")

    # 4) BRK alias
    if canonicalize_ticker("BRK.B") != "BRK-B":
        failures.append("BRK.B alias")
        _fail("BRK.B → BRK-B")
    else:
        _ok("BRK.B → BRK-B")

    return failures


_UA = "QuantRadar-P0-Smoke/0.2 (+https://github.com/Alexaliao001/quantradar)"


def http_get_json(url: str, timeout: float = 30) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            "User-Agent": _UA,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
        raw = e.read().decode("utf-8", errors="replace")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        body = {"_raw": raw[:500], "_non_json": True}
    return code, body if isinstance(body, dict) else {"_body": body}


def probe_base(base: str, label: str) -> list[str]:
    failures: list[str] = []
    base = base.rstrip("/")
    print(f"== HTTP {label}: {base} ==")

    code, health = http_get_json(f"{base}/health", timeout=15)
    if code != 200:
        failures.append(f"{label} /health HTTP {code}")
        _fail(f"/health → {code}")
    else:
        if health.get("manus_login") is False and health.get("service") == "quantradar-shell":
            _ok(f"/health shell sha={health.get('git_sha')} p0={health.get('p0_gates')}")
        elif health.get("service") == "quantradar" and "manus_login" not in health:
            _fail("/health still legacy Manus shape (not path-C shell)")
            failures.append(f"{label} not cut over to shell")
        else:
            _ok(f"/health keys={list(health)[:8]}")

    # XXXX must not be a buy
    code, body = http_get_json(f"{base}/api/analyze?ticker=XXXX", timeout=60)
    if body.get("_non_json"):
        failures.append(f"{label} /api/analyze returned non-JSON (SPA?)")
        _fail("/api/analyze?ticker=XXXX non-JSON")
    elif body.get("ok") is True and float((body.get("score") or {}).get("final") or 0) >= 50:
        sig = str((body.get("gate") or {}).get("signal") or body.get("action") or "")
        # also catch Manus tRPC-shaped nested results
        failures.append(f"{label} XXXX still returns tradeable ok/score")
        _fail(f"XXXX ok={body.get('ok')} score={body.get('score')} sig={sig}")
    elif code in {400, 404, 502} and body.get("ok") is False:
        _ok(f"XXXX rejected HTTP {code} error={body.get('error')}")
    else:
        # Manus tRPC path may not exist
        code2, trpc = http_post_trpc_xxxx(base)
        if trpc is not None:
            if trpc_looks_like_fake_buy(trpc):
                failures.append(f"{label} tRPC XXXX fake buy")
                _fail("tRPC quant.analyzeStock(XXXX) still fake-buy")
            else:
                _ok("tRPC XXXX not a fake buy (or endpoint changed)")
        else:
            _ok(f"XXXX path HTTP {code} body.ok={body.get('ok')}")

    code, body = http_get_json(f"{base}/api/analyze?ticker=INTC", timeout=60)
    if body.get("ok") and body.get("score", {}).get("final") is not None:
        _ok(f"INTC REST score={body['score']['final']}")
    elif body.get("_non_json"):
        failures.append(f"{label} INTC REST not wired")
        _fail("INTC /api/analyze not shell JSON")
    else:
        _fail(f"INTC REST HTTP {code} ok={body.get('ok')}")
        # not always a hard failure for live until cutover — count as fail for --live cutover check
        failures.append(f"{label} INTC REST not ok")

    code, _ = http_get_json(f"{base}/api/oauth/callback", timeout=15)
    if code == 410:
        _ok("oauth → 410")
    else:
        _fail(f"oauth → {code} (want 410)")
        failures.append(f"{label} oauth not 410")

    return failures


def http_post_trpc_xxxx(base: str) -> tuple[int | None, dict | None]:
    url = f"{base.rstrip('/')}/api/trpc/quant.analyzeStock"
    data = json.dumps(
        {
            "json": {
                "symbol": "XXXX",
                "includeOptions": True,
                "skipGateCheck": False,
                "riskPreference": "balanced",
                "enableLLMValidation": False,
            }
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "content-type": "application/json",
            "Accept": "application/json",
            "User-Agent": _UA,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, None
    except Exception:
        return None, None


def trpc_looks_like_fake_buy(body: dict) -> bool:
    try:
        node = body.get("result", {}).get("data", {}).get("json", body)
    except Exception:
        node = body
    if not isinstance(node, dict):
        return False
    # Manus shape
    score = node.get("finalScore") or node.get("comprehensiveScore") or node.get("score")
    try:
        score_n = float(score) if score is not None else 0
    except (TypeError, ValueError):
        score_n = 0
    rec = str(
        node.get("primaryRecommendation")
        or (node.get("stockRecommendation") or {}).get("action")
        or node.get("action")
        or ""
    ).lower()
    vol = node.get("volumeAnalysis") or {}
    avg = vol.get("avgVolume20")
    cur = vol.get("currentVolume")
    if score_n >= 50 and rec in {"buy", "long", "full", "build", "probe"}:
        return True
    if score_n >= 50 and avg == 0 and cur == 0:
        return True
    if node.get("symbol") == "XXXX" and score_n >= 50:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="QuantRadar P0 smoke")
    ap.add_argument("--live", action="store_true", help="probe https://quantradar.one")
    ap.add_argument("--base", default="", help="probe this base URL (shell)")
    args = ap.parse_args()

    failures = local_inprocess()

    if args.base:
        failures.extend(probe_base(args.base, "custom"))

    if args.live:
        failures.extend(probe_base("https://quantradar.one", "live"))

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(f"  - {f}")
        print(
            "\nIf live fails: domain still on Manus SPA. "
            "Deploy path-C shell per docs/MANUS_SYNC.md then re-run --live."
        )
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
