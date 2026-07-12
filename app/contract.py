"""ENGINE_CONTRACT v1 — request normalize + charts payload → shell response map.

No scoring formulas here. Scores and gates come only from charts JSON.
"""

from __future__ import annotations

import re
from typing import Any

from app.quality import (
    assess_charts_payload,
    canonicalize_ticker,
    extract_options_snapshot,
    extract_volume_snapshot,
    is_blocked_ticker,
)

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
    raw = canonicalize_ticker(str(ticker))
    if not _TICKER_RE.match(raw):
        raise ValueError(f"invalid ticker: {ticker!r}")
    if is_blocked_ticker(raw):
        raise ValueError(f"invalid or placeholder ticker: {raw}")
    out: dict[str, Any] = {
        "contract_version": contract_version or CONTRACT_VERSION,
        "ticker": raw,
        "sector": canonicalize_ticker(str(sector)) if sector else None,
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
    quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map a real charts fetch_all / *_analysis.json object to ENGINE_CONTRACT response."""
    ticker = canonicalize_ticker(str(payload.get("ticker") or ""))
    mechanical = payload.get("mechanical_scores") or {}
    state = mechanical.get("state") or {}
    if not isinstance(state, dict):
        state = {}
    data_quality = payload.get("data_quality") or {}
    fundamentals = payload.get("fundamentals") or {}
    market_env = payload.get("market_env") or {}
    indicator_data = payload.get("indicator_data") or {}

    q = quality if quality is not None else assess_charts_payload(payload, ticker)
    vol = q.get("volume") or extract_volume_snapshot(payload)
    opt = q.get("options") or extract_options_snapshot(payload)

    signal = str(
        mechanical.get("signal_timing_gated")
        or mechanical.get("signal_mechanical")
        or "NO"
    )
    warnings = [str(w) for w in (q.get("warnings") or [])]
    # de-dupe while preserving order
    seen: set[str] = set()
    uniq_warnings: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            uniq_warnings.append(w)
    warnings = uniq_warnings

    reliability = str(
        q.get("reliability") or data_quality.get("reliability") or "unknown"
    )
    volume_narrative_allowed = True
    if vol.get("volume_zero_flag"):
        volume_narrative_allowed = False
    elif vol.get("volume_unavailable") and vol.get("volume_ratio") is None:
        volume_narrative_allowed = False

    options_actionable = bool(opt.get("options_actionable"))
    degraded = reliability in {"low", "poor"} or bool(warnings)
    if not volume_narrative_allowed:
        degraded = True
    if opt.get("options_simulated"):
        degraded = True

    base = mechanical.get("base_score") or {}
    base_total = base.get("total") if isinstance(base, dict) else None
    final = mechanical.get("final_score")
    if final is None:
        final = 0
        if "score missing from charts payload" not in warnings:
            warnings.append("score missing from charts payload")
            degraded = True

    default_sources = sources or [
        {
            "name": "charts",
            "role": "engine",
            "status": "ok" if not degraded else "degraded",
        },
    ]

    # Single primary conclusion — never dual buy + wait
    primary_action = signal if signal in SIGNAL_LABELS else "NO"
    primary_label = SIGNAL_LABELS.get(primary_action, primary_action)

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
            "primary": primary_action,
            "market_gate": {
                "status": "pass" if market_env else "unknown",
                "spy_change_pct": market_env.get("spy_change_pct"),
                "market_state": market_env.get("market_state"),
            },
            "sector_gate": {
                "status": "pass"
                if market_env.get("sector_etf") or market_env.get("sector_change_pct") is not None
                else "unavailable",
                "sector_etf": market_env.get("sector_etf"),
                "sector_change_pct": market_env.get("sector_change_pct"),
            },
        },
        "score": {
            "final": float(final),
            "base_total": float(base_total) if base_total is not None else None,
            "scale": 100,
            "withheld": False,
        },
        # TG-1: only public-facing composite. UI must not invent sibling "Composite" scores.
        "primary_score": {
            "value": float(final),
            "scale": 100,
            "label": "Mechanical posture score",
            "withheld": False,
            "note": "Single authoritative score from charts. Not a multi-panel composite mix.",
        },
        "primary": {
            "action": primary_action,
            "label": primary_label,
            "reason": state.get("reason") or primary_label,
        },
        "summary": (
            f"{ticker} — Score: {float(final):.0f}/100 · "
            f"Primary: {primary_label}"
            + (f" · {state.get('name')}" if state.get("name") else "")
        ),
        "data_quality": {
            "usable": True,
            "reliability": reliability,
            "volume_narrative_allowed": volume_narrative_allowed,
            "volume": vol,
            "options_actionable": options_actionable,
            "options": opt,
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
            "score_withheld": False,
            "primary": primary_action,
            "disclaimer": "Educational radar only — not investment advice.",
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

    ok = obj.get("ok")
    gate = obj.get("gate")
    if not isinstance(gate, dict):
        errors.append("gate must be object")
    elif not (gate.get("signal") or gate.get("state_code")):
        errors.append("gate must include signal or state_code")

    score = obj.get("score")
    if not isinstance(score, dict):
        errors.append("score must be object")
    else:
        final = score.get("final")
        withheld = bool(score.get("withheld")) or ok is False
        if final is None:
            if not withheld:
                errors.append("score.final must be a number unless withheld/ok=false")
        elif not isinstance(final, (int, float)):
            errors.append("score.final must be a number")
        if "scale" not in score or not isinstance(score["scale"], (int, float)):
            errors.append("score.scale must be a number")

    # P0: never emit actionable buy-like signals for hard failures
    if ok is False:
        if not obj.get("error"):
            errors.append("ok=false requires error")
        if looks_like_fake_buy(obj):
            errors.append("ok=false must not look like a buy recommendation with score")
        primary = (
            (obj.get("primary") or {}).get("action")
            if isinstance(obj.get("primary"), dict)
            else None
        )
        gate_sig = gate.get("signal") if isinstance(gate, dict) else None
        if primary and primary not in (None, "NO", "WAIT"):
            errors.append("ok=false primary.action must be NO or WAIT")
        if gate_sig and gate_sig not in (None, "NO", "WAIT"):
            errors.append("ok=false gate.signal must be NO or WAIT")

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


def looks_like_fake_buy(obj: dict[str, Any]) -> bool:
    """True if a failed/no-data response still looks like a buy call (P0)."""
    score = obj.get("score") if isinstance(obj.get("score"), dict) else {}
    final = score.get("final")
    if score.get("withheld") or final is None:
        return False
    try:
        score_n = float(final)
    except (TypeError, ValueError):
        return False
    if score_n < 50:
        return False
    sig = str((obj.get("gate") or {}).get("signal") or "").upper()
    primary = ""
    if isinstance(obj.get("primary"), dict):
        primary = str(obj["primary"].get("action") or "").upper()
    bullish = {"FULL", "BUILD", "PROBE", "BUY", "LONG"}
    return sig in bullish or primary in bullish
