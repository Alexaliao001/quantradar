"""行情加载：默认 fixture；live 仅在授权后走 Tushare。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app import config


def _symbol_path(symbol: str) -> Path:
    return config.FIXTURES / "ohlcv" / f"{symbol}.json"


def load_fixture(symbol: str) -> dict[str, Any] | None:
    path = _symbol_path(symbol)
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_bars(symbol: str, mode: str | None = None) -> dict[str, Any] | None:
    mode = (mode or config.MODE).lower()
    if mode == "live" and config.live_eligible():
        live = _load_tushare(symbol)
        if live is not None:
            return live
        # fail-closed：live 失败不静默编造
        return None
    return load_fixture(symbol)


def _load_tushare(symbol: str) -> dict[str, Any] | None:
    """可选依赖：未安装或失败则返回 None。"""
    try:
        import tushare as ts  # type: ignore
    except Exception:
        return None
    try:
        pro = ts.pro_api(config.TUSHARE_TOKEN)
        ts_code = _to_ts_code(symbol)
        df = pro.daily(ts_code=ts_code, limit=120)
        if df is None or df.empty:
            return None
        basic = pro.stock_basic(ts_code=ts_code, fields="ts_code,name,market,list_status")
        name = str(basic.iloc[0]["name"]) if basic is not None and not basic.empty else symbol
        bars = []
        for _, row in df.sort_values("trade_date").iterrows():
            bars.append(
                {
                    "date": str(row["trade_date"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["vol"]),
                }
            )
        return {
            "symbol": symbol,
            "name": name,
            "market": "A",
            "is_st": "ST" in name.upper(),
            "is_star_or_chinext": ts_code.startswith("688") or ts_code.startswith("300"),
            "bars": bars,
            "source": "tushare",
        }
    except Exception:
        return None


def _to_ts_code(symbol: str) -> str:
    if symbol.startswith("6"):
        return f"{symbol}.SH"
    if symbol.startswith(("0", "3")):
        return f"{symbol}.SZ"
    if symbol.startswith(("4", "8")):
        return f"{symbol}.BJ"
    return f"{symbol}.SH"
