"""Free engine tests — iOS formula parity, aggregation, contract fit."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "free_engine"))

from app.contract import map_charts_payload, validate_response  # noqa: E402
from app.quality import assess_charts_payload  # noqa: E402
from free_aggregate import aggregate_bars  # noqa: E402
from free_mechanical import (  # noqa: E402
    action_to_signal,
    apply_post_gates,
    core,
    etf_for_sector,
    pct_change_over,
    rsi14,
    sma,
)


def bars_seq(closes, volumes=None, start="2026-01-01"):
    from datetime import date, timedelta

    d = date.fromisoformat(start)
    out = []
    for i, c in enumerate(closes):
        v = volumes[i] if volumes else 1_000_000.0
        out.append(((d + timedelta(days=i)).isoformat(), float(c), float(v)))
    return out


def uptrend_closes():
    """Searched fixture: 45-day gentle rise + shaped 14-delta tail.

    Hand-verified against the iOS formula: +18 trend (last>sma20>sma50),
    +12 momentum (RSI 63.2 ∈ 45..65), +8 volume (ratio 1.5), pullback −0.16%,
    RSI < 68 → final 88, action SETUP.
    """
    closes = [100.0 + i * 0.3 for i in range(45)]
    v = closes[-1]
    for d in [0.9] * 8 + [-0.7] * 6:
        v += d
        closes.append(v)
    return closes


def uptrend_vols():
    return [1e6] * 58 + [1.5e6]


class SMARSITests(unittest.TestCase):
    def test_sma_needs_n(self) -> None:
        self.assertEqual(sma([1.0, 2.0], 3), 0.0)
        self.assertAlmostEqual(sma([1.0, 2.0, 3.0], 3), 2.0)
        # suffix(n) semantics
        self.assertAlmostEqual(sma([10.0, 1.0, 2.0, 3.0], 3), 2.0)

    def test_rsi14_slice_of_15(self) -> None:
        # 16 closes → window is last 15 → 14 deltas, all +1 → RSI 100
        closes = [100.0 + i for i in range(16)]
        self.assertAlmostEqual(rsi14(closes), 100.0)
        # exactly 15 closes → None (Swift: closes.count > 15)
        self.assertIsNone(rsi14(closes[:15]))
        # all down → avg_loss>0, avg_gain=0 → rs=0 → RSI 0
        down = [100.0 - i for i in range(16)]
        self.assertAlmostEqual(rsi14(down), 0.0)


class CoreParityTests(unittest.TestCase):
    """Each case hand-computed from the iOS FreeMechanicalScorer formula."""

    def test_uptrend_setup(self) -> None:
        closes = uptrend_closes()
        c = core(bars_seq(closes, uptrend_vols()), None)
        # +18 trend, +12 momentum, +8 volume → 88
        self.assertEqual(c["score"], 88.0)
        self.assertEqual(c["adjustments"]["trend_sma"], 18.0)
        self.assertEqual(c["adjustments"]["momentum_rsi"], 12.0)
        self.assertEqual(c["adjustments"]["volume_price"], 8.0)
        self.assertEqual(c["market_gate"], "PASS")
        # SETUP needs score>=68, pullback in [-2, 8], rsi<68
        self.assertEqual(c["action"], "SETUP")
        self.assertEqual(c["stock_gate"], "PASS")

    def test_downtrend_no(self) -> None:
        closes = [200.0 - i * 1.2 for i in range(60)]
        c = core(bars_seq(closes), None)
        # last < sma50 → -18; rsi low → +4; vol flat → 0 → 36 < 38 → NO
        self.assertEqual(c["score"], 36.0)
        self.assertEqual(c["action"], "NO")
        self.assertEqual(c["stock_gate"], "NO")

    def test_spy_gate_thresholds(self) -> None:
        flat = bars_seq(uptrend_closes(), uptrend_vols())
        # SPY down 4% over the 5-bar window → WATCH, -10
        spy_down4 = bars_seq([100.0, 100.0, 100.0, 100.0, 96.0])
        c = core(flat, spy_down4)
        self.assertEqual(c["market_gate"], "WATCH")
        self.assertEqual(c["adjustments"]["market_gate"], -10.0)
        # SPY down 7% → NO gate (-10 and -15 stack = -25)
        spy_down7 = bars_seq([100.0, 100.0, 100.0, 100.0, 93.0])
        c2 = core(flat, spy_down7)
        self.assertEqual(c2["market_gate"], "NO")
        self.assertEqual(c2["adjustments"]["market_gate"], -25.0)
        self.assertEqual(c2["action"], "NO")

    def test_pct_change_over_ios_window(self) -> None:
        # iOS: spy[count-5] vs spy.last → 5 bars, 4 intervals
        spy = bars_seq([100.0, 101.0, 102.0, 103.0, 104.0])
        self.assertAlmostEqual(pct_change_over(spy, 5), (104.0 - 100.0))
        self.assertIsNone(pct_change_over(spy[:4], 5))

    def test_earnings_gate_flips_setup_to_wait(self) -> None:
        c = core(bars_seq(uptrend_closes(), uptrend_vols()), None)
        self.assertEqual(c["action"], "SETUP")
        gated = apply_post_gates(c, earnings_near=True, sector_action=None)
        self.assertEqual(gated["action"], "WAIT")
        self.assertTrue(gated["earnings_forced_wait"])
        self.assertEqual(gated["stock_gate"], "WATCH")

    def test_sector_no_blocks_setup(self) -> None:
        c = core(bars_seq(uptrend_closes(), uptrend_vols()), None)
        gated = apply_post_gates(c, earnings_near=False, sector_action="NO")
        self.assertEqual(gated["action"], "WAIT")

    def test_clamp_bounds(self) -> None:
        up = bars_seq(uptrend_closes(), uptrend_vols())
        self.assertLessEqual(core(up, None)["score"], 95.0)
        self.assertGreaterEqual(core(up, None)["score"], 5.0)


class AggregationTests(unittest.TestCase):
    def test_median_voting(self) -> None:
        a = [("2026-01-02", 100.0, 1e6), ("2026-01-03", 101.0, 1e6)]
        b = [("2026-01-02", 100.0, 1e6), ("2026-01-03", 101.0, 1e6)]
        glitch = [("2026-01-02", 55.0, 1e6)]  # glitched close, 1 of 3
        agg = aggregate_bars({"s1": a, "s2": b, "s3": glitch})
        day1 = agg["bars"][0]
        self.assertAlmostEqual(day1[1], 100.0)  # median resists the glitch
        self.assertEqual(agg["days"], 2)

    def test_disagree_flag(self) -> None:
        a = [("2026-01-02", 100.0, 1e6)]
        b = [("2026-01-02", 110.0, 1e6)]  # 10% spread
        agg = aggregate_bars({"s1": a, "s2": b})
        self.assertEqual(agg["disagree_days"], ["2026-01-02"])
        self.assertAlmostEqual(agg["bars"][0][1], 105.0)

    def test_single_source_kept(self) -> None:
        agg = aggregate_bars({"s1": [("2026-01-02", 50.0, 1.0)]})
        self.assertEqual(agg["days"], 1)


class ContractFitTests(unittest.TestCase):
    def test_engine_payload_shape(self) -> None:
        from free_engine.fetch_all import MIN_BARS  # noqa: F401 (import check)

        closes = uptrend_closes()
        bars = bars_seq(closes, uptrend_vols())
        # Build the same structural payload the engine emits (no network)
        c = core(bars, None)
        signal = action_to_signal(c["action"])
        state = {"code": "A", "name": "setup_zone", "reason": c["reason"]}
        payload = {
            "ticker": "TESTCO",
            "fetch_time": "2026-09-01T00:00:00+00:00",
            "data_quality": {
                "reliability": "high",
                "timeframes_ok": 1,
                "option_chain_ok": False,
                "warnings": [],
            },
            "mechanical_scores": {
                "final_score": c["score"],
                "signal_mechanical": signal,
                "state": state,
                "base_score": {
                    "total": 88.0,
                    "trend": {"total": 43.0, "max": 50.0},
                    "momentum": {"total": 37.0, "max": 50.0},
                    "volume_price": {
                        "total": 33.0,
                        "max": 50.0,
                        "volume_ratio": c["vol_ratio"],
                    },
                },
                "entry_timing": {"grade": "A", "total": c["score"], "max": 100.0},
            },
            "indicator_data": {},
            "market_env": {"spy_change_pct": -0.2},
            "fundamentals": {},
            "market_context": {},
        }
        self.assertEqual(signal, "PROBE")
        q = assess_charts_payload(payload, "TESTCO")
        self.assertTrue(q["usable"], q)
        resp = map_charts_payload(payload, mode="live", quality=q)
        self.assertTrue(resp["ok"])
        self.assertEqual(validate_response(resp), [])
        self.assertEqual(resp["primary"]["action"], "PROBE")
        self.assertFalse(resp["data_quality"]["options_actionable"])

    def test_signal_mapping(self) -> None:
        self.assertEqual(action_to_signal("SETUP"), "PROBE")
        self.assertEqual(action_to_signal("WAIT"), "WAIT")
        self.assertEqual(action_to_signal("NO"), "NO")

    def test_sector_etf_map_matches_ios(self) -> None:
        self.assertEqual(etf_for_sector("Technology"), "XLK")
        self.assertEqual(etf_for_sector("Consumer Discretionary"), "XLY")
        self.assertEqual(etf_for_sector("Consumer Defensive"), "XLP")
        self.assertEqual(etf_for_sector("Real Estate"), "XLRE")
        self.assertEqual(etf_for_sector("Communication Services"), "XLC")
        self.assertIsNone(etf_for_sector("Crypto Mining"))
        self.assertIsNone(etf_for_sector(None))


if __name__ == "__main__":
    unittest.main()
