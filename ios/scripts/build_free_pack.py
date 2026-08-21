#!/usr/bin/env python3
"""Optional: build a zero-cost daily JSON pack via yfinance for static hosting (GitHub Pages).

Does NOT use Massive/Polygon. Free for publishing to users; run on your Mac or free CI.

  python3 ios/scripts/build_free_pack.py --tickers AAPL,NVDA,SPY -o ios/pack/today.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def score_closes(closes: list[float], volumes: list[float]) -> dict:
    def sma(n: int) -> float:
        if len(closes) < n:
            return 0.0
        return sum(closes[-n:]) / n

    last = closes[-1]
    s20, s50 = sma(20), sma(50)
    # RSI14
    gains = losses = 0.0
    for i in range(-14, 0):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    ag, al = gains / 14, losses / 14
    rsi = 100.0 if al == 0 else 100 - (100 / (1 + ag / al))
    vol_sma = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 1.0
    vol_ratio = (volumes[-1] / vol_sma) if vol_sma else 1.0

    score = 50.0
    if last > s20 > s50 > 0:
        score += 18
    elif last > s20 > 0:
        score += 8
    elif s50 > 0 and last < s50:
        score -= 18
    if 45 <= rsi <= 65:
        score += 12
    elif rsi > 70:
        score -= 10
    if vol_ratio >= 1.2:
        score += 8
    score = max(5, min(95, round(score)))

    if score < 38:
        action, label = "NO", "Avoid"
    elif score >= 68 and rsi < 68:
        action, label = "BUY", "Setup watch → actionable zone"
    else:
        action, label = "WAIT", "Wait & Watch"

    return {
        "primary_score": {"value": score, "scale": 100, "label": "Mechanical posture score", "withheld": False},
        "primary": {"action": action, "label": label, "reason": f"Pack RSI={rsi:.0f} score={score}"},
        "meta": {"mode": "free_pack", "data_path": "yfinance_pack", "disclaimer": "Educational only."},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", default="SPY,QQQ,AAPL,NVDA,TSLA,INTC")
    ap.add_argument("-o", "--output", default="ios/pack/today.json")
    args = ap.parse_args()
    try:
        import yfinance as yf
    except ImportError as e:
        raise SystemExit("pip install yfinance") from e

    out: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "yfinance",
        "massive": False,
        "tickers": {},
    }
    for t in [x.strip().upper() for x in args.tickers.split(",") if x.strip()]:
        hist = yf.Ticker(t).history(period="1y", interval="1d")
        if hist.empty or len(hist) < 40:
            continue
        closes = [float(x) for x in hist["Close"].tolist()]
        volumes = [float(x) for x in hist["Volume"].tolist()]
        payload = score_closes(closes, volumes)
        payload["ticker"] = t
        payload["ok"] = True
        out["tickers"][t] = payload
        print(t, payload["primary"]["action"], payload["primary_score"]["value"])

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    print("wrote", path, "count", len(out["tickers"]))


if __name__ == "__main__":
    main()
