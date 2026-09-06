"""Immutable, dated mechanical replay and downloadable daily charts."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import zipfile

from free_engine.free_mechanical import core
from free_engine.market_calendar import session_window

FORMULA_VERSION = "mechanical-2-market-required"
CSV_FIELDS = ("date", "close", "volume", "score", "action", "market_gate", "rsi14", "sma20", "sma50", "note")


def build_replay(payload: dict, *, sessions: int = 90, cutoff: str | None = None) -> list[dict]:
    cutoff = cutoff or payload["data_quality"]["market_as_of"]
    bars = [tuple(row) for row in payload.get("daily_bars", []) if row[0] <= cutoff]
    spy = [tuple(row) for row in payload.get("spy_daily_bars", []) if row[0] <= cutoff]
    dates = session_window(cutoff, sessions)
    if dates is None:
        raise ValueError("calendar coverage unavailable for requested replay")
    out = []
    for day in dates:
        window = session_window(day, 50)
        stock_slice = [row for row in bars if row[0] <= day]
        spy_slice = [row for row in spy if row[0] <= day]
        row = {key: None for key in CSV_FIELDS}
        row.update(date=day, action="UNKNOWN", market_gate="UNKNOWN", note="Missing or incomplete daily history")
        if stock_slice and stock_slice[-1][0] == day:
            row.update(close=stock_slice[-1][1], volume=stock_slice[-1][2])
        if window and [b[0] for b in stock_slice[-50:]] == window:
            expected_spy = session_window(day, 5)
            if [b[0] for b in spy_slice[-5:]] != expected_spy:
                spy_slice = []
            result = core(stock_slice, spy_slice or None)
            row.update(score=result["score"], action=result["action"], market_gate=result["market_gate"],
                       rsi14=result["rsi"], sma20=result["sma20"], sma50=result["sma50"],
                       note="Mechanical reconstruction; historical earnings and sector gates unavailable")
        out.append(row)
    return out


def _line_chart(title: str, rows: list[dict], series: list[tuple[str, str]], *, fixed_range=None) -> str:
    width, height = 960, 340
    values = [r[key] for r in rows for key, _ in series if r.get(key) is not None]
    low, high = fixed_range or (min(values, default=0), max(values, default=1))
    span = high - low or 1
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
             f'<title id="title">{html.escape(title)}</title>',
             '<rect width="960" height="340" fill="#0b1420"/>',
             f'<text x="48" y="30" fill="#ffffff" font-family="sans-serif" font-size="18">{html.escape(title)}</text>',
             '<path d="M48 54 V286 H936" stroke="#738397" fill="none"/>']
    for key, color in series:
        segment = []
        for i, row in enumerate(rows):
            value = row.get(key)
            if value is None:
                if segment:
                    parts.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="2"/>')
                segment = []
            else:
                x = 48 + 888 * i / max(1, len(rows) - 1)
                y = 280 - 220 * (value - low) / span
                segment.append(f"{x:.2f},{y:.2f}")
        if segment:
            parts.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="2"/>')
    for y, value in ((65, high), (280, low)):
        parts.append(f'<text x="4" y="{y}" fill="#adbccc" font-size="11">{value:.1f}</text>')
    if rows:
        for x, day in ((48, rows[0]["date"]), (850, rows[-1]["date"])):
            parts.append(f'<text x="{x}" y="310" fill="#adbccc" font-family="sans-serif" font-size="12">{day}</text>')
    legend = " · ".join(key for key, _ in series)
    parts.append(f'<text x="48" y="333" fill="#adbccc" font-size="11">{html.escape(legend)}</text></svg>')
    return "".join(parts)


def build_report_bundle(payload: dict, *, include_csv: bool = False) -> dict:
    from app.contract import map_charts_payload
    from app.quality import assess_charts_payload

    ticker = payload["ticker"]
    cutoff = payload["data_quality"]["market_as_of"]
    replay = build_replay(payload, cutoff=cutoff)
    if len(replay) != 90 or any(row["close"] is None or row["score"] is None for row in replay):
        raise ValueError("A full report requires 139 consecutive completed trading sessions")
    quality = assess_charts_payload(payload, ticker)
    if not quality["usable"]:
        raise ValueError("Snapshot did not pass the data quality gate")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report = {
        "report_version": 2, "formula_version": FORMULA_VERSION, "ticker": ticker, "as_of": cutoff,
        "input_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "snapshot": map_charts_payload(payload, mode="live", quality=quality),
        "replay": replay, "inputs": payload,
        "notes": ["Reconstructed daily mechanical posture, not previously published signals or trading performance.",
                  "Historical earnings and sector gates are unavailable; today's fundamentals are not applied to past sessions.",
                  "Daily close and volume only. No invented candles, intraday charts or options data.",
                  "Data vendors may revise historical prices; this purchased snapshot remains fixed."],
    }
    assets = {"report.json": json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)}
    assets["price.svg"] = _line_chart(f"{ticker} · daily close / SMA20 / SMA50", replay,
                                       [("close", "#50e3ad"), ("sma20", "#7aa7ff"), ("sma50", "#f6bb60")])
    assets["rsi.svg"] = _line_chart(f"{ticker} · RSI14", replay, [("rsi14", "#7aa7ff")], fixed_range=(0, 100))
    assets["volume.svg"] = _line_chart(f"{ticker} · daily volume", replay, [("volume", "#50e3ad")])
    colors = {"SETUP": "#50e3ad", "WAIT": "#f6bb60", "NO": "#ee6e7d", "UNKNOWN": "#738397"}
    cells = "".join(f'<rect x="{i*10}" y="32" width="9" height="36" fill="{colors[r["action"]]}"><title>{r["date"]}: {r["action"]}</title></rect>' for i, r in enumerate(replay))
    assets["posture.svg"] = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 100" role="img"><title>90-session reconstructed posture</title><rect width="900" height="100" fill="#0b1420"/><text x="0" y="20" fill="white" font-size="14">SETUP green · WAIT amber · NO red · UNKNOWN gray</text>' + cells + '</svg>'
    if include_csv:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(replay)
        assets["replay.csv"] = output.getvalue()
    return {"ticker": ticker, "as_of": cutoff, "sessions": len(replay), "assets": assets,
            "input_sha256": report["input_sha256"], "formula_version": FORMULA_VERSION}


def zip_bundle(bundle: dict) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, text in bundle["assets"].items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text.encode("utf-8"))
    return output.getvalue()
