"""Mechanical posture scoring — exact port of iOS FreeMechanicalScorer.core.

The iOS app and the web product must agree tick-for-tick on the same formula.
Every constant, branch, and clamp below mirrors
ios/QuantRadar/Services/FreeDataRadar.swift (FreeMechanicalScorer) and
ios/QuantRadar/Services/PostureDepth.swift. No invented rules.

Pure functions, no I/O — unit-testable against hand-computed fixtures.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

# Bars are (date, close, volume) tuples, ascending by date.
Bar = tuple[str, float, float]

EARNINGS_WINDOW_DAYS = 3

# Sector keyword → SPDR ETF (iOS PostureDepth.etf(forSector:))
_SECTOR_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("technolog", "XLK"),
    ("financ", "XLF"),
    ("energy", "XLE"),
    ("health", "XLV"),
    ("cyclical", "XLY"),
    ("discretion", "XLY"),
    ("defensive", "XLP"),
    ("staple", "XLP"),
    ("industrial", "XLI"),
    ("material", "XLB"),
    ("basic", "XLB"),
    ("real estate", "XLRE"),
    ("utilit", "XLU"),
    ("communicat", "XLC"),
)


def sma(values: Sequence[float], n: int) -> float:
    if len(values) < n:
        return 0.0
    return sum(values[-n:]) / float(n)


def rsi14(closes: Sequence[float]) -> float | None:
    """Swift rsi14: last 15 closes → 14 deltas, simple (non-Wilder) average."""
    if len(closes) <= 15:
        return None
    window = list(closes[-15:])
    gains = 0.0
    losses = 0.0
    for i in range(1, len(window)):
        d = window[i] - window[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_gain = gains / 14.0
    avg_loss = losses / 14.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def pct_change_over(bars: Sequence[Bar], lookback: int = 5) -> float | None:
    """Percent change between bars[-lookback] and bars[-1].

    Mirrors iOS exactly: ``spy[spy.count - 5]`` vs ``spy.last`` (a window of
    `lookback` bars, i.e. lookback-1 intervals).
    """
    if len(bars) < lookback:
        return None
    a = bars[-lookback][1]
    b = bars[-1][1]
    if a <= 0:
        return None
    return (b - a) / a * 100.0


def _round_half_away(x: float) -> float:
    # Swift .rounded() = half away from zero (not banker's rounding)
    return math.floor(x + 0.5) if x >= 0 else math.ceil(x - 0.5)


def etf_for_sector(sector: str | None) -> str | None:
    if not sector:
        return None
    s = sector.lower()
    for keyword, etf in _SECTOR_KEYWORDS:
        if keyword in s:
            return etf
    return None


def core(bars: Sequence[Bar], spy_bars: Sequence[Bar] | None) -> dict[str, Any]:
    """Exact port of FreeMechanicalScorer.core(bars:spyBars:).

    Returns all intermediates (score/action/label/reason/pullback/rsi/gates)
    so the caller can build contract payloads and apply earnings/sector gates.
    """
    closes = [b[1] for b in bars]
    volumes = [b[2] for b in bars]
    last = closes[-1] if closes else 0.0
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    rsi = rsi14(closes)
    vol_sma = sma(volumes, 20)
    vol_ratio = (volumes[-1] / vol_sma) if (vol_sma > 0 and volumes) else 1.0
    pullback = ((sma20 - last) / sma20 * 100.0) if sma20 > 0 else 0.0

    score = 50.0
    sma_adj = 0.0
    if sma20 > 0 and sma50 > 0:
        if last > sma20 and sma20 > sma50:
            sma_adj = 18.0
        elif last > sma20:
            sma_adj = 8.0
        elif last < sma50:
            sma_adj = -18.0
        else:
            sma_adj = -8.0
    score += sma_adj

    rsi_adj = 0.0
    if rsi is not None:
        if 45.0 <= rsi <= 65.0:
            rsi_adj = 12.0
        elif rsi > 70.0:
            rsi_adj = -10.0
        elif rsi < 30.0:
            rsi_adj = 4.0
        else:
            rsi_adj = 2.0
    score += rsi_adj

    vol_adj = 0.0
    if vol_ratio >= 1.2:
        vol_adj = 8.0
    elif vol_ratio < 0.7:
        vol_adj = -4.0
    score += vol_adj

    market_gate = "PASS"
    spy_pct: float | None = None
    spy_adj = 0.0
    if spy_bars is not None and len(spy_bars) >= 5:
        a = spy_bars[-5][1]
        b = spy_bars[-1][1]
        if a > 0:
            spy_pct = (b - a) / a * 100.0
        # Two independent checks (NOT elif) — both fire below -6%
        if spy_pct is not None and spy_pct < -3.0:
            market_gate = "WATCH"
            spy_adj -= 10.0
        if spy_pct is not None and spy_pct < -6.0:
            market_gate = "NO"
            spy_adj -= 15.0
    score += spy_adj

    score = min(95.0, max(5.0, _round_half_away(score)))

    if market_gate == "NO" or score < 38.0:
        action, label = "NO", "Avoid"
        reason = "Posture is weak or the market gate is blocked — do not force a trade."
    elif score >= 68.0 and -2.0 <= pullback <= 8.0 and (rsi if rsi is not None else 50.0) < 68.0:
        action, label = "SETUP", "Setup zone"
        reason = (
            f"Trend supportive, RSI {(rsi if rsi is not None else 0.0):.0f}, "
            f"pullback {max(0.0, pullback):.1f}% from SMA20."
        )
    else:
        action, label = "WAIT", "Wait & Watch"
        reason = (
            f"Score {score:.0f} — timing not fully aligned "
            f"(RSI {(rsi if rsi is not None else 0.0):.0f})."
        )

    stock_gate = "PASS" if action == "SETUP" else ("NO" if action == "NO" else "WATCH")

    return {
        "score": score,
        "action": action,
        "label": label,
        "reason": reason,
        "market_gate": market_gate,
        "stock_gate": stock_gate,
        "spy_pct": spy_pct,
        "pullback": pullback,
        "rsi": rsi,
        "vol_ratio": vol_ratio,
        "sma20": sma20,
        "sma50": sma50,
        "last": last,
        "adjustments": {
            "trend_sma": sma_adj,
            "momentum_rsi": rsi_adj,
            "volume_price": vol_adj,
            "market_gate": spy_adj,
        },
    }


def is_near_earnings(earnings_date: str | None, today: str) -> bool:
    """0..3 NY calendar days ahead — PostureDepth.isNearEarnings port.

    Dates are ISO strings; day math is calendar-date arithmetic (no tz math
    needed for a 3-day window granularity).
    """
    if not earnings_date:
        return False
    try:
        from datetime import date

        e = date.fromisoformat(str(earnings_date)[:10])
        t = date.fromisoformat(str(today)[:10])
        delta = (e - t).days
        return 0 <= delta <= EARNINGS_WINDOW_DAYS
    except ValueError:
        return False


def apply_post_gates(
    c: dict[str, Any],
    *,
    earnings_near: bool,
    sector_action: str | None,
) -> dict[str, Any]:
    """iOS score() post-processing: earnings window + sector gate overrides."""
    out = dict(c)
    earnings_forced = False
    if earnings_near and out["action"] == "SETUP":
        out["action"] = "WAIT"
        out["label"] = "Wait & Watch"
        out["reason"] = "Earnings within 3 days — radar stays on wait."
        out["stock_gate"] = "WATCH"
        earnings_forced = True
    if sector_action == "NO" and out["action"] == "SETUP":
        out["action"] = "WAIT"
        out["label"] = "Wait & Watch"
        out["reason"] = "Sector posture is blocked — wait even if the stock looks ready."
        out["stock_gate"] = "WATCH"
    out["earnings_forced_wait"] = earnings_forced
    return out


def action_to_signal(action: str) -> str:
    """Map iOS action vocabulary to ENGINE_CONTRACT signals.

    SETUP  → PROBE (gates allow engagement — small/confirm, never "full size")
    WAIT   → WAIT
    NO     → NO
    """
    if action == "SETUP":
        return "PROBE"
    if action == "WAIT":
        return "WAIT"
    return "NO"


def grade_for(action: str, score: float) -> str:
    if action == "SETUP":
        return "A"
    if score >= 55.0:
        return "B"
    return "C"
