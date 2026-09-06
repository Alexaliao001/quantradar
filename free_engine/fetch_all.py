#!/usr/bin/env python3
"""QuantRadar free-data engine — drop-in replacement for charts fetch_all.py.

Same CLI contract the quantradar facade expects:

    python fetch_all.py TICKER [SECTOR_ETF] [--output-dir DIR]

JSON payload on stdout (ENGINE_CONTRACT-compatible), logs on stderr.
Zero paid APIs: Yahoo chart (x2 hosts) + Nasdaq.com + Stooq, aggregated by
per-day median voting; fundamentals fail-open via Yahoo quoteSummary with
Nasdaq summary fallback. VIX via Yahoo "^VIX" (free).

No third-party imports — stdlib only, so it runs inside the shell's
interpreter without a venv.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from free_aggregate import aggregate_bars  # noqa: E402
from free_mechanical import (  # noqa: E402
    action_to_signal,
    apply_post_gates,
    core,
    etf_for_sector,
    grade_for,
    is_near_earnings,
    pct_change_over,
)
from free_sources import SOURCE_NAMES, fetch_all_sources, fetch_fundamentals  # noqa: E402
from market_calendar import completed_bars, completed_session  # noqa: E402

MIN_BARS = 50
CACHE_DIR = HERE / ".cache"
SPY = "SPY"

# Same class-share aliases the shell normalizes (app/quality.py) — keep the
# request ticker and payload ticker in canonical form so the quality gate's
# mismatch check never fires.
_SYMBOL_ALIASES = {
    "BRK.B": "BRK-B",
    "BF.B": "BF-B",
}


def _canonical(symbol: str) -> str:
    return _SYMBOL_ALIASES.get(symbol.upper(), symbol.upper())


def _log(msg: str) -> None:
    print(f"[free-engine] {msg}", file=sys.stderr, flush=True)


def _aggregate_symbol(symbol: str, now: datetime | None = None) -> tuple[dict, dict[str, str]]:
    bars_by_source, errors = fetch_all_sources(symbol, days=365, cache_dir=CACHE_DIR, as_of=now)
    if not bars_by_source:
        raise RuntimeError(
            "all free sources failed: "
            + "; ".join(f"{k}: {v}" for k, v in sorted(errors.items()))
        )
    agg = aggregate_bars(bars_by_source)
    agg["bars"] = completed_bars(agg["bars"], now=now, minimum=MIN_BARS)
    agg["days"] = len(agg["bars"])
    if set(agg["disagree_days"]) & {row[0] for row in agg["bars"][-50:]}:
        raise RuntimeError(f"independent price feeds disagree for {symbol}; score withheld")
    if agg["days"] < MIN_BARS:
        raise RuntimeError(f"too few bars for {symbol} ({agg['days']} < {MIN_BARS})")
    return agg, errors


def _reliability(agg: dict, errors: dict[str, str]) -> str:
    latest = agg["per_day_sources"].get(agg["bars"][-1][0], [])
    agreeing = len({"yahoo" if n.startswith("yahoo_") else n for n in latest if n not in errors})
    recent_disagree = set(agg["disagree_days"]) & {row[0] for row in agg["bars"][-5:]}
    if agreeing >= 3 and not recent_disagree:
        return "high"
    if agreeing >= 2:
        return "medium"
    return "low"


def _state_for(action: str, reason: str) -> dict:
    if action == "SETUP":
        return {"code": "A", "name": "setup_zone", "reason": reason}
    if action == "WAIT":
        return {"code": "B", "name": "wait_watch", "reason": reason}
    return {"code": "C", "name": "stand_aside", "reason": reason}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def build_payload(ticker: str, sector_arg: str | None) -> dict:
    warnings: list[str] = []
    t0 = time.time()
    batch_now = datetime.now(timezone.utc)

    agg, errors = _aggregate_symbol(ticker, batch_now)
    bars = agg["bars"]
    for name in SOURCE_NAMES:
        if name in errors:
            warnings.append(f"source {name} unavailable: {errors[name]}")
    if agg["disagree_days"]:
        warnings.append(
            f"{len(agg['disagree_days'])} day(s) had >3% cross-source spread "
            f"(e.g. {agg['disagree_days'][-1]}); median used"
        )

    # Market gate: SPY multi-source aggregate (free, same pipeline)
    spy_pct = None
    spy_bars_for_gate = None
    try:
        spy_agg = agg if ticker == SPY else _aggregate_symbol(SPY, batch_now)[0]
        spy_bars_for_gate = spy_agg["bars"]
        spy_pct = pct_change_over(spy_bars_for_gate, 5)
    except Exception as exc:
        warnings.append(f"SPY market gate unavailable ({exc}); gate shows unknown")

    # Fundamentals — fail-open (name/sector/earnings)
    fund = fetch_fundamentals(ticker, cache_dir=CACHE_DIR)
    sector_name = fund.get("sector")
    company_name = fund.get("company_name")
    earnings_date = fund.get("earnings_date")

    # Sector gate: resolve ETF (arg overrides detection), score it free
    sector_etf = (sector_arg or "").strip().upper() or etf_for_sector(sector_name)
    sector_action = None
    sector_pct = None
    if sector_etf:
        try:
            sec_agg, _ = _aggregate_symbol(sector_etf, batch_now)
            sector_pct = pct_change_over(sec_agg["bars"], 5)
            sec_core = core(sec_agg["bars"], spy_bars_for_gate)
            sector_action = sec_core["action"]
        except Exception as exc:
            warnings.append(f"sector gate unavailable for {sector_etf}: {exc}")
            sector_etf = None

    # VIX via Yahoo ^VIX (free; not on Nasdaq/stocks)
    vix_current = None
    vix_trend = None
    try:
        vix_bars, _ = fetch_all_sources("^VIX", days=30, cache_dir=CACHE_DIR, as_of=batch_now)
        vix_agg = aggregate_bars(vix_bars)
        vc = [b[1] for b in completed_bars(vix_agg["bars"], now=batch_now, minimum=5)]
        if vc:
            vix_current = vc[-1]
            if len(vc) >= 5:
                vix_trend = "rising" if vc[-1] > vc[-5] else "falling"
    except Exception:
        warnings.append("VIX unavailable; risk gauge omitted")

    # Core scoring — exact iOS formula, then earnings/sector gates
    c = core(bars, spy_bars_for_gate)
    today = bars[-1][0]
    earnings_near = is_near_earnings(earnings_date, today)
    c = apply_post_gates(c, earnings_near=earnings_near, sector_action=sector_action)

    signal = action_to_signal(c["action"])
    state = _state_for(c["action"], c["reason"])
    adj = c["adjustments"]

    score = float(c["score"])
    base_total = _clamp(50.0 + adj["trend_sma"] + adj["momentum_rsi"] + adj["volume_price"], 0.0, 100.0)

    reliability = _reliability(agg, errors)
    if len([n for n in agg["source_coverage"] if n not in errors]) == 1:
        warnings.append("single-source data — consensus voting unavailable this run")

    live_sources = sorted(n for n in agg["source_coverage"] if n not in errors)
    fetch_ms = int((time.time() - t0) * 1000)

    payload: dict = {
        "ticker": ticker.upper(),
        "fetch_time": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "data_quality": {
            "reliability": reliability,
            "timeframes_ok": 1,
            "bars": agg["days"],
            "market_as_of": bars[-1][0],
            "expected_session": completed_session(batch_now),
            "market_gate": c["market_gate"],
            "sources_live": live_sources,
            "sources_failed": sorted(errors.keys()),
            "disagree_days": len(agg["disagree_days"]),
            # Free sources provide no options chain — omit option_chain_ok so
            # the shell reports options as not-actionable without claiming a
            # simulated feed (never invent options data).
            "warnings": warnings,
        },
        "mechanical_scores": {
            "final_score": score,
            "signal_mechanical": signal,
            "state": state,
            "base_score": {
                "total": base_total,
                "trend": {
                    "total": _clamp(25.0 + adj["trend_sma"], 0.0, 50.0),
                    "max": 50.0,
                },
                "momentum": {
                    "total": _clamp(25.0 + adj["momentum_rsi"], 0.0, 50.0),
                    "max": 50.0,
                },
                "volume_price": {
                    "total": _clamp(25.0 + adj["volume_price"], 0.0, 50.0),
                    "max": 50.0,
                    "volume_ratio": round(c["vol_ratio"], 3),
                },
            },
            "entry_timing": {
                "grade": grade_for(c["action"], score),
                "total": score,
                "max": 100.0,
            },
            "detail": {
                "rsi14": round(c["rsi"], 2) if c["rsi"] is not None else None,
                "pullback_from_sma20_pct": round(c["pullback"], 2),
                "sma20": round(c["sma20"], 4),
                "sma50": round(c["sma50"], 4),
                "last_close": c["last"],
                "earnings_forced_wait": c.get("earnings_forced_wait", False),
            },
        },
        "indicator_data": {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "timeframe": "daily",
        },
        "daily_bars": [list(row) for row in bars],
        "spy_daily_bars": [list(row) for row in (spy_bars_for_gate or [])],
        "market_env": {
            "spy_change_pct": round(spy_pct, 3) if spy_pct is not None else None,
            "market_state": (
                "risk_off"
                if c["market_gate"] == "NO"
                else ("watch" if c["market_gate"] == "WATCH" else "normal")
                if spy_pct is not None
                else None
            ),
            "sector_etf": sector_etf,
            "sector_change_pct": round(sector_pct, 3) if sector_pct is not None else None,
            "sector_action": sector_action,
            "vix_current": round(vix_current, 2) if vix_current is not None else None,
            "vix_trend": vix_trend,
        },
        "fundamentals": {
            "company_name": company_name,
            "sector": sector_name,
            "earnings_date": earnings_date,
        },
        "market_context": {
            "earnings_within_window": earnings_near,
            "sources_aggregated": live_sources,
            "options_note": "no options chain from free sources — options views omitted",
            "fetch_ms": fetch_ms,
        },
    }
    return payload


def main(argv: list[str]) -> int:
    # tolerate "--output-dir DIR" (charts facade compat; dir unused)
    cleaned: list[str] = []
    skip_next = False
    for a in argv:
        if skip_next:
            skip_next = False
            continue
        if a == "--output-dir":
            skip_next = True
            continue
        cleaned.append(a)
    args = cleaned
    if not args:
        print("usage: fetch_all.py TICKER [SECTOR_ETF]", file=sys.stderr)
        return 2
    ticker = _canonical(args[0].strip())
    sector_arg = args[1].strip().upper() if len(args) > 1 else None

    try:
        payload = build_payload(ticker, sector_arg)
    except Exception as exc:
        # Contract-shaped engine error — quality gate will fail this closed.
        err = {
            "ticker": ticker,
            "ok": False,
            "error": str(exc)[:400],
            "fetch_time": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        }
        _log(f"engine error: {exc}")
        print(json.dumps(err, ensure_ascii=False))
        return 0

    _log(
        f"{ticker} score={payload['mechanical_scores']['final_score']} "
        f"signal={payload['mechanical_scores']['signal_mechanical']} "
        f"sources={payload['market_context']['sources_aggregated']} "
        f"{payload['market_context']['fetch_ms']}ms"
    )
    print(json.dumps(payload, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
