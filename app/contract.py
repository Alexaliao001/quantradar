"""ENGINE_CONTRACT v1 — request normalize + charts payload → shell response map.

No scoring formulas here. Scores and gates come only from charts JSON.
"""

from __future__ import annotations

import re
from typing import Any

CONTRACT_VERSION = "1.0.0"

_TICKER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")

SIGNAL_LABELS = {
    "FULL": "Full size",
    "BUILD": "Build",
    "PROBE": "Probe",
    "WAIT": "Wait",
    "NO": "No / stand aside",
    "PUT": "Put / hedge bias",
}


def normalize_request(
    ticker: str | None,
    sector: str | None = None,
    mode: str | None = None,
    request_id: str | None = None,
    contract_version: str | None = None,
) -> dict[str, Any]:
    """Normalize and validate an analyze request. Raises ValueError on bad ticker."""
    if ticker is None or not str(ticker).strip():
        raise ValueError("ticker is required")
    raw = str(ticker).strip().upper()
    if not _TICKER_RE.match(raw):
        raise ValueError(f"invalid ticker: {ticker!r}")
    out: dict[str, Any] = {
        "contract_version": contract_version or CONTRACT_VERSION,
        "ticker": raw,
        "sector": str(sector).strip().upper() if sector else None,
        "context": {
            "mode": (mode or "").strip().lower() or None,
            "request_id": request_id,
        },
    }
    return out


def _chart_paths(indicator_data: dict[str, Any]) -> dict[str, str | None]:
    files = (indicator_data or {}).get("chart_files") or {}
    daily = files.get("daily") or {}
    weekly = files.get("weekly") or {}
    return {
        "daily_price": daily.get("price"),
        "daily_indicators": daily.get("indicators"),
        "weekly_price": weekly.get("price"),
        "weekly_indicators": weekly.get("indicators"),
    }


def map_charts_payload(
    payload: dict[str, Any],
    *,
    mode: str,
    analysis_json_path: str | None = None,
    sources: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Map a real charts fetch_all / *_analysis.json object to ENGINE_CONTRACT response."""
    ticker = str(payload.get("ticker") or "").upper()
    mechanical = payload.get("mechanical_scores") or {}
    state = mechanical.get("state") or {}
    if not isinstance(state, dict):
        state = {}
    data_quality = payload.get("data_quality") or {}
    fundamentals = payload.get("fundamentals") or {}
    market_env = payload.get("market_env") or {}
    indicator_data = payload.get("indicator_data") or {}

    signal = str(
        mechanical.get("signal_timing_gated")
        or mechanical.get("signal_mechanical")
        or "NO"
    )
    warnings = [str(w) for w in (data_quality.get("warnings") or [])]
    reliability = str(data_quality.get("reliability") or "unknown")
    degraded = reliability in {"low", "poor"} or bool(warnings)

    base = mechanical.get("base_score") or {}
    base_total = base.get("total") if isinstance(base, dict) else None
    final = mechanical.get("final_score")
    if final is None:
        final = 0
        if "score missing from charts payload" not in warnings:
            warnings.append("score missing from charts payload")
            degraded = True

    default_sources = sources or [
        {"name": "charts", "role": "engine", "status": "ok" if not degraded else "degraded"},
    ]

    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "ticker": ticker,
        "company_name": fundamentals.get("company_name") or ticker,
        "sector": fundamentals.get("sector") or market_env.get("sector_etf"),
        "gate": {
            "state_code": state.get("code"),
            "state_name": state.get("name"),
            "state_reason": state.get("reason"),
            "signal": signal,
            "signal_label": SIGNAL_LABELS.get(signal, signal),
        },
        "score": {
            "final": float(final),
            "base_total": float(base_total) if base_total is not None else None,
            "scale": 100,
        },
        "artifacts": {
            "charts": _chart_paths(indicator_data if isinstance(indicator_data, dict) else {}),
            "analysis_json": analysis_json_path,
            "report_html": None,
        },
        "sources": default_sources,
        "warnings": warnings,
        "degraded": degraded,
        "market": {
            "market_state": market_env.get("market_state"),
            "spy_change_pct": market_env.get("spy_change_pct"),
            "sector_etf": market_env.get("sector_etf"),
            "sector_change_pct": market_env.get("sector_change_pct"),
            "vix_current": market_env.get("vix_current"),
            "vix_trend": market_env.get("vix_trend"),
        },
        "meta": {
            "engine": "charts",
            "mode": mode,
            "fetch_time": payload.get("fetch_time"),
            "generated_at": (indicator_data or {}).get("generated_at")
            if isinstance(indicator_data, dict)
            else None,
            "reliability": reliability,
        },
    }


def validate_response(obj: Any) -> list[str]:
    """Return list of contract violations (empty = valid). Stdlib-only structural check."""
    errors: list[str] = []
    if not isinstance(obj, dict):
        return ["response must be an object"]
    for key in (
        "ok",
        "contract_version",
        "ticker",
        "gate",
        "score",
        "artifacts",
        "sources",
        "warnings",
    ):
        if key not in obj:
            errors.append(f"missing required field: {key}")
    if "ok" in obj and not isinstance(obj["ok"], bool):
        errors.append("ok must be boolean")
    if obj.get("contract_version") in (None, ""):
        errors.append("contract_version must be non-empty")
    if obj.get("ticker") in (None, ""):
        errors.append("ticker must be non-empty")
    gate = obj.get("gate")
    if not isinstance(gate, dict):
        errors.append("gate must be object")
    elif not (gate.get("signal") or gate.get("state_code")):
        errors.append("gate must include signal or state_code")
    score = obj.get("score")
    if not isinstance(score, dict):
        errors.append("score must be object")
    else:
        if "final" not in score or not isinstance(score["final"], (int, float)):
            errors.append("score.final must be a number")
        if "scale" not in score or not isinstance(score["scale"], (int, float)):
            errors.append("score.scale must be a number")
    artifacts = obj.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be object")
    elif "charts" not in artifacts or not isinstance(artifacts["charts"], dict):
        errors.append("artifacts.charts must be object")
    if "sources" in obj and not isinstance(obj["sources"], list):
        errors.append("sources must be array")
    if "warnings" in obj and not isinstance(obj["warnings"], list):
        errors.append("warnings must be array")
    return errors
